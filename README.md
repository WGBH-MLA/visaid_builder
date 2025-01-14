# Visaid Builder
Routines for processing MMIF files to create visual indexes ("visaids") and other useful output.

## Overview

The `use_swt.py` module is a stand-alone (not presupposing any particular workflow or media source) application for creating visaids.

The `process_swt.py` module includes functions for processing MMIF produced by the [CLAMS swt-detection app](https://github.com/clamsproject/app-swt-detection).

The `post_proc_item` module includes functions called by `run_job.py` from [clams-kitchen](https://github.com/WGBH-MLA/clams-kitchen) calls functions in `process_swt.py` to perform postprocessing on MMIF produced by swt-detection.

## Installation

Clone the repository.  Change to the repository directory and do a `pip install -r requirements.txt`.

## Usage

For basic usage run `python use_swt.py -h`.


