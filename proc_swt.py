"""
process_swt.py

Defines functions that perform processing on MMIF output from SWT.

The `default_to_none` parameter means that parameters not specified by the calling
function will have values of `None` instead of the values specified in 
`PROC_SWT_DEFAULTS`.
"""

import json
from pprint import pprint # DIAG

import pandas as pd

from mmif import Mmif
from mmif import AnnotationTypes

try:
    # if being run from higher level module
    from . import lilhelp
except ImportError:
    # if run as stand-alone
    import lilhelp


PROC_SWT_DEFAULTS = { "default_to_none": False,
                      "include_only": None,
                      "exclude": [],
                      "max_unsampled_gap": 120100,
                      "subsampling": { 
                          "credits": 1900,
                          "chyron": 15100,
                          "slate": 9900 },
                      "default_subsampling": 30100,
                      "include_first_time": False,
                      "include_final_time": False }


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
    grabbing metadata from MMIF files. It is useful for extracting serialized
    CLAMS metadata for inclusion or display in CLAMS consuming procedures.
    """

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
    
    Returns an ordered pair comprising the version numbers used to create
    the views.

    This is useful for conditional logic, where program execution depends
    on the version(s) of the CLAMS app used.
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



def first_final_time_in_mmif( mmif_str:str, tp_view_id:str="" ):
    """
    Takes serialized MMIF as a string as input.
    Analyzes MMIF with TimePoints and returns the times of the first and final ones.
    """

    usemmif = Mmif(mmif_str)

    # Get the right view.  
    # (If it has not been supplied, make a reasonable assumption about which one.)
    if tp_view_id != "":
        tp_view = usemmif.get_view_by_id(tp_view_id)
    else:
        tp_view = usemmif.get_all_views_contain(AnnotationTypes.TimePoint)[-1]

    tpanns = tp_view.get_annotations(AnnotationTypes.TimePoint)

    first_time = 86400000
    final_time = 0
    for ann in tpanns:
        if ann.get_property("timePoint") < first_time:
            first_time = ann.get_property("timePoint")
        if ann.get_property("timePoint") > final_time:
            final_time = ann.get_property("timePoint")

    return first_time, final_time



def tfs_from_mmif( mmif_str:str, 
                   tp_view_id:str="",
                   tf_view_id:str="" ):
    """
    Analyzes MMIF file from SWT, combining  TimeFrame and TimePoint annotations, 
    and returns tabular data.

    Takes serialized MMIF as a string as input.
    Returns a table (list of lists) representing the TimeFrame annotations

    Columns of returned "tfs" table of scene time frames:
        0: TimeFrame id (from MMIF file) (string)
        1: bin label (string)
        2: start time in milliseconds (int)
        3: end time in milliseconds (int)
        4: representative still time in milliseconds (int)
        5: representative still point label (string)
    """

    usemmif = Mmif(mmif_str)

    # If there is no view with a TimeFrame, return an empty list.
    if len(usemmif.get_all_views_contain(AnnotationTypes.TimeFrame)) == 0:
        print("Warning: MMIF file contained no TimeFrame annotations.")
        tfs = []
    else:
        # Get the correct views for TimePoint and TimeFrame annotations.
        # If these have not been supplied, make simple assumptions about which 
        # views to get, i.e., the last (end of list) view that contains 
        # annotations of the relevant type.
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

        # Go through the TimeFrame annotations
        # Build two lists, one of TimeFrames and one of TimeFrame + target TimePoints
        tfs = []
        tfpts = []   
        for ann in tfanns:
            tf_id = ann.get_property("id")
            tf_frameType = ann.get_property("frameType")

            # Add timeFrames to the main table of scenes.
            # As of yet, there are no values for the times.  
            # These will be added later, on the basis of the join between the 
            # TimeFrames and their target TimePoints.
            tfs += [[tf_id, tf_frameType, -1, -1, -1, ""]]

            # Add target TimePoints of each TimeFrame to a list of their own.
            for tp_id in ann.get_property("targets"):
                is_rep = tp_id in ann.get_property("representatives")
                tfpts += [[ tf_id, tf_frameType, tp_id, is_rep ]]

        # Go through the TimePoint annotations
        # Build a list for putre TimePoints
        tps = []
        for ann in tpanns:
            
            # Compose the TimePoint id for purposes of joining view id and annotation id
            # (As of SWT v6.0 and above, this is necessary.)
            tpt_id = ref_prefix + ann.get_property("id") 

            tps += [[ tpt_id, 
                      ann.get_property("label"), 
                      ann.get_property("timePoint") ]]  

        #print("Lengths (tfs, tfpts, tps):", (len(tfs), len(tfpts), len(tps))) # DIAG

        # Create DataFrames from lists and perform a merge (join)
        tfpts_df = pd.DataFrame(tfpts, columns=['tf_id','frameType','tp_id','is_rep'])
        tps_df = pd.DataFrame(tps, columns=['tp_id','label','timePoint'])
        tfs_tps_df = pd.merge(tfpts_df,tps_df)

        # Iterate through the scenes in tfs and use the merged DataFrame to look up times
        # (need to cast np.int64 values to ordinary int)
        for tf in tfs:

            # perform lookup
            tfrows = tfs_tps_df[ tfs_tps_df["tf_id"] == tf[0] ]

            # within rows for this time frame, find start and end times
            tf_start_time = int( (tfrows["timePoint"]).min() )
            tf_end_time = int( (tfrows["timePoint"]).max() )

            # narrow down to rows that are rep time points, and choose one from the middle
            tfreprows = tfrows[tfrows["is_rep"]]
            chosen_row_index = (len(tfreprows) - 1) // 2
            tfreprow = tfreprows.iloc[chosen_row_index]
            tf_rep_time = int( tfreprow["timePoint"] )
            tf_rep_label = tfreprow["label"]

            tf[2] = tf_start_time
            tf[3] = tf_end_time
            tf[4] = tf_rep_time
            tf[5] = tf_rep_label 

        # sort list of timeFrames by start time
        tfs.sort(key=lambda f:f[2])

    return tfs



def adjust_tfs( tfs_in:list, 
                first_time:int,
                final_time:int,
                params_in:dict ):
    """
    Adds and/or removes rows to the array returned by `tfs_from_mmif()`.  

    The data structure for the table output is the same as in the input `tfs` table.

    Ajdustments are made on the basis of the parameter values passed in.
    """

    # Warn about spurious parameters
    for key in params_in:
        if key not in PROC_SWT_DEFAULTS:
            print("Warning: `" + key + "` is not a valid param for tfs adjustment. Ignoring.")

    # Set parameters not passed in to their defaul values
    # If "default_to_none" is True, then parameters not explicitly passed in will be 
    # assigned the `None` value.
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
        elif params["default_to_none"]:
            params[key] = None
        else:
            params[key] = PROC_SWT_DEFAULTS[key]


    # Make a copy of the input list, so not to alter it
    tfs = tfs_in[:]

    # Go ahead and filter out scene types, according to parameters
    if params["include_only"] is not None:
        tfs = [ tf for tf in tfs if tf[1] in params["include_only"] ]
    
    if params["exclude"] is not None and len(params["exclude"]) > 0:
        tfs = [ tf for tf in tfs if tf[1] not in params["exclude"] ]

    # Add frames for first and final timepoints.
    # These may be removed later, but we add them for now.
    # (The main reason for this is that we want to be able to find gaps where
    # there are no scene annotations, including the beginning and end of the video.
    # Logically, scene gaps must be between seens.  So we need beginning and ending
    # scenes in order to catch the gaps.)
    tfs.insert(0, ['f_0', 'first frame checked', first_time, first_time, first_time, ""])
    tfs.append(['f_n', 'last frame checked', final_time, final_time, final_time, ""])


    #
    # Gap sampling
    # 
    # If this parameter has been passed in with a non-zero value to the function, 
    # then intersperse sampled of non-labeled scenes among labeled scenes.
    #
    # The "max_unsampled_gap" value controls the largest gap between scenes that does
    # not trigger the addtition of interspersed samples.
    # 
    if params["max_unsampled_gap"]: 
        max_gap = params["max_unsampled_gap"]

        # Samples scenes are primarily useful for their central frame, but they need a 
        # duration to be represented in the tfs data structure.
        #
        # As long as the duration is less than the maximum gap, then the choice of sample
        # duration is somewhat arbitrary.
        sample_dur = max_gap // 2

        # collect samples to add to the main table of scenes
        samples = []

        # index for use in the scene's id and label
        next_sample_num = 1

        # Iterate through existing time frames to identify gaps in which to 
        # insert samples.  Specifically, for each time frame, after the first,
        # look back to see how much time since the last one.  If that gap is 
        # bigger than the max_gap, then make one or more samples.
        for rnum in range(1, len(tfs)) :
            
            # calculate the distance between the start of the current frame
            # and the end of the previous
            full_gap = tfs[rnum][2] - tfs[rnum-1][3]

            if full_gap > max_gap :

                # Figure out how many samples to make
                num_samples = full_gap // max_gap

                # Calculate the size of the gaps within which we'll locate new samples
                gap_size = full_gap // num_samples

                # collect samples (we'll add them into tfs later)
                for sample_count in range(num_samples):

                    # gap starts from the end of the last main scene, then offset by the
                    # samples we've already made in this full gap
                    gap_start = tfs[rnum-1][3] + ( sample_count * gap_size )

                    sample_id = "s_" + str(next_sample_num)                    
                    sample_label = "unlabeled sample"
                    sample_start = gap_start + (gap_size - sample_dur)//2
                    sample_end = sample_start + sample_dur
                    sample_rep = sample_start + sample_dur//2

                    samples.append([sample_id, sample_label, sample_start, sample_end, sample_rep, ""])
                    next_sample_num += 1

        # add all the samples collected to the tfs list 
        tfs += samples

    # 
    # Scene subsampling
    # (Add extra samples scenes for longer scenes (especially, e.g., credits sequences) )
    #
    if params["subsampling"] is not None or params["default_subsampling"] is not None:

        # First, collect the subsampling thresholds for each scene type
        subsampling = {}
        if params["default_subsampling"] is None:
            # no default subsampling; just use subsampling specified in params dictionary
            subsampling = params["subsampling"]
        else:
            # assign subsampling for all frame types
            bin_labels = set( [ tf[1] for tf in tfs_in ] )
            for label in bin_labels:
                # go ahead and set subsampling for all labels to the default value
                subsampling[label] = params["default_subsampling"]
            if params["subsampling"]:
                # overwrite the default value for subampling values specified in params dictionary
                for label in params["subsampling"]:
                    subsampling[label] = params["subsampling"][label]

        # Check for and remove invalid subsampling threshold values
        invalid_subsamples = []
        for scenetype in subsampling:
            if not ( subsampling[scenetype] > 0 and subsampling[scenetype] < 9000000 ):
                print("Ignoring invalid scene sampling:", scenetype, ":", subsampling[scenetype])
                invalid_subsamples.append(scenetype)
        for scenetype in invalid_subsamples:
            del subsampling[scenetype]

        # collect new rows for the new samples
        new_scenes = []

        # iterate through scene rows of tfs for which the label is subejct to subsampling
        for tf in [ tf for tf in tfs if tf[1] in subsampling]:

            # duration for the entire scene
            scene_dur = tf[3] - tf[2]

            # check to see whether this scene meets the subsampling threshold for its label
            if scene_dur > subsampling[tf[1]] :

                # We want enough subsample scenes so that each is shorter than the 
                # subsampling threshold.
                # Example: 36s scene with 10s subsampling -> 4 x 9s subsample scenes
                num_subsamples = ( scene_dur // subsampling[tf[1]] ) + 1        
                subsample_dur = scene_dur // num_subsamples

                subsamples = []   # subsample scenes to be collected for this scene
                next_start = tf[2]  # first subsample starts at start of the long scene
                
                for _ in range(num_subsamples):
                    subsample_id = tf[0] + "_s_" + str(len(subsamples))
                    subsample_label = tf[1] + " subsample"
                    subsample_start = next_start
                    subsample_end = next_start + subsample_dur
                    subsample_rep = next_start + ( subsample_dur // 2 )

                    subsample = [ subsample_id, subsample_label, 
                                  subsample_start, subsample_end, 
                                  subsample_rep, "" ]
                    subsamples.append(subsample)

                    next_start = subsample_end
                
                # Done with this scene.  Add new samples to running list of new scenes
                new_scenes += subsamples

        # Done iterating through labeled scenes.  Add the new scenes the main list.
        tfs += new_scenes

        
    # If appropriate, remove first frame and final scenes (which were inserted above)
    to_remove = []
    if not params["include_first_time"]:
        to_remove.append('f_0')
    if not params["include_final_time"]:
        to_remove.append('f_n')
    if len(to_remove) > 0:
        tfs = [ row for row in tfs if row[0] not in to_remove ]

    tfs.sort(key=lambda f:f[2])
    return tfs


def display_tfs(tfs:list):
    """
    This function simply prints a simple table of TimeFrame annotations from a tfs table
    """
    tfs_pretty = []
    for f in tfs:
        tfs_pretty += [[ f"{f[2]:08}", 
                         lilhelp.tconv(f[2]), 
                         lilhelp.tconv(f[3]), 
                         f[1] ]]
    pprint(tfs_pretty)
