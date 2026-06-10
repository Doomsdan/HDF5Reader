"""Time helpers: series."""

from ._shared import *


__all__ = ['build_diff_timestring', 'time_part', 'time_part_', 'time_part_sort_', 'time_part_sort', 'regularize', 'expand_timeseries']


def build_diff_timestring(diff):
    """Split time difference given in seconds into a string representation of
    days, hours, minutes and seconds.
    """
    days = hours = minutes = 0
    seconds = abs(diff)
    while seconds >= 60:
        minutes += 1
        seconds -= 60
    while minutes >= 60:
        hours += 1
        minutes -= 60
    while hours >= 24:
        days += 1
        hours -= 24

    diff_str = ""
    if days > 0:
        diff_str += "%d d " % days
    if hours > 0:
        diff_str += "%d h " % hours
    if minutes > 0:
        diff_str += "%d m " % minutes
    diff_str += "%f s" % seconds

    return diff_str


def time_part(timestamps_or_datetimes, sub_format_str):
    """Returns the "time_part" of a timestamp or datetimes.
    The time_part has to be convertible into an integer.
    This is useful to group values according to months, weeks and so on.
    """
    def single_time_part_unix(stamp, d_format):
        return (int(unix2str(stamp, d_format))
                if np.isfinite(stamp) else None)

    def single_time_part_date(time_, d_format):
        return int(time_.strftime(d_format))

    times_ = np.asarray(timestamps_or_datetimes)

    if times_.dtype == object:
        single_time_part = single_time_part_date
    else:
        single_time_part = single_time_part_unix

    try:
        return np.array([single_time_part(timestamp, sub_format_str)
                         for timestamp in times_])
    except TypeError:
        return single_time_part(np.asscalar(times_), sub_format_str)


def time_part_(datetimes, date_part):
    try:
        return np.array([getattr(date, date_part) for date in datetimes])
    except TypeError:
        return getattr(datetimes, date_part)


def time_part_sort_(datetimes, values, date_part):
    assert len(datetimes) == len(values)
    time_of_values = np.array([getattr(date, date_part) for date in datetimes])
    grouped_values = []
    times = sorted(set(time_of_values))
    for time_key in times:
        grouped_values += \
            [values[np.where(time_of_values == time_key)[0]]]
    return times, grouped_values


def time_part_sort(timestamps, values, sub_format_str):
    """Groups "values" as a nested list according to the "sub_format_str" of
    the "timestamps".

    >>> dtimes = datetime(2000, 1, 1) + np.arange(4) * timedelta(days=16)
    >>> values = np.arange(4)
    >>> time_part_sort(dtimes, values, "%m")
    ([1, 2], [array([0, 1]), array([2, 3])])
    """
    assert len(timestamps) == len(values)
    time_of_values = time_part(timestamps, sub_format_str)
    grouped_values = []
    times = sorted(set(time_of_values))
    for time_key in times:
        grouped_values += \
            [values[np.where(time_of_values == time_key)[0]]]
    return times, grouped_values


def regularize(values, dtimes, nan=False, main_diff=None):
    """Regularize an irregular time series by linear interpolation.
    The time interval is guessed from the most frequent interval in `times`.

    >>> dtimes = datetime(2000, 1, 1) + np.arange(4) * timedelta(hours=1)
    >>> dtimes[1] += timedelta(minutes=30)
    >>> values = np.arange(4.)
    >>> values[1] = 1.5
    >>> values
    array([ 0. ,  1.5,  2. ,  3. ])
    >>> dtimes
    array([datetime.datetime(2000, 1, 1, 0, 0),
           datetime.datetime(2000, 1, 1, 1, 30),
           datetime.datetime(2000, 1, 1, 2, 0),
           datetime.datetime(2000, 1, 1, 3, 0)], dtype=object)
    >>> regularize(values, dtimes)
    (array([ 0.,  1.,  2.,  3.]), array([datetime.datetime(2000, 1, 1, 0, 0),
           datetime.datetime(2000, 1, 1, 1, 0),
           datetime.datetime(2000, 1, 1, 2, 0),
           datetime.datetime(2000, 1, 1, 3, 0)], dtype=object))
    """
    in_unix = datetime2unix(dtimes)
    t_diffs = np.diff(in_unix)
    unique_t_diffs = np.unique(t_diffs)
    if len(unique_t_diffs) == 1:
        # our work is not needed
        return values, dtimes
    if main_diff is None:
        hist, edges = np.histogram(t_diffs, unique_t_diffs)
        main_diff_seconds = edges[np.argmax(hist)]
        main_diff = timedelta(seconds=main_diff_seconds)
    elif type(main_diff) is timedelta:
        main_diff_seconds = main_diff.total_seconds()
    else:
        main_diff_seconds = main_diff
        main_diff = timedelta(seconds=main_diff_seconds)
    n_diff = int(np.ceil((in_unix[-1] - in_unix[0]) / main_diff_seconds)) + 1
    out_dtimes = dtimes[0] + main_diff * np.arange(n_diff)
    out_unix = datetime2unix(out_dtimes)
    out_values = np.interp(out_unix, in_unix, values)
    if nan:
        # put in nans where there are missing timesteps
        missing = np.where(t_diffs > main_diff_seconds)[0]
        if len(missing) > 1:
            mask = np.zeros_like(out_values, dtype=bool)
            for ii in missing:
                start_dt, end_dt = dtimes[ii:ii + 2]
                mask |= (out_dtimes > start_dt) & (out_dtimes < end_dt)
            out_values[mask] = np.nan
    return out_values, out_dtimes


def expand_timeseries(timestamps, repeats=4, values=None):
    """Interpolates timestamps and repeats according values.  Assumes constant
    length of time-step.

    Examples
    --------
    >>> import numpy as np
    >>> timestamps = str2unix(["01.01.1980 00:00:00", "02.01.1980 00:00:00"])
    >>> values = np.array([1, 2])
    >>> timestamps, values = expand_timeseries(timestamps, 2, values)
    >>> print unix2str(timestamps), values
    ['01.01.1980 00:00:00' '01.01.1980 12:00:00' '02.01.1980 00:00:00'
     '02.01.1980 12:00:00'] [1 1 2 2]
    """
    dt = (timestamps[1] - timestamps[0]) / repeats
    dts = np.arange(0, repeats * dt, dt)
    old_len = len(timestamps)
    timestamps = timestamps.repeat(repeats).reshape((old_len, repeats))
    timestamps += dts
    timestamps = timestamps.ravel()
    if values is not None:
        return timestamps, values.repeat(repeats)
    return timestamps

