"""
analyze_tps.py

This script helps select and extract images for SWT-style labeling.

The main function is `analyze_mmif()` which takes a collection of MMIF files 
output by SWT.
For each MMIF file, it analyzes the TimePoint annotations.
It looks for timepoints meeting certain intrinsic and relational criteria,
yielding a list of millisecond denominated for timestamps corresponding to that
MMIF file.

Function output is a dictionary with keys as AAPB IDs.  
Dictionary values are dictionaries with the following keys:
  - timePoint - timestamp in milliseconds
  - label - single character type label
  - subLabel - single character for subtype label (if applicable)
  - confidence - confidence about that label

The script uses the output of this function to extract stills and create a
KSL-style index for the a labeling project

"""

# %%
# Run import statements
import os
import shutil
import glob

import av
import json

import mmif
from mmif import Mmif
from mmif import AnnotationTypes
from mmif import DocumentTypes

from drawer.mmif_adjunct import mmif_check

# %%
# Set hard-coded parameters

#media_dir = "D:/challenge_2_pbd"
media_dir = "D:/challenge_1_bm"

#mmif_dir = "C:/Users/owen_king/kitchen/stovetop/challenge_2_pbd/mmif"
#mmif_dir = "C:/Users/owen_king/kitchen/stovetop/challenge_2_pbd/challenge_mmif2"
mmif_dir = "C:/Users/owen_king/kitchen/stovetop/challenge_1_bm/challenge_mmif1"

#labeler_path = "C:/Users/owen_king/frame_labeling/challenge"
#labeler_path = "C:/Users/owen_king/frame_labeling/challenge_2-2_pbd"
labeler_path = "C:/Users/owen_king/frame_labeling/challenge_1-1_bm"

ksl_path = "C:/Users/owen_king/keystrokelabeler"

if not os.path.exists(labeler_path):
    print("Creating directory:", labeler_path)
    os.mkdir(labeler_path)

    # Copy KSL setup files
    copy_files = ["conf.js", "ksllogic.js", "labeler.html", "layout.css"]
    for fn in copy_files:
        shutil.copyfile((ksl_path + "/" + fn), (labeler_path + "/" + fn))
else:
    print("Error: Project directory exists.")
    raise Exception

image_path = labeler_path + "/images"

if not os.path.exists(image_path):
    print("Creating directory:", image_path)
    os.mkdir(image_path)
else:
    print("Error: Image directory exists.")
    raise Exception


#############################################################################
# %%
# Function definitions

def analyze_mmif(mmifstr:str):

    # turn the MMIF string into a Mmif object
    usemmif = Mmif(mmifstr)

    #doc_path = usemmif.get_document_location(DocumentTypes.VideoDocument)

    # going to build a list of time points of interest
    tpois = []

    # First, get the first view that contains a TimePoint
    # If none exists, return an empty list.
    if len(usemmif.get_all_views_contain(AnnotationTypes.TimePoint)) > 0:
        useview = usemmif.get_all_views_contain(AnnotationTypes.TimePoint).pop()
    else:
        print("Warning: MMIF file contained no TimePoint annotations.")
        return tpois
    
    # Drill down to the annotations we're after, creating generators
    tpanns = useview.get_annotations(AnnotationTypes.TimePoint)


    get_low_conf = True
    get_sandwiches = True
    
    # need a list so we can examine sequences more easily
    tpannsl = list(tpanns)

    if len(tpannsl) < 3:
        print("Not enough TimePoint annotations.")
        raise Exception

    for i, ann in enumerate(tpannsl):

        sandwich = False
        low_conf = False
        label = ann.get_property("label")
        probs = ann.get_property("classification")

        # check for sandwiches
        if i > 0 and i < len(tpannsl) - 1:
            label_prev = tpannsl[i-1].get_property("label")
            label_next = tpannsl[i+1].get_property("label")
            if ( label_prev == label_next and 
                    label_prev != "NEG" and 
                    label_prev != label ):
                sandwich = True

        # check for low confidence
        if label == "NEG":
            if probs[label] < 0.50:
                low_conf = True
        elif label == "P":
            if probs[label] < 0.55:
                low_conf = True
        elif probs[label] < 0.60:
            low_conf = True
        elif label in ["O", "M", "I", "C"]:
            if probs[label] < 0.80:
                low_conf = True
        
        if (sandwich and get_sandwiches) or (low_conf and get_low_conf):
            
            if sandwich and low_conf:
                explanation = "[Sandwich; Low confidence]"
            elif sandwich:
                explanation = "[Sandwich]"
            elif low_conf:
                explanation = "[Low confidence]"

            note = label + ": " + format(probs[label], '.2f') + " " + explanation

            tpois.append( [ ann.get_property("timePoint"), label, note ])

    tpcount = len(tpannsl)

    print("tpois:", len(tpois), "out of", tpcount)  

    return( tpois )



#############################################################################
# %%
# Run process over collection of MMIF files

guid_tps = {}

mmifpaths = glob.glob(mmif_dir + "/*1.mmif")

# Build a dictionary of timepoints to analyze
for mmifpath in mmifpaths:

    print("Processing MMIF:", mmifpath)

    if not os.path.exists(mmifpath):
        print("Error:  Invalid file path for MMIF file at", mmifpath)    

    with open(mmifpath, "r") as f:
        mmifstr = f.read()
    
    item_tps = analyze_mmif(mmifstr)

    #guid_start = mmifpath.rfind("/")+1
    guid_start = mmifpath.find("cpb-aacip")
    guid_end = mmifpath.find(".",guid_start)
    if mmifpath.find("_",guid_start) < guid_end:
        guid_end = mmifpath.find("_",guid_start)
    guid = mmifpath[guid_start:guid_end]

    guid_tps[guid] = item_tps
    

# %%
# Extract images and build an index for the timepoints


ksl_index = []
stills_count = 0

for guid in guid_tps:

    video_path = media_dir + "/" + guid + ".mp4"

    container = av.open(video_path)
    video_stream = next((s for s in container.streams if s.type == 'video'), None)
    if video_stream is None:
        raise Exception("No video stream found in {}".format(video_path) ) 

    # get technical stats on the video stream; assumes FPS is constant
    fps = video_stream.average_rate.numerator / video_stream.average_rate.denominator
    
    # calculate duration in ms
    length = int((video_stream.frames / fps) * 1000)

    tps = guid_tps[guid]

    print("Extracting from", video_path)
    print("Extracting to", image_path)
    print("First extraction:", tps[0]) # DIAG
    
    fcount = 0
    stills_count = 0
    target_time = int(tps[stills_count][0])

    # going to loop through every frame in the video stream, starting at the beginning 
    for frame in container.decode(video_stream):

        # calculate the time of the frame
        ftime = int(frame.time * 1000)   

        # find the next frame after the target timeframe
        if ftime >= target_time and stills_count < len(tps):
            ifilename =  f'{guid}_{length:08}_{target_time:08}_{ftime:08}' + ".jpg"
            ipathname = image_path + "/" + ifilename
            frame.to_image().save(ipathname)

            # If label includes a subtype, then break it up.
            if (tps[stills_count][1].find(":") > 0):
                loc = tps[stills_count][1].find(":")
                label = tps[stills_count][1][:loc-1]
                sublabel = tps[stills_count][loc:]
            else:
                label = tps[stills_count][1]
                sublabel = ""

            note = tps[stills_count][2]

            ksl_index.append([ ifilename, 
                               False, 
                               label, 
                               sublabel, 
                               False, 
                               "",
                               note ])

            stills_count += 1
            if ( stills_count < len(tps) ):
                target_time = int(tps[stills_count][0])    
        
        fcount += 1

    container.close()

    print("Extracted", stills_count, "stills out of", fcount, "video frames checked.")

# %%
# Create index for KSL

print("Creating stills index...")

# convert array to a JSON string 
image_array_j = json.dumps(ksl_index)

# prettify with line breaks
image_array_j = image_array_j.replace("[[", "[\n[")
image_array_j = image_array_j.replace("], [", "], \n[")
image_array_j = image_array_j.replace("]]", "]\n]")

# add bits around the JSON text to make it valid Javascript
image_array_j = "imgArray=\n" + image_array_j
image_array_j = image_array_j + "\n;"

# write Javascript file 
array_pathname = labeler_path + "/img_arr_init.js"
with open(array_pathname, "w") as array_file:
    array_file.write(image_array_j)

print("Stills index created at " + array_pathname + ".")


# %%
