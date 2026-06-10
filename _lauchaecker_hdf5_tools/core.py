"""Lauchaecker HDF5 tools: core."""

from ._shared import *


__all__ = ['open_hdf5', 'path_dirname', 'path_basename']


def open_hdf5(x, *arg, **kw):
    """this enables using the with statement when opening an hdf5 file.
    """
    return closing(tables.open_file(x, *arg, **kw))


def path_dirname(x):
    """os.path.dirname analogue"""
    return tables.path.split_path(x)[0]


def path_basename(x):
    """os.path.basename analogue"""
    return tables.path.split_path(x)[1]

