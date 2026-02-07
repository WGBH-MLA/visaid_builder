"""
proc_swt.py

Defines functions that perform processing on MMIF output from SWT.

The primary functions here are:
`tfs_from_mmif` - creates a tfs array from an MMIF file
`adjust_tfs` - makes adjustments to a tfs array

The `adjust_tfs` function takes a parameter called `params_in` that tell it
what adjustments to make.  These are the kinds of options specified by the
parameters for the visaid builder.  

The valid keys for `params_in` are as follows:
    "default_to_none" (bool) - If True, then parameters not specified when `adjust_tfs` 
    is called will get the value None instead of the values specified in 
    `PROC_SWT_DEFAULTS`.  

    "include_only" (list) - A list of postbin categories such that only those bins should
    be included.  

    "exclude" (list) - A list of postbin categories that should be excluded.

    "max_unsampled_gap" (int) - The maximumn number of milliseconds to go without adding a
    sample not included in a scene.  Use None to get no unlabeled samples.

    "subsampling" (dict) - Key value pairs indicating the milliseconds sampling rate. The 
    idea is to create enough subsample scenes so that each is shorter than the subsampling threshold.
    Example: 36s scene with 10s subsampling -> 4 x 9s subsample scenes

    "include_first_time" (bool) - Whether to add the first video frame

    "include_final_frame" (bool) - Whether to add the final video frame

"""

import json
import logging
from pprint import pprint 

from mmif import Mmif
from mmif import AnnotationTypes
from mmif import DocumentTypes

from . import lilhelp


# These paramaters for which there are defaults are used by `adjust_tfs`.
# These default values are used only if 
#   1) the key is not included in `params_in`
#   2) the value of "default_to_none" is `False`.
PROC_SWT_DEFAULTS = { "default_to_none": True,
                      "include_only": None,
                      "exclude": [],
                      "max_unsampled_gap": 60000,
                      "subsampling": { 
                          "bars": 120100,
                          "credits": 1900,
                          "chyron": 15100,
                          "person & chyron": 15100,
                          "other text": 4900,
                          "slate": 9900 },
                      "default_subsampling": 30100,
                      "include_first_time": False,
                      "include_final_time": False }


def get_swt_view_ids(usemmif:Mmif):
    """
    Takes a MMIF string and returns the IDs of the TimePoint containg view and the 
    TimeFrame containing view relevant to SWT processing
    
    NOTE:
    This function assumes that a valid view will have "swt-detection" as a substring 
    of the view metadata "app" property.

    If there are several views fiting the criteria, this function picks the *final*
    such view.
    """

    tp_views = usemmif.get_all_views_contain(AnnotationTypes.TimePoint)
    swt_tp_views = [ view for view in tp_views 
                     if view.metadata.app.find("swt-detection") > -1 ]
    if len(swt_tp_views):
        tp_view = swt_tp_views[-1]
        tp_view_id = tp_view.id
    else:
        tp_view_id= None
    
    tf_views = usemmif.get_all_views_contain(AnnotationTypes.TimeFrame)
    swt_tf_views = [ view for view in tf_views 
                     if view.metadata.app.find("swt-detection") > -1 ]
    if len(swt_tf_views):
        tf_view = swt_tf_views[-1]
        tf_view_id = tf_view.id
    else:
        tf_view_id = None

    return (tp_view_id, tf_view_id)


def get_td_view_id(usemmif:Mmif):
    """
    Takes a MMIF string and returns the ID of a view with TextDocument annotations
    from a captioner app.
    
    NOTE:
    This function assumes that a valid view will have "captioner" as a substring 
    of the view metadata "app" property.

    If there are several views fiting the criteria, this function picks the *first*
    such view.
    """

    td_views = usemmif.get_all_views_contain(DocumentTypes.TextDocument)
    cap_td_views = [ view for view in td_views 
                     if view.metadata.app.find("captioner") > -1 ]

    if len(cap_td_views):
        td_view = cap_td_views[0]
        td_view_id = td_view.id
    else:
        td_view_id= None

    return td_view_id


def get_mmif_metadata_str( usemmif:Mmif, tp_view_id:str, tf_view_id:str ):
    """
    Takes the metadata object from the view(s) specified.    
    Returns prettified serialized JSON for that metadata.
    
    This is a helper function for this module, not a general function for
    grabbing metadata from MMIF files. It is useful for extracting serialized
    CLAMS metadata for inclusion or display in CLAMS consuming procedures.
    """

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



def get_CLAMS_app_ver( usemmif:Mmif, view_id:str ):
    """
    Gets the CLAMS version number for a given view

    This is useful for conditional logic, where program execution depends
    on the version(s) of the CLAMS app used.
    """

    if view_id is None:
        ver = None
    else:
        view = usemmif.get_view_by_id(view_id)
        app = view.metadata.app
        if app.rfind("/v") != -1:
            ver = app[app.rfind("/v")+1:]
        else:
            ver = ""
    
    return ver



def first_final_time_in_mmif( usemmif:Mmif, tp_view_id:str="" ):
    """
    Takes serialized MMIF as a string as input.
    Analyzes MMIF with TimePoints and returns the times of the first and final ones.
    """

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



def tfsd_from_mmif( usemmif:Mmif, 
                    tp_view_id:str, 
                    tf_view_id:str,
                    td_view_id:str 
                    ):
    """
    Analyzes MMIF file from SWT, combining  TimeFrame and TimePoint annotations, 
    along with associated TextDocument annotations.  
    It returns tabular data (as a list of dictionaries).

    This function is like the original `tfs_from_mmif` function for SWT, except 
    returning a list of dictionaries (and allowing additional fields).

    Takes serialized MMIF as a string as input.
    Returns a list of dictionaries representing the TimeFrame annotations

    Columns of returned "tfsd" table:
      (0) "tf_id":    TimeFrame ID (from MMIF file) (string)
      (1) "tf_label": TimeFrame label (string)
      (2) "start":    start time in milliseconds (int)
      (3) "end":      end time in milliseconds (int)
      (4) "tp_time":  representative still time in milliseconds (int)
      (5) "tp_label": representative still point label (string)
      (-) "tp_id":    TimePoint ID (from MMIF file) of representative time point
      (-) "td_id":    TextDocument ID (from MMIF file)
      (-) "text":     text from the TextDocument
    """

    # If there is no view with a TimeFrame, return an empty list.
    if tf_view_id is None:
        logging.info("MMIF file contained no SWT TimeFrame annotations.")
        tfsd = []
        return tfsd

    # Otherwise, get the relevant views
    tp_view = usemmif.get_view_by_id(tp_view_id)
    tf_view = usemmif.get_view_by_id(tf_view_id)
    if td_view_id is not None:
        td_view = usemmif.get_view_by_id(td_view_id)
    else:
        logging.info("MMIF file contained no captioner TextDocument annotations.")
        td_view = None

    # Collect TD annotations 
    # (list of dictionaries of TDs)
    tds = []
    if td_view is not None:
        # First, get mapping of TD ann to its ource TP ann
        tas = {}
        for ann in td_view.get_annotations(AnnotationTypes.Alignment):
            tas[ann.get_property("target")] = ann.get_property("source") 

        # Build a list of TD anns along with source TP
        for ann in td_view.get_annotations(DocumentTypes.TextDocument):
            td = {}
            td["td_id"] = ann.get_property("id")
            td["tf_id"] = ann.get_property("origin")
            td["tp_id"] = tas[td["td_id"]]
            td["text"] = ann.get_property("text").value
            tds.append(td)

    # Collect TP anns
    # (dictionary keyed by TP ann ID)
    tps = {}
    for ann in tp_view.get_annotations(AnnotationTypes.TimePoint):
        tps[ann.get_property("id")] = {
            "time": ann.get_property("timePoint"),
            "tp_label": ann.get_property("label") }

    # Build a list of TF anns
    # (list of dictionaries of TFs)
    tfsd = []
    for ann in tf_view.get_annotations(AnnotationTypes.TimeFrame):
        tf = {}
        tf["tf_id"] = ann.get_property("id")
        tf["tf_label"] = ann.get_property("frameType")
        
        # iterate through target TPs to get start time and end time
        tf["start"] = 36000000 # 10 hours
        tf["end"] = -1
        for tp_id in ann.get_property("targets"):
            if tps[tp_id]["time"] < tf["start"]:
                tf["start"] = tps[tp_id]["time"]
            if tps[tp_id]["time"] > tf["end"]:
                tf["end"] = tps[tp_id]["time"]

        # see if we have data from a TD
        tftds = [ td for td in tds if td["tf_id"] == tf["tf_id"] ]
        if not len(tftds):
            tf["td_id"] = None
            tf["text"] = None
        else:
            if len(tftds) > 1:
                logging.info(f'More than one TextDocument annotation for TimeFrame {tf["tf_id"]}')
            td = tftds[0]
            tf["td_id"] = td["td_id"]
            tf["text"] = td["text"]
            if td["tp_id"] in ann.get_property("representatives"):
                # we have a rep chosen by the TextDocumemnt annotator; choose that as the TF rep
                tf["tp_id"] = td["tp_id"]

        # if we didn't get a rep TP before, then we have to choose one
        if "tp_id" not in tf:
            reps = []
            for tp_id in ann.get_property("representatives"):
                rep = { "tp_id": tp_id, 
                        "time": tps[tp_id]["time"] }
                reps.append(rep)
            reps.sort(key=lambda f:f["time"])

            # choose one from the middle
            tf["tp_id"] = reps[ (len(reps)-1)//2 ]["tp_id"] 

        # Now that we definitely have a rep, set the rep's time and label
        tf["tp_time"] = tps[tf["tp_id"]]["time"]
        tf["tp_label"] = tps[tf["tp_id"]]["tp_label"]

        tfsd.append(tf)

    # all done; sort and return
    tfsd.sort(key=lambda f:f["start"])
    return tfsd


def adjust_tfsd( tfsd_in:list, 
                 first_time:int,
                 final_time:int,
                 params_in:dict ):
    """
    Adds and/or removes rows to the array returned by `tfsd_from_mmif()`.  

    The data structure for the table output is the same as in the input `tfsd` table.

    Ajdustments are made on the basis of the parameter values passed in.
    """

    # Warn about spurious parameters
    for key in params_in:
        if key not in PROC_SWT_DEFAULTS:
            logging.warning("Warning: `" + key + "` is not a valid param for tfsd adjustment. Ignoring.")

    # Set parameters not passed in to their defaul values
    # If "default_to_none" is True, then parameters not explicitly passed in will be 
    # assigned the `None` value.
    params = {}

    # First, set the value for "default_to_none"
    if "default_to_none" in params_in:
        params["default_to_none"] = params_in["default_to_none"]
    elif "default_to_none" in PROC_SWT_DEFAULTS:
        params["default_to_none"] = PROC_SWT_DEFAULTS["default_to_none"]
    else:
        params["default_to_none"] = True

    # Now, set the values for the other keys
    for key in PROC_SWT_DEFAULTS:
        if key == "default_to_none":
            # value should be already set; don't want to re-set it
            params[key] = params[key]
        elif key in params_in:
            params[key] = params_in[key]
        elif not params["default_to_none"]:
            params[key] = PROC_SWT_DEFAULTS[key]
        else:
            params[key] = None

    # Make a (shallow) copy of the input list, so not to alter it
    tfsd = tfsd_in[:]

    # Go ahead and filter out scene types, according to parameters
    if params["include_only"] is not None:
        tfsd = [ tf for tf in tfsd if tf["tf_label"] in params["include_only"] ]
    
    if params["exclude"] is not None and len(params["exclude"]) > 0:
        tfsd = [ tf for tf in tfsd if tf["tf_label"] not in params["exclude"] ]
    
    # Sort just in case it was not already sorted
    tfsd.sort(key=lambda f:f["start"])

    # Add frames for first and final timepoints.
    # These may be removed later, but we add them for now.
    # (The main reason for this is that we want to be able to find gaps where
    # there are no scene annotations, including the beginning and end of the video.
    # Logically, scene gaps must be between seens.  So we need beginning and ending
    # scenes in order to catch the gaps.)
    first = {
      "tf_id": 'f_0',
      "tf_label": 'first frame checked',
      "start": first_time,
      "end": first_time, 
      "tp_time": first_time,
      "tp_label": None,
      "tp_id": None,
      "td_id": None,
      "text": None }
    tfsd.insert(0, first)

    final = {
      "tf_id": 'f_n',
      "tf_label": 'last frame checked',
      "start": final_time,
      "end": final_time, 
      "tp_time": final_time,
      "tp_label": None,
      "tp_id": None,
      "td_id": None,
      "text": None }
    tfsd.append(final)

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
        # duration to be represented in the tfsd data structure.
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
        for rnum in range(1, len(tfsd)) :
            
            # calculate the distance between the start of the current frame
            # and the end of the previous
            full_gap = tfsd[rnum]["start"] - tfsd[rnum-1]["end"]

            if full_gap > max_gap :

                # Figure out how many samples to make
                num_samples = full_gap // max_gap

                # Calculate the size of the gaps within which we'll locate new samples
                gap_size = full_gap // num_samples

                # collect samples (we'll add them into tfsd later)
                for sample_count in range(num_samples):

                    # gap starts from the end of the last main scene, then offset by the
                    # samples we've already made in this full gap
                    gap_start = tfsd[rnum-1]["end"] + ( sample_count * gap_size )

                    sample_id = "s_" + str(next_sample_num)                    
                    sample_label = "unlabeled sample"
                    sample_start = gap_start + (gap_size - sample_dur)//2
                    sample_end = sample_start + sample_dur
                    sample_rep = sample_start + sample_dur//2

                    sample = {
                        "tf_id": sample_id,
                        "tf_label": sample_label,
                        "start": sample_start,
                        "end": sample_end, 
                        "tp_time": sample_rep,
                        "tp_label": None,
                        "tp_id": None,
                        "td_id": None,
                        "text": None }
                    samples.append(sample)

                    next_sample_num += 1

        # add all the samples collected to the tfsd list 
        tfsd += samples

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
            bin_labels = set( [ tf["tf_label"] for tf in tfsd_in ] )
            for label in bin_labels:
                # go ahead and set subsampling for all labels to the default value
                subsampling[label] = params["default_subsampling"]
            if params["subsampling"]:
                # overwrite the default value for subsampling values specified in params dictionary
                for label in params["subsampling"]:
                    subsampling[label] = params["subsampling"][label]

        # Check for and remove invalid subsampling threshold values
        invalid_subsamples = []
        for scenetype in subsampling:
            if not ( subsampling[scenetype] > 0 and subsampling[scenetype] < 9000000 ):
                logging.warning("Ignoring invalid scene sampling:", scenetype, ":", subsampling[scenetype])
                invalid_subsamples.append(scenetype)
        for scenetype in invalid_subsamples:
            del subsampling[scenetype]

        # collect new rows for the new samples
        new_scenes = []

        # iterate through scene rows of tfsd for which the label is subejct to subsampling
        for tf in [ tf for tf in tfsd if tf["tf_label"] in subsampling]:

            # duration for the entire scene
            scene_dur = tf["end"] - tf["start"]

            # check to see whether this scene meets the subsampling threshold for its label
            if scene_dur > subsampling[tf["tf_label"]] :

                # We want enough subsample scenes so that each is shorter than the 
                # subsampling threshold.
                # Example: 36s scene with 10s subsampling -> 4 x 9s subsample scenes
                num_subsamples = ( scene_dur // subsampling[tf["tf_label"]] ) + 1        
                subsample_dur = scene_dur // num_subsamples

                subsamples = []           # subsample scenes to be collected for this scene
                next_start = tf["start"]  # first subsample starts at start of the long scene
                
                for _ in range(num_subsamples):
                    subsample_id = tf["tf_id"] + "_s_" + str(len(subsamples))
                    subsample_label = tf["tf_label"] + " - - -"
                    subsample_start = next_start
                    subsample_end = next_start + subsample_dur
                    subsample_rep = next_start + ( subsample_dur // 2 )

                    subsample = {
                        "tf_id": subsample_id,
                        "tf_label": subsample_label,
                        "start": subsample_start,
                        "end": subsample_end, 
                        "tp_time": subsample_rep,
                        "tp_label": None,
                        "tp_id": None,
                        "td_id": None,
                        "text": None }
                    subsamples.append(subsample)

                    next_start = subsample_end
                
                # Done with this scene.  Add new samples to running list of new scenes
                new_scenes += subsamples

        # Done iterating through labeled scenes.  Add the new scenes the main list.
        tfsd += new_scenes

        
    # If appropriate, remove first frame and final scenes (which were inserted above)
    to_remove = []
    if not params["include_first_time"]:
        to_remove.append('f_0')
    if not params["include_final_time"]:
        to_remove.append('f_n')
    if len(to_remove) > 0:
        tfsd = [ tf for tf in tfsd if tf["tf_id"] not in to_remove ]

    tfsd.sort(key=lambda f:f["start"])
    return tfsd


def tfsd_to_tfs(tfsd:list):
    """
    Takes a list in the tfsd style and returns the corresponding list in the
    deprecated tfs style.

    Columns of returned "tfs" table of scene time frames:
        0: TimeFrame id (from MMIF file) (string)
        1: bin label (string)
        2: start time in milliseconds (int)
        3: end time in milliseconds (int)
        4: representative still time in milliseconds (int)
        5: representative still point label (string)
    """
    tfs = []

    for tfd in tfsd:
        tf = [ tfd["tf_id"], 
               tfd["tf_label"],
               tfd["start"],
               tfd["end"],
               tfd["tp_time"],
               ( tfd["tp_label"] or "" ) ]
        tfs.append(tf)

    return tfs


def find_overlaps( tfsd: list) -> list:
    """
    This is a diagnostic function to identify overlapping scenes represented by the
    tfsd data structure.

    It returns a list of dictionaries describing overlaps.
    """
    
    # make a shallow copy of tfsd, since we'll be re-sorting
    tfsd = tfsd[:]

    # order time frames by starting ms
    tfsd.sort( key=lambda f:f["start"] )

    # iterate through timeframes and search for other time frames that start before
    # the end of the current one.
    overlaps = []
    for i in tfsd:
        for j in tfsd:
            if ( i["start"] <= j["start"] and
                 i["end"] >= j["start"] and
                 i["tf_id"] != j["tf_id"] 
                ):
                 overlap = {
                    "tf_id": i["tf_id"],
                    "tf_label": i["tf_label"],
                    "ov_id": j["tf_id"],
                    "ov_label": j["tf_label"],
                    "start": j["start"],
                    "end": min( i["end"], j["end"] ),
                    "dur": min( i["end"], j["end"] ) - j["start"] 
                 }
                 overlaps.append(overlap)
                    
    return overlaps



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


def display_tfsd(tfsd:list):
    """
    This function simply prints a simple table of TimeFrame annotations from a tfsd table
    """
    key_order = ["start","end","tf_id","tf_label","tp_time","tp_id","tp_label","td_id","text"]

    for tf in tfsd:
        line = ""
        for key in key_order:
            line += key 
            line += ":"
            line += str(tf[key])[:50]
            line += "\t"
        print(line)
