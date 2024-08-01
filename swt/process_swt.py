"""
process_swt.py
v1.0

Defines functions that perform processing on MMIF output from SWT
"""

# %%
# Run import statements
import os
import io
import base64

import pandas as pd
import av

import mmif
from mmif import Mmif
from mmif import AnnotationTypes

import drawer.lilhelp


def list_tfs( mmifstr:str, max_gap:int=0 ):
    """
    Analyzes MMIF file from SWT and returns tabular data.

    Takes serialized MMIF as a string as input.
    Returns a table (list of lists) representing the timeFrame annotations
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
    except Error as e:
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
            tfpts += [[ tf_id, tf_frameType, t, is_rep ]]

    # work-around for v3.0 timePont bug
    if useview.metadata.app == 'http://apps.clams.ai/swt-detection/v3.0' :
        tP_prop = "timePont"
    else :
        tP_prop = "timePoint"

    # Build another list for TimePoints
    tps = []
    for ann in tpanns:
        
        # tpt_id = ann.get_property("id") # for v5.1 and below
        tpt_id = ref_prefix + ann.get_property("id") # new, for v6.0 and above

        tps += [[ tpt_id, 
                  ann.get_property("label"), 
                  ann.get_property(tP_prop) ]]  # work-around for v3.0 bug

    # create DataFrames from lists and merge
    tfpts_df = pd.DataFrame(tfpts, columns=['tf_id','frameType','tp_id','is_rep'])
    tps_df = pd.DataFrame(tps, columns=['tp_id','label','timePoint'])
    tfs_tps_df = pd.merge(tfpts_df,tps_df)

    # iterate through the timeFrames and use the merged DataFrame to look up times
    for f in tfs:
        tfrows = tfs_tps_df[ tfs_tps_df["tf_id"] == f[0] ]
        f[2] = (tfrows["timePoint"]).min()  # start time
        f[3] = (tfrows["timePoint"]).max()  # end time
        f[4] = (tfrows[tfrows["is_rep"]]["timePoint"]).min() # rep time

    # sort list of timeFrames by start time
    tfs.sort(key=lambda f:f[2])

    # intersperse sample non-labeled frames among labeled timeframes.
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
        for rnum in range(1, len(tfs)-1) :

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

                    samples.append([tf_id, 'unlabeled_sample', sample_start, sample_end, sample_rep])
                    sample_counter += 1

        # add samples to timeframes and re-sort
        tfs += samples
        tfs.sort(key=lambda f:f[2])


    return tfs



def create_aid(video_path: str, 
               tfs: list,
               proj_name: str = "asset",
               guid: str = None,
               stdout: bool = False,
               output_dirname: str = ".",
               types: list = []
               ):
    """
    Creates an HTML file (with embedded images) as a visual aid, based on the output
    of `list_tfs`.

    If a list of types is passed in, the visaid is limited to those types.
    """

    if len(types) > 0:
        tfs = [ row for row in tfs if row[1] in types ] 

    # find the first video stream
    container = av.open(video_path)
    video_stream = next((s for s in container.streams if s.type == 'video'), None)
    if video_stream is None:
        raise Exception("No video stream found in {}".format(vfilename) ) 

    # get technical stats on the video stream; assumes FPS is constant
    fps = video_stream.average_rate.numerator / video_stream.average_rate.denominator
    
    # calculate duration in ms
    length = int((video_stream.frames / fps) * 1000)

    # table like tfs, but with images
    tfsi = []

    # build up tfsi table with image data
    if len(tfs) > 0:
        next_scene = 0 
        target_time = tfs[next_scene][4]
        
        for frame in container.decode(video_stream):
            
            ftime = int(frame.time * 1000)   
            if ( ftime >= target_time ):
                
                # save frame to memory buffer
                buf = io.BytesIO()
                frame.to_image().save(buf, format="JPEG", quality=75)

                # convert out binary image data to UTF-8 string
                img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                #html_img_tag = f'<img src="data:image/jpeg;base64,{img_str}" />'

                tfsi.append(tfs[next_scene] + [img_str])
                
                next_scene += 1
                if next_scene < len(tfs):            
                    target_time = tfs[next_scene][4]
                else:
                    break

    container.close()

    # Get CSS for inclusion in HTML 
    py_dir = os.path.dirname(__file__)
    css_path = os.path.join(py_dir, "visaid.css")
    with open(css_path, "r") as css_file:
        css_str = css_file.read()

    # create HTML string
    html_top = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>""" + proj_name + """</title>
<style>
""" + css_str + """
</style>
</head>
<body>
<div class='top'>Visual index from <br /><span class='proj'>""" + proj_name + """</span>
</div>
<div class='container'>
"""
    html_end = """
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
            html_start = "<a href='https://americanarchive.org/catalog/" + guid + "?proxy_start_time=" + start_sec + "'>" + start_str + "</a>"
        else:
            html_start = start_str

        html_img_tag = f'<img src="data:image/jpeg;base64,{f[5]}" />'
        html_cap = f'<span>{html_start} - {end_str}: {label}</span><br />'

        html_body += ("<div class='item'>" + html_cap + html_img_tag + "</div>")
        

    html_str = html_top + html_body + html_end

    if stdout:
        print(html_str)
        hfilename = None
        hfilepath = None
    else:
        hfilename = "visaid_" + proj_name + ".html"
        hfilepath = output_dirname + "/" + hfilename
        with open(hfilepath, "w") as html_file:
            html_file.write(html_str)
            print("Visual index created at " + hfilepath + ".")
    
    return (hfilename, hfilepath)
   

