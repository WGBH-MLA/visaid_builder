"""
integration_example.py

Example module showing how to integrate this library into other Python projects.
"""

import visaid_builder

# These values will be set by the calling module.
mmif_path = "./sample_files/cpb-aacip-4071f72dd46_swt_v72.mmif"
video_path = "./sample_files/cpb-aacip-4071f72dd46.mp4"
visaid_path = "./cpb-aacip-4071f72dd46_visaid_example1.html"

# This dictionary will be set by the calling module, which might read this 
# dict from a JSON file.
cust_params = {
    "include_only": None,
    "exclude": [],
    "max_unsampled_gap": 60000,
    "subsampling": {
        "bars": 120100,
        "slate": 9900,
        "chyron": 15100,
        "main title": 15100,
        "other text": 15100,  
        "filmed text": 30100,
        "credits": 1900 },
    "default_subsampling": 60100,
    "include_first_time": False,
    "include_final_time": False,
    "job_id_in_visaid_filename": False,
    "display_video_duration": True,
    "display_job_info": True,
    "display_image_ms": True,
    "aapb_timecode_link": False }

# Call to the function that creates a visaid
visaid_builder.proc_visaid ( mmif_path, 
                             video_path, 
                             visaid_path=visaid_path, 
                             cust_params=cust_params )
                             