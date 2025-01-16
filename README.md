# Visaid Builder
Routines for processing MMIF files to create visual indexes ("visaids") and other useful output.

These routines require existing MMIF files containing annotations of videos.  MMIF files with relevant annotations can be created with the [CLAMS scenes-with-text detection app](https://github.com/clamsproject/app-swt-detection).

## Overview

The `use_swt.py` module is a stand-alone (not presupposing any particular workflow or media source) application for creating visaids from an existing MMIF file and the corresponding media file.

The `process_swt.py` module includes functions for processing MMIF produced by the [CLAMS swt-detection app](https://github.com/clamsproject/app-swt-detection).

The `post_proc_item` module includes functions called by `run_job.py` from [clams-kitchen](https://github.com/WGBH-MLA/clams-kitchen) calls functions in `process_swt.py` to perform postprocessing on MMIF produced by swt-detection.

## Installation

Clone the repository.  Change to the repository directory and do a `pip install -r requirements.txt`.

## Usage

For basic usage guidance, run `python use_swt.py -h`.

To create a visaid using the sample MMIF file in this repository, download the corresponding [media file](https://drive.google.com/file/d/1-sSZxDUf9ZKCseVL_QBpqwQNAaffXRBu/view?usp=sharing) to the `sample_files` directory.  Then run 

```
$ python use_swt.py -d -v sample_files/cpb-aacip-4071f72dd46_swt_v72.mmif sample_files/cpb-aacip-4071f72dd46.mp4
```



