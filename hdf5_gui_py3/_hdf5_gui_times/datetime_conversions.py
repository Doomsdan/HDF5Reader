"""Time helpers: datetime conversions."""

from ._shared import *


__all__ = ['dy2datetime', 'datetime2ordinal', 'datetime2str', 'datetime2unix', 'datetime2doy', 'datetime2hour', 'doy2datetime', 'ordinal2datetime', 'unix2datetime', 'unix2ordinal', 'unix2str', 'xls2datetime']


def dy2datetime(dy):
    """Converts a DYRESM float time (a.k.a. julian date) into a datetime
    object.

    >>> dy2datetime(2451544.5)
    datetime.datetime(2000, 1, 1, 0, 0)
    >>> dy2datetime(2456462.4375)
    datetime.datetime(2013, 6, 18, 22, 30)
    """
    return ordinal2datetime(dy - 1721424.5)


def datetime2ordinal(dt):
    """Converts a datetime object into an ordinal.

    >>> import datetime
    >>> dt = datetime.datetime(2040, 1, 1, 0, 0, 0, 500000)
    >>> datetime2ordinal(dt)
    744730
    >>> datetime2ordinal(datetime.datetime(1, 1, 1, 0, 0))
    1
    """
    try:
        return np.array([sub_dt.toordinal() for sub_dt in dt])
    except TypeError:
        return dt.toordinal()


def datetime2str(dt, d_format="%d.%m.%Y %H:%M:%S"):
    """Converts a datetime object into a human-readable string.

    >>> import datetime
    >>> datetime2str(datetime.datetime(2040, 1, 1, 0, 0, 0, 500000))
    '01.01.2040 00:00:00'
    """
    try:
        return np.array([sub_datetime.strftime(d_format)
                         for sub_datetime in dt])
    except TypeError:
        return dt.strftime(d_format)


def datetime2unix(dt):
    """Converts a dateime object into a unix-timestamp.

    >>> import datetime
    >>> dt = datetime.datetime(2040, 1, 1, 0, 0, 0, 500000)
    >>> datetime2unix(dt)
    2208988800.5
    >>> datetime2unix(datetime.datetime(1970, 1, 1, 0, 0))
    0.0
    """
    try:
        tzinfo = dt.tzinfo if hasattr(dt, "tzinfo") else dt[0].tzinfo
    except IndexError:
        tzinfo = None
    diff = dt - datetime(1970, 1, 1, 0, 0, tzinfo=tzinfo)
    try:
        return np.array([sub_diff.days * 86400 + sub_diff.seconds +
                         sub_diff.microseconds / 1e6
                         for sub_diff in diff])
    except TypeError:
        return diff.days * 86400 + diff.seconds + diff.microseconds / 1e6


def datetime2doy(dt):
    """ Extracts the day of year as a float from the given datetimes.

    >>> import datetime
    >>> dt = datetime.datetime(2040, 1, 1, 12, 30, 30, 500000)
    >>> datetime2doy(dt)
    1.5211863425925927
    """
    def datetime2doy_single(dt):
        return (dt.timetuple().tm_yday +
                dt.hour / 24. +
                dt.minute / (24. * 60) +
                dt.second / (24. * 60 ** 2) +
                dt.microsecond / (24. * 60 ** 2 * 1e6))
    try:
        return np.array([datetime2doy_single(sub_dt) for sub_dt in dt])
    except TypeError:
        return datetime2doy_single(dt)


def datetime2hour(dt):
    """ Extracts the hour of a day as a float from the given datetimes.

    >>> import datetime
    >>> dt = datetime.datetime(2040, 1, 1, 12, 30)
    >>> datetime2hour(dt)
    12.5
    """
    def datetime2hour_single(dt):
        return (dt.hour +
                dt.minute / 60. +
                dt.second / (60. ** 2) +
                dt.microsecond / (60. ** 2 * 1e6))
    try:
        return np.array([datetime2hour_single(sub_dt) for sub_dt in dt])
    except TypeError:
        return datetime2hour_single(dt)


def doy2datetime(doy, year=2000):
    """Constructs a datetime object from given day of year.

    Parameters
    ----------
    year : int, optional
        The year of the day of the year.

    Examples
    --------
    >>> import datetime, numpy
    >>> doy2datetime(1.5211863425925927, 2040)
    datetime.datetime(2040, 1, 1, 12, 30, 30, 500000)
    >>> doy2datetime(numpy.arange(1,3))
    array([datetime.datetime(2000, 1, 1, 0, 0),
           datetime.datetime(2000, 1, 2, 0, 0)], dtype=object)
    """
    def doy2datetime_single(doy, year):
        return (datetime(int(year), month=1, day=1) +
                timedelta(days=float(doy) - 1))
    # TODO: interpret 365, 0 as a new year
    try:
        if type(year) is int:
            years = itertools.cycle([year])
        else:
            years = year
        return np.array([doy2datetime_single(sub_doy, sub_year)
                         for sub_doy, sub_year in zip(doy, years)])
    except TypeError:
        return doy2datetime_single(doy, year)


def ordinal2datetime(ord_):
    """Converts an ordinal to a datetime object.

    >>> ordinal2datetime(744730)
    datetime.datetime(2040, 1, 1, 0, 0)
    """
    try:
        return np.array([(datetime.fromordinal(int(sub_ord)) +
                          timedelta(sub_ord - int(sub_ord)))
                         for sub_ord in ord_])
    except TypeError:
        return datetime.fromordinal(int(ord_)) + timedelta(ord_ - int(ord_))


def unix2datetime(timestamp):
    """Convert a unix time stamp to a datetime object.

    >>> import datetime
    >>> unix2datetime(2208988800.5)
    datetime.datetime(2040, 1, 1, 0, 0, 0, 500000)
    >>> unix2datetime(0)
    datetime.datetime(1970, 1, 1, 0, 0)
    """
    try:
        return np.array([datetime(1970, 1, 1) + timedelta(seconds=float(stamp))
                         for stamp in timestamp])
    except TypeError:
        return datetime(1970, 1, 1) + timedelta(seconds=float(timestamp))


def unix2ordinal(timestamp):
    """Converts a unix time stamp to an ordinal.

    >>> unix2ordinal(2208988800.0)
    744730
    """
    try:
        np.array([datetime2ordinal(unix2datetime(stamp))
                  for stamp in timestamp])
    except TypeError:
        return datetime2ordinal(unix2datetime(timestamp))


def unix2str(timestamp, d_format="%d.%m.%Y %H:%M:%S"):
    """Converts a unix-timestamp into a time-string of the given d_format
    (default: "dd.mm.yyyy HH:MM:SS").

    >>> unix2str(2208988800.5)
    '01.01.2040 00:00:00'
    >>> unix2str(0)
    '01.01.1970 00:00:00'
    """
    return datetime2str(unix2datetime(timestamp), d_format)


def xls2datetime(xldate, datemode=0):
    """ Here's the bare-knuckle no-seat-belts use-at-own-risk version
    posted by John Machin in http://stackoverflow.com
    datemode: 0 for 1900-based, 1 for 1904-based
    """
    def xls2datetime_single(xldate, datemode):
        return (
            # 30.Dez, weil 1900 in Excel ein Schaltjahr ist --> ab dem 1. Maerz
            # stimmts
            datetime(1899, 12, 30)
            + timedelta(days=xldate + 1462 * datemode))
    try:
        return xls2datetime_single(xldate, datemode)
    except (ValueError, TypeError):
        return np.array([xls2datetime_single(xl, datemode) for xl in xldate])

