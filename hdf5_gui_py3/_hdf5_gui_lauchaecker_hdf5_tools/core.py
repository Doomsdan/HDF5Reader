"""Lauchaecker HDF5 tools: core."""

from ._shared import *


__all__ = ['str2datetime', 'stamp2index', 'open_hdf5', 'path_dirname', 'path_basename']


def str2datetime(x):
        return pd.core.tools.datetimes.parse_time_string(x)[0]


def stamp2index(stamp):
            
            liste=pd.date_range(datetime.datetime.strptime(str(refts),"b'%Y-%m-%dT%H:%M:%S'"), datetime.datetime.now(),freq=str(int(period.total_seconds()/60))+'Min')
            index=(liste == stamp).argmax()
            #index = times.timestamp2index(stamp, period, refts)
            if index==0 and stamp!=refts:
                index=total_timesteps - 1
            # wrap around to indices that actually exist
            return min(total_timesteps - 1, max(0, index))


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

