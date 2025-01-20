"""
process_swt.py

Defines functions that perform processing on MMIF output from SWT.

The `default_to_none` parameter means that parameters not specified by the calling
function will have values of `None` instead of the values specified in 
`PROC_SWT_DEFAULTS`.
"""

import json

import pandas as pd

from mmif import Mmif
from mmif import AnnotationTypes

PROC_SWT_DEFAULTS = { "default_to_none": False,
                      "include_only": None,
                      "exclude": [],
                      "max_unsampled_gap": 120100,
                      "default_subsampling": 15100,
                      "subsampling": { 
                          "credits": 1900,
                          "slate": 7900 },
                      "include_first_frame": True,
                      "include_final_frame": True }


def get_swt_view_ids(mmif_str):
    """
    Takes a MMIF string and returns the IDs of the TimePoint containg view and the 
    TimeFrame containing view relevant to SWT processing
    
    NOTE:
    At this point in time, the implementation of this function is very naive and 
    assumes that there aren't a bunch of other views in the MMIF.  This function 
    will need to be updated to something smarter to deal with more heavily laden 
    MMIF files with multiple views containing TimePoint and TimeFrame annotations.
    """

    # turn the MMIF string into a Mmif object
    usemmif = Mmif(mmif_str)

    tp_views = usemmif.get_all_views_contain(AnnotationTypes.TimePoint)
    if len(tp_views):
        tp_view = tp_views[-1]
        tp_view_id = tp_view.id
    else:
        tp_view_id= None
    
    tf_views = usemmif.get_all_views_contain(AnnotationTypes.TimeFrame)
    if len(tf_views):
        tf_view = tf_views[-1]
        tf_view_id = tf_view.id
    else:
        tf_view_id = None

    return (tp_view_id, tf_view_id)



def get_mmif_metadata_str( mmif_str:str, tp_view_id:str, tf_view_id:str ):
    """
    Takes the metadata object from the view(s) specified.    
    Returns prettified serialized JSON for that metadata.
    
    This is a helper function for this module, not a general function for
    grabbing metadata from MMIF files. It is useful for extracting the 
    CLAMS metadata for inclusion in CLAMS consuming procedures.
    """

    # turn the MMIF string into a Mmif object
    usemmif = Mmif(mmif_str)

    if tp_view_id is None:
        tp_str = "{ }"
    else:
        tp_view = usemmif.get_view_by_id(tp_view_id)
        tp_str = str(tp_view.metadata)

    if tf_view_id is None:
        tf_str = "{ }"
    else:
        tf_view = usemmif.get_view_by_id(tf_view_id)
        tf_str = str(tf_view.metadata)

    mstr = "[ " + tp_str + ", " + tf_str + " ]"

    return json.dumps(json.loads(mstr), indent=2)



def get_CLAMS_app_vers( mmif_str:str, tp_view_id:str, tf_view_id:str ):
    """
    Takes the metadata from two the relevant views.  Then looks at the
    app metadata for each to find the version.
    
    Returns an ordered pair consisting of the version number used to 
    create each view.

    This is useful for conditional logic, where program execution depends
    on the version of the CLAMS app used.
    """

    usemmif = Mmif(mmif_str)

    # get the app version for TimePoint annotations
    if tp_view_id is None:
        tp_ver = None
    else:
        tp_view = usemmif.get_view_by_id(tp_view_id)
        tp_app = tp_view.metadata.app
        if tp_app.rfind("/v") != -1:
            tp_ver = tp_app[tp_app.rfind("/v")+1:]
        else:
            tp_ver = ""

    # get the app version for TimeFrame annotations
    if tf_view_id is None:
        tf_ver = None
    else:
        tf_view = usemmif.get_view_by_id(tf_view_id)
        tf_app = tf_view.metadata.app
        if tf_app.rfind("/v") != -1:
            tf_ver = tf_app[tf_app.rfind("/v")+1:]
        else:
            tf_ver = ""
    
    return (tp_ver, tf_ver)



def tfs_from_mmif( mmif_str:str, 
                   tp_view_id:str="",
                   tf_view_id:str="" ):
    """
    Analyzes MMIF file from SWT, containining TimeFrame and TimePoint
    annotations, and returns tabular data.

    Takes serialized MMIF as a string as input.
    Returns a table (list of lists) representing the TimeFrame annotations

    Output columns:
    0: TimeFrame id (from MMIF file) (string)
    1: bin label (string)
    2: start time in milliseconds (int)
    3: stop time in milliseconds (int)
    4: representative still time in milliseconds (int)
    5: representative still point label (string)

    """
    # turn the MMIF string into a Mmif object
    usemmif = Mmif(mmif_str)

    # If there is no view with a TimeFrame, return an empty list.
    if len(usemmif.get_all_views_contain(AnnotationTypes.TimeFrame)) == 0:
        print("Warning: MMIF file contained no TimeFrame annotations.")
        tfs = []
    else:
        # Get the correct views for TimePoint and TimeFrame annotations.
        # If these have not been supplied, make the traditional (simple) 
        # assumptions about which views to get, i.e., the last (end of list)
        # view that contains annotations of the relevant type.
        if tp_view_id != "":
            tp_view = usemmif.get_view_by_id(tp_view_id)
        else:
            tp_view = usemmif.get_all_views_contain(AnnotationTypes.TimePoint)[-1]         

        if tf_view_id != "":
            tf_view = usemmif.get_view_by_id(tf_view_id)
        else:
            tf_view = usemmif.get_all_views_contain(AnnotationTypes.TimeFrame)[-1]

        # Get information about the app version from the TimeFrame view
        # If version >= 6.0, use view ID prefix for time point refs
        app = tf_view.metadata.app
        try:
            app_ver = float(app[app.rfind("/v")+2:])
            
            # For SWT v6.0 and above, TimePoints targeted by other frames include
            # a reference to the view from which they came.
            if app_ver > 5.9999:
                ref_prefix = tp_view.id + ":"
            else:
                ref_prefix = ""
        except Exception as e:
            print("Error:", e)
            print("Could not get app version.")
            print("Assuming version less than 6.0")
            ref_prefix = ""

        # Drill down to the annotations we're after, creating generators
        tfanns = tf_view.get_annotations(AnnotationTypes.TimeFrame)
        tpanns = tp_view.get_annotations(AnnotationTypes.TimePoint)

        # Build two lists, one of TimeFrames and one of TimeFrame+Points
        tfs = []
        tfpts = []   
        for ann in tfanns:
            tf_id = ann.get_property("id")
            tf_frameType = ann.get_property("frameType")

            # add timeFrames to their list; no values for times yet
            tfs += [[tf_id, tf_frameType, -1, -1, -1, ""]]
            

            # add timeFrame points to their list
            for t in ann.get_property("targets"):
                is_rep = t in ann.get_property("representatives")
                tfpts += [[ tf_id, tf_frameType, t, is_rep ]]

        # Build another list for TimePoints
        tps = []
        for ann in tpanns:
            
            tpt_id = ref_prefix + ann.get_property("id") # new, for v6.0 and above

            tps += [[ tpt_id, 
                    ann.get_property("label"), 
                    ann.get_property("timePoint") ]]  

        #print("Lengths (tfs, tfpts, tps):", (len(tfs), len(tfpts), len(tps))) # DIAG

        # create DataFrames from lists and merge
        tfpts_df = pd.DataFrame(tfpts, columns=['tf_id','frameType','tp_id','is_rep'])
        tps_df = pd.DataFrame(tps, columns=['tp_id','label','timePoint'])
        tfs_tps_df = pd.merge(tfpts_df,tps_df)

        # iterate through the timeFrames and use the merged DataFrame to look up times
        # (need to cast np.int64 values to ordinary int)
        for f in tfs:
            tfrows = tfs_tps_df[ tfs_tps_df["tf_id"] == f[0] ]

            # within rows for this time frame, find start and end times
            tf_start_time = int( (tfrows["timePoint"]).min() )
            tf_end_time = int( (tfrows["timePoint"]).max() )
            #tf_rep_time = int( (tfrows[tfrows["is_rep"]]["timePoint"]).min() )
            #tf_rep_label = ""  

            # narrow down to rows that are rep time points, and choose one
            tfreprows = tfrows[tfrows["is_rep"]]
            chosen_row_index = (len(tfreprows) - 1) // 2
            #print("Num reps:", len(tfreprows), "; chosen index:", chosen_row_index) # DIAG
            tfreprow = tfreprows.iloc[chosen_row_index]
            tf_rep_time = int( tfreprow["timePoint"] )
            tf_rep_label = tfreprow["label"]
            #print(tf_rep_time, tf_rep_label) # DIAG

            f[2] = tf_start_time
            f[3] = tf_end_time
            f[4] = tf_rep_time
            f[5] = tf_rep_label 

        # sort list of timeFrames by start
        tfs.sort(key=lambda f:f[2])

    return tfs



def last_time_in_mmif( mmif_str:str, tp_view_id:str="" ):
    """
    Analyzes MMIF with timepoints and returns the last time
    Takes serialized MMIF as a string as input.
    """

    # turn the MMIF string into a Mmif object
    usemmif = Mmif(mmif_str)

    # Get the right view.  
    # (If it has not been supplied, make a reasonable assumption about which
    # one to get.)
    if tp_view_id != "":
        tp_view = usemmif.get_view_by_id(tp_view_id)
    else:
        tp_view = usemmif.get_all_views_contain(AnnotationTypes.TimePoint)[-1]

    tpanns = tp_view.get_annotations(AnnotationTypes.TimePoint)

    last_time = 0
    for ann in tpanns:
        if ann.get_property("timePoint") > last_time:
            last_time = ann.get_property("timePoint")

    return last_time



def adjust_tfs( tfs_in:list, 
                last_time: int,
                params_in:dict ):
    """
    Adds extra rows to the array returned by `tfs_from_mmif()`.  
    """

    # Warn about spurious parameters
    for key in params_in:
        if key not in PROC_SWT_DEFAULTS:
            print("Warning: `" + key + "` is not a valid parm for tfs adjustment. Ignoring.")

    # Sanatize params
    params = {}
    
    if "default_to_none" in params_in:
        params["default_to_none"] = params_in["default_to_none"]
    elif "default_to_none" in PROC_SWT_DEFAULTS:
        params["default_to_none"] = PROC_SWT_DEFAULTS["default_to_none"]
    else:
        params["default_to_none"] = False

    for key in PROC_SWT_DEFAULTS:
        if key in params_in:
            params[key] = params_in[key]
        elif not params["default_to_none"]:
            params[key] = PROC_SWT_DEFAULTS[key]
        else:
            params[key] = None


    # Make a copy of the input list, so not to alter it
    tfs = tfs_in[:]

    # Go ahead and filter out scene types, according to parameters
    if params["include_only"] is not None:
        tfs = [ tf for tf in tfs if tf[1] in params["include_only"] ]
    
    if params["exclude"] is not None and len(params["exclude"]) > 0:
        tfs = [ tf for tf in tfs if tf[1] not in params["exclude"] ]

    # add frames for first and last timepoints 
    # (Because gaps have to be between timepoints, and we want to catch gaps
    # at the beginning and end.)
    # These may be removed later, but we may need them for other parts of this
    # process.
    tfs.insert(0, ['f_0', 'first frame', 0, 0, 0, ""])
    tfs.append(['f_n', 'last frame', last_time, last_time, last_time, ""])


    # If this parameter has been passed in with a non-zero valueto the function, 
    # then intersperse sample non-labeled frames among labeled timeframes.
    # The max_gap value controls the largest gap without the addtition
    # of an interspersed frame.
    if params["max_unsampled_gap"]: 
        max_gap = params["max_unsampled_gap"]

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

                    samples.append([tf_id, 'unlabeled sample', sample_start, sample_end, sample_rep, ""])
                    sample_counter += 1

        # add samples to timeframes and re-sort
        tfs += samples
        tfs.sort(key=lambda f:f[2])


    # Add extra samples scenes for longer scenes  (like credits sequences)
    if params["subsampling"] is not None or params["default_subsampling"] is not None:

        subsampling = {}
        if params["default_subsampling"] is None:
            subsampling = params["subsampling"]
        else:
            bin_labels = set( [ tf[1] for tf in tfs_in ] )
            for label in bin_labels:
                subsampling[label] = params["default_subsampling"]
            if params["subsampling"]:
                for label in params["subsampling"]:
                    subsampling[label] = params["subsampling"][label]


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

                    new_row = [ new_id, new_label, sample_start, sample_end, sample_rep, "" ]
                    new_samples.append(new_row)

                    sample_start = sample_end

                scene_samples += new_samples
                sampled_scene_ids.append(row[0])
        
        # Add new samples to tfs
        tfs += scene_samples
        
    # if appropriate, remove first frame and last frame pseudo-annotations
    to_remove = []
    if not params["include_first_frame"]:
        to_remove.append('f_0')
    if not params["include_final_frame"]:
        to_remove.append('f_n')
    if len(to_remove) > 0:
        tfs = [ row for row in tfs if row[0] not in to_remove ]

    # pprint.pprint(tfs) # DIAG
    tfs.sort(key=lambda f:f[2])
    return tfs




def list_tfs( mmif_str:str, 
              tp_view_id:str="",
              tf_view_id:str="",
              max_gap:int=0, 
              include_startframe:bool=False,
              include_endframe:bool=False,
              subsampling:dict=None):
    """
    Analyzes MMIF file from SWT, makes requested additions, and returns tabular 
    data.

    Takes serialized MMIF as a string as input, along with optional params.
    Returns a table (list of lists) representing the timeFrame annotations

    This function is primarily a wrapper+processingor around `tfs_from_mmif()`.  
    If all arguments besides the `mmif_str` are left as defaults, then the 
    output will be the same as from `tfs_from_mmif(mmif_str)`.

    Output columns:
    0: TimeFrame id (from MMIF file) (string)
    1: bin label (string)
    2: start time in milliseconds (int)
    3: stop time in milliseconds (int)
    4: representative still time in milliseconds (int)
    5: representative still point label (string)

    """

    # Run the functions that provide the raw ingreidents for this.
    tfs = tfs_from_mmif( mmif_str, tp_view_id=tp_view_id, tf_view_id=tf_view_id )
    last_time = last_time_in_mmif( mmif_str, tp_view_id=tp_view_id )

    # add frames for first and last timepoints 
    # (Because gaps have to be between timepoints, and we want to catch
    # gaps at the beginning and end.)
    # These may be removed later
    tfs.insert(0, ['f_0', 'first frame', 0, 0, 0])
    tfs.append(['f_n', 'last frame', last_time, last_time, last_time, ""])

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

                    samples.append([tf_id, 'unlabeled sample', sample_start, sample_end, sample_rep, ""])
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

                    new_row = [ new_id, new_label, sample_start, sample_end, sample_rep, "" ]
                    new_samples.append(new_row)

                    sample_start = sample_end

                scene_samples += new_samples
                sampled_scene_ids.append(row[0])
        
        # Add new samples to tfs
        tfs += scene_samples
        
    # if appropriate, remove first frame and last frame pseudo-annotations
    to_remove = []
    if not include_startframe:
        to_remove.append('f_0')
    if not include_endframe:
        to_remove.append('f_n')
    if len(to_remove) > 0:
        tfs = [ row for row in tfs if row[0] not in to_remove ]

    # pprint.pprint(tfs) # DIAG
    tfs.sort(key=lambda f:f[2])
    return tfs

