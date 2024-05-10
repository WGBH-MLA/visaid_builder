# %%
# Import modules

import os
import csv
import json
import datetime

from drawer.media_availability import check_avail, make_avail, remove_media

######################################################################
# %% 
# define parameters for the run

#batch_def_path = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/WIPR_GUIDs_2024-04-22_batch_aapb_cids+eds.csv"
#batch_def_path = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/WIPR_GUIDs_2024-04-22_batch_ams2_cids.csv"
#batch_def_path = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/WIPR_GUIDs_2024-05-02_batch_ams2_cids.csv"
#batch_def_path = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/batch_2024-05-07_unknowns_x1018/WIPR_GUIDS_2024-05-07_unknowns_batch_ams2_cids.csv"
#batch_def_path = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/complete/complete_sonyci_set.csv"

batch_def_path = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/complete/wipr_complete_media_batch_2024-05-10.csv"

#batch_def_path = "C:/Users/owen_king/kitchen/stovetop/challenge_2_pbd/full_media_batch.csv"
#batch_def_path = "C:/Users/owen_king/kitchen/stovetop/shipment_34080_34125_NC_PBS/batch_def.csv"

#media_dir = "E:/WIPR"
#media_dir = "C:/Users/owen_king/batchmedia/WIPR"
#media_dir = "D:/peabody_sc"
#media_dir = "C:/Users/owen_king/batchmedia"
#media_dir = "D:/WIPR_002_131"
#media_dir = "C:/Users/owen_king/batchmedia/WIPR_004_1018"
media_dir = "D:/WIPR_full"

batch_name = "WIPR_full_get"
#batch_name = "PBD_ProgsEPs"
#batch_name = "NCPBS_sample"


######################################################################
# %% 
# helper functikons
def update_batch_results():
    # Write out results to a CSV file and to a JSON file
    # Only write out records that have been reached so far
    # Re-writing after every iteration of the loop
    global batch_results_json_path
    global batch_l, item_count
    
    with open(batch_results_json_path, 'w') as file:
        json.dump(batch_l, file, indent=2)


######################################################################
# %%
# Set up job
batch_results_file_base = batch_name + "_get_media_results"
timestamp = str(int(datetime.datetime.now().timestamp()))
batch_results_json_path  = batch_results_file_base + timestamp + ".json"


# Make sure at least an empty list exists to define the batch
batch_l = []

# expects a CSV file with the first two columns labeled "asset_id" and "sonyci_id"
# open batch as a list of dictionaries
with open(batch_def_path, encoding='utf-8', newline='') as csvfile:
    batch_l = list(csv.DictReader(csvfile))

item_count = 0

print("About to get media for", len(batch_l), "items...")

######################################################################
# %%
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
        print("Media file for " + item["asset_id"] + " could not be made available.")
        print("SKIPPING", item["asset_id"])
        item["skip_reason"] = "media"
    
    update_batch_results()
    tn = datetime.datetime.now()
    print("elapsed time:", (tn-t0).seconds, "seconds")

print()
print("****************************")
print("Batch complete.")
print("Batch results recorded in:")
print(batch_results_json_path)


