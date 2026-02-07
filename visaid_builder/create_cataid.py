"""
create_cataid.py

Defines a function for creating a cataid from a list of scene TimeFrames.

The main required parameters are the path to the video file and a table
(list of dicts) in the style of the `tfsd` tables created by the proc_swt module.

This function reads and depends on the display ingredients in these files:
   visaid_ingredients/visaid_embedded_styles.css
   visaid_ingredients/cataid_embedded_styles.css
   visaid_ingredients/cataid_embedded_logic.js
   visaid_ingredients/cataid_structure.html
"""

import os
import io
import base64
import json
import logging

from datetime import datetime
from importlib.metadata import version

import av
from titlecase import titlecase

__version__ = version("visaid_builder")
from . import lilhelp

CATAID_DEFAULTS = { "deselected_scene_types": ["filmed text"],
                    "job_id_in_cataid_filename": False,
                    "display_video_duration": True,
                    "display_job_info": True,
                    "display_image_ms": True,
                    "aapb_timecode_link": False,
                    "max_img_height": 360 }

STRETCH_THRESHOLD = 0.005

# These are scene types (optionally) created by `proc_swt`, not defined by the 
# SWT bins.  They are displayed in a different area of the page layout.
SPECIAL_SCENE_TYPES = [ "first frame checked", 
                        "last frame checked", 
                        "unlabeled sample"] 


def create_cataid( video_path:str, 
                   tfsd:list,
                   stdout:bool = False,
                   output_dirname:str = ".",
                   hfilename:str = "",
                   job_id:str = None,
                   job_name:str = None,
                   item_id:str = "",
                   item_name:str = "",
                   proc_swt_params:dict = {},
                   cataid_params:dict = {},
                   mmif_metadata_str: str = ""
                   ):                  
    """
    Creates an HTML file (with embedded images) as a visaid with cataloging features,, 
    based on MMIF file processed into the tfsd structure.

    """

    problems = []
    infos = []
    extras = {}

    # Warn about spurious parameter keys
    for key in cataid_params:
        if key not in CATAID_DEFAULTS:
            if not stdout:
                logging.warning("Warning: `" + key + "` is not a valid cataid option. Ignoring.")
            problems.append("invalid-cataid_param")

    # Process parameters, using defaults where appropriate
    params = {}
    for key in CATAID_DEFAULTS:
        if key in cataid_params:
            params[key] = cataid_params[key]
        else:
            params[key] = CATAID_DEFAULTS[key]

    # Consruct output cataid filename
    if hfilename == "":
        if item_id:
            prefix = item_id + "_"
        else:
            prefix = ""
        if params["job_id_in_cataid_filename"]:
            suffix = "_" + str(job_id)
        else:
            suffix = ""
        hfilename = prefix + "cataid" + suffix + ".html"

    # Construct video name/identifier string to display in cataid
    video_fname = video_path[video_path.rfind("/")+1:]
    if item_name:
        video_identifier = item_name
    elif item_id:
        video_identifier = item_id
    else:
        video_identifier = video_fname
    
    # Construct a cataid identifier
    cataid_identifier = video_identifier + "#" + datetime.now().strftime("%Y%m%d%H%M%S")

    # 
    # Begin analyzing video in terms of tfsd table
    #

    # find the first video stream
    container = av.open(video_path)
    video_stream = next((s for s in container.streams if s.type == 'video'), None)
    if video_stream is None:
        raise Exception("No video stream found in {}".format(video_path) ) 

    # get technical stats on the video stream; assumes FPS is constant
    fps = video_stream.average_rate.numerator / video_stream.average_rate.denominator
    extras["fps"] = float(f"{fps:.2f}")

    # determine whether anamorphic stills will need to be stretched
    if video_stream.sample_aspect_ratio is not None:
        sar = float(video_stream.sample_aspect_ratio)
        extras["sar"] = float(f"{sar:.3f}")
    else:
        # If SAR cannot be determined, assume it is 1 for present purposes
        sar = 1.0
        # But report it as None
        extras["sar"] = None

    if abs( 1 - sar ) > STRETCH_THRESHOLD:
        stretch = True
        if not stdout:
            logging.info(f'Sample aspect ratio: {sar:.3f}. Will stretch anamorphic frames.')
        infos.append(f'SAR-{sar:.3f}')
    else:
        stretch = False

    # calculate duration in ms
    media_length = int((video_stream.frames / fps) * 1000)
    extras["media_length"] = media_length

    # Table like tfsd, but with an extra columns. 
    # Uses rows from the tfsd table, but adds additional columns for actual frame 
    # time and base64 image data.

    tfsdi = []
    
    # Build up tfsdi table by adding rows based on tfsd rows.
    if len(tfsd) > 0:

        # Create a new list sorted in order of rep frame times .
        # Because we need to proceed in order of video frames to be extracted
        # (not necessarily the order of the scene start times).
        tfsd_s = sorted(tfsd, key=lambda f:f["tp_time"])

        # initialize target scene and still 
        next_scene = 0 
        target_time = tfsd_s[next_scene]["tp_time"]
        last_packet_error = 0
      
        # looping through packets instead of frames allows exception handling for each
        # particular decode step.  This main loop originally iterated over frames in
        # `container.decode(video_stream)`.
        for packet in container.demux(video_stream):
            #break # TESTING 
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

                        # add new row to tfsdi
                        new_tf = dict(tfsd_s[next_scene])
                        new_tf["video_frame_time"] = ftime
                        new_tf["img_str"] = img_str
                        tfsdi.append(new_tf)
                        
                        next_scene += 1
                        if next_scene >= len(tfsd_s):            
                            # no need to continue decoding video if we have all our scenes saved
                            break
                        else:
                            target_time = tfsd_s[next_scene]["tp_time"]

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

            if next_scene >= len(tfsd_s):
                # no need to continue decoding video if we have all our scenes saved
                break

    # Done with the video media itself
    container.close()

    # Re-sort new array in terms of scene start time, then by TimeFrame id,
    # (so that subsamples come after the scenes from which they've been sampled.)
    tfsdi.sort(key=lambda f:(f["start"],f["tf_id"]))
    #tfsdi = tfsd # TESTING

    # Get ingredient code strings for inclusion in HTML files
    py_dir = os.path.dirname(__file__)
    ingredients_dir = os.path.join(py_dir, "visaid_ingredients")

    # start with visaid styles as basis
    css_path = os.path.join(ingredients_dir, "visaid_embedded_styles.css")
    with open(css_path, "r") as css_file:
        css_str = css_file.read()

    # make cataid-specific style additions as appropriate
    css_path = os.path.join(ingredients_dir, "cataid_embedded_styles.css")
    with open(css_path, "r") as css_file:
        css_str += "\n" + css_file.read()

    js_path = os.path.join(ingredients_dir, "cataid_embedded_logic.js")
    with open(js_path, "r") as js_file:
        js_str = js_file.read()

    html_path = os.path.join(ingredients_dir, "cataid_structure.html")
    with open(html_path, "r") as html_file:
        structure_str = html_file.read()

    #
    # Build additional HTML strings to include in cataid HTML structure
    #

    # create media duration HTML snippet
    if params["display_video_duration"]:
        video_duration = "[" + lilhelp.tconv(media_length, frac=False) + "]"
    else:
        video_duration = ""


    # create strings of HTML snippets for kinds of checkboxes

    # build up a list scene types, preserving order
    all_scene_types = []
    for f in tfsd:
        if f["tf_label"] not in all_scene_types:
            all_scene_types.append(f["tf_label"])

    subsamples_present = False
    for t in all_scene_types:
        if t.find(" - - -") != -1:
            subsamples_present = True
            break

    # filter to get SWT bins and special scene types
    scene_types = [ t for t in all_scene_types if 
                    t not in SPECIAL_SCENE_TYPES and t.find(" - - -") == -1 ]

    sample_types = [ t for t in SPECIAL_SCENE_TYPES if 
                     t in all_scene_types ]

    # set initial visibility
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

    # serialize metadata about process and cataid options
    cataid_options_str = json.dumps( [proc_swt_params, cataid_params], indent=2 )

    # Build HTML strig for main body of cataid -- the collection of cataid scenes, KIE, and annotation
    # (This is the bulk of the cataid.)
    cataid_body = ""
    if len(tfsdi) == 0:
        cataid_body += ("<div class=''>(No annotated scenes.)</div>")

    # Create new item divs for each row in tfsdi
    for f in tfsdi:

        # `tf_label` is the displayed label, the value of `data-label`
        tf_label = f["tf_label"]
        tp_id = f["tp_id"]
        tp_time = f["tp_time"]
        video_frame_time = f["video_frame_time"] 
        #video_frame_time = 0000 # TESTING 

        # information to keep at the top itemrow-level div
        itemrow_div_class = "itemrow" 
        item_div_class = "item"

        # scenetype is the tf_label without the subsample suffix
        if tf_label.find(" - - -") != -1:
            item_div_class += " subsample"
            scenetype = tf_label[:tf_label.find(" - - -")]
        elif tf_label.find("unlabeled sample") != -1:
            item_div_class += " unsample"
            scenetype = tf_label
        else:
            item_div_class = item_div_class
            scenetype = tf_label

        #
        # Build some strings as inline ingredients
        #

        # Human-readable time span for the item
        time_start_str = lilhelp.tconv(f["start"], False)
        time_end_str = lilhelp.tconv(f["end"], False) 

        # human-readable time span for the item
        time_start_str = lilhelp.tconv(f["start"], False)
        time_end_str = lilhelp.tconv(f["end"], False) 

        # Hyperlinked start time
        if params["aapb_timecode_link"] and item_id:
            # creating a link to the AAPB
            time_start_sec = str(f["start"]/1000)
            html_time_start = ( "<a href='https://americanarchive.org/catalog/" +
                           item_id + "?proxy_start_time=" + time_start_sec + "'>" + 
                           time_start_str + "</a>" )
        else:
            html_time_start = time_start_str

        # top row of each of the item divs
        html_vis_itemcap = ( '<span class="item-top">' + 
                             f'<span>{html_time_start}-{time_end_str}: <span class="label">{tf_label}</span></span>' + 
                             '</span>' )
        html_aid_itemcap = ( '<span class="item-top">' + 
                             '<span class="label">extracted text</span>' + 
                             f'<span class="engage-toggle label clickable" data-tptime="{tp_time}">&nbsp; &#9703; </span>' + 
                             '</span>' )
        html_edt_itemcap = ( '<span class="item-top">' + 
                             '<span class="label">catalog data</span>' + 
                             '<span class="label invisible">&nbsp; &#9703; </span>' + 
                             '</span>' )

        # the image and stuff about it
        html_img_tag = f'<img src="data:image/jpeg;base64,{f["img_str"]}" >'
        #html_img_tag = f'<img src="https://aapb-aux.s3.amazonaws.com/slates/cpb-aacip-225-10wpzhs0_slate.jpg" >' # TESTING 
        
        img_fname = f'{item_id}_{media_length:08}_{tp_time:08}_{video_frame_time:08}' + ".jpg"
        html_img_fname = "<span class='img-fname hidden'>" + img_fname + "<br></span>"
        if params["display_image_ms"]:
            html_img_ms = f"<span class='img-ms'>{tp_time:08} {video_frame_time:08}</span>"
        else:
            html_img_ms = f"<span class='img-ms hidden'><br>{tp_time:08} {video_frame_time:08}</span>"

        # extracted text
        if f["text"]:
            aid_text = titlecase( f["text"].replace("\\n", "\n").lower() )
            editor_text = aid_text
        else:
            aid_text = "[NO TEXT EXTRACTED]"
            editor_text = ""

        #
        # Build main block ingredients for itemrow
        #

        # start of the itemrow div
        html_itemrow_div_open = f"<div class='{itemrow_div_class}' data-label='{tf_label}' data-scenetype='{scenetype}'>"

        # visaid-style div
        html_itemvis_div = ( f"<div class='{item_div_class}'>" + "\n" +
                             html_vis_itemcap + "\n" +
                             html_img_tag + "\n" +
                             "<div class='img-caption'>" +
                             html_img_fname + "\n" +
                             html_img_ms + "\n" + 
                             "</div>" + "\n" + 
                             "</div>" + "\n" )

        # extracted text div
        html_itemaid_div = ( f"<div class='{item_div_class} item-aid'>" + "\n" +
                             html_aid_itemcap + "\n" +
                             "<pre class='aid-text'>" + "\n" +
                             aid_text + "\n" +
                             "</pre>" + "\n" + 
                             "</div>" + "\n" )

        # text editor div
        html_itemedt_div = ( f"<div class='{item_div_class} item-editor' data-scenetype='{scenetype}' data-tptime='{tp_time}'>" + "\n" +
                             html_edt_itemcap + "\n" +
                             f"<pre class='editor-text' contenteditable='true' data-tptime='{tp_time}' data-tpid='{tp_id}'>" + "\n" +
                             editor_text + "\n" +
                             "</pre>" + "\n" + 
                             "</div>" + "\n" )

        # full itemrow div
        html_itemrow = ( html_itemrow_div_open + "\n" +
                         html_itemvis_div + "\n" +
                         "<div class='cataid-extra'>" + "\n\n" +
                         html_itemaid_div + "\n" +
                         html_itemedt_div + "\n" +
                         "</div><!-- end of cataid portions-->" + "\n" +
                         "</div>" + "\n" + 
                         "<!-- end of itemrow-->" + "\n\n\n" )

        # Add the new divs to the growing HTML
        cataid_body += html_itemrow


    # Map values from Python variables into HTML placeholders.
    # (This dictionary provides values for the placeholder fields in the string read
    # from the HTML structure file.)
    html_field_map = {
        "video_identifier": video_identifier,
        "cataid_identifier": cataid_identifier,
        "css_str": css_str,
        "js_str": js_str,
        "job_info": job_info,
        "video_duration": video_duration,
        "scene_type_checkboxes": scene_type_checkboxes,
        "sample_type_checkboxes": sample_type_checkboxes,
        "cataid_options_str": cataid_options_str,
        "mmif_metadata_str": mmif_metadata_str,
        "cataid_body": cataid_body,
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
    
    return hfilepath, problems, infos, extras
   
