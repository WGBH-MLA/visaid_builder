"""
post_proc_item.py

Defines functions for doing post processing of MMIF created by SWT.

Assumes processing takes place in the context of job processing in the style of 
clams-kitchen, with `item` and `cf` dictionaries passed from the job runner 
routine.

Handles creation artifacts appearing in the VALID_ARTIFACTS global variable.

Handles options passed in via the `params` dict argument to the main function,
as long as they are defined in one of the option defauls global variables.

Explanation of particular options:

`prog_start_min` - The earliest valid start time for the program.  (We won't 
bother to set a proxy start time if the computed value is less than this.)

`prog_start_max` - The latest valid start time for the program.  (We won't 
look for the main program slate after this point. And we won't assign a proxy 
start time after this point.)

"""

# %%
# Run import statements

import csv
import json
import datetime

from mmif import Mmif


try:
    # if being run from higher level module
    from . import lilhelp
    from . import proc_swt
    from . import create_visaid
except ImportError:
    # if run as stand-alone
    import lilhelp
    import proc_swt
    import create_visaid



MODULE_VERSION = "0.30"


# These are the defaults specific to routines defined in this module.
POSTPROC_DEFAULTS = { "name": None,
                      "artifacts": [],
                      "prog_start_min": 3000,
                      "prog_start_max": 150000 }

# Names of the artifact types that this module can create
VALID_ARTIFACTS = [ "data", 
                    "slates",
                    "reps",
                    "ksl",
                    "visaids" ]

PROC_SWT_DEFAULTS = { "include_only": None,
                      "exclude": [
                          "garbage" ],
                      "max_unsampled_gap": 120100,
                      "default_subsampling": 15100,
                      "subsampling": { 
                          "credits": 1900,
                          "slate": 7900 },
                      "include_startframe": False,
                      "include_endframe": True }

VISAID_DEFAULTS = { "visibility": {
                        "bars": "on",
                        "filmed text": "off",
                        "other text": "on" },
                    "display_duration": True,
                    "job_id_in_visaid_filename": False,
                    "visaid_image_filanames": False,
                    "aapb_timecode_link": False }

# aliases specific to calculating/inferring proxy start time
BARS_BINS = ['bars', 'Bars']
SLATE_BINS = ['slate', 'Slate', 'S', 'S:H', 'S:C', 'S:D', 'S:B', 'S:G']


def run_post( item:dict, 
              cf:dict, 
              params:dict ):
    """
    Calls particular methods to run post processing for the item according to the 
    configuration specified in the `cf` and `params` dictionaries.
    """

    errors = []

    # 
    # Process and validate options passed in
    # 

    if "name" in params:
        if params["name"].lower() not in ["swt", "visaid_builder", "visaid-builder", "visaid"]:
            print("Post-processing error: Tried to run", params["name"],
                  "process with visaid_builder post-processing function.")
            errors.append("post_proc_name")
            return errors
    else:
        print("Post-processing error: No post-process or name specified.")
        errors.append("post_proc_name")
        return errors

    # Set up for the particular kinds of artifacts requested 
    if "artifacts" in params:
        artifacts = params["artifacts"]
        artifacts_dir = cf["artifacts_dir"]
    else:
        print("Warning: No artifacts specified.")  
        artifacts = []

    for atype in artifacts:
        if atype not in VALID_ARTIFACTS:
            print("Warning: Invalid artifact type '" + atype + "' will not be created.")
            print("Valid artifact types:", VALID_ARTIFACTS)

    # assign options based on input or default values
    #for key in params:
    #    if key not in OPTION_DEFAULTS


    if "prog_start_min" in params:
        prog_start_min = params["prog_start_min"]
    else:
        prog_start_min = POSTPROC_DEFAULTS["prog_start_min"]

    if "prog_start_max" in params:
        prog_start_max = params["prog_start_max"]
    else:
        prog_start_max = POSTPROC_DEFAULTS["prog_start_max"]

    if "subsampling" in params:
        subsampling = params["subsampling"]
    else:
        subsampling = None

    if "max_gap" in params:
        max_gap = params["max_gap"]
    elif "max_unsampled_gap" in params:
        max_gap = params["max_unsampled_gap"]
    else:
        max_gap = None

    #
    # Perform foundational processing of MMIF file
    #
    print("Attempting to process MMIF into SWT scene list...")

    # Open MMIF and start processing
    mmif_path = item["mmif_paths"][-1]
    with open(mmif_path, "r") as file:
        mmif_str = file.read()

    tp_view_id, tf_view_id = proc_swt.get_swt_view_ids(mmif_str)

    # call SWT MMIF processors to get a table of time frames
    tfs = proc_swt.list_tfs(mmif_str, 
                               tp_view_id=tp_view_id,
                               tf_view_id=tf_view_id,
                               max_gap=max_gap, 
                               subsampling=subsampling,
                               include_startframe=False,
                               include_endframe=True)

    print("SWT scene list of length", len(tfs), "created.")

    # get mmif_metadata_str
    mmif_metadata_str = proc_swt.get_mmif_metadata_str( mmif_str,
                                                           tp_view_id,
                                                           tf_view_id )

    #
    # Infer metadata
    #
    if "data" in artifacts:
        print("Attempting to infer data...")
        data_dir = artifacts_dir + "/data"

        # Calculate some significant datapoints based on table of time frames
        #
        # Note:  For reasons I don't understand, we have to cast some integer
        # values originally created by Pandas to int from int64

        # The end of the bars is the end of the last bars timeframe
        # If there is no bars timeframe, then the value is 0
        bars_end = 0
        bars_tfs = [ tf for tf in tfs 
                        if (tf[1] in BARS_BINS and tf[3] <= prog_start_max) ]
        if len(bars_tfs) > 0:
            bars_end = int(bars_tfs[-1][3])

        # Proxy starts at the end of the bars or the beginning of the slate,
        # whichever is greater
        # The main way that this can go wrong is if there is a false positive 
        # for a slate in the first period of the show, after some substantial
        # content has already begun playing.
        slate_begin = None
        slate_tfs = [ tf for tf in tfs 
                        if (tf[1] in SLATE_BINS and tf[3] <= prog_start_max)]
        if len(slate_tfs) > 0:
            slate_begin = int(slate_tfs[0][2])
            proxy_start_ms = max(bars_end, slate_begin)
        else:
            proxy_start_ms = bars_end
        
        if proxy_start_ms < prog_start_min:
            proxy_start_ms = 0

        # print("bars end:", bars_end, "slate begin:", slate_begin, "proxy start:", proxy_start_ms) # DIAG        

        proxy_start = proxy_start_ms // 1000
        print("Proxy start:", proxy_start)

        # get app names
        tp_ver, tf_ver = proc_swt.get_CLAMS_app_vers(mmif_str, tp_view_id, tf_view_id)

        data_artifact = [{ 
            "metadata": {
                "asset_id": item["asset_id"],
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "job_id": cf["job_id"],
                "process": "clams-kitchen/swt/post_proc_item",
                "process_version": MODULE_VERSION,
                "process_details": {
                    "swt-tp_version": tp_ver,
                    "swt-tf_version": tf_ver,
                    "min_proxy_start_ms": prog_start_min,
                    "max_proxy_start_ms": prog_start_max
                }
            },
            "data":{
                "proxy_start_time": proxy_start
            }
        }]
        # print(data_artifact) # DIAG 

        if (int(proxy_start) == 0):
            print("Will not create a data artifact for this item.")
        else:
            data_artifact_path = data_dir + "/" + item["asset_id"] + "_inferred_data.json"
            with open(data_artifact_path, "w", newline="") as file:
                json.dump(data_artifact, file, indent=2)
            print("Data artifact saved.")


    #
    # Extract the slate
    #
    if "slates" in artifacts:
        print("Attempting to save a slate...")
        slates_dir = artifacts_dir + "/slates"

        # The slate rep is the rep timepoint from from the first slate timeframe
        # If there is not slate timeframe, then the value is None
        slate_rep = None
        slate_tfs = [ tf for tf in tfs if tf[1] in SLATE_BINS ]
        if len(slate_tfs) > 0:
            slate_rep = int(slate_tfs[0][4])

        if slate_rep is not None:
            try:
                slates = lilhelp.extract_stills( 
                           item["media_path"], 
                           [ slate_rep ], 
                           item["asset_id"],
                           slates_dir,
                           verbose=False )
                if len(slates) == 1:
                    print("Slate saved.")
                else:
                    print("Warning: Saved", len(slates), "slates.")

            except Exception as e:
                print("Extraction of slate frame at", slate_rep ,"failed.")
                print("Error:", e)
                errors.append("get_slate")
            
        else:
            print("No slate found.")


    #
    # Extract representative stills from timeframes
    #
    if "reps" in artifacts:
        print("Attempting to save representative stills...")
        reps_dir = artifacts_dir + "/reps"

        if len(tfs) > 0:
            tps = [ tf[4] for tf in tfs ] 
            tps = list(set(tps))
            tps.sort()

            try:
               rep_images = lilhelp.extract_stills( 
                  item["media_path"], 
                  tps, 
                  item["asset_id"],
                  reps_dir,
                  verbose=False )

            except Exception as e:
               print("Extraction of frame failed.")
               print("Error:", e)  
               errors.append("get_reps")

            print("Saved", len(rep_images), "representative stills from", len(tfs), "scenes.")

        else:
            print("No scenes from which to extract stills.")


    # 
    # Create KSL-style index of still images extracted
    #
    if "ksl" in artifacts:
        print("Attempting to make a KSL-style index...")
        ksl_dir = artifacts_dir + "/ksl"

        if not get_reps:
            print("Cannot make index because representative stills were not extracted.")
        else:

            # build KSL data for this item
            ksl_arr = []
            for fname in rep_images:
                
                # extract the requersted frame time from the filename
                tp = int(fname.split("_")[2])

                # lookup label in tfs array
                #label = [ tf[5] for tf in tfs if tf[4] == tp ][0]
                label = ""

                if label.find(":") != -1:
                    label, sublabel = label.split(":")
                else:
                    sublabel = ""

                row = [ fname, label, sublabel, "Job ID: "+cf["job_id"] ]
                ksl_arr.append(row) 

            # set name of index 
            ksl_index_path = ksl_dir + "/img_label_predictions.csv"

            # append to CSV file
            with open(ksl_index_path, 'a') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(ksl_arr)
            
            print("Appended", len(ksl_arr), "rows to image index CSV.")

            # Now, to rewrite the JS file
            # load full array based on updated CSV file
            full_ksl_arr = []
            with open(ksl_index_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    full_ksl_arr.append(row)
            
            # check for duplicates and remove them
            full_ksl_tups = set(tuple(r) for r in full_ksl_arr)
            if len(full_ksl_arr) != len( full_ksl_tups ):
                print("Warning: Duplicate items in accumulated KSL array.")
                full_ksl_arr = [ list(tup) for tup in full_ksl_tups ] 

            full_ksl_arr.sort(key=lambda f:f[0])

            # build JS array file
            proto_js_arr = [ [r[0], False, r[1], r[2], False, "", ""] for r in full_ksl_arr ]

            # convert array to a JSON string 
            image_array_j = json.dumps(proto_js_arr)

            # prettify with line breaks
            image_array_j = image_array_j.replace("[[", "[\n[")
            image_array_j = image_array_j.replace("], [", "], \n[")
            image_array_j = image_array_j.replace("]]", "]\n]")

            # add bits around the JSON text to make it valid Javascript
            image_array_j = "imgArray=\n" + image_array_j
            image_array_j = image_array_j + "\n;"

            # write Javascript file 
            array_pathname = ksl_dir + "/img_arr_init.js"
            with open(array_pathname, "w") as array_file:
                array_file.write(image_array_j)
            
            print("Updated image index JS, now with", len(proto_js_arr), "entries.")


    #
    # Save a visaid
    #
    if "visaids" in artifacts:
        print("Attempting to make a visaid...")
        visaids_dir = artifacts_dir + "/visaids"

        visaid_filename = visaid_path = None

        if "scene_types" in params:
            scene_types = params["scene_types"]
        else:
            scene_types = None

        visaid_options_str = ( "{\n" +
                               "'max_gap': " + str(max_gap) + ",\n" +
                               "'subsampling': " + str(subsampling) + "\n" +
                               "}" )

        try:
            visaid_filename, visaid_path = create_visaid.create_visaid( 
                video_path=item["media_path"], 
                tfs=tfs, 
                stdout=False, 
                output_dirname=visaids_dir,
                job_id=cf["job_id"],
                job_name=cf["job_name"], 
                id_in_filename=False,
                guid=item["asset_id"],
                mmif_metadata_str=mmif_metadata_str,
                visaid_options_str=visaid_options_str
                )

            if visaid_path:
                print("Visual index created at")
                print(visaid_path)
            else:
                print("Visaid creation procedure completed, but no file path returned.")

        except Exception as e:
            print("Creation of visaid failed.")
            print("Error:", e)
            errors.append("visaid")

    return errors
