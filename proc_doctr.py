"""
proc_doctr.py

Defines functions that perform processing on MMIF output from docTR.

"""

import logging
from pprint import pprint 

import pandas as pd

from mmif import Mmif
from mmif import AnnotationTypes

try:
    # if being run from higher level module
    from . import lilhelp
except ImportError:
    # if run as stand-alone
    import lilhelp
