"""
use_swt.py

# Overview

This module creates useful data artifacts from the output of the 
SWT detection CLAMS app.
"""
# %%

# Import standard modules
import argparse
import os
import sys
import warnings
import json
from pprint import pprint

# Import local modules
import proc_swt 
import create_visaid
import lilhelp


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



def proc_display(mmif_path:str):
    """
    This function simply prints a simple table of TimeFrame annotations from the MMIF file
    """

    # Load up the MMIF serialization from a MMIF file
    with open(mmif_path, "r") as usefile:
        mmif_str = usefile.read()

    print("Attempting to process MMIF into a scene list...")

    # Get the right views
    tp_view_id, tf_view_id = proc_swt.get_swt_view_ids(mmif_str)

    # create TimeFrame table from the serialized MMIF
    tfs = proc_swt.tfs_from_mmif( mmif_str, 
                                  tp_view_id=tp_view_id,
                                  tf_view_id=tf_view_id )

    print(len(tfs), "scenes labeled in")
    print(mmif_path, ":\n")

    display_tfs(tfs)

    print()



def proc_visual( mmif_path:str, 
                 video_path:str, 
                 visaid_path:str=None, 
                 stdout:bool=False,
                 scene_adj:bool=True,
                 cust_params:dict={} ):
    """
    This performs all the steps to process a MMIF file and create a visaid.
    """

    #
    # Collect and sort all the declared and default parameters        
    #
    if not cust_params:
        cust_params = {}

    proc_swt_params = {}
    for key in proc_swt.PROC_SWT_DEFAULTS:
        if key in cust_params:
            proc_swt_params[key] = cust_params[key]
        else:
            proc_swt_params[key] = proc_swt.PROC_SWT_DEFAULTS[key]
    visaid_params = {}
    for key in create_visaid.VISAID_DEFAULTS:
        if key in cust_params:
            visaid_params[key] = cust_params[key]
        else:
            visaid_params[key] = create_visaid.VISAID_DEFAULTS[key]

    
    # Load up the MMIF serialization from a MMIF file
    with open(mmif_path, "r") as usefile:
        mmif_str = usefile.read()

    if not stdout:
        print("Attempting to process MMIF into a scene list...")

    # Get the right views
    tp_view_id, tf_view_id = proc_swt.get_swt_view_ids(mmif_str)

    # create TimeFrame table from the serialized MMIF
    tfs = proc_swt.tfs_from_mmif( mmif_str, 
                                  tp_view_id=tp_view_id,
                                  tf_view_id=tf_view_id )

    # find the outer temporal boundaries of the TimePoint analysis
    first_time, final_time = proc_swt.first_final_time_in_mmif( mmif_str, tp_view_id=tp_view_id )

    # Create an adjusted TimeFrame table (with scenes added and/or removed)
    if scene_adj:
        tfs_adj = proc_swt.adjust_tfs( tfs, first_time, final_time, proc_swt_params )
    else:
        tfs_adj = tfs[:]

    mmif_metadata_str = proc_swt.get_mmif_metadata_str( mmif_str,
                                                        tp_view_id,
                                                        tf_view_id )

    # Assign values for other required parameters
    if visaid_path:
        output_dirname, hfilename = os.path.split(visaid_path)
    else:
        output_dirname, hfilename = ".", ""

    _, video_filename = os.path.split(video_path)


    if not stdout:
        print("Creating a visual index...")

    _, visaid_path = create_visaid.create_visaid( 
        video_path=video_path, 
        tfs=tfs_adj, 
        stdout=stdout, 
        output_dirname=output_dirname,
        hfilename=hfilename,
        item_id=video_filename,
        proc_swt_params=proc_swt_params,
        visaid_params=visaid_params,
        mmif_metadata_str=mmif_metadata_str
        )

    if not stdout:
        print("Visual index created at")
        print(visaid_path)




def main():
    app_desc="""
    Creates useful data artifacts from the output of the SWT detection CLAMS app.
    """

    parser = argparse.ArgumentParser(
        prog='python use_swt.py',
        description=app_desc,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("mmif_path", metavar="MMIF", type=str,
        help="Path and filename for the MMIF file")
    parser.add_argument("video_path", metavar="VIDEO", type=str, nargs="?",
        help="Path and filename for the video file")
    parser.add_argument("-d", "--display", action="store_true",
        help="Output a summary index of TimeFrames from MMIF")
    parser.add_argument("-v", "--visual", action="store_true",
        help="Create an HTML file with a visual index of TimeFrames (requires video file)")
    parser.add_argument("-s", "--stdout", action="store_true",
        help="Outputs the visual index HTML to stdout instead of writing a file.  Implies 'visual'. Implies not 'display'.")
    parser.add_argument("-o", "--visaid_path", type=str, default=None,
        help="File path for visual index HTML file.  Implies 'visual'.")
    parser.add_argument("-m", "--mmif_only", action="store_true",
        help="Include only MMIF TimeFrames (do not adjust scenes according to customizations) before creating a visual index")
    parser.add_argument("-c", "--customization", type=str, default=None,
        help="Path to a JSON file supplying the values of customization options")
    
    args = parser.parse_args() 

    # Make argument values consistent
    stdout = args.stdout
    if stdout:
        display = False
        visual = True
        warn = False
    else:
        display = args.display
        visual = args.visual

    # Validate non-boolean  arguments
    mmif_path = args.mmif_path
    if not os.path.exists(mmif_path):
        print("Error:  Invalid file path for MMIF file.")
        print("Run with '-h' for help.")
        sys.exit(1)

    video_path = args.video_path
    if visual:
        if video_path is None:
            print("Error:  Video file path must be provided for 'visual'.")
            print("Run with '-h' for help.")
            sys.exit(1)
        elif not os.path.exists(video_path):
            print("Error:  Invalid file path for video file.")
            print("Run with '-h' for help.")
            sys.exit(1)

    visaid_path = args.visaid_path
    if visual and visaid_path:
        output_dirname, hfilename = os.path.split(visaid_path)
        if not os.path.exists(output_dirname):
            print("Error:  No directory exists corresponding to visaid file path.")
            print("Run with '-h' for help.")
            sys.exit(1)

    # Validate customization file
    cust_path = args.customization
    if cust_path:
        if not os.path.exists(cust_path):
            print("Error:  No file exists at the supplied customization file path.")
            print("Run with '-h' for help.")
            sys.exit(1)

    if args.mmif_only:
        scene_adj = False
    else:
        scene_adj = True


    # Call the appropriate procedures. 
    # (These are not mutually exclusive.)

    # suppress warnings that come from the Mmif module
    warnings.filterwarnings("ignore")

    if display:
        proc_display(mmif_path)

    if visual:
        if cust_path:
            with open(cust_path, "r") as file:
                cust_params = json.load(file)
            if not stdout:
                # Warn about spurious parameters
                for key in cust_params:
                    if key not in { **proc_swt.PROC_SWT_DEFAULTS, 
                                    **create_visaid.VISAID_DEFAULTS } :
                        print("Warning: `" + key + "` is not a valid config option for this postprocess. Ignoring.")
        else:
            cust_params = {}

        proc_visual( mmif_path, 
                     video_path, 
                     visaid_path=visaid_path,
                     stdout=stdout, 
                     scene_adj=scene_adj,
                     cust_params=cust_params )


#
# Call to main function for stand-alone execution
#
if __name__ == "__main__":
    main()

