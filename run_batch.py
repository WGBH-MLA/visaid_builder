# %%
# Import modules
# required modules not in Python standard library: 
#   requests, av, pandas, mmif-python, pillow

import os
import platform
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

# Batch config filename is hard-coded (for now).
# This is the only line that needs to be changed per run.
#batch_conf_path = "./stovetop/shipments/ARPB_2024-07_x2064_redo/batchconf_03.json"
#batch_conf_path = "./stovetop/clams_whisper_batch_test/batchconf_01.json"
#batch_conf_path = "./stovetop/shipments/OPB_35059_35124_35135_35195_35220/batchconf_01.json"
#batch_conf_path = "./stovetop/shipments/SFL_PBS_34959/batchconf_01.json"
#batch_conf_path = "./stovetop/shipments/Hawaii_35148_35227_35255/batchconf_01.json"
#batch_conf_path = "./scratch/Hawaii_35148_35227_35255_TEST/batchconf_fern01.json"
batch_conf_path = "./stovetop/shipments/SFL_PBS_34959_redo/batchconf_01.json"

########################################################
# Set batch-specific parameters based on values in conf file
with open(batch_conf_path, "r") as conffile:
    conf = json.load(conffile)

try: 
    batch_id = conf["id"] # required

    if "name" in conf:
        batch_name = conf["name"]
    else:
        batch_name = batch_id

    if "clams_run_cli" in conf:
        clams_run_cli = conf["clams_run_cli"]
    else:
        clams_run_cli = False

    if clams_run_cli:
        # need to know the docker image if (but only if) running in CLI mode
        clams_images = conf["clams_images"]
    else:
        # ignore clams_images if not running in CLI mode
        clams_images = ""

    if "clams_params" in conf:
        clams_params = conf["clams_params"]
    else:
        clams_params = []

    if "local_base" in conf:
        local_base = conf["local_base"]
    else:
        local_base = ""

    if "mnt_base" in conf:
        mnt_base = conf["mnt_base"]
    else:
        mnt_base = ""

    results_dir = local_base + conf["results_dir"]
    batch_def_path = local_base + conf["def_path"]
    media_dir = local_base + conf["media_dir"]
    
    mnt_results_dir = mnt_base + conf["results_dir"]
    mnt_media_dir = mnt_base + conf["media_dir"]
    
    if "mmif_dir" in conf:
        mmif_dir = local_base + conf["mmif_dir"]
        mnt_mmif_dir = mnt_base + conf["mmif_dir"]
    else:
        mmif_dir = ""  # to be set below

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

    if "post_proc" in conf:
        post_proc = conf["post_proc"]
    else:
        post_proc = ""

    # config parameters specific to SWT

    if "get_slate" in conf:
        get_slate = conf["get_slate"]
    else:
        get_slate = False

    if "make_visaid" in conf:
        make_visaid = conf["make_visaid"]
    else:
        make_visaid = False

    if "scene_types" in conf:
        scene_types = conf["scene_types"]
    else:
        scene_types = []

except KeyError as e:
    print("Invalid configuration file at", batch_conf_path)
    print("Error for expected key:", e)
    raise SystemExit


#########################################################
# Set up batch directories and files

# Checks to make sure directories and setup file exist
for dirpath in [results_dir, batch_def_path, media_dir]:
    if not os.path.exists(dirpath):
        raise FileNotFoundError("Path does not exist: " + dirpath)

# Results files get a new name every time this script is run
batch_results_file_base = results_dir + "/" + batch_name + "_results"
timestamp = str(int(datetime.datetime.now().timestamp()))
batch_results_csv_path  = batch_results_file_base + timestamp + ".csv"
batch_results_json_path  = batch_results_file_base + timestamp + ".json"

# Directory for MMIF files
if mmif_dir == "":
    # MMIF file not set by config file.  Will use default.
    mmif_dir_name = "mmif"
    mmif_dir = results_dir + "/" + mmif_dir_name 
    mnt_mmif_dir = mnt_results_dir + "/" + mmif_dir_name 
else:
    # MMIF directory set by conf file; check that it exists
    if not os.path.exists(mmif_dir):
        raise FileNotFoundError("Path does not exist: " + mmif_dir)

artifacts_dir = "artifacts"
artifacts_dir = results_dir + "/" + artifacts_dir

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


def cleanup_media(item_count, item):
    # Cleanup media, i.e., remove media file for this item
    # Do this only if the global settings allow it
    
    # refer to data structures that are global to this script
    global cleanup_media_per_item, cleanup_beyond_item

    print("# CLEANING UP MEDIA")

    if cleanup_media_per_item and item_count > cleanup_beyond_item:
        print("Attempting to removing media at", item["media_path"])
        removed = remove_media(item["media_path"])
        if removed:
            print("Media removed.")
    else:
        print("Leaving media for this item.")


########################################################
# %%
# Process batch in a loop

# Make sure at least an empty list exists to define the batch
# (This value should get overwritten when we open a batch def file in the next 
# step. However, if there is no such file, having an empty list this enables 
# us to exit the empty loop gracefully.)
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
        print("Media not yet available; will try to make available.") 
        if item["sonyci_id"] :
            media_filename = make_avail(item["asset_id"], item["sonyci_id"], media_dir)
            if media_filename is not None:
                media_path = media_dir + "/" + media_filename
        else:
            print("No Ci ID for " + item["asset_id"])

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
            print("Using 'video' as the MIME type.")
            mime = "video"
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
        cleanup_media(item_count, item)
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


        if not clams_run_cli :
            ################################################################
            # Run CLAMS app, assuming the app is already running as a local web service
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

            # Write out MMIF file
            if mmif_str != "":
                with open(mmif_path, "w") as file:
                    num_chars = file.write(mmif_str)
                if num_chars < len(mmif_str):
                    raise Exception("Tried to write MMIF, but failed.")
                print("MMIF file created.")

        else:
            ################################################################
            # Run CLAMS app by calling the Docker image
            print("Attempting to call Dockerized CLAMS app CLI...")

            input_mmif_filename = item["mmif_files"][mmifi-1]
            output_mmif_filename = mmif_filename

            # Set the environment-specific path to Docker and Windows-specific additions
            current_os = platform.system()
            if current_os == "Windows":
                docker_bin_path = "/mnt/c/Program Files/Docker/Docker/resources/bin/docker"
                coml_prefix = ["bash"]
            elif current_os == "Linux":
                docker_bin_path = "/usr/bin/docker"
                coml_prefix = []
            else:
                raise OSError(f"Unsupported operating system: {current_os}")

            # build shell command as list for `subprocess.run()`
            coml = [
                    docker_bin_path, 
                    "run",
                    "-v",
                    mnt_media_dir + '/:/data',
                    "-v",
                    mnt_mmif_dir + '/:/mmif',
                    "-i",
                    "--rm",
                    clams_images[clamsi],
                    "python",
                    "cli.py"
                   ]

            coml = coml_prefix + coml

            # If there are parameters, add them to the command list
            if len(clams_params[clamsi]) > 0:
                app_params = []
                for p in clams_params[clamsi]:
                    if type(clams_params[clamsi][p]) != dict:
                        # parameter is not nested; just add it
                        app_params.append( "--" + p )
                        app_params.append( str(clams_params[clamsi][p]) )
                    else:
                        # parameter is a dictionary; break it into separately
                        # specified parameters
                        for mkey in clams_params[clamsi][p]:
                            app_params.append( "--" + p )
                            mvalue = clams_params[clamsi][p][mkey]
                            app_params.append( mkey + ":" +  mvalue )

                # Work-around to delimit values passed with --map flag:
                # Add a dummy flag
                app_params.append("--")
            
                coml += app_params

            coml.append("/mmif/" + input_mmif_filename)
            coml.append("/mmif/" + output_mmif_filename)

            # print(coml) # DIAG
            print( " ".join(coml) ) # DIAG

            result = subprocess.run(coml, capture_output=True, text=True)
            if result.stderr:
                print("Warning: CLI returned with error.  Contents of stderr:")
                print(result.stderr)
            else:
                print("CLAMS app finished without errors.")


    # Validate CLAMS app run
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
        cleanup_media(item_count, item)
        update_batch_results()
        continue

    ########################################################
    # Process MMIF and get useful output
    # 
    
    if post_proc :

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
    
    if post_proc.lower() == "swt" :

        # call SWT MMIF processors to get a table of time frames
        tfs = swt.process_swt.list_tfs(mmif_str, max_gap=180000)

        # get metadata_str
        metadata_str = swt.process_swt.get_mmif_metadata_str(mmif_str)

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

        # For now:  Just use bars end time.
        proxy_start_ms = bars_end

        # A proxy start time > 150s is pretty sketchy.  Don't believe it.
        if proxy_start_ms > 150000:
            proxy_start_ms = 0

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
                print("Trying to exact a slate...")

                try:
                    slate_rslt = extract_stills( item["media_path"], 
                                                [ slate_rep ], 
                                                item["asset_id"],
                                                slates_dir,
                                                verbose=False )
                    item["slate_filename"] = slate_rslt[0]
                    item["slate_path"] = slate_rslt[1]

                    print("Slate saved at", item["slate_path"])

                except Exception as e:
                    print("Extraction of slate frame at", slate_rep ,"failed.")
                    print("Error:", e)
                
            else:
                print("No slate found.")

        #
        # Save a visaid
        #
        if make_visaid:
            print("Trying to make a visaid...")

            try:
                visaid_filename, visaid_path = swt.process_swt.create_aid( 
                    video_path=item["media_path"], 
                    tfs=tfs, 
                    stdout=False, 
                    output_dirname=visaids_dir,
                    proj_name=item["mmif_files"][mmifi], 
                    guid=item["asset_id"],
                    types=scene_types,
                    metadata_str=metadata_str
                    )

                item["visaid_filename"] = visaid_filename
                item["visaid_path"] = visaid_path

            except Exception as e:
                print("Creation of visaid failed.")
                print("Error:", e)


    ########################################################
    # Done with this item.  
    # 

    # Clean up
    cleanup_media(item_count, item)

    # Update results
    update_batch_results()

    # Print diag info
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
