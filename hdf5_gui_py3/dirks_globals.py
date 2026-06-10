"""Compatibility wrapper for the split dirks_globals.py implementation.

Implementation details live in the `_hdf5_gui_dirks_globals` package so this
module can stay import-compatible with the historic single-file API.
"""

from _hdf5_gui_dirks_globals import load_namespace as _load_namespace


_namespace, __all__ = _load_namespace()
globals().update(_namespace)

del _namespace, _load_namespace
