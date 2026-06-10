# -*- coding: utf-8 -*-
r"""
Tools for the Lauchaecker hdf5 file (:mod:`meteo.lauchaecker_hdf5_tools`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This module was written to work with the data of the
lauchaecker meteo station, stored in the file
lconf.hdf5_filename

It contains functions to get the data in and out of the file, and some plotting
routines to produce pre-defined plots such as meteogram and pluviogram.


   create_hdf5
   logger2hdf5
   hdf52df
   plot_logger_data_reaches
   compare_year
   data2hdf5
   data_reaches
   evapo_from_hdf5
   evapo_plot
   hdf52txt
   hdf5_2_meteogram
   hdf5_2_pluviogram
   hdf5_2_soilplot
   kenntage
   read_hdf5
"""

# import a lot of tools that are or may be of use (but importing is slow)
import os
import calendar
import time
from datetime import timedelta
import datetime
from collections import namedtuple
import warnings
import glob
from contextlib import closing
import tables
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.dates import num2date
import pandas as pd
import distutils
import times
# enthaelt div. Funktionen zur Be- und Umrechung von Meteodaten (-> Magda)
import meteox2y as mxy
import lauchaecker_config as lconf
# Funktionen zur Mittelung von Windaten (-> Raphael, Dirk)
from avrwind import (angle2component, avrwind, component2angle)
import dirks_globals as my
