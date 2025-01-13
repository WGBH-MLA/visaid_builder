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
from pprint import pprint

# Import local modules
import process_swt 
import lilhelp

MAX_GAP = 180000

def main():
    
    app_desc="""
    Creates useful data artifacts from the output of the SWT detection CLAMS app.
    """

    parser = parser = argparse.ArgumentParser(
        prog='python use_swt.py',
        description=app_desc,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("mmif_path", metavar="MMIF",
        help="Path and filename for the MMIF file")
    parser.add_argument("video_path", metavar="VIDEO", nargs="?",
        help="Path and filename for the video file")
    parser.add_argument("-d", "--display", action="store_true",
        help="Output a summary index of TimeFrames from MMIF")
    parser.add_argument("-e", "--extract", action="store_true",
        help="Extract representative stills from each TimeFrame and save them in a directory (requires video file)")
    parser.add_argument("-v", "--visual", action="store_true",
        help="Create an HTML file with a visual index of TimeFrames (requires video file)")
    parser.add_argument("-s", "--stdout", action="store_true",
        help="Outputs the visual index HTML to stdout instead of writing a file.  Implies 'visual'. Implies not 'display' or 'extract'.")
    parser.add_argument("-w", "--warn", action="store_true",
        help="Display (do not suppres) Python warning messages")
    
    args = parser.parse_args() 
    #print(args)

    if not args.warn:
        warnings.filterwarnings("ignore")

    # make argument values consistent
    stdout = args.stdout
    if stdout:
        display = False
        extract = False
        visual = True
    else:
        display = args.display
        extract = args.extract
        visual = args.visual

    # validate positional arguments
    mmif_path = args.mmif_path
    video_path = args.video_path
    if not os.path.exists(mmif_path):
        print("Error:  Invalid file path for MMIF file.")
        print("Run with '-h' for help.")
        sys.exit(1)
    if visual or extract:
        if video_path is None:
            print("Error:  Video file path must be provided for 'visual' or 'extract'.")
            print("Run with '-h' for help.")
            sys.exit(1)
        elif not os.path.exists(video_path):
            print("Error:  Invalid file path for video file.")
            print("Run with '-h' for help.")
            sys.exit(1)

    # Load up the MMIF serialization from a MMIF file
    usefile = open(mmif_path, "r")
    mmifstr = usefile.read()
    usefile.close()

    # Process the serialized MMIF to create the table of time frames
    if visual:
        tfs = process_swt.list_tfs(mmifstr, max_gap=MAX_GAP, include_endframe=True)
    else:
        tfs = process_swt.list_tfs(mmifstr)

    # Display the TimeFrame index
    if display: 
        # create prettier table
        tfs_pretty = []
        for f in tfs:
            tfs_pretty += [[ f"{f[2]:08}", 
                             lilhelp.tconv(f[2]), 
                             lilhelp.tconv(f[3]), 
                             f[1] ]]

        print(len(tfs), "scenes labeled in")
        print(mmif_path, ":")
        print()
        pprint(tfs_pretty)
        print()

    # Extract stills that are representatives of each TimeFrame
    if extract :
        print("Extracting representative stills for TimeFrame annotations...")
        exlist = []
        for row in tfs:
            #if row[1] == 'chyron' or row[1] == 'credits' :
            exlist.append(row[4])  # representative timepoint for the TimeFrame (in ms)

        # title project based on the name of the video file
        vfilename = os.path.basename(video_path)
        fname, ext = os.path.splitext(vfilename)
        
        lilhelp.extract_stills(video_path, exlist, fname)
        print("Done.")

    # Make visual aid for cataloging
    if visual:
        if not stdout:
            print("Creating a visual index of TimeFrame annotations...")

        # Title the project based on the name of the MMIF file
        mfilename = os.path.basename(mmif_path)
        proj_name, ext = os.path.splitext(mfilename)

        # If the filename begins with "cpb-aacip", then assume that
        # the guid is the filename without the extension.
        vfilename = os.path.basename(video_path)
        vfname, ext = os.path.splitext(vfilename)
        if  vfname[:9] == "cpb-aacip" :
            guid = vfname
        else:
            guid = None

        process_swt.create_aid(
            video_path=video_path, 
            tfs=tfs, 
            stdout=stdout, 
            guid=guid,
            id_in_filename=False)

        if not stdout:
            print("Done.")
        

if __name__ == "__main__":
    main()

