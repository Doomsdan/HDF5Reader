# Name:        times
# Purpose: several time conversions and stuff, formerly found in
#          time_array_conversion, timestamp or my_globals
#
# Author:      Thomas Pfaff, Magdalena Eder, Dirk Schlabing
#
# Created:     17.11.2011
# Copyright:   (c) guttenberg 2011
# Licence:     <who cares?>
#!/usr/bin/env python
"""
Time helpers and conversions (:mod:`times`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Helper functions to convert arrays containing time information.
All the functions with a ``2`` in the name provide the advertised conversions
for scalar as well as for *array* input.

.. currentmodule:: lhglib.contrib.times

.. autosummary::
   :nosignatures:
   :toctree: generated/

    cwr2datetime
    cwr2str
    cwr2unix
    datetime2doy
    datetime2ordinal
    datetime2str
    datetime2unix
    doy2datetime
    iso2datetime
    iso2unix
    ordinal2datetime
    str2datetime
    str2ordinal
    str2unix
    unix2cwr
    unix2datetime
    unix2ordinal
    unix2str

    time_part
    time_part_sort
    timestamp2index
    index2timestamp
"""

from datetime import datetime, timedelta
import itertools
import time
import calendar
import numpy as np
import pandas as pd
