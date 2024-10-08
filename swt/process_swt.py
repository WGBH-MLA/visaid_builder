"""
process_swt.py

Defines functions that perform processing on MMIF output from SWT
"""

# %%
# Run import statements
import os
import io
import base64
import json

import pandas as pd
import av

from mmif import Mmif
from mmif import AnnotationTypes

import drawer.lilhelp


MODULE_VERSION = "1.42"


def get_mmif_metadata_str( mmifstr:str ):
    """
    Takes the metadata object from the first view with TimeFrame annotations.
    Returns prettified serialized JSON for that metadata.
    This is a helper function for this module, not a general function for
    grabbing metadata from MMIF files.
    """

    # turn the MMIF string into a Mmif object
    usemmif = Mmif(mmifstr)

    # First, get the first view that contains a TimeFrame
    # If none exists, return an empty list.
    if len(usemmif.get_all_views_contain(AnnotationTypes.TimeFrame)) > 0:
        useview = usemmif.get_all_views_contain(AnnotationTypes.TimeFrame).pop()
    else:
        return ""

    return json.dumps(json.loads(str(useview.metadata)), indent=2)



def list_tfs( mmifstr:str, 
              max_gap:int=0, 
              include_startframe:bool=False,
              include_endframe:bool=True,
              subsampling:dict=None,
              remove_sampled=False):
    """
    Analyzes MMIF file from SWT and returns tabular data.

    Takes serialized MMIF as a string as input.
    Returns a table (list of lists) representing the timeFrame annotations

    Columns:
    0: TimeFrame id (from MMIF file) (string)
    1: bin label (string)
    2: start time in milliseconds (int)
    3: stop time in milliseconds (int)
    4: represenative still time in milliseconds(int)

    """

    # turn the MMIF string into a Mmif object
    usemmif = Mmif(mmifstr)

    # Get the annotations from the MMIF and do something with them

    # First, get the first view that contains a TimeFrame
    # If none exists, return an empty list.
    if len(usemmif.get_all_views_contain(AnnotationTypes.TimeFrame)) > 0:
        useview = usemmif.get_all_views_contain(AnnotationTypes.TimeFrame).pop()
    else:
        return []

    # New, to account for change in SWT v6.0
    # Get information about the app version.
    # If version >= 6.0, use view ID prefix for time point refs
    app = useview.metadata.app
    try:
        app_ver = float(app[app.rfind("/v")+2:])
        
        # For SWT v6.0 and above timepoints targeted by other frames include
        # a reference to the view from which they came.
        if app_ver > 5.9999:
            ref_prefix = useview.id + ":"
        else:
            ref_prefix = ""
    except Exception as e:
        print("Error:", e)
        print("Could not get app version.")
        print("Assuming version less than 6.0")
        ref_prefix = ""


    # Drill down to the annotations we're after, creating generators
    tfanns = useview.get_annotations(AnnotationTypes.TimeFrame)
    tpanns = useview.get_annotations(AnnotationTypes.TimePoint)

    # Build two lists, one of TimeFrames and one of TimeFrame+Points
    tfs = []
    tfpts = []   
    for ann in tfanns:
        tf_id = ann.get_property("id")
        tf_frameType = ann.get_property("frameType")

        # add timeFrames to their list; no values for times yet
        tfs += [[tf_id, tf_frameType, -1, -1, -1]]

        # add timeFrame points to their list
        for t in ann.get_property("targets"):
            is_rep = t in ann.get_property("representatives")

            # need to cast timepoint back to int from np.int64
            tfpts += [[ tf_id, tf_frameType, t, is_rep ]]

    # work-around for v3.0 timePont bug
    if useview.metadata.app == 'http://apps.clams.ai/swt-detection/v3.0' :
        tP_prop = "timePont"
    else :
        tP_prop = "timePoint"

    # Build another list for TimePoints
    tps = []
    last_time = 0
    for ann in tpanns:
        
        tpt_id = ref_prefix + ann.get_property("id") # new, for v6.0 and above

        tps += [[ tpt_id, 
                  ann.get_property("label"), 
                  ann.get_property(tP_prop) ]]  # work-around for v3.0 bug
        
        if ann.get_property(tP_prop) > last_time:
            last_time = ann.get_property(tP_prop)

    # create DataFrames from lists and merge
    tfpts_df = pd.DataFrame(tfpts, columns=['tf_id','frameType','tp_id','is_rep'])
    tps_df = pd.DataFrame(tps, columns=['tp_id','label','timePoint'])
    tfs_tps_df = pd.merge(tfpts_df,tps_df)

    # iterate through the timeFrames and use the merged DataFrame to look up times
    # (need to cast np.int64 values to ordinary int)
    for f in tfs:
        tfrows = tfs_tps_df[ tfs_tps_df["tf_id"] == f[0] ]
        f[2] = int( (tfrows["timePoint"]).min() )  # start time
        f[3] = int( (tfrows["timePoint"]).max() ) # end time
        f[4] = int( (tfrows[tfrows["is_rep"]]["timePoint"]).min() )# rep time

    # sort list of timeFrames by start time
    tfs.sort(key=lambda f:f[2])

    # add frames for first and last timepoints 
    # (Because gaps have to be between timepoints, and we want to catch
    # gaps at the beginning and end.)
    # These may be removed later
    tfs.insert(0, ['f_0', 'first frame', 0, 0, 0])
    tfs.append(['f_n', 'last frame', last_time, last_time, last_time])


    # If this parameter has been passed to the function, then
    # intersperse sample non-labeled frames among labeled timeframes.
    # The max_gap value controls the largest gap without the addtition
    # of an interspersed frame.
    if max_gap: 

        # Samples are primarily useful for their central frame, but they need a 
        # duration to be represented in the tfs data structure
        sample_dur = max_gap // 2

        sample_counter = 1
        samples = []

        # Iterate through existing time frames to identify gaps in which to 
        # insert samples.  Specifically, for each time frame, after the first,
        # look back to see how much time since the last one.  If that gap is 
        # bigger than the max_gap, then make a sample.
        for rnum in range(1, len(tfs)) :
            
            # calculate the distance between the start of the current frame
            # and the end of the previous
            full_gap = tfs[rnum][2] - tfs[rnum-1][3]

            if full_gap > max_gap :

                # figure out how many and where to sample
                num_samples = full_gap // max_gap
                gap_size = full_gap // num_samples

                # collect samples (we'll add them into tfs later)
                for sample_num in range(num_samples):
                    gap_start = sample_num * gap_size + tfs[rnum-1][3]
                    
                    sample_start = gap_start + (gap_size - sample_dur)//2
                    sample_end = sample_start + sample_dur
                    sample_rep = sample_start + sample_dur//2

                    tf_id = "s_" + str(sample_counter)

                    samples.append([tf_id, 'unlabeled sample', sample_start, sample_end, sample_rep])
                    sample_counter += 1

        # add samples to timeframes and re-sort
        tfs += samples
        tfs.sort(key=lambda f:f[2])


   # Add extra samples scenes for longer scenes  (like credits sequences)
    if subsampling is not None:

        # check for and remove invalid sampling entries
        for scenetype in subsampling:
            if not ( subsampling[scenetype] > 0 and subsampling[scenetype] , last_time ):
                print("Ignoring invalid scene sampling:", scenetype, ":", subsampling[scenetype])
                del subsampling[scenetype]

        # collect IDs scenes in case we want to remove them (because replaced by samples)
        sampled_scene_ids = []
        
        # collect new rows for the new samples
        scene_samples = []

        # iterate through scene rows in tfs
        for row in [row for row in tfs if row[1] in subsampling ]:

            scene_dur = row[3] - row[2]
            num_samples = int( scene_dur/ subsampling[row[1]] ) + 1
            
            # Replace scene with samples only if we need more than one sample
            if num_samples > 1: 

                new_samples = []

                sample_dur = int(scene_dur/(num_samples - 1))

                sample_start = row[2]  # first sample is at scene start

                for _ in range(num_samples):
                    new_id = row[0] + "_s_" + str(len(new_samples)) 
                    new_label = row[1] + " subsample"

                    if len(new_samples) < (num_samples - 1):
                        sample_end = sample_start + sample_dur
                        sample_rep = sample_start
                    else:
                        # last sample -- at the endpoint of the credits scene
                        sample_end = sample_start
                        sample_rep = sample_start

                    new_row = [ new_id, new_label, sample_start, sample_end, sample_rep ]
                    new_samples.append(new_row)

                    sample_start = sample_end

                scene_samples += new_samples
                sampled_scene_ids.append(row[0])
        
        # Add new samples to tfs
        tfs += scene_samples
        
    # if appropriate, remove first frame and last frame pseudo-annotations
    to_remove = []
    if remove_sampled:
        to_remove += sampled_scene_ids
    if not include_startframe:
        to_remove.append('f_0')
    if not include_endframe:
        to_remove.append('f_n')

    if len(to_remove) > 0:
        tfs = [ row for row in tfs if row[0] not in to_remove ]

    # pprint.pprint(tfs) # DIAG
    tfs.sort(key=lambda f:f[2])
    return tfs




def create_aid(video_path: str, 
               tfs: list,
               job_id: str = None,
               job_name: str = None,
               hfilename: str = "",
               guid: str = "",
               stdout: bool = False,
               output_dirname: str = ".",
               types: list = None,
               metadata_str: str = "",
               max_gap: int = None,
               subsampling:dict = None
               ):
    """
    Creates an HTML file (with embedded images) as a visual aid, based on the output
    of `list_tfs`.

    If a list of types is passed in, the visaid is limited to those types.
    """

    if hfilename == "":
        if guid:
            hfilename = guid + "_visaid.html"
        else:
            hfilename = "visaid.html"

    if guid:
        video_identifier = guid
    else:
        video_fname = video_path[video_path.rfind("/")+1:]
        video_identifier = video_fname

    if len(types) > 0:
        tfs = [ row for row in tfs if row[1] in types ] 

    # find the first video stream
    container = av.open(video_path)
    video_stream = next((s for s in container.streams if s.type == 'video'), None)
    if video_stream is None:
        raise Exception("No video stream found in {}".format(video_path) ) 

    # get technical stats on the video stream; assumes FPS is constant
    fps = video_stream.average_rate.numerator / video_stream.average_rate.denominator
    
    # calculate duration in ms
    length = int((video_stream.frames / fps) * 1000)

    # table like tfs, but with images
    tfsi = []

    # Build up tfsi table.
    # Use rows from the tfs table, but add additional columns for actual frame 
    # time and image data
    if len(tfs) > 0:
        next_scene = 0 
        target_time = tfs[next_scene][4]
        
        for frame in container.decode(video_stream):
            
            ftime = int(frame.time * 1000)   
            if ftime >= target_time :
                
                # save frame to memory buffer
                buf = io.BytesIO()
                frame.to_image().save(buf, format="JPEG", quality=75)

                # convert out binary image data to UTF-8 string
                img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                #html_img_tag = f'<img src="data:image/jpeg;base64,{img_str}" >'


                tfsi.append(tfs[next_scene] + [ ftime ] + [ img_str ] )
                
                next_scene += 1
                if next_scene < len(tfs):            
                    target_time = tfs[next_scene][4]
                else:
                    break

    container.close()

    # Get CSS for inclusion in HTML 
    py_dir = os.path.dirname(__file__)
    css_path = os.path.join(py_dir, "visaid_embedded_styles.css")
    with open(css_path, "r") as css_file:
        css_str = css_file.read()

    # Get JS for inclusion in HTML 
    py_dir = os.path.dirname(__file__)
    js_path = os.path.join(py_dir, "visaid_embedded_logic.js")
    with open(js_path, "r") as js_file:
        js_str = js_file.read()


    #
    # create HTML string
    #

    # create job information HTML
    if job_id is not None:
        job_info = "<span class='job-info'><span class='identifier' id='job-id'>" + job_id
        job_info += " </span>"
        if job_name is not None and job_name != job_id:
            job_info += ( '("' + job_name + '")' )
        job_info += "</span>"
    else:
        job_info = ""

    html_top = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>""" + video_identifier + """ / Visual Index</title>
<style>
""" + css_str + """
</style>
<script defer>
""" + js_str + """
</script>
<!-- 
The next two elements reference files that are optional.  They are not required 
for the visaid to display properly.  However, they can be customized to 
restyle, enhance, or alter a visaid.
-->
<link rel='stylesheet' href='visaid_style_override.css'>
<script src='visaid_enhance.js' defer></script>
</head>


<body>
<div class='top'>Visual index of 
<span class='video-id' id='video-id'>""" + video_identifier + """</span>
<br>""" + job_info + """
<pre class="metadata" id="visaid-options">
{
'max_gap': """ + str(max_gap) + """,
'subsampling': """ + str(subsampling) + """
}
</pre>
<pre class="metadata" id="mmif-metadata">
""" + metadata_str + """
</pre>
</div>
<div class='button-container'>
<button type='button' class='hidden' id='unsamplesVisButton'>Toggle Unlabeled Samples</button>
<button type='button' class='hidden' id='subsamplesVisButton'>Toggle Scene Subsamples</button>
</div>
<div class='container'>
"""
    html_end = """
</div>
<div class="version">
visaid version: <span id='visaid-version'>""" + MODULE_VERSION + """</span>
<span class="enhance-indicator" id="enhance-indicator"></span>
</div>
</body>
</html>
"""
    html_body = ""

    # build HTML body
    if len(tfsi) == 0:
        html_body += ("<div class=''>(No annotated scenes.)</div>")

    for f in tfsi:
        label = f[1]
        start_str = drawer.lilhelp.tconv(f[2], False)
        end_str = drawer.lilhelp.tconv(f[3], False) 

        if guid:
            # creating a link for an AAPB segment, which requires both a start time and end time
            start_sec = str(f[2]/1000)
            #end_sec = str(f[3]/1000)
            end_sec = str(length/1000)
            html_start = ( "<a href='https://americanarchive.org/catalog/" +
                           guid + "?proxy_start_time=" + start_sec + "'>" + 
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
        html_img_tag = f'<img src="data:image/jpeg;base64,{f[6]}" >'
        img_fname = f'{guid}_{length:08}_{f[4]:08}_{f[5]:08}' + ".jpg"
        html_img_fname = "<br><span class='img-fname'>" + img_fname + "</span>"

        html_body += (html_div_open + 
                      html_cap + 
                      html_img_tag + "\n" +
                      html_img_fname +
                      "</div>" + "\n")
        

    html_str = html_top + html_body + html_end

    if stdout:
        print(html_str)
        hfilename = None
        hfilepath = None
    else:
        hfilepath = output_dirname + "/" + hfilename
        with open(hfilepath, "w") as html_file:
            html_file.write(html_str)
            print("Visual index created at " + hfilepath + ".")
    
    return (hfilename, hfilepath)
   
