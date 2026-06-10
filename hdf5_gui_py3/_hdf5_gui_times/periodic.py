"""Time helpers: periodic."""

from ._shared import *


__all__ = ['periodic_distance', 'doy_distance', 'hour_distance', 'daily_ranges', 'feb29_mask']


def periodic_distance(x1, x2, period):
    """

    Examples
    --------
    >>> periodic_distance(0, 23, 24)
    array(1.0)
    """
    period = float(period)
    dist = (x1 - x2) % period
    return np.where(dist > period / 2, period - dist, dist)


def doy_distance(doy1, doy2):
    """

    Examples
    --------
    >>> import numpy as np
    >>> doy_distance(0, np.array([364, 0, 1]))
    array([ 1.,  0.,  1.])
    """
    return periodic_distance(doy1, doy2, 365)


def hour_distance(hour1, hour2):
    return periodic_distance(hour1, hour2, 24)


def daily_ranges(dtimes, data):
    """Daily max-min.

    Parameters
    ----------
    dtimes : sequence of datetime objects
        For the time being it is assumed that time steps are equally spaced!
    data : 1d array

    Returns
    -------
    ranges : 1d array
        length is number of days in dtimes.
    """
    step_length = (dtimes[1] - dtimes[0]).total_seconds()
    steps_per_day = 60 ** 2 * 24 / step_length
    data_2d = data.reshape(-1, steps_per_day)
    maxs = np.nanmax(data_2d, axis=1)
    mins = np.nanmin(data_2d, axis=1)
    return maxs - mins


def feb29_mask(dtimes):
    """Returns a mask indicating the location of the additional day in the
    leap years.

    Should help you to get rid off those buggers.

    Parameter
    ---------
    dtimes : ndarray

    Returns
    -------
    mask : boolean ndarray
    """
    months = time_part(dtimes, "%m")
    days = time_part(dtimes, "%d")
    return (months == 2) & (days == 29)

