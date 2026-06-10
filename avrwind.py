"""Compatibility wrapper for the hdf5_gui_py3 avrwind module."""

from pathlib import Path
import sys


_HDF5_GUI_DIR = Path(__file__).resolve().parent / "hdf5_gui_py3"
_hdf5_gui_dir = str(_HDF5_GUI_DIR)
if _hdf5_gui_dir not in sys.path:
    sys.path.insert(0, _hdf5_gui_dir)

from hdf5_gui_py3.avrwind import *  # noqa: F401,F403

del _HDF5_GUI_DIR, _hdf5_gui_dir
