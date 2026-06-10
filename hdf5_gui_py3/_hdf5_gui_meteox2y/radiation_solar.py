"""Meteorological conversions: radiation solar."""

from ._shared import *


__all__ = ['pot_s_rad', 'pot_s_rad_daily', 'sunshine', 'sonnenscheindauer', 'altitude']


def pot_s_rad(date, lat=48.738, longt=9.099, in_format='%Y-%m-%dT%H:%M',
              tz_mer=15.0, wog=-1):
    """ theoretical maximal potential solar radiation outside of atmosphere

    Parameters
    ----------
    date : numpy.array of time strings (format: in_format) or datetime objects
        or floats (doys)
    lat : float, optional
        latitude of station in decimal degrees, default: Stuttgart Lauchaecker
    longt : float, optional
        longitude of station in decimal degrees, default: Stuttgart Lauchaecker
    in_format : time format string, optional
        format of date if date is string, default '%Y-%m-%dT%H:%M'
    tz_mer : int, optional
        central meridian of time zone, default: 15 (CET)
    wog : {-1, 1}, optional
        west of greenwich, 1 if west, -1 if east, default = -1

    Returns
    -------
    smax : numpy.array of floats
        maximal potential solar radiation in W/m^2

    Notes
    -----
    from campbell technical note 18 [1]_, except declination of sun (d):
    formula of Spencer (1971) [2]_

    WARNING: Campbell Scientific recommends the use of a high quality sun
    screen lotion when exposing your skin to solar radiation for large values
    of sunshine hours!

    References
    ----------
    .. [1] Campbell Scientific (2005) technical note 18: CALCULATING SUNSHINE
       HOURS FROM PYRANOMETER / SOLARIMETER DATA
    .. [2] Spencer JW (1971) Fourier series representation of the position of
       the Sun. Search 2: 172.

    Examples
    --------
    >>> date_str = np.array(["2011-09-28T11:27"])
    >>> pot_s_rad(date_str)
    array([ 855.35624182])
    >>> from lhglib.contrib import times
    >>> dt = times.str2datetime(date_str, "%Y-%m-%dT%H:%M")
    >>> pot_s_rad(dt)
    array([ 855.35624182])
    >>> pot_s_rad(times.datetime2doy(dt))
    array([ 855.35624182])
    """
    s0 = 1373  # Solarkonstante W/m^2
    # once upon a time there was a latitude
    Lc = wog * (tz_mer - longt) / 15.0  # Local correction of time
    lat = lat * np.pi / 180  # in rad
    try:
        # where we used to raise an exception
        doys = date.timetuple().tm_yday #times.datetime2doy(date)  # if date is datetime
    except (TypeError, AttributeError, ValueError, NotImplementedError,
            IndexError):
        try:
            # ...or two
            # if date is string
            doys=datetime.strptime(date, in_format).timetuple().tm_yday
            #doys = times.datetime2doy(times.str2datetime(date, in_format))
        except (TypeError, IndexError):
            # those were the doys my friend, i thought they never end
            doys = date  # if date is already in doys
    hours = (doys - int(doys)) * 24
    # remember how we typecasted away the hours
    doys =int(doys)
    j1 = doys / 100.
    j2 = (doys - 180) / 100.
    Et = np.where(doys > 180,
                  (-0.05039 - 0.33954 * j2 + 0.04084 * j2 ** 2 +
                   1.8928 * j2 ** 3 - 1.7619 * j2 ** 4 + 0.4224 * j2 ** 5),
                  (-0.04056 - 0.74503 * j1 + 0.08823 * j1 ** 2 +
                   2.0516 * j1 ** 3 - 1.8111 * j1 ** 4 + 0.42832 * j1 ** 5))
    t0 = 12 - Lc - Et
    # we sang and dance forever and a doy (less)
    # la la la la lala lala lala lala
    la = 2 * np.pi / 365 * (doys - 1)
    d = (0.006918 - 0.399912 * np.cos(la) + 0.070257 * np.sin(la) -
         0.006758 * np.cos(2 * la) + 0.000907 * np.sin(2 * la) -
         0.002697 * np.cos(3 * la) + 0.00148 * np.sin(3 * la))
    sind = np.sin(d)
    sinphi = np.atleast_1d(sind * np.sin(lat) +
                           np.cos(d) * np.cos(lat) *
                           np.cos(15 * np.pi / 180.0 * (hours - t0)))
    sinphi[sinphi < 0] = 0
    smax = s0 * sinphi
    return smax


def pot_s_rad_daily(date, lat=48.738, longt=9.099, in_format='%Y-%m-%d',
                    tz_mer=15.0, wog=-1):
    """ daily average values of --> pot_s_rad
    """
    # machen wir mal stundenweise:
    if type(date[0]) != datetime:
        date = times.str2datetime(date, in_format)
    date_h = np.array([dt__ + timedelta(hours=i) for dt__ in date
                       for i in range(24)])
    pot_h = pot_s_rad(date_h, lat, longt, tz_mer=tz_mer, wog=wog)
    return np.average(pot_h.reshape(-1, 24), axis=1)


def sunshine(sw, date, lat=48.738, longt=9.099, in_format='%Y-%m-%dT%H:%M',
             tz_mer=15.0, wog=-1):
    """sunshine or not?

    calculates maximum potential solar radiation depending on latitude,
    longitude, and time and compares it to actual solar radiation. Sunshine if
    actual solar radiation > 0.4*maximum potential solar radiation
    accurate enough for normal non-scientific use of sunshine hour data

    Parameters
    ----------
    sw : numpy.array of floats
        solar (short wave) radiation in W/m^2
    date : numpy.array of time strings
        date and time in format in_format
    lat : float, optional
        latitude of station in decimal degrees, default: Stuttgart Lauchaecker
    longt : float, optional
        longitude of station in decimal degrees, default: Stuttgart Lauchaecker
    in_format : time format string, optional
        format of date, default '%Y-%m-%dT%H:%M'
    tz_mer : int, optional
        central meridian of time zone, default: 15 (CET)
    wog : {-1, 1}, optional
        west of greenwich, 1 if west, -1 if east, default = -1

    Returns
    -------
    shining : numpy.array containing 0 and 1
        1: sun is shining in corresponding time step, 0: sun is not shining in
        corresponding time step

    Examples
    --------
    >>> sunshine(np.array([450]),np.array(["2011-09-28T11:27"]))
    array([1])
    >>> sunshine(np.array([200]),np.array(["2011-09-28T11:27"]))
    array([0])
    """
    shining = np.zeros_like(sw)
    smax = pot_s_rad(date, lat, longt, in_format=in_format, tz_mer=tz_mer,
                     wog=wog)
    # There are warnings occuring due to nan values
    # Set them to a very small number first, do the operation. As the value 
    # is very small, there will be no sunshine. Finally set them back to nan

    mask = np.isnan(sw)
    sw[mask] = -999999
    shining[np.where(sw > 0.4 * smax)] = 1
    # keep the nan values
    shining[mask] = np.nan
    return shining


def sonnenscheindauer(date, sw, del_t=60):
    r"""
    bestimmt Sonnenscheindauer anhand der kurzwelligen Solarstrahlung

    Parameters
    ----------
    date  : string
        datetime.datetime(2040, 1, 1, 0, 0, 0)
    sw : numpy.array of floats
        solar (short wave) radiation in W/m^2
    del_t : int, optional
        timestep in minutes: 1-min-data is averaged to this timestep.
        Default is 60

    Returns
    -------
    sunshine_hour
    """

    sunshine_min = sunshine(sw, date)
 #   sunshine_sum = np.sum(sunshine_min)
    sunshine_hour = sunshine_min/float(del_t)

    return sunshine_hour


def altitude(temp1, temp0, pres1, pres0, alt0):
    r"""Converts continous meassured vertical pressure and temperature data to
    altitude.
    # 1 means i and 0 means i-1

    Parameters
    ----------
    temp1 : float or array_like
        Temperature value at timestep i.
    temp0 : float or array_like
        Temperature value at timestep i-1.
    pres1 : float or array_like
        Pressure value at timestep i.
    pres0 : float or array_like
        Pressure value at timestep i-1.
    alt0 : float or array_like
        Altitude value at timestep i-1.

    Returns
    -------
    altitude : float or array_like
        Altitude at timestep i

    Notes
    -----
    This is the implemented equation:

    g : Gravity acceleration 9.81 m/s^2
    T_0 : Temperature 273.16 K

    .. math::

        altitude = ((\frac{\ln(pres0)}{pres1})*287*((\frac{(\frac{(temp1+temp0)}{2})+T_0)}/{g}))+alt0

    References
    ----------
    *** -> Ask Felix!!! ***

    Examples
    --------
    >>> alt = np.nan*np.ones(40)
    >>> alt[0] = 600
    >>> for i,element in enumerate(alt):    # doctest: +SKIP
    ...    if str(element) == 'nan':    # doctest: +SKIP
    ...        element = altitude(temp[i], temp[i-1], pres[i], pres[i-1], alt[i-1])    # doctest: +SKIP
    """
    tk0 = 273.16
    g = 9.81

    altitude = ((np.log(pres0 / pres1)) * 287 *
                ((((temp0 + temp1) / 2) + tk0) / g)) + alt0
    # ;print 'altitude: ',self.altitude

    return altitude

