"""
create_visaid.py

Defines function for creating a visaid from a list of scene TimeFrames
"""

import os
import io
import base64
import json

import av

try:
    # if being run from higher level module
    from . import lilhelp
except ImportError:
    # if run as stand-alone
    import lilhelp


MODULE_VERSION = "1.80"

VISAID_DEFAULTS = { "job_id_in_visaid_filename": False,
                    "display_video_duration": True,
                    "display_job_info": True,
                    "display_image_ms": True,
                    "aapb_timecode_link": False }

MAX_STORED_FRAME_HEIGHT = 360



def create_visaid(video_path:str, 
                  tfs:list,
                  stdout:bool = False,
                  output_dirname:str = ".",
                  hfilename:str = "",
                  job_id:str = None,
                  job_name:str = None,
                  item_id:str = "",
                  proc_swt_params:dict = {},
                  visaid_params:dict = {},
                  mmif_metadata_str: str = ""
                  ):                  
    """
    Creates an HTML file (with embedded images) as a visual aid, based on the output
    of `list_tfs`.

    """

    # Warn about spurious options
    for key in visaid_params:
        if key not in VISAID_DEFAULTS:
            print("Warning: `" + key + "` is not a valid visaid option. Ignoring.")

    # Process params/options
    params = {}
    for key in VISAID_DEFAULTS:
        if key in visaid_params:
            params[key] = visaid_params[key]
        else:
            params[key] = VISAID_DEFAULTS[key]

    # Consruct output visaid filename
    if hfilename == "":
        if params["job_id_in_visaid_filename"]:
            suffix = "_" + str(job_id)
        else:
            suffix = ""
        if item_id:
            hfilename = item_id + "_visaid" + suffix + ".html"
        else:
            hfilename = "visaid" + suffix + ".html"

    # Construct video identifier string to display in visaid
    if item_id:
        video_identifier = item_id
    else:
        video_fname = video_path[video_path.rfind("/")+1:]
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
    if abs( 1 - sar ) > 0.03:
        stretch = True
        print("Sample aspect ratio:", sar, ". Will stretch anamorphic frames.")
    else:
        stretch = False

    # calculate duration in ms
    media_length = int((video_stream.frames / fps) * 1000)

    # table like tfs, but with images
    tfsi = []

    # Build up tfsi table.
    # Use rows from the tfs table, but add additional columns for actual frame 
    # time and image data
    if len(tfs) > 0:

        # create a new list sorted in order of rep frame times 
        # so we can proceed in sequential order of video frames to be extracted
        #tfs.sort(key=lambda f:f[4])
        tfs_s = sorted(tfs, key=lambda f:f[4])

        # initialize target scene and still 
        next_scene = 0 
        target_time = tfs_s[next_scene][4]
      
        # loop through video frames to capture targets
        for frame in container.decode(video_stream):
            
            ftime = int(frame.time * 1000)   

            # look for the frame nearest to the target
            if ftime+15 >= target_time :
                
                # Check for anamorphic and stretch if necessary
                if stretch:
                    if sar > 1.0:
                        # stretch width
                        new_width = int( sar * frame.width)
                        new_height = frame.height
                    else:
                        # stretch height
                        new_width = frame.width
                        new_height = int(frame.height / sar)
                    stretched_frame = frame.reformat( width=new_width, height=new_height )
                else:
                    stretched_frame = frame

                # Reduce frame height, if necessary
                if stretched_frame.height > MAX_STORED_FRAME_HEIGHT:
                    res_factor = MAX_STORED_FRAME_HEIGHT / stretched_frame.height 
                    new_width = int(stretched_frame.width * res_factor)
                    res_frame = stretched_frame.reformat( width=new_width, height=MAX_STORED_FRAME_HEIGHT )
                else:
                    res_frame = stretched_frame

                # save frame to memory buffer
                buf = io.BytesIO()
                res_frame.to_image().save(buf, format="JPEG", quality=75)

                # convert out binary image data to UTF-8 string
                img_str = base64.b64encode(buf.getvalue()).decode('utf-8')

                tfsi.append(tfs_s[next_scene] + [ ftime ] + [ img_str ] )
                
                next_scene += 1
                if next_scene < len(tfs_s):            
                    target_time = tfs_s[next_scene][4]
                else:
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

    # create job information HTML
    if params["display_job_info"] and job_id is not None:
        job_info = "<br><span class='extra-info'>JOB: <span class='identifier' id='job-id'>"
        job_info += job_id + "</span> "
        if job_name is not None and job_name != job_id:
            job_info += ( '("' + job_name + '")' )
        job_info += "</span>"
    else:
        job_info = ""

    # create media duration HTML
    if params["display_video_duration"]:
        video_duration = "<span class='extra-info'>["
        video_duration += lilhelp.tconv(media_length, frac=False)
        video_duration += "]</span>"
    else:
        video_duration = ""

    # create metadata about process and visaid options
    visaid_options_str = json.dumps( [proc_swt_params,visaid_params], indent=2 )

    # build HTML strig for main body of visaid -- the collection of visaid scenes
    visaid_body = ""
    if len(tfsi) == 0:
        html_body += ("<div class=''>(No annotated scenes.)</div>")

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
        if label.find("unlabeled sample") != -1:
            div_class += " unsample"
        html_div_open = "<div class='" + div_class + "' data-label='" + label + "'>"
        html_cap = f'<span>{html_start}-{end_str}: </span><span class="label">{label}</span><br>'
        html_img_tag = f'<img src="data:image/jpeg;base64,{f[7]}" >'
        img_fname = f'{item_id}_{media_length:08}_{f[4]:08}_{f[6]:08}' + ".jpg"
        html_img_fname = "<span class='img-fname hidden'>" + img_fname + "<br></span>"
        if params["display_image_ms"]:
            html_img_ms = f"<span class='img-ms'>{f[4]:08} {f[6]:08}</span>"
        else:
            html_img_ms = f"<span class='img-ms hidden'><br>{f[4]:08} {f[6]:08}</span>"

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
        "visaid_options_str": visaid_options_str,
        "mmif_metadata_str": mmif_metadata_str,
        "visaid_body": visaid_body,
        "MODULE_VERSION": MODULE_VERSION
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
    
    return (hfilename, hfilepath)
   
