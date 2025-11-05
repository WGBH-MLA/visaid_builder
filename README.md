# Visaid Builder
Routines for processing MMIF files to create visual indexes ("visaids") and other useful output.

These routines require existing MMIF files containing annotations of videos.  MMIF files with relevant annotations can be created with the [CLAMS scenes-with-text detection app](https://github.com/clamsproject/app-swt-detection).

## Overview

The `use_swt` module is a stand-alone (not presupposing any particular workflow or media source) application for creating visaids from an existing MMIF file and the corresponding media file.

The `process_swt` module includes functions for processing MMIF produced by the [CLAMS swt-detection app](https://github.com/clamsproject/app-swt-detection).

The `post_proc_item` module includes functions called by `run_job` from [clams-kitchen](https://github.com/WGBH-MLA/clams-kitchen) and calls functions in `process_swt` to perform postprocessing on MMIF produced by swt-detection.

## Installation

To install the necessary dependencies, navigate to the project's root directory and run:

```bash
pip install .
```

## Usage

### CLI

For guidance on usage of the stand-alone CLI, run `visswt -h`.

To see a list of the TimeFrame annotations in a MMIF file from SWT-detection, run:
```bash
visswt -d my_swt_output.mmif
```

To create a visaid using the sample MMIF file in this repository, download the corresponding [media file](https://drive.google.com/file/d/1-sSZxDUf9ZKCseVL_QBpqwQNAaffXRBu/view?usp=sharing) to the `sample_files` directory. Then run:

```bash
visswt -d -v sample_files/cpb-aacip-4071f72dd46_swt_v72.mmif sample_files/cpb-aacip-4071f72dd46.mp4
```

### Integration in Python projects

The easiest way to integrate visaid creation into another Python project is by importing `proc_visaid` directly from the `visaid_builder` package and calling it. For an example, see the `visaid_builder/integration_example.py` file.


