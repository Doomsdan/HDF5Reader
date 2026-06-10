"""Meteorological conversions: humidity."""

from ._shared import *


__all__ = ['sat_vap_p', 'rel2vap_p', 'vap_p2rel', 'dewpoint', 'dew2rel', 'spec_hum', 'psychro2e', 'slope_sat_p']


def sat_vap_p(at):
    """ saturation vapour pressure from air temperature

    Parameters
    ----------
    at : float or numpy.array of floats
        air temperature [deg C]

    Returns
    -------
    c_e : float or numpy.array of floats
        saturation vapour pressure [hPa]

    References
    ----------
    Hydrologie-Skript I, p. 17

    Examples
    --------
    >>> sat_vap_p(25.0)
    31.688149728170984

    >>> at = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> sat_vap_p(at[:3])
    array([ 6.11      ,  7.31533365,  8.72596589])
    >>> sat_vap_p(at[3:])
    array([ 10.3711941 ,  12.28364703])
    """
    at = np.array(at)
    e0 = 6.11
    a = 17.27
    b = 237.3
    c_e = e0 * np.exp(a * at / (b + at))
    return c_e


def rel2vap_p(rh, at):
    """ vapour pressure from relative humidity and air temperature

    Parameters
    ----------
    rh : float or numpy.array of floats
        relative humidity with values between 0 and 1 [-]
    at : float or numpy.array of floats
        air temperature [deg C]

    Returns
    -------
    e : float or numpy.array of floats
        vapour pressure [hPa]

    Examples
    --------
    >>> rel2vap_p(0.5,20.0)
    11.695234581996313

    >>> rh = np.array((0.9, 0.8, 0.7, 0.6, 0.5))
    >>> at = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> rel2vap_p(rh,at)
    array([ 5.499     ,  5.85226692,  6.10817613,  6.22271646,  6.14182351])

    """
    rh, at = np.array(rh), np.array(at)
    c_e = sat_vap_p(at)
    e = rh * c_e
    return e


def vap_p2rel(e, at):
    """ relative humidity from vapour pressure and air temperature

    Parameters
    ----------
    e : float or numpy.array of floats
        vapour pressure [hPa]
    at : float or numpy.array of floats
        air temperature [deg C]

    Returns
    -------
    rh : float or numpy.array of floats
        relative humidity with values between 0 and 1 [-]

    Examples
    --------
    >>> vap_p2rel(6.22,20.0)
    0.26592027532201407

    >>> e = np.array((5.5, 5.8, 6.1, 6.2, 6.3))
    >>> at = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> vap_p2rel(e,at)
    array([ 0.90016367,  0.79285516,  0.69906301,  0.59780966,  0.512877  ])
    """
    e, at = np.array(e), np.array(at)
    c_e = sat_vap_p(at)
    rh = e / c_e
    return rh


def dewpoint(at, rh=None, e=None):
    """  dewpoint from air temperature and humidity

    As input is required: air temperature (`at`) and EITHER relative humidity
    (`rh`) OR vapour pressure (`e`).

    Parameters
    ----------
    at : float or numpy.array of floats
        air temperature [deg C]
    rh : float or numpy.array of floats or None
        relative humidity with values between 0 and 1 [-]
    e : float or numpy.array of floats or None
        vapour pressure [hPa]

    Returns
    -------
    dew : float or numpy.array of floats
        dewpoint [deg C]

    Raises
    ------
    Warning
        If relative humidity is > 1.1 (e. g. if vapour pressure is taken as
        relative humidity)

    Examples
    --------
    >>> dewpoint(20.,rh=0.5)
    9.2696286371249084

    >>> dewpoint(20.,e=10.0)
    6.9681968406881376

    >>> at = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> rh = np.array((0.9, 0.8, 0.7, 0.6, 0.5))
    >>> dewpoint(at, rh=rh)
    array([-1.43893707, -0.59071344, -0.0041022 ,  0.25144096,  0.07140267])

    >>> at = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> e = np.array((5.5, 5.8, 6.1, 6.2, 6.3))
    >>> dewpoint(at, e=e)
    array([-1.43646874, -0.71330622, -0.02250498,  0.20109231,  0.42152362])
    """
    at = np.array(at)
    e0 = 6.11
    a = 17.27
    b = 237.3
    if rh is not None:
        e = rel2vap_p(rh, at)
        summ = np.sum(rh > 1.1)
        if summ > 0:
            warnings.warn(" %i relative humidity values are > 1.1" % summ)
    dew = b * (np.log(e) - np.log(e0)) / (a - (np.log(e) - np.log(e0)))
    return dew


def dew2rel(dew, at):
    """ relative humidity from dewpoint and air temperature

    Parameters
    ----------
    at : float or numpy.array of floats
        air temperature [deg C]
    dew : float or numpy.array of floats
        dewpoint [deg C]

    Returns
    -------
    rh : float or numpy.array of floats
        relative humidity with values between 0 and 1 [-]

    Examples
    --------
    >>> dew2rel(15.,16.0)
    0.9378863357566809

    >>> at = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> dew = np.array((0.0, 3., 5.0, 7.7, 10.0))
    >>> dew2rel(at,dew)
    array([ 1.        ,  0.96506519,  1.        ,  0.98642692,  1.        ])
    """
    dew, at = np.array(dew), np.array(at)
    e = sat_vap_p(dew)
    c_e = sat_vap_p(at)
    rh = e / c_e
    return rh


def spec_hum(e, p):
    """Calculates the specific humidity

    Parameters
    ----------
    pressure : float
        air pressure in hPa
    e : float
        vapour pressure in hPa


    Returns
    -------
    spec_hum : float

    Notes
    -----
    The formula is:
    s = ((0.623*e)/(p-0.377*e))*1000
    where M_w/M_tL=0.622
    and 0.378 = 1-0.622"""

    spec_hum = (0.622 * e * 1000) / (p - 0.378 * e)

    return spec_hum


def psychro2e(t_dry, t_wet, p=None):
    """Vapour pressure from dry and wet temperature from Assmann psychrometer
    using Sprung's [1]_ formula (as seen on wikipedia)

    Parameters
    ----------
    t_dry : float or np.array of floats
        dry temperature [deg C]
    t_wet : float or np.array of floats
        wet temperature [deg C]
    p : float or np.array of floats or None, optional
        air pressure [hPa], if None: use the simplified version of the formula,
        default is None

    Returns
    -------
    e : float or np.array of floats
        vapour pressure [hPa]

    Notes
    -----
    If p is None, a simplification is used which can be used below 500m above
    sea level

    References
    ----------
    .. [1] Sprung, A.: Ueber die Bestimmung der Luftfeuchtigkeit mit Hilfe des
        Assmannschen Aspirationspsychrometers, Z. Angew. Meteorol., Das Wetter,
        5 (1888), S. 105?108

    Examples
    --------
    >>> psychro2e(np.array([17.5,18.9]),np.array([12.3,12.1]))
    array([ 10.82619823,   9.56701424])

    >>> p = np.array([800,800])
    >>> psychro2e(np.array([17.5,18.9]),np.array([12.3,12.1]),p=p)
    array([ 11.57630294,  10.54309631])
    """
    p = np.array(p)
    if p.any():
        cp = 1005.4  # specific heat capacity of air J/(kg*K)
        mu = 0.622  # molar mass ratio water/air
        # latent heat of vaporization of water [J/kg]
        lam = (-0.0000614342 * t_dry ** 3 + 0.00158927 * t_dry ** 2 -
               2.36418 * t_dry + 2500.79) * 1000
        gamma = p * cp / (mu * lam)  # hPa/K
    else:
        gamma = 0.67  # hPa/K, simplification, can be used below 500m asl
    return sat_vap_p(t_wet) - gamma * (t_dry - t_wet)


def slope_sat_p(at):
    """slope of the saturation vapor pressure function,
    depends only on air temperature

    Parameters
    ----------
    at : float or numpy.array of floats
        (mean daily) air temperature [deg C]

    Returns
    -------
    slope : float or numpy.array of floats
        slope of the saturation vapor pressure function  [kPa/deg C]

    Notes
    -----
    A polynomial is used to evaluate the slope and is only valid
    for -5 < 'at' > 45 [deg C].

    References
    ----------
    .. [1] Campbell Scientific (1995) application note 4-D: On-Line
        Estimation of Grass Reference Evapotranspiration with the Campbell
        Scientific Automated Weather Station
    """

    slope = (45.3 + 2.97 * at + 0.0549 * at ** 2 + 0.00223 * at ** 3) / 1000

    return slope

