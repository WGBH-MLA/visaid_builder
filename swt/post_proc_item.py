"""
post_proc_item.py

Defines functions for doing post processing of MMIF created by SWT
"""
module_version = "0.1"

# %%
# Run import statements

import mmif
from mmif import Mmif
from mmif import AnnotationTypes

import drawer.lilhelp
import swt.process_swt

# Global default values for SWT processing
# The longest gap without a sample
max_gap = 180000
# The latest valid start time for the program
#   (We won't look for the main program slate after this point.)
#   (And we won't assign a proxy start time after this point.)
prog_start_max = 150000


def run_post(item, post_proc, mmif_path, artifacts_dir:str, batch_id:str, batch_name:str=""):

    if batch_name == "":
        batch_name = batch_id

    global max_gap, prog_start_max

    if "name" in post_proc:
        if post_proc["name"].lower() != "swt":
            print("Post-processing error: Tried to run", post_proc["name"],
                  "process with SWT post-processing function.")
            return False
    else:
        print("Post-processing error: No post-process or name specified.")
        return False


    # Set up for hte particular kinds of artifacts requested 
    if "artifacts" in post_proc:
        artifacts = post_proc["artifacts"]
    else:
        artifacts = []

    if "data" in artifacts:
        data_dir = artifacts_dir + "/data"
        infer_data = True

    if "slates" in artifacts:
        slates_dir = artifacts_dir + "/slates"
        get_slate = True

    if "visaids" in artifacts:
        visaids_dir = artifacts_dir + "/visaids"
        make_visaid = True


    # Open MMIF and start processing
    with open(mmif_path, "r") as file:
        mmif_str = file.read()

    # call SWT MMIF processors to get a table of time frames
    tfs = swt.process_swt.list_tfs(mmif_str, max_gap=max_gap)

    # get metadata_str
    metadata_str = swt.process_swt.get_mmif_metadata_str(mmif_str)


    #
    # Infer metadata
    #
    if infer_data:

        # Calculate some significant datapoints based on table of time frames
        #
        # Note:  For reasons I don't understand, we have to cast some integer
        # values originally created by Pandas to int from int64

        # The end of the bars is the end of the last bars timeframe
        # If there is no bars timeframe, then the value is 0
        bars_end = 0
        bars_tfs = [ tf for tf in tfs 
                        if (tf[1] in ['bars'] and tf[3] <= prog_start_max) ]
        if len(bars_tfs) > 0:
            bars_end = int(bars_tfs[-1][3])

        # Proxy starts at the end of the bars or the beginning of the slate,
        # whichever is greater
        slate_begin = None
        slate_tfs = [ tf for tf in tfs 
                        if (tf[1] in ['slate'] and tf[3] <= prog_start_max)]
        if len(slate_tfs) > 0:
            slate_begin = int(slate_tfs[0][2])
            proxy_start_ms = max(bars_end, slate_begin)
        else:
            proxy_start_ms = bars_end

        # print("bars end:", bars_end, "slate begin:", slate_begin, "proxy start:", proxy_start_ms) # DIAG

        item["slate_begin"] = slate_begin
        item["bars_end"] = bars_end
        item["proxy_start"] = proxy_start_ms / 1000

        print("Proxy start:", item["proxy_start"])


    #
    # Extract the slate
    #
    if get_slate:
        # The slate rep is the rep timepoint from from the first slate timeframe
        # If there is not slate timeframe, then the value is None
        slate_rep = None
        slate_tfs = [ tf for tf in tfs if tf[1] in ['slate'] ]
        if len(slate_tfs) > 0:
            slate_rep = int(slate_tfs[0][4])

        if slate_rep is not None:
            print("Trying to exact a slate...")

            try:
                slate_rslt = drawer.lilhelp.extract_stills( 
                               item["media_path"], 
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

        if "scene_types" in post_proc:
            scene_types = post_proc["scene_types"]
        else:
            scene_types = []

        try:
            visaid_filename, visaid_path = swt.process_swt.create_aid( 
                video_path=item["media_path"], 
                tfs=tfs, 
                stdout=False, 
                output_dirname=visaids_dir,
                batch_name=batch_name, 
                guid=item["asset_id"],
                types=scene_types,
                metadata_str=metadata_str
                )

            item["visaid_filename"] = visaid_filename
            item["visaid_path"] = visaid_path

        except Exception as e:
            print("Creation of visaid failed.")
            print("Error:", e)
