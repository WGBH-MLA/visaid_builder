# %%

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



mmif_path = "./buffet/cpb-aacip-37-95w6mnpw_out44-test.mmif"


# Load up the MMIF serialization from a MMIF file
usefile = open(mmif_path, "r")
mmifstr = usefile.read()
usefile.close()

# Process the serialized MMIF to create the table of time frames
tfs = swt.process_swt.list_tfs(mmifstr)


video_path = "../../AAPBv/cpb-aacip-37-95w6mnpw.mp4"


mfilename = os.path.basename(mmif_path)
proj_name, ext = os.path.splitext(mfilename)

# If the filename begins with "cpb-aacip", then assume that
# the guid is the filename without the extension.
vfilename = os.path.basename(video_path)
vfname, ext = os.path.splitext(vfilename)
if ( vfname[:9] == "cpb-aacip" ):
    guid = vfname
else:
    guid = None

swt.process_swt.create_aid(
    video_path=video_path, 
    tfs=tfs, 
    proj_name=proj_name, 
    guid=guid,
    types=['bars','slate','chyron','credit']
    )

