"""Time helpers: cwr."""

from ._shared import *


__all__ = ['TimeParseError', 'cwr2datetime', 'cwr2str', 'cwr2unix', 'datetime2cwr', 'datetime2cwr_old', 'unix2cwr']


class TimeParseError(ValueError):
    pass


def cwr2datetime(cwr_string):
    """Converts a CWR-timesting into a datetime object.
    >>> cwr2datetime("2040001.00")
    datetime.datetime(2040, 1, 1, 0, 0)
    >>> cwr2datetime('1980001')
    datetime.datetime(1980, 1, 1, 0, 0)
    """
    def cwr2datetime_single(cwr_string_single):
        year = int(cwr_string_single[:4])
        doy = int(cwr_string_single[4:7]) - 1
        try:
            decimal_day = float(cwr_string_single[7:])
        except ValueError:
            decimal_day = 0
        seconds = decimal_day * 24 * 60 ** 2
        return datetime(year, 1, 1) + timedelta(days=doy, seconds=seconds)

    try:
        return cwr2datetime_single(str(cwr_string))
    except ValueError:
        cwr_string = np.array(cwr_string).astype(str)
        return np.array([cwr2datetime_single(cwr) for cwr in cwr_string])


def cwr2str(cwr_string, d_format="%d.%m.%Y %H:%M:%S"):
    """Converts a CWR-timestring into a human-readable timestring.

    >>> cwr2str("2040001.00")
    '01.01.2040 00:00:00'
    """
    dt = cwr2datetime(cwr_string)
    return datetime2str(dt, d_format)


def cwr2unix(cwr_string):
    """Converts a CWR-timestring to a unix timestamp.

    >>> cwr2unix("2040001.00")
    2208988800.0
    """
    def cwr2unix_single(cwr_string_single):
        cwr_string_single = '%013.5f' % float(cwr_string_single)
        yearday = int(float(cwr_string_single[4:]))  # round down to whole days
        # this saves us from calculating the month and day-of-month
        timestamp = str2unix(cwr_string_single[:7], "%Y%j")
        seconds = (float(cwr_string_single[4:]) - yearday) * 86400
        return timestamp + seconds

    try:
        return cwr2unix_single(cwr_string)
    except (ValueError, TypeError):
        return np.array([cwr2unix_single(cwr) for cwr in cwr_string])


def datetime2cwr(dt):
    """Converts a datetime object into a CWR/Julian timestamp.

    >>> import datetime
    >>> datetime2cwr(datetime.datetime(2040, 1, 1, 12, 30, 30, 0))
    2040001.521181
    """
    def datetime2cwr_single(dt):
        timetuple = dt.timetuple()
        year = timetuple.tm_year
        yearday = timetuple.tm_yday
        seconds_as_days = (
            float(timetuple.tm_hour * 3600 +
                  timetuple.tm_min * 60 +
                  timetuple.tm_sec) /
            86400)
        return float(str(year) +
                     ("%03d" % yearday) +
                     "." + str(seconds_as_days)[2:])
    try:
        return np.array([datetime2cwr_single(sub_dt)
                         for sub_dt in dt])
    except TypeError:
        return datetime2cwr_single(dt)


def datetime2cwr_old(dt):
    return unix2cwr(datetime2unix(dt))


def unix2cwr(timestamp):
    """Converts a unix-timestamp to a CWR-timestring.

    >>> unix2cwr(2208988800.0)
    2040001.0
    """
    def unix2cwr_single(timestamp_single):
        src_tuple = time.gmtime(timestamp_single)
        # we are looking for "{year}{yearday}.{seconds expressed in days}
        year = str(src_tuple[0])
        yearday = time.strftime("%j", src_tuple)
        year_yearday_tuple = time.strptime(year + yearday, "%Y%j")
        diff_seconds = timestamp_single - calendar.timegm(year_yearday_tuple)
        seconds_as_days = float(diff_seconds) / 86400
        return "%s%03d%s" % (year, int(yearday),
                             str("%f" % seconds_as_days)[1:])

    try:
        return float(unix2cwr_single(timestamp))
    except TypeError:
        return np.array([float(unix2cwr_single(ts)) for ts in timestamp])

