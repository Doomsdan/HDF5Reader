"""Time helpers: timestamps."""

from ._shared import *


__all__ = ['timedelta2seconds', 'timedelta2slice', 'timestamps2slice', 'timestamp2index', 'isoformat2unix', 'index2timestamp']


def timedelta2seconds(dt):
    return dt.days * 86400 + dt.seconds + dt.microseconds * 1e-6


def timedelta2slice(delta, dt, offset=0, step=None):
    start = offset
    stop = None if delta is None else offset + int(timedelta2seconds(delta) /
                                                   timedelta2seconds(dt))
    return slice(start, stop, step)


def timestamps2slice(startts=None, endts=None, dt=None, refts=None, step=None):
    """Ask Thomas.

    >>> timestamps2slice('2010-03-01T23:54:00', '2010-03-07T23:52:00', \
                         timedelta(days=1))
    slice(0, 5, None)
    >>> timestamps2slice('2010-03-01T23:54:00', '2010-03-07T23:52:00', \
                         timedelta(days=1), '2010-03-04T00:00:00')
    slice(-2, 3, None)
    >>> timestamps2slice('2010-03-01T23:54:00', '2010-03-07T23:52:00', \
                         timedelta(days=1), '2010-01-04T00:00:00')
    slice(56, 61, None)
    """
    # Dirk: Ist das Kunst oder kann das weg?
#    if dt is None:
#        tdelta = timedelta(seconds=1)

    if startts is None:
        tstart = None
    if type(startts) == str:
        tstart = datetimefromisoformat(startts)
    else:
        tstart = startts

    if endts is None:
        tend = None
    if type(endts) == str:
        tend = datetimefromisoformat(endts)
    else:
        tend = endts

    if refts is None:
        tref = tstart
    elif type(refts) == str:
        tref = datetimefromisoformat(refts)
    else:
        tref = refts

    if (tstart is None) or (tref is None):
        slicestart = None
    else:
        slicestart = int(timedelta2seconds(tstart - tref) /
                         timedelta2seconds(dt))

    return timedelta2slice(None if ((tend is None)or(tstart is None))
                           else tend - tstart, dt, slicestart, step)


def timestamp2index(ts, dt, refts, **kwargs):
    """Calculates the array index for a certain time in an equidistant
    time-series given the reference time (where the index would be 0)
    and the time discretization.
    If any of the input parameters contains timezone information, all others
    also need to contain timezone information.

    Parameters
    ----------
    ts        : str or datetime-object
                The timestamp to determine the index for
                If it is a string, it will be converted to datetime using the
                function _datetimefromisoformat Formatting keywords may be
                passed to this function

    dt        : str or timedelta object
                The discretization of the time series (the amount of time that
                elapsed between indices)
                If used as a string, it needs to be given in the format
                "keyword1=value1,keyword2=value2". Keywords must be understood
                by the timedelta constructor (like days, hours,
                minutes, seconds) and the values may only be integers.

    refts     : str or datetime-object
                The timestamp to determine the index for
                If it is a string, it will be converted to datetime using the
                function _datetimefromisoformat Formatting keywords may be
                passed to this function

    Returns
    -------
    index    : integer
               The index of a discrete time series array of the given
               parameters

    Example
    -------
    >>> timestr1, timestr2 = '2008-06-01T00:00:00', '2007-01-01T00:00:00'
    >>> timestamp2index(timestr1, 'minutes=5', timestr2)
    148896
    >>> timestamp2index(timestr1, 'hours=1,minutes=5',timestr2)
    11453
    >>> timestamp2index(timestr1, timedelta(hours=1, minutes=5), timestr2)
    11453
    """
    if not isinstance(ts, datetime):
        _ts = datetimefromisoformat(ts, **kwargs)
    else:
        _ts = ts
    if not isinstance(refts, datetime):
        _refts = datetimefromisoformat(refts, **kwargs)
    else:
        _refts = refts
    if not isinstance(dt, timedelta):
        kwargs = dict([(sp[0], int(sp[1]))
                       for sp in [item.split('=') for item in dt.split(',')]])
        _dt = timedelta(**kwargs)
    else:
        _dt = dt
    return int(timedelta2seconds(_ts - _refts) / timedelta2seconds(_dt))


def isoformat2unix(ts):
    dt = timedelta(seconds=1)
    tstart = datetimefromisoformat('1970-01-01T00:00:00')
    return timestamp2index(datetimefromisoformat(ts), dt, tstart)


def index2timestamp(idx, dt, refts, **kwargs):
    """Calculates the ISOstring timestamp for a certain index in an equidistant
    time-series given the reference time (where the index would be 0)
    and the time discretization.
    If any of the input parameters contains timezone information, all others
    also need to contain timezone information.

    Parameters
    ----------
    idx        : str or datetime-object
                The timestamp to determine the index for
                If it is a string, it will be converted to datetime using the
                function _datetimefromisoformat Formatting keywords may be
                passed to this function

    dt        : str or timedelta object
                The discretization of the time series (the amount of time that
                elapsed between indices)
                If used as a string, it needs to be given in the format
                "keyword1=value1,keyword2=value2". Keywords must be understood
                by the timedelta constructor (like days, hours,
                minutes, seconds) and the values may only be integers.

    refts     : str or datetime-object
                The timestamp to determine the index for
                If it is a string, it will be converted to datetime using the
                function _datetimefromisoformat Formatting keywords may be
                passed to this function

    Returns
    -------
    ISO-timestamp    : string
               The ISO-timestamp of a discrete time series array of the given
               parameters in this format: '%Y-%m-%dT%H:%M:%S'

    Examples
    --------
    >>> index2timestamp(25637, 'seconds=10', '2010-09-25T00:00:10')
    '2010-09-27T23:13:00'
    >>> index2timestamp(365, 'days=1', '2010-09-25T00:00:10')
    '2011-09-25T00:00:10'
    """
    if not isinstance(refts, datetime):
        _refts = datetimefromisoformat(refts, **kwargs)
    else:
        _refts = refts
    if not isinstance(dt, timedelta):
        kwargs = dict([(sp[0], int(sp[1]))
                       for sp in [item.split('=') for item in dt.split(',')]])
        _dt = timedelta(**kwargs)
    else:
        _dt = dt

    return str(datetime.isoformat(_refts + idx * _dt))

