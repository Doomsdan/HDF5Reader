"""Just some functions I find myself writing or searching for again and
again..."""

# The imports are not all done here.  Importing this module to use a few
# specific functions would mean pulling a lot of other imports in that are not
# needed.  As importing some of the modules can be quite costly speed-wise,
# the clarity of having the import statements at the beginning is consciously
# compromised.
from __future__ import with_statement

import contextlib
import fnmatch
import inspect
import itertools
import logging
import os
import re
import subprocess
import sys
import warnings
#from UserDict import UserDict
from collections import UserDict

try:
    # should make multiprocessing less stressfull
    import dill as pickle
except ImportError:
    import pickle
import multiprocessing
from queue import Queue
import threading
import hashlib
import functools
import random
import numpy as np
try:
    import numexpr as ne
    NE = True
except ImportError:
    NE = False
from scipy import optimize, stats
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as mpatches
##from lhglib.contrib import smoothing
# further imports following below
# import string
# import doctest
# from scipy.stats import stats as sp_stats

# Generic
