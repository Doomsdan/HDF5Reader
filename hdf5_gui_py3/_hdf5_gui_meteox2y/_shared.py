"""
Meteorological Conversions (:mod:`meteo.meteox2y`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The meteox2y module provides functions to calculate derived meteorological
variables from measured meteorological values.

.. currentmodule:: lhglib.contrib.meteo.meteox2y

.. autosummary::
   :nosignatures:
   :toctree: generated/

   sat_vap_p
   rel2vap_p
   vap_p2rel
   dewpoint
   dew2rel
   norm_pressure
   iziomon
   lw2clouds
   lw_tennessee
   haude
   turc
   turc_rad
   hargreaves
   penman_monteith
   pot_s_rad
   sunshine
   blackbody_rad
   altitude
   spec_hum
   psychro2e
   slope_sat_p

"""

from datetime import datetime, timedelta
import warnings
import numpy as np
import times
import dirks_globals as my
