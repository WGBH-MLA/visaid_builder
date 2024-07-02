# %%
# Import modules

import csv
from pprint import pprint
import glob

# import installed modules
import pandas as pd

# Set the display options to show all rows and columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width',2000)


# %%
# Define functions for I/O -- reading parameters and writing out results
def write_csv( df, csv_filename: str ):
    # write out dataframe to CSV
    df.to_csv(csv_filename, index=False)

def write_json( df, json_filename: str):
    # write out dataframe to JSON
    df.to_json(json_filename, orient='records', indent=2)

def write_guids_list( df, txt_filename: str):
    df["asset_id"].to_csv(txt_filename, index=False, header=False)


# %%
# LOAD
# Load working DataFrame from file
wdf_init = pd.read_json("./stovetop/WIPR_transcripts/complete/transcription_work_init.json")
wdf = pd.read_json("./stovetop/WIPR_transcripts/complete/transcription_work_cur.json")


############################################################################
# %%
# We shouldn't be running this straight through
# So, if it's running from the top, then....  Stop here!
raise Exception

#################################################################
# %%
# Make assignments for the earlier unknowns batch

uf = "./stovetop/WIPR_transcripts/batch_2024-05-07_unknowns_x1018/WIPR_GUIDS_2024-05-07_unknowns.txt"
#with open (uf, "r")  as file:
#    unkguids = [line.strip() for line in file.readlines()]

uff = "./stovetop/WIPR_transcripts/batch_2024-05-07_unknowns_x1018/WIPR_2024-05-07_unknowns_filelist.txt"
with open (uff, "r")  as file:
    unkguids = [line.strip()[:-4] for line in file.readlines()]


unwdf = wdf_init.copy()
for guid in unkguids:
    unwdf.loc[wdf["asset_id"] == guid, "status"] = "Assigned"
    unwdf.loc[wdf["asset_id"] == guid, "batch"] = "Caroline-Unknowns"

# %%
# Assign others
unassigned = wdf["status"] == "Unassigned"
batch_indices = wdf[ unassigned ].head(1500).index
wdf.loc[batch_indices, "batch"] = "Kevin-01"
wdf.loc[batch_indices, "status"] = "Assigned"

unassigned = wdf["status"] == "Unassigned"
batch_indices = wdf[ unassigned ].head(1500).index
wdf.loc[batch_indices, "batch"] = "LTO3-01"
wdf.loc[batch_indices, "status"] = "Assigned"

unassigned = wdf["status"] == "Unassigned"
batch_indices = wdf[ unassigned ].head(1500).index
wdf.loc[batch_indices, "batch"] = "mine-01"
wdf.loc[batch_indices, "status"] = "Assigned"

# a couple extra for me
my_val_guids = ["cpb-aacip-f289e15bb05", "cpb-aacip-f3cf81fd778"]
batch_indices = wdf[ wdf["asset_id"].isin(my_val_guids) ].index
wdf.loc[batch_indices, "batch"] = "mine-01"
wdf.loc[batch_indices, "status"] = "Assigned"

# remaining ones for Kevin
unassigned = wdf["status"] == "Unassigned"
batch_indices = wdf[ unassigned ].index
wdf.loc[batch_indices, "batch"] = "Kevin-02"
wdf.loc[batch_indices, "status"] = "Assigned"


#################################################################
# %%
# Translation batch assignments

wdf["es2en_status"] = "Unassigned"

# Sample for Valeria
valeria_guids = ["cpb-aacip-4a7ac2f798d", "cpb-aacip-2af687941c9", "cpb-aacip-6726dbe3924", "cpb-aacip-f3cf81fd778", "cpb-aacip-f289e15bb05", "cpb-aacip-99e3c50f646", "cpb-aacip-4c7b29fe96e", "cpb-aacip-b612dc8f1ad", "cpb-aacip-98c874aba44", "cpb-aacip-c28b63eb55e" ]
batch_indices = wdf[ wdf["asset_id"].isin(valeria_guids) ].index
wdf.loc[batch_indices, "es2en_batch"] = "valeria-01"
wdf.loc[batch_indices, "es2en_status"] = "Assigned"

# first translation batch for LTO3
batch_indices = wdf[ ( wdf["batch"] == "LTO3-01" ) & ( wdf["es2en_status"] != "Assigned" ) ].index
wdf.loc[batch_indices, "es2en_batch"] = "LTO3-01"
wdf.loc[batch_indices, "es2en_status"] = "Assigned"

# first translation batch for Owen
unassigned = wdf["es2en_status"] == "Unassigned"
batch_indices = wdf[ unassigned ].head(800).index
wdf.loc[batch_indices, "es2en_batch"] = "mine-01"
wdf.loc[batch_indices, "es2en_status"] = "Assigned"

# second translation batch for Owen
unassigned = wdf["es2en_status"] == "Unassigned"
batch_indices = wdf[ unassigned ].head(1000).index
wdf.loc[batch_indices, "es2en_batch"] = "mine-02"
wdf.loc[batch_indices, "es2en_status"] = "Assigned"

# second translation batch for LTO3
unassigned = wdf["es2en_status"] == "Unassigned"
batch_indices = wdf[ unassigned ].head(1500).index
wdf.loc[batch_indices, "es2en_batch"] = "LTO3-02"
wdf.loc[batch_indices, "es2en_status"] = "Assigned"

# third translation batch for LTO3
unassigned = wdf["es2en_status"] == "Unassigned"
batch_indices = wdf[ unassigned ].head(1300).index
wdf.loc[batch_indices, "es2en_batch"] = "LTO3-03"
wdf.loc[batch_indices, "es2en_status"] = "Assigned"

# third translation batch for Owen
unassigned = wdf["es2en_status"] == "Unassigned"
batch_indices = wdf[ unassigned ].index
wdf.loc[batch_indices, "es2en_batch"] = "mine-03"
wdf.loc[batch_indices, "es2en_status"] = "Assigned"


#################################################################
# %%
# Write out a batch list

#batchname = "Kevin-01"
batchname = "Kevin-02"
cols = ["asset_id", "sonyci_id", "asset_type", "consolidated_title", "proxy_duration"]
write_csv( wdf[ wdf["batch"] == batchname ][cols], batchname+"_batch.csv")


#############################################################################
# %%
# Check for *transcript* files and update Dataframe

basedir = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/complete/0TRANSCRIPTS"

# Scan directories from Kevin
kevin_dirs = ["Kevin-01_1498", "Kevin-02_1097"]

# go into each batch-level dir
for dstr in kevin_dirs:
    top_dir = basedir + "/" + dstr
    guid_dirs = glob.glob(top_dir + "/cpb*")
    
    # go into each guid-named dir
    for gd in guid_dirs:
        guid = gd[gd.find("cpb-aacip"):]
        ts_files = glob.glob(gd + "/cpb-aacip-*-transcript.json")
        if len(ts_files) != 1:
            wdf.loc[ wdf['asset_id'] == guid, 'status'] = 'Failed'
        else:
            wdf.loc[ wdf['asset_id'] == guid, 'status'] = 'Transcribed'

# Scan directories from Owen
owen_dirs = ["transcripts_Additions-01x4",
             "transcripts_LTO3-01",
             "transcripts_mine-01",
             "transcripts_unknowns_batch"]

# go into each batch-level dir
for dstr in owen_dirs:
    top_dir = basedir + "/" + dstr

    # Use the presence of a vtt file as evidence of an attempt
    guids = [ fn[fn.find("cpb-aacip"):-4] for fn in glob.glob(top_dir + "/*.vtt") ]

    for guid in guids:
        ts_files = glob.glob(top_dir + "/" + guid + "-transcript.json")
        if len(ts_files) != 1:
            wdf.loc[ wdf['asset_id'] == guid, 'status'] = 'Failed'
        else:
            wdf.loc[ wdf['asset_id'] == guid, 'status'] = 'Transcribed'

# filter for those that failed the first round
fails = ( wdf["status"] == 'Assigned') | (wdf["status"] == 'Failed')

# manually select GUIDS to redo
redo_guids = ["cpb-aacip-33126a770a9", "cpb-aacip-36ae1567d49", "cpb-aacip-9e26b7c8fb8", "cpb-aacip-a37b452d625", "cpb-aacip-f5c15b690c2", "cpb-aacip-faf95aaaffa"]
redos = wdf["asset_id"].isin(redo_guids)
wdf.loc[ redos, 'status' ] = 'Redone'

# one last one not redone
wdf.loc[ wdf["status"] == 'Assigned', 'status'] = 'Skipped'


#############################################################################
# %%
# Check for *translation* files and update Dataframe

basedir = "C:/Users/owen_king/kitchen/stovetop/WIPR_transcripts/complete/0TRANSLATIONS"

# Scan directories from Owen
owen_dirs = ["translations_LTO3-01",
             "translations_LTO3-02",
             "translations_LTO3-03",
             "translations_mine-01",
             "translations_mine-02",
             "translations_mine-03",
             "translations_valeria_sample"]

# go into each batch-level dir
for dstr in owen_dirs:
    top_dir = basedir + "/" + dstr

    # Use the presence of a vtt file as evidence of an attempt
    guids = [ fn[fn.find("cpb-aacip"):-4] for fn in glob.glob(top_dir + "/*.vtt") ]

    for guid in guids:
        ts_files = glob.glob(top_dir + "/" + guid + "-translation-en.json")
        if len(ts_files) != 1:
            wdf.loc[ wdf['asset_id'] == guid, 'es2en_status'] = 'Failed'
        else:
            wdf.loc[ wdf['asset_id'] == guid, 'es2en_status'] = 'Translated'

# filter for those that failed the first round
not_attempted = ( wdf["es2en_status"] == 'Assigned') 
fails = (wdf["es2en_status"] == 'Failed')


#############################################################################
# %%
# SAVE
# Save working working dataframe to file
write_json(wdf, "./stovetop/WIPR_transcripts/complete/transcription_work_cur.json")
write_csv(wdf, "./stovetop/WIPR_transcripts/complete/transcription_work_cur.csv")




# %%
