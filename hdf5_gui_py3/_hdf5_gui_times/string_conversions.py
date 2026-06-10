"""Time helpers: string conversions."""

from ._shared import *


__all__ = ['iso2datetime', 'datetimefromisoformat', 'iso2unix', 'str2datetime', 'str2ordinal', 'str2unix']


def iso2datetime(iso):
    """Converts an ISO formated time string to a datetime object."""
    try:
        return str2datetime(iso, "%Y-%m-%dT%H:%M:%S.%f")
    except (ValueError, TypeError):
        return str2datetime(iso, "%Y-%m-%dT%H:%M:%S")


def datetimefromisoformat(ts, fmt='%Y-%m-%dT%H:%M:%S'):
    return datetime.strptime(ts, fmt)


def iso2unix(iso):
    """Converts an ISO formated time string to a unix time stamp."""
    try:
        return str2unix(iso, "%Y-%m-%dT%H:%M:%S.%f")
    except (ValueError, TypeError):
        # sometimes the microsecond is missing
        return str2unix(iso, "%Y-%m-%dT%H:%M:%S")


def str2datetime(str_, d_format="%d.%m.%Y %H:%M:%S"):
    """Converts a human readable time string tinto a datetime object.

    >>> str2datetime("01.01.2040 00:00:00")
    datetime.datetime(2040, 1, 1, 0, 0)
    """
    if isinstance(str_, str):
        return datetime.strptime(str_, d_format)

    try:
        if not isinstance(str_[0], str):
            raise TypeError("Sequence is of type %s, not str" %
                            type(str_[0]))
        pd_series = pd.to_datetime(str_, format=d_format)
        return pd_series.to_pydatetime()
    except (ValueError, AttributeError, TypeError):
        return datetime.strptime(str_, d_format)


def str2ordinal(str_, d_format="%d.%m.%Y %H:%M:%S"):
    """Converts a human readable time string to an ordinal.

    >>> str2ordinal("01.01.2040 00:00:00")
    744730
    >>> str2ordinal("01.01.0001 00:00:00")
    1
    """
    return datetime2ordinal(str2datetime(str_, d_format))


def str2unix(str_, d_format="%d.%m.%Y %H:%M:%S"):
    """Converts a time-string of the given d_format (default:
    "dd.mm.yyyy HH:MM:SS") into a unix-timestamp.

    >>> str2unix("01.01.2040 00:00:00")
    2208988800.0
    >>> str2unix("01.01.1970 00:00:00")
    0.0
    """
    return datetime2unix(str2datetime(str_, d_format))

