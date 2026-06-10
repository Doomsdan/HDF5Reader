"""Compatibility wrapper for the split hdf5_gui_py3 meteox2y module."""

from pathlib import Path
import sys


_HDF5_GUI_DIR = Path(__file__).resolve().parent / "hdf5_gui_py3"
_hdf5_gui_dir = str(_HDF5_GUI_DIR)
if _hdf5_gui_dir not in sys.path:
    sys.path.insert(0, _hdf5_gui_dir)

from _hdf5_gui_meteox2y import load_namespace as _load_namespace


_namespace, __all__ = _load_namespace()
globals().update(_namespace)

del _HDF5_GUI_DIR, _hdf5_gui_dir, _namespace, _load_namespace
