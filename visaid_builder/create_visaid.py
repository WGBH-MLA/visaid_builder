"""
create_visaid.py

Defines a function for creating a visaid from a list of scene TimeFrames.

The main required parameters are the path to the video file and a table
(list of lists) in the style of the `tfs` tables created by the proc_swt module.

This function reads and depends on the display ingredients in these files:
   visaid_ingredients/visaid_embedded_logic.js
   visaid_ingredients/visaid_embedded_styles.css
   visaid_ingredients/visaid_structure.html
"""

import os
import io
import base64
import json
import logging

import av

from importlib.metadata import version

__version__ = version("visaid_builder")
from . import lilhelp

VISAID_DEFAULTS = { "deselected_scene_types": ["filmed text", "person with extra text"],
                    "job_id_in_visaid_filename": False,
                    "display_video_duration": True,
                    "display_job_info": True,
                    "display_image_ms": True,
                    "aapb_timecode_link": False,
                    "max_img_height": 360 }

STRETCH_THRESHOLD = 0.01

# These are scene types (optionally) created by `proc_swt`, not defined by the 
# SWT bins.  They are displayed in a different area of the page layout.
SPECIAL_SCENE_TYPES = [ "first frame checked", 
                        "last frame checked", 
                        "unlabeled sample"] 


def create_visaid( video_path:str, 
                   tfs:list,
                   stdout:bool = False,
                   output_dirname:str = ".",
                   hfilename:str = "",
                   job_id:str = None,
                   job_name:str = None,
                   item_id:str = "",
                   item_name:str = "",
                   proc_swt_params:dict = {},
                   visaid_params:dict = {},
                   mmif_metadata_str: str = ""
                   ):                  
    """
    Creates an HTML file (with embedded images) as a visual aid, based on the output
    of `list_tfs`s.

    """

    problems = []
    infos = []

    # Warn about spurious parameter keys
    for key in visaid_params:
        if key not in VISAID_DEFAULTS:
            if not stdout:
                logging.warning("Warning: `" + key + "` is not a valid visaid option. Ignoring.")
            problems.append("invalid-visaid_param")

    # Process parameters, using defaults where appropriate
    params = {}
    for key in VISAID_DEFAULTS:
        if key in visaid_params:
            params[key] = visaid_params[key]
        else:
            params[key] = VISAID_DEFAULTS[key]

    # Consruct output visaid filename
    if hfilename == "":
        if item_id:
            prefix = item_id + "_"
        else:
            prefix = ""
        if params["job_id_in_visaid_filename"]:
            suffix = "_" + str(job_id)
        else:
            suffix = ""
        hfilename = prefix + "visaid" + suffix + ".html"

    # Construct video name/identifier string to display in visaid
    video_fname = video_path[video_path.rfind("/")+1:]
    if item_name:
        video_identifier = item_name
    elif item_id:
        video_identifier = item_id
    else:
        video_identifier = video_fname

    # 
    # Begin analyzing video in terms of tfs table
    #

    # find the first video stream
    container = av.open(video_path)
    video_stream = next((s for s in container.streams if s.type == 'video'), None)
    if video_stream is None:
        raise Exception("No video stream found in {}".format(video_path) ) 

    # get technical stats on the video stream; assumes FPS is constant
    fps = video_stream.average_rate.numerator / video_stream.average_rate.denominator

    # determine whether anamorphic stills will need to be stretched
    if video_stream.sample_aspect_ratio is not None:
        sar = float(video_stream.sample_aspect_ratio)
    else:
        # If SAR cannot be determined, assume it is 1
        sar = 1.0

    if abs( 1 - sar ) > STRETCH_THRESHOLD:
        stretch = True
        if not stdout:
            logging.info(f'Sample aspect ratio: {sar:.3f}. Will stretch anamorphic frames.')
        infos.append(f'SAR-{sar:.3f}')
    else:
        stretch = False

    # calculate duration in ms
    media_length = int((video_stream.frames / fps) * 1000)

    # Table like tfs, but with an extra columns. 
    # Uses rows from the tfs table, but adds additional columns for actual frame 
    # time and base64 image data.

    tfsi = []

    # Build up tfsi table by adding rows based on tfs rows.
    if len(tfs) > 0:

        # Create a new list sorted in order of rep frame times .
        # Because we need to proceed in order of video frames to be extracted
        # (not necessarily the order of the scene start times).
        tfs_s = sorted(tfs, key=lambda f:f[4])

        # initialize target scene and still 
        next_scene = 0 
        target_time = tfs_s[next_scene][4]
        last_packet_error = 0
      
        # looping through packets instead of frames allows exception handling for each
        # particular decode step.  This main loop originally iterated over frames in
        # `container.decode(video_stream)`.
        for packet in container.demux(video_stream):
            try:
                for frame in packet.decode():
                    ftime = int(frame.time * 1000)   

                    # look for the frame nearest to the target
                    if ftime+15 >= target_time :
                        
                        # Check for anamorphic and stretch if necessary
                        if stretch:
                            if sar > 1.0:
                                # stretch the width
                                new_width = int( sar * frame.width)
                                new_height = frame.height
                            else:
                                # stretch the height
                                new_width = frame.width
                                new_height = int(frame.height / sar)
                            stretched_frame = frame.reformat( width=new_width, height=new_height )
                        else:
                            stretched_frame = frame

                        # Reduce the size of the image, if necessary
                        if stretched_frame.height > params["max_img_height"]:
                            res_factor = params["max_img_height"] / stretched_frame.height 
                            new_width = int(stretched_frame.width * res_factor)
                            res_frame = stretched_frame.reformat( width=new_width, height=params["max_img_height"] )
                        else:
                            res_frame = stretched_frame

                        # Save frame to memory buffer
                        buf = io.BytesIO()
                        res_frame.to_image().save(buf, format="JPEG", quality=75)

                        # convert binary image data to base64 serialized in a UTF-8 string
                        img_str = base64.b64encode(buf.getvalue()).decode('utf-8')

                        # add new row to tfsi
                        tfsi.append(tfs_s[next_scene] + [ ftime ] + [ img_str ] )
                        
                        next_scene += 1
                        if next_scene >= len(tfs_s):            
                            # no need to continue decoding video if we have all our scenes saved
                            break
                        else:
                            target_time = tfs_s[next_scene][4]

            except av.error.InvalidDataError as e:
                # This exception may get raised many times if there are many packets with problems
                # However, we'll log only one error per (starting) time stamp of corrupt region.
                if last_packet_error != ftime:
                    if not stdout:
                        logging.warning(f"{video_fname} at {ftime} ms: {e}")
                    last_packet_error = ftime
                if "decode" not in problems:
                    problems.append("decode")
                continue  # Skip this packet and try the next one

            if next_scene >= len(tfs_s):
                # no need to continue decoding video if we have all our scenes saved
                break

    # Done with the video media itself
    container.close()

    # Re-sort new array in terms of scene start time, then by TimeFrame id,
    # (so that subsamples come after the scenes from which they've been sampled.)
    tfsi.sort(key=lambda f:(f[2],f[0]))

    # Get ingredient code strings for inclusion in HTML files
    py_dir = os.path.dirname(__file__)
    ingredients_dir = os.path.join(py_dir, "visaid_ingredients")

    css_path = os.path.join(ingredients_dir, "visaid_embedded_styles.css")
    with open(css_path, "r") as css_file:
        css_str = css_file.read()

    js_path = os.path.join(ingredients_dir, "visaid_embedded_logic.js")
    with open(js_path, "r") as js_file:
        js_str = js_file.read()

    html_path = os.path.join(ingredients_dir, "visaid_structure.html")
    with open(html_path, "r") as html_file:
        structure_str = html_file.read()

    #
    # Build additional HTML strings to include in visaid HTML structure
    #

    # create media duration HTML snippet
    if params["display_video_duration"]:
        video_duration = "[" + lilhelp.tconv(media_length, frac=False) + "]"
    else:
        video_duration = ""


    # create strings of HTML snippets for kinds of checkboxes

    # build up a list scene types, preserving order
    all_scene_types = []
    for f in tfs:
        if f[1] not in all_scene_types:
            all_scene_types.append(f[1])

    subsamples_present = False
    for t in all_scene_types:
        if t.find(" subsample") != -1:
            subsamples_present = True
            break

    # filter to get SWT bins and special scene types
    scene_types = [ t for t in all_scene_types if 
                    t not in SPECIAL_SCENE_TYPES and t.find(" subsample") == -1 ]

    sample_types = [ t for t in SPECIAL_SCENE_TYPES if 
                     t in all_scene_types ]

    # Ideally it'd be nice to pull the visibility boolean from elsewhere, like 
    # the config options for the visaid
    scene_types_visibility = [ (t, True) for t in scene_types 
                               if t not in params["deselected_scene_types"] ]
    scene_types_visibility += [ (t, False) for t in scene_types 
                                if t in params["deselected_scene_types"] ]
    sample_types_visibility = [ (t, False) for t in sample_types ] 

    # build up HTML scene types snippet
    scene_type_checkboxes = ""
    for i, (t, v) in enumerate(scene_types_visibility):
        line = f"<label><input type='checkbox' id='stcp{i}' value='{t}' {'checked' if v else ''}>{t}</label>\n" 
        scene_type_checkboxes += line

    # build up HTML sample types snippet
    sample_type_checkboxes = ""
    for i, (t, v) in enumerate(sample_types_visibility):
        line = f"<label><input type='checkbox' id='sacp{i}' value='{t}' {'checked' if v else ''}>{t}</label>\n" 
        sample_type_checkboxes += line
    if subsamples_present:
        t = "scene subsample"
        v = False
        line = f"<label><input type='checkbox' id='sscb' value='{t}' {'checked' if v else ''}>{t}</label>\n" 
        sample_type_checkboxes += line


    # create job information HTML snippet
    if params["display_job_info"] and job_id is not None:
        job_info = "[JOB: <span class='identifier' id='job-id'>"
        job_info += job_id + "</span>"
        if job_name is not None and job_name != job_id:
            job_info += ( '("' + job_name + '")' )
        job_info += "]"
    else:
        job_info = ""

    # serialize metadata about process and visaid options
    visaid_options_str = json.dumps( [proc_swt_params,visaid_params], indent=2 )

    # Build HTML strig for main body of visaid -- the collection of visaid scenes
    # (This is the bulk of the visaid.)
    visaid_body = ""
    if len(tfsi) == 0:
        visaid_body += ("<div class=''>(No annotated scenes.)</div>")

    # Create a new item div for each row in tfsi
    for f in tfsi:
        label = f[1]
        start_str = lilhelp.tconv(f[2], False)
        end_str = lilhelp.tconv(f[3], False) 

        if params["aapb_timecode_link"] and item_id:
            # creating a link to the AAPB
            start_sec = str(f[2]/1000)
            html_start = ( "<a href='https://americanarchive.org/catalog/" +
                           item_id + "?proxy_start_time=" + start_sec + "'>" + 
                           start_str + "</a>" )
        else:
            html_start = start_str

        div_class = "item" 
        if label.find("subsample") != -1:
            div_class += " subsample"
            scenetype = label[:label.find(" subsample")]
        elif label.find("unlabeled sample") != -1:
            div_class += " unsample"
            scenetype = label
        else:
            div_class = div_class
            scenetype = label

        #html_div_open = "<div class='" + div_class + "' data-label='" + label + "'>"
        html_div_open = f"<div class='{div_class}' data-label='{label}' data-scenetype='{scenetype}'>"

        html_cap = f'<span>{html_start}-{end_str}: </span><span class="label">{label}</span><br>'

        html_img_tag = f'<img src="data:image/jpeg;base64,{f[7]}" >'
        img_fname = f'{item_id}_{media_length:08}_{f[4]:08}_{f[6]:08}' + ".jpg"
        html_img_fname = "<span class='img-fname hidden'>" + img_fname + "<br></span>"

        if params["display_image_ms"]:
            html_img_ms = f"<span class='img-ms'>{f[4]:08} {f[6]:08}</span>"
        else:
            html_img_ms = f"<span class='img-ms hidden'><br>{f[4]:08} {f[6]:08}</span>"

        # Add the new div to the growing HTML
        visaid_body += (html_div_open + 
                        html_cap + 
                        html_img_tag + "\n" +
                        "<div class='img-caption'>" +
                        html_img_fname +
                        html_img_ms + 
                        "</div></div>" + "\n")


    # Map values from Python variables into HTML placeholders.
    # (This dictionary provides values for the placeholder fields in the string read
    # from the HTML structure file.)
    html_field_map = {
        "video_identifier": video_identifier,
        "css_str": css_str,
        "js_str": js_str,
        "job_info": job_info,
        "video_duration": video_duration,
        "scene_type_checkboxes": scene_type_checkboxes,
        "sample_type_checkboxes": sample_type_checkboxes,
        "visaid_options_str": visaid_options_str,
        "mmif_metadata_str": mmif_metadata_str,
        "visaid_body": visaid_body,
        "MODULE_VERSION": __version__
    }
    # Create final HTML string from the structure string and substitution map
    html_str = structure_str.format_map(html_field_map)

    # Write output to stdout or to a file
    if stdout:
        print(html_str)
        hfilename = None
        hfilepath = None
    else:
        hfilepath = output_dirname + "/" + hfilename
        with open(hfilepath, "w") as html_file:
            html_file.write(html_str)
    
    return hfilepath, problems, infos
   
