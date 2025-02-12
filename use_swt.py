"""
use_swt.py

This functions in this module create useful data artifacts from the output of the 
SWT detection CLAMS app.

The module can be run as a stand-alone program, by passing command-line arguments.

For integration into other Python programs, the easiest option to is to call the 
`proc_display` function and the `proc_visaid` function.

"""
# %%

# Import standard modules
import argparse
import os
import sys
import warnings
import logging
import json
from pprint import pprint

from mmif import Mmif
from mmif import DocumentTypes

# Import local modules
import proc_swt 
import create_visaid
import lilhelp


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)


def proc_display(mmif_path:str):
    """
    This function simply prints a simple table of TimeFrame annotations from the MMIF file.

    It is one of the procedures conditionally called by the main() function.
    """

    # Load up the MMIF serialization from a MMIF file
    with open(mmif_path, "r") as usefile:
        mmif_str = usefile.read()

    logging.info("Attempting to process MMIF into a scene list...")

    # Get the right views
    tp_view_id, tf_view_id = proc_swt.get_swt_view_ids(mmif_str)

    # create TimeFrame table from the serialized MMIF
    tfs = proc_swt.tfs_from_mmif( mmif_str, 
                                  tp_view_id=tp_view_id,
                                  tf_view_id=tf_view_id )

    print(len(tfs), "scenes labeled in")
    print(mmif_path, ":\n")

    proc_swt.display_tfs(tfs)

    print()



def proc_visaid( mmif_path:str, 
                 video_path:str, 
                 visaid_path:str=None, 
                 stdout:bool=False,
                 scene_adj:bool=True,
                 cust_params:dict={} ):
    """
    This performs all the steps to process a MMIF file and create a visaid.

    Args:
        mmif_path (str): Path to the input MMIF file
        video_path (str): Path to the input video file
        visaid_path (str): Path to the output video file
        stdout (bool): If true, visaid is written to stdout.
        scene_adj (bool):  If true, visaid scenes (such as scene subamples) are 
            added and/or removed before visaid creation
        cust_params (dict):  Dictionary of values for custom parameters

    Returns:
        (no return value)

    Raises:
        FileNotFoundError: If the media file is missing.
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

    #
    # Figure out the path to the media file, if it has not been provided
    #
    visaid_video_path = ""
    visaid_video_dir = ""

    # if a path has been given, figure out what it is
    if video_path:
        if os.path.isdir(video_path):
            visaid_video_dir = video_path
        else:
            visaid_video_path = video_path

    # need to get information out of the MMIF file
    if not visaid_video_path:

        # get the document path from the MMIF file
        usemmif = Mmif(mmif_str)
        doc_path = usemmif.get_document_location(DocumentTypes.VideoDocument, path_only=True)

        if visaid_video_dir:
            # We were given a directory path as input.
            # Need to take the dir given and append the file name from the MMIF doc.
            visaid_video_dir = os.path.realpath(visaid_video_dir) # normalize path
            _, mmif_doc_filename = os.path.split(doc_path)
            visaid_video_path = visaid_video_dir + "/" + mmif_doc_filename
        else:
            visaid_video_path = doc_path

    if not os.path.isfile(visaid_video_path):
        raise FileNotFoundError(f"No media file found at '{visaid_video_path}'.")


    #
    # Process MMIF and create visaid
    # 
    if not stdout:
        logging.info("Attempting to process MMIF into a scene list...")

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

    _, video_filename = os.path.split(visaid_video_path)
    video_filename_base, _ = os.path.splitext(video_filename)

    if visaid_path:
        output_dirname, hfilename = os.path.split(visaid_path)
        if not output_dirname:
            output_dirname = "."
    else:
        hfilename = video_filename_base + "_visaid.html"
        output_dirname = "."


    if not stdout:
        logging.info("Creating a visual index...")

    # Create visaid
    _, visaid_path = create_visaid.create_visaid( 
        video_path=visaid_video_path, 
        tfs=tfs_adj, 
        stdout=stdout, 
        output_dirname=output_dirname,
        hfilename=hfilename,
        item_id=video_filename_base,
        item_name=video_filename,
        proc_swt_params=proc_swt_params,
        visaid_params=visaid_params,
        mmif_metadata_str=mmif_metadata_str
        )

    if not stdout:
        logging.info("Visual index created at")
        logging.info(visaid_path)



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
        help="File path for the MMIF file")
    parser.add_argument("video_path", metavar="VIDEO", type=str, nargs="?",
        help="File path for the video file.  If this is not passed in, the path will be copied from the location in the MMIF file.  If just a directory path is provided, the full file path will be inferred from that and the MMIF file.")
    parser.add_argument("-d", "--display", action="store_true",
        help="Output a summary index of TimeFrames from MMIF")
    parser.add_argument("-v", "--visaid", action="store_true",
        help="Create an HTML visual index (visaid) of TimeFrames (requires video file)")
    parser.add_argument("-s", "--stdout", action="store_true",
        help="Outputs the visaid HTML to stdout instead of writing a file.  Implies option 'visaid'. Implies not 'display'.")
    parser.add_argument("-o", "--visaid_path", type=str, default=None,
        help="File path for visaid HTML file.  Implies 'visaid'.")
    parser.add_argument("-m", "--mmif_only", action="store_true",
        help="Include only MMIF TimeFrames (do not adjust scenes according to customizations) before creating a visaid")
    parser.add_argument("-c", "--customization", type=str, default=None,
        help="Path to a JSON file supplying the values of customization options")
    
    args = parser.parse_args() 

    # Make argument values consistent
    stdout = args.stdout
    if stdout:
        display = False
        visaid = True
        warn = False
    else:
        display = args.display
        visaid = args.visaid

    # Validate non-boolean  arguments
    mmif_path = args.mmif_path
    if not os.path.exists(mmif_path):
        print("Error:  Invalid file path for MMIF file.")
        print("Run with '-h' for help.")
        sys.exit(1)

    video_path = args.video_path
    if visaid:
        if video_path is not None:
            if not os.path.exists(video_path):
                print("Error:  Invalid file or directory path for the video file.")
                print("Run with '-h' for help.")
                sys.exit(1)

    visaid_path = args.visaid_path
    if visaid and visaid_path:
        output_dirname, _ = os.path.split(visaid_path)
        if output_dirname and not os.path.exists(output_dirname):
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

    if visaid:
        if cust_path:
            with open(cust_path, "r") as file:
                cust_params = json.load(file)
            if not stdout:
                # Warn about spurious parameters
                for key in cust_params:
                    if key not in { **proc_swt.PROC_SWT_DEFAULTS, 
                                    **create_visaid.VISAID_DEFAULTS } :
                        logging.warning("Warning: `" + key + "` is not a valid config option for this postprocess. Ignoring.")
        else:
            cust_params = {}

        proc_visaid( mmif_path, 
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

