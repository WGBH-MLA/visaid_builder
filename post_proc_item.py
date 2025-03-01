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

from pprint import pprint # DIAG

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



MODULE_VERSION = "0.31"


# These are the defaults specific to routines defined in this module.
POSTPROC_DEFAULTS = { "name": None,
                      "artifacts": [],
                      "prog_start_min": 3000,
                      "prog_start_max": 150000,
                      "adj_tfs": True }

# Names of the artifact types that this module can create
VALID_ARTIFACTS = [ "data", 
                    "slates",
                    "reps",
                    "ksl",
                    "visaids" ]

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
    problems = []

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


    # check params for extra params
    for key in params:
        if key not in { **POSTPROC_DEFAULTS, 
                        **proc_swt.PROC_SWT_DEFAULTS,
                        **create_visaid.VISAID_DEFAULTS } :
            print("Warning: `" + key + "` is not a valid config option for this postprocess. Ignoring.")


    # Assign parameter values.
    # For each of the available parameter keys, if that parameter was passed in, then
    # use that.  Otherwise, use the defaul value.
    pp_params = {}
    for key in POSTPROC_DEFAULTS:
        if key in params:
            pp_params[key] = params[key]
        else:
            pp_params[key] = POSTPROC_DEFAULTS

    proc_swt_params = {}
    for key in proc_swt.PROC_SWT_DEFAULTS:
        if key in params:
            proc_swt_params[key] = params[key]
        else:
            proc_swt_params[key] = proc_swt.PROC_SWT_DEFAULTS[key]

    visaid_params = {}
    for key in create_visaid.VISAID_DEFAULTS:
        if key in params:
            visaid_params[key] = params[key]
        else:
            visaid_params[key] = create_visaid.VISAID_DEFAULTS[key]



    #
    # Perform foundational processing of MMIF file
    #
    
    # Open MMIF and start processing
    mmif_path = item["mmif_paths"][-1]
    with open(mmif_path, "r") as file:
        mmif_str = file.read()

    # Get the right views
    tp_view_id, tf_view_id = proc_swt.get_swt_view_ids(mmif_str)

    # call SWT MMIF processors to get a table of time frames

    print("Attempting to process MMIF into SWT scene list...")
    
    # create TimeFrame table from the serialized MMIF
    tfs = proc_swt.tfs_from_mmif( mmif_str, 
                                  tp_view_id=tp_view_id,
                                  tf_view_id=tf_view_id )

    print("SWT scene list length:", len(tfs) )

    # find the outer temporal boundaries of the TimePoint analysis
    first_time, final_time = proc_swt.first_final_time_in_mmif( mmif_str, tp_view_id=tp_view_id )
    print(f"First TimePoint annotation at {lilhelp.tconv(first_time, frac=False)} ({first_time} ms).")
    print(f"Final TimePoint annotation at {lilhelp.tconv(final_time, frac=False)} ({final_time} ms).")

    # Create an adjusted TimeFrame table (with scenes added and/or removed)
    if pp_params["adj_tfs"]:
        tfs_adj = proc_swt.adjust_tfs( tfs, first_time, final_time, proc_swt_params )
        print("Adjusted scene list length:", len(tfs_adj) )
    else:
        tfs_adj = tfs[:]

    # pprint(tfs) # DIAG
    # pprint(tfs_adj) # DIAG

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
                        if (tf[1] in BARS_BINS and tf[3] <= pp_params["prog_start_max"]) ]
        if len(bars_tfs) > 0:
            bars_end = int(bars_tfs[-1][3])

        # Proxy starts at the end of the bars or the beginning of the slate,
        # whichever is greater
        # The main way that this can go wrong is if there is a false positive 
        # for a slate in the first period of the show, after some substantial
        # content has already begun playing.
        slate_begin = None
        slate_tfs = [ tf for tf in tfs 
                        if (tf[1] in SLATE_BINS and tf[3] <= pp_params["prog_start_max"]) ]
        if len(slate_tfs) > 0:
            slate_begin = int(slate_tfs[0][2])
            proxy_start_ms = max(bars_end, slate_begin)
        else:
            proxy_start_ms = bars_end
        
        if proxy_start_ms < pp_params["prog_start_min"]:
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
                "process": "visaid_builder/post_proc_item",
                "process_version": MODULE_VERSION,
                "process_details": {
                    "swt-tp_version": tp_ver,
                    "swt-tf_version": tf_ver,
                    "min_proxy_start_ms": pp_params["prog_start_min"],
                    "max_proxy_start_ms": pp_params["prog_start_max"]
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
                errors.append(pp_params["name"]+":"+"slates")
            
        else:
            print("No slate found.")


    #
    # Extract representative stills from timeframes
    # 
    # Note:  Key frames are extracted from the adjusted TimeFrame table. If 
    # this is not desired, set the adj_tfs parameter to false.
    #
    if "reps" in artifacts:
        print("Attempting to save representative stills...")
        reps_dir = artifacts_dir + "/reps"

        if len(tfs_adj) > 0:
            tps = [ tf[4] for tf in tfs_adj ] 
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
               errors.append(pp_params["name"]+":"+"reps")
               rep_images = []

            print("Saved", len(rep_images), "representative stills from", len(tfs_adj), "scenes.")

        else:
            print("No scenes from which to extract stills.")


    # 
    # Create KSL-style index of still images extracted
    #
    # This works by keeping a running CSV file of all the image reps made as part
    # of this job.  After each item in the job, it uses the running CSV file to 
    # re-create the JavaScript file that serves as the KSL index.
    #
    if "ksl" in artifacts:
        print("Attempting to index representatives in a KSL-style index...")
        ksl_dir = artifacts_dir + "/ksl"

        if not "reps" in artifacts:
            print("Cannot make index because representative stills were not extracted.")
        else:

            # Indicate where (if anywhere) to include labels predicted by SWT
            # Valid values: "nowhere", "field", "annotation"
            include_predicted_labels = "nowhere"

            # build KSL data for this item
            ksl_arr = []
            for fname in rep_images:
                
                # extract the requersted frame time from the filename
                tp = int(fname.split("_")[2])

                # lookup label in tfs_adj array
                label = [ tf[5] for tf in tfs_adj if tf[4] == tp ][0]

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
            if len(full_ksl_arr) != len(full_ksl_tups):
                print("Warning: Duplicate items added to the cumulative KSL array.  Will de-dupe.")
                full_ksl_arr = [ list(tup) for tup in full_ksl_tups ] 

            full_ksl_arr.sort(key=lambda f:f[0])

            # build JS array file
            if include_predicted_labels == "field":
                proto_js_arr = [ [r[0], False, r[1], r[2], False, "", ""] for r in full_ksl_arr ]
            elif include_predicted_labels == "annotation":
                proto_js_arr = [ [r[0], False, "", "", False, (f"Predicted label: {r[1]}" if r[1] else ""), ""] for r in full_ksl_arr ]
            else:
                proto_js_arr = [ [r[0], False, "", "", False, "", ""] for r in full_ksl_arr ]

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
    # Note:  Visaid is created from the adjusted TimeFrame table. If this is not 
    # desired, set the adj_tfs parameter to false.
    #
    if "visaids" in artifacts:
        print("Attempting to make a visaid...")
        visaids_dir = artifacts_dir + "/visaids"

        visaid_path = None
        visaid_problems = []

        try:
            visaid_path, visaid_problems = create_visaid.create_visaid( 
                video_path=item["media_path"], 
                tfs=tfs_adj, 
                stdout=False, 
                output_dirname=visaids_dir,
                job_id=cf["job_id"],
                job_name=cf["job_name"], 
                item_id=item["asset_id"],
                proc_swt_params=proc_swt_params,
                visaid_params=visaid_params,
                mmif_metadata_str=mmif_metadata_str
                )
        except av.error.InvalidDataError as e:
            print("Creation of visaid failed.")
            print("Error:", e)
            errors.append(pp_params["name"]+":"+"visaids")

        problems += [ "visaid:"+p for p in visaid_problems ]

        if visaid_path:
            print("Visual index created at")
            print(visaid_path)
        else:
            print("Visaid creation procedure completed, but no file path returned.")
            errors.append(pp_params["name"]+":"+"visaids")

    # 
    # Finished with the whole postprocess
    # 
    return errors, problems
