"""
analyze_tps.py

"""

# %%
# Run import statements
import os
import io
import base64

import pandas as pd
import av

import mmif
from mmif import Mmif
from mmif import AnnotationTypes

import drawer.lilhelp


mmif_filepath = 