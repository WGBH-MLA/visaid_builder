# %%
# Import modules

import os
import csv
import json
import datetime
import warnings
import subprocess
import requests

from drawer.media_availability import check_avail, make_avail, remove_media
from drawer.mmif_adjunct import make_blank_mmif, mmif_check
from drawer.lilhelp import extract_stills

import swt.process_swt


########################################################
# %%
# Read batch conf file for batch-specific parameters

# Batch config filename is hard-coded (for now).
# This is the only line that needs to be changed per run.
batch_conf_path = "./stovetop/challenge_2_pbd/batchconf_1.json"
#batch_conf_path = "./stovetop/shipments/Cascade_34524/batchconf.json"


########################################################
# Set batch-specific parameters based on values in conf file
with open(batch_conf_path, "r") as conffile:
    conf = json.load(conffile)

try: 
    batch_id = conf["id"]

    if "name" in conf:
        batch_name = conf["name"]
    else:
        batch_name = batch_id

    batch_results_dir = conf["results_dir"]
    batch_def_path = conf["def_path"]
    media_dir = conf["media_dir"]

    if "get_slate" in conf:
        get_slate = conf["get_slate"]
    else:
        get_slate = False

    if "make_visaid" in conf:
        make_visaid = conf["make_visaid"]
    else:
        make_visaid = False

    if "start_after_item" in conf:
        start_after_item = conf["start_after_item"]
    else:
        start_after_item = 0

    if "end_after_item" in conf:
        if conf["end_after_item"] == "":
            end_after_item = None
        elif conf["end_after_item"] is None:
            end_after_item = None
        else:
            end_after_item = conf["end_after_item"]
    else:
        end_after_item = None

    if "overwrite_mmif" in conf:
        overwrite_mmif = conf["overwrite_mmif"]
    else:
        overwrite_mmif = False

    if "cleanup_media_per_item" in conf:
        cleanup_media_per_item = conf["cleanup_media_per_item"]
    else:
        cleanup_media_per_item = True
    
    if "cleanup_beyond_item" in conf:
        cleanup_beyond_item = conf["cleanup_beyond_item"]
    else:
        cleanup_beyond_item = 0

    if "filter_warnings" in conf:
        warnings.filterwarnings(conf["filter_warnings"])
    else:
        warnings.filterwarnings("ignore")

    if "scene_types" in conf:
        scene_types = conf["scene_types"]
    else:
        scene_types = []

    if "clams_params" in conf:
        clams_params = conf["clams_params"]
    else:
        clams_params = []

except KeyError as e:
    print("Invalid configuration file at", batch_conf_path)
    print("Error for expected key:", e)
    raise SystemExit

#########################################################
# Set up batch directories and files

# Checks to make sure directories and setup file exist
for dirpath in [batch_results_dir, batch_def_path, media_dir]:
    if not os.path.exists(dirpath):
        raise FileNotFoundError("Path does not exist: " + dirpath)

# Results files get a new name every time this script is run
batch_results_file_base = batch_results_dir + "/" + batch_name + "_results"
timestamp = str(int(datetime.datetime.now().timestamp()))
batch_results_csv_path  = batch_results_file_base + timestamp + ".csv"
batch_results_json_path  = batch_results_file_base + timestamp + ".json"


mmif_dir = "mmif"
mmif_dir = batch_results_dir + "/" + mmif_dir 

artifacts_dir = "artifacts"
artifacts_dir = batch_results_dir + "/" + artifacts_dir

slates_dir = artifacts_dir + "/" + "slates"

visaids_dir = artifacts_dir + "/" + "visaids"

# Checks to make sure these directories exist
# If directories do not exist, then create them
for dirpath in [mmif_dir, 
                artifacts_dir, 
                slates_dir,
                visaids_dir]:
    if os.path.exists(dirpath):
        print("Found existing directory: " + dirpath)
    else:
        print("Creating directory: " + dirpath)
        os.mkdir(dirpath)


########################################################
# %%
# Define helper functions
# Note:  These functions are simply for wrapping repeated code.  Hence, they
# use global variables from this file.

def update_batch_results():
    # Write out results to a CSV file and to a JSON file
    # Only write out records that have been reached so far
    # Re-writing after every iteration of the loop
    
    # use data structures that are global relative to this script
    global batch_results_csv_path, batch_results_json_path
    global batch_l, item_count

    with open(batch_results_csv_path, 'w', newline='') as file:
        fieldnames = batch_l[0].keys()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(batch_l[:(item_count-start_after_item)])
    
    with open(batch_results_json_path, 'w') as file:
        json.dump(batch_l[:(item_count-start_after_item)], file, indent=2)



########################################################
# %%
# Process batch in a loop

# Make sure at least an empty list exists to define the batch
# (This value should get overwritten when we open a batch def file in the next 
# step. However, if there is no such file, this enables us to exit the empty 
# loop gracefully.)
batch_l = []

# open batch as a list of dictionaries
with open(batch_def_path, encoding='utf-8', newline='') as csvfile:
    batch_l = list(csv.DictReader(csvfile))

# restrict to the appropriate subset
batch_l = batch_l[start_after_item:end_after_item]

item_count = start_after_item

# Main loop
for item in batch_l:
    t0 = datetime.datetime.now()

    item_count += 1
    print()
    print("*** ITEM #", item_count, item["asset_id"], t0, "***")

    ########################################################
    # initialize new dictionary elements (do only once per item)
    item["batch_item"] = item_count
    item["skip_reason"] = ""
    item["media_filename"] = ""
    item["media_path"] = ""
    item["mmif_files"] = []
    item["mmif_paths"] = []

    # set default value for `media_type` if this is not supplied
    if "media_type" not in item:
        item["media_type"] = "Moving Image"
        print("Warning:  Media type not specified. Assuming it is 'Moving Image'.")

    item["bars_end"] = 0
    item["slate_begin"] = None

    item["proxy_start"] = 0.0
    item["slate_path"] = ""
    item["slate_filename"] = ""
    item["visaid_path"] = ""
    item["visaid_filename"] = ""

    # set the index of the MMIF files so far for this item
    mmifi = -1


    ########################################################
    # Add media to the availability place, if it is not already there,
    # and update the dictionary

    print("# MEDIA AVAILABILITY")

    media_path = ""

    media_filename = check_avail(item["asset_id"], media_dir)

    if media_filename is not None:
        media_path = media_dir + "/" + media_filename
        print("Media already available:  ", media_path) 
    else:
        print("Media not yet available; will make available.") 
        media_filename = make_avail(item["asset_id"], item["sonyci_id"], media_dir)
        if media_filename is not None:
            media_path = media_dir + "/" + media_filename

    if media_filename is not None and os.path.isfile(media_path):
        item["media_filename"] = media_filename
        item["media_path"] = media_path
    else:
        # step failed
        # print error messages, updated results, continue to next loop iteration
        print("Media file for " + item["asset_id"] + " could not be made available.")
        print("SKIPPING", item["asset_id"])
        item["skip_reason"] = "media"
        update_batch_results()
        continue


    ########################################################
    # MMIF creation #0
    # Add blank MMIF file, if it's not already there

    print("# MAKING BLANK MMIF")

    # Check for prereqs
    if item["media_filename"] == "":
        # prereqs not satisfied
        # print error messages, updated results, continue to next loop iteration
        print("Step prerequisite failed: No media filename recorded.")
        print("SKIPPING", item["asset_id"])
        item["skip_reason"] = "mmif-0-prereq"
        update_batch_results()
        continue
    else:
        print("-- Step prerequisites passed. --")


    # define MMIF for this stage of this iteration
    mmifi += 1
    mmif_filename = item["asset_id"] + "_" + batch_id + "_" + str(mmifi) + ".mmif"
    mmif_path = mmif_dir + "/" + mmif_filename

    # Check to see if it exists; if not create it
    if ( os.path.isfile(mmif_path) and not overwrite_mmif):
        print("Will use existing MMIF:    " + mmif_path)
    else:
        print("Will create MMIF file:     " + mmif_path)

        if item["media_type"] == "Moving Image":
            mime = "video"
        elif item["media_type"] == "Sound":
            mime = "audio"
        else:
            print("Warning: media type of " + item["asset_id"] + " is `" + item["media_type"] + "`.")
            print("Using 'text' as the MIME type.")
            mime = "text"
        mmif_str = make_blank_mmif(item["media_filename"], mime)

        with open(mmif_path, "w") as file:
            num_chars = file.write(mmif_str)
        if num_chars < len(mmif_str):
            raise Exception("Tried to write MMIF, but failed.")
    
    mmif_status = mmif_check(mmif_path)
    if 'blank' in mmif_status:
        item["mmif_files"].append(mmif_filename)
        item["mmif_paths"].append(mmif_path)
    else:
        # step failed
        # print error messages, updated results, continue to next loop iteration
        mmif_check(mmif_path, complain=True)
        print("SKIPPING", item["asset_id"])
        item["skip_reason"] = "mmif-0"
        update_batch_results()
        continue


    ########################################################
    # MMIF creation #1
    # Construct CLAMS call and call CLAMS app
    # Save output MMIF file

    print("# RUNNING CLAMS APP TO CREATE ANNOTATIONS IN MMIF")

    # Check for prereqs
    mmif_status = mmif_check(item["mmif_paths"][mmifi])
    if 'valid' not in mmif_status:
        # prereqs not satisfied
        # print error messages, updated results, continue to next loop iteration
        mmif_check(mmif_path, complain=True)
        print("Step prerequisite failed.")
        print("SKIPPING", item["asset_id"])
        item["skip_reason"] = "mmif-1-prereq"
        update_batch_results()
        continue
    else:
        print("-- Step prerequisites passed. --")

    # Define MMIF for this step of the batch
    mmifi += 1
    clamsi = mmifi - 1
    mmif_filename = item["asset_id"] + "_" + batch_id + "_" + str(mmifi) + ".mmif"
    mmif_path = mmif_dir + "/" + mmif_filename

    # Check to see if it exists; if not create it
    if ( os.path.isfile(mmif_path) and not overwrite_mmif):
        print("Will use existing MMIF:    " + mmif_path)
    else:
        print("Will try making MMIF file: " + mmif_path)

        # Run CLAMS app, assuming CLAMS is running as a local web service
        print("Sending request to CLAMS web service...")
        if len(clams_params[clamsi]) > 0:
            # build querystring with parameters in batch configuration
            qsp = "?"
            for p in clams_params[clamsi]:
                qsp += p
                qsp += "="
                qsp += str(clams_params[clamsi][p])
                qsp += "&"
            qsp = qsp[:-1] # remove trailing "&"
        service = "http://localhost:5000"
        endpoint = service + qsp

        headers = {'Accept': 'application/json'}

        with open(item["mmif_paths"][mmifi-1], "r") as file:
            mmif_str = file.read()

        try:
            response = requests.post(endpoint, headers=headers, data=mmif_str)
        except Exception as e:
            print("Encountered exception:", e)
            print("Failed to get a response from the CLAMS web service.")
            print("Check CLAMS web service and resume before batch item:", item_count)
            raise SystemExit("Exiting script.")

        print("CLAMS app web serivce response code:", response.status_code)
        
        # use the HTTP response as appropriate
        if response.status_code :
            mmif_str = response.text

            if response.status_code == 500:
                mmif_path += "500"

            with open(mmif_path, "w") as file:
                num_chars = file.write(mmif_str)
            
            if num_chars < len(mmif_str):
                raise Exception("Tried to write MMIF, but failed.")

            print("MMIF file created.")

    # Validate step     
    mmif_status = mmif_check(mmif_path)
    if ('laden' in mmif_status and 'error-views' not in mmif_status):
        item["mmif_files"].append(mmif_filename)
        item["mmif_paths"].append(mmif_path)
    else:
        # step failed
        # print error messages, updated results, continue to next loop iteration
        mmif_check(mmif_path, complain=True)
        print("SKIPPING", item["asset_id"])
        item["skip_reason"] = "mmif-1"
        update_batch_results()
        continue

    ########################################################
    # Process MMIF and get useful output
    # 
    print("# USING CLAMS OUTPUT")

    # Check for prereqs
    mmif_status = mmif_check(item["mmif_paths"][mmifi])
    if ('laden' not in mmif_status or 'error-views' in mmif_status):
        # prereqs not satisfied
        # print error messages, updated results, continue to next loop iteration
        mmif_check(mmif_path, complain=True)
        print("Step prerequisite failed.")
        print("SKIPPING", item["asset_id"])
        item["skip_reason"] = "usemmif-prereq"
        update_batch_results()
        continue
    else:
        print("-- Step prerequisites passed. --")

    with open(item["mmif_paths"][mmifi], "r") as file:
        mmif_str = file.read()
    
    # call SWT MMIF processors to get a table of time frames
    tfs = swt.process_swt.list_tfs(mmif_str)

    # restrict to just bars and slates
    #tfs = [ tf for tf in tfs if tf[1] in ['bars', 'slate'] ]

    #
    # Calculate some significant datapoints based on table of time frames
    #
    # Note:  For reasons I don't understand, we have to cast some integer
    # values originally created by Pandas to int from int64

    # The end of the bars is the end of the last bars timeframe
    # If there is no bars timeframe, then the value is 0
    bars_end = 0
    bars_tfs = [ tf for tf in tfs if tf[1] in ['bars'] ]
    if len(bars_tfs) > 0:
        bars_end = int(bars_tfs[-1][3])
    
    # The slate rep is the rep timepoint from from the first slate timeframe
    # If there is not slate timeframe, then the value is None
    slate_rep = None
    slate_tfs = [ tf for tf in tfs if tf[1] in ['slate'] ]
    if len(slate_tfs) > 0:
        slate_rep = int(slate_tfs[0][4])

    # Proxy starts at the end of the bars or the beginning of the slate,
    # whichever is greater
    slate_begin = None
    proxy_start_ms = 0 
    if len(slate_tfs) > 0:
        slate_begin = int(slate_tfs[0][2])
        proxy_start_ms = max(bars_end, slate_begin)
    else:
        proxy_start_ms = bars_end
    
    print("bars end:", bars_end, "slate rep:", slate_rep, "proxy start:", proxy_start_ms)

    item["slate_begin"] = slate_begin
    item["bars_end"] = bars_end
    item["proxy_start"] = proxy_start_ms / 1000

    print("Proxy start:", item["proxy_start"])


    #
    # Extract the slate
    #
    if get_slate:
        if slate_rep is not None:
            print("Trying to exact a slate to", slates_dir)

            slate_rslt = extract_stills( item["media_path"], 
                                        [ slate_rep ], 
                                        item["asset_id"],
                                        slates_dir,
                                        verbose=False )
            item["slate_filename"] = slate_rslt[0]
            item["slate_path"] = slate_rslt[1]

            print("Slate saved at", item["slate_path"])
        else:
            print("No slate found.")

    #
    # Save a visaid
    #
    if make_visaid:
        print("Trying to make a visaid in", visaids_dir)

        visaid_filename, visaid_path = swt.process_swt.create_aid( 
            video_path=item["media_path"], 
            tfs=tfs, 
            stdout=False, 
            output_dirname=visaids_dir,
            proj_name=item["mmif_files"][mmifi], 
            guid=item["asset_id"],
            types=scene_types
            )

        item["visaid_filename"] = visaid_filename
        item["visaid_path"] = visaid_path


    ########################################################
    # Clean up
    # 
    print("# CLEANING UP MEDIA")

    if cleanup_media_per_item and item_count > cleanup_beyond_item:
        print("Attempting to removing media at", item["media_path"])
        removed = remove_media(item["media_path"])
        if removed:
            print("Media removed.")
    else:
        print("Leaving media for this item.")




    ########################################################
    # Done with this item.  Update results
    # 
    update_batch_results()
    tn = datetime.datetime.now()
    print("elapsed time:", (tn-t0).seconds, "seconds")


# end of main processing loop
########################################################


print()
print("****************************")
print("Batch complete.")
print("Batch results recorded in:")
print(batch_results_csv_path)
print(batch_results_json_path)


# %%
