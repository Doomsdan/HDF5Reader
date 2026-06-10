"""Meteorological conversions: radiation longwave."""

from ._shared import *


__all__ = ['norm_pressure', 'iziomon', 'temp2lw', 'lw2clouds', 'lw_tennessee', 'blackbody_rad']


def norm_pressure(p, at, h=454.0):
    """ normalize pressure to sealevel

    formula from wikipedia.de for linear temperature gradient 0.0065K/m

    Parameters
    ----------
    p : float or numpy.array of floats
        pressure [hPa]
    at : float or numpy.array of floats
        air temperature [deg C]
    h : float, optional
        height above sea level of measuring station [m]
        default value = 454.0 (height of station Stuttgart-Lauchaecker)

    Returns
    -------
    p_nn : float or numpy.array of floats
        sea level pressure [hPa]

    References
    ----------

    Examples
    --------
    >>> "%.9f" % norm_pressure(930,10.0)
    '982.074383073'

    >>> "%.9f" % norm_pressure(930,10.0,h=765)
    '1019.090035371'

    >>> at = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> p = np.array((925, 930, 935, 932, 931))
    >>> norm_pressure(p,at,h=765)
    array([ 1016.98077228,  1021.60706988,  1026.24032953,  1022.10690872,
            1020.18583111])
    """
    tk = at + 273.16  # T in Kelvin
    p_nn = p * (1 + 0.0065 * h / tk) ** 5.255
    return p_nn


def iziomon(temp, clouds, rh=None, dew=None, e=None, site='low'):
    """ incident long wave radiation following Iziomon et al (2003)[1]_

    As input is required: air temperature (`temp`), cloud cover (`clouds`) and
    EITHER relative humidity (`rh`) OR dewpoint (`dew`) OR vapour pressure
    (`e`).

    Parameters
    ----------
    temp : float or numpy.array of floats
        air temperature [deg C]
    clouds : float or numpy.array of floats
        cloud cover with values between 0 and 1 [-]
    rh : float or numpy.array of floats or None
        relative humidity with values between 0 and 1 [-]
    dew : float or numpy.array of floats or None
        dewpoint [deg C]
    e : float or numpy.array of floats or None
        vapour pressure [hPa]
    site : {'low', 'high'}
        parameterisation for lowland or highland site

    Returns
    -------
    lw : float or numpy.array of floats
        incident longwave radiation [W/m**2]

    See Also
    --------
    lw2clouds : reverse (get cloud cover out of long wave, temperature and
        humidity)

    Notes
    -----
    Empirical formula, found for experiments in Bremgarten (47deg54'35''N;
    7deg37'18''E) in the Upper Rhine plain in Germany (lowland site) and
    Feldberg, 1489 m asl, 47deg52'31''N, 8deg00'11''E, Black Forest, Germany
    (highland site)

    References
    ----------
    .. [1] Iziomon, M.G., Mayer H, Matzarakis A. (2003): Downward atmospheric
       longwave irradiance under clear and cloudy skies: Measurement and
       parameterization, Journal of Atmospheric and Solar-Terrestrial Physics
       65 (2003) 1107 - 1116

    Examples
    --------
    >>> iziomon(15.,0.5,rh=0.89)
    327.52426791875763

    >>> temp = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> clouds = np.array((0.0, 0.1, 0.8, 0.5, 1.0))
    >>> e = np.array((5.5, 5.8, 6.1, 6.2, 6.3))
    >>> iziomon(temp,clouds,e=e)
    array([ 225.34414848,  235.0777488 ,  279.01405432,  267.25348612,
            321.15448959])
    """
    # iziomon-parameter lowland site:
    if site == 'low':
        Xs, Ys, Zs = 0.35, 10.0, 0.0035
##    if site == 'low': Xs, Ys, Zs = 0.35, 1.5, 0.009
    # mountain site:
    elif site == 'high':
        Xs, Ys, Zs = 0.43, 11.5, 0.005
    # temp in Kelvin:
    tk = temp + 273.16
    # humidity in vapour pressure:
    if rh is not None:
        e = rel2vap_p(rh, temp)
    elif dew is not None:
        e = sat_vap_p(dew)
    # clouds in Okta:
    clouds = clouds * 8
    # iziomon:
    lw_clear = blackbody_rad(temp=temp) * (1 - Xs * np.exp(-Ys * e / tk))
    lw = lw_clear * (1 + Zs * clouds ** 2)
    return lw


def temp2lw(temp):
    """Incident long-wave radiation from air temperature (Gal pc).

    Parameters
    ----------
    temp : float or numpy.array of floats
        air temperature [deg C]

    Returns
    -------
    lw : float or numpy.array of floats
        incident longwave radiation [W/m**2]
    """
    from scipy import constants
    theta_kelvin = constants.C2K(temp)
    e = 6.2 * np.exp(17.26 * temp / (theta_kelvin - 35.8))
    boltz = 0.0000000567  # ask gideon
    alpha, beta = .42, .065
    return boltz * theta_kelvin ** 4 * (alpha + beta * np.sqrt(e))


def lw2clouds(lw, temp, rh=None, dew=None, e=None, site='low'):
    """Cloud cover from incident long wave radiation (Iziomon et al (2003)[1]_)

    As input is required: incident long wave radiation (`lw`),
    air temperature (`temp`) and EITHER relative humidity (`rh`)
    OR dewpoint (`dew`) OR vapour pressure (`e`)

    Parameters
    ----------
    lw : float or numpy.array of floats
        incident longwave radiation [W/m**2]
    temp : float or numpy.array of floats
        air temperature [deg C]
    rh : float or numpy.array of floats or None
        relative humidity with values between 0 and 1 [-]
    dew : float or numpy.array of floats or None
        dewpoint [deg C]
    e : float or numpy.array of floats or None
        vapour pressure [hPa]
    site : {'low', 'high'}
        parameterisation for lowland or highland site

    Returns
    -------
    clouds : float or numpy.array of floats
        cloud cover with values between 0 and 1 [-]

    See Also
    --------
    iziomon : incident long wave radiation from air temperature, cloud cover
        and humidity

    Notes
    -----
    Resulting cloud cover is always between 0 and 1. Gives 0 for unrealistic
    low and 1 for unrealistic high values of `lw`.

    References
    ----------
    .. [1] Iziomon, M.G., Mayer H, Matzarakis A. (2003): Downward atmospheric
       longwave irradiance under clear and cloudy skies: Measurement and
       parameterization, Journal of Atmospheric and Solar-Terrestrial Physics
       65 (2003) 1107 - 1116

    Examples
    --------
    >>> lw2clouds(328., 15., rh=0.9)
    0.49959967427213553

    >>> lw = np.array((225.5, 235.1, 279, 267, 321.2))
    >>> temp = np.array((0.0, 2.5, 5.0, 7.5, 10.0))
    >>> e = np.array((5.5, 5.8, 6.1, 6.2, 6.5))
    >>> lw2clouds(lw,temp,e=e)
    array([ 0.0555659 ,  0.1020956 ,  0.79983929,  0.49550839,  0.99289638])
    """
    lw, temp = np.atleast_1d(lw, temp)
    # iziomon-parameter lowland site:
    if site == 'low':
        Xs, Ys, Zs = 0.35, 10.0, 0.0035
    # mountain site:
    elif site == 'high':
        Xs, Ys, Zs = 0.43, 11.5, 0.005
    # temp in Kelvin:
    tk = temp + 273.16
    # humidity in vapour pressure:
    if rh is not None:
        e = np.atleast_1d(rel2vap_p(rh, temp))
    elif dew is not None:
        e = np.atleast_1d(sat_vap_p(dew))
    elif e is not None:
        e = np.atleast_1d(e)
    # iziomon:
    lw_clear = blackbody_rad(temp=temp) * (1 - Xs * np.exp(-Ys * e / tk))
    lw_valid = lw > lw_clear
    n = np.zeros_like(lw)
    n[lw_valid] = ((lw[lw_valid] / lw_clear[lw_valid] - 1) / Zs) ** 0.5
    clouds = n / 8.
    clouds[np.isnan(clouds)] = 0
    clouds[clouds > 1] = 1
    return clouds


def lw_tennessee(temp, clouds):
    """ incident long wave radiation

    Parameters
    ----------
    temp : float or numpy.array of floats
        air temperature [deg C]
    clouds : float or numpy.array of floats
        cloud cover with values between 0 and 1 [-]

    Returns
    -------
    lw : float or numpy.array of floats
        incident longwave radiation [W/m**2]

    See Also
    --------
    iziomon : other empirical formula, from southwestern germany

    References
    ----------
    .. [1] Tennessee Valley Authority 1972. Heat and mass transfer between a
       water surface and the atmosphere Water Resources Research Laboratory
       Report 14, Report No. 0-6803. (I didn't find it. But it's mentioned in:)
    .. [2] ELCOM Science manual
    """
    # temp in Kelvin:
    tk = temp + 273.16
    c_e = 9.37 * 10 ** -6  # K**-2
    eps_a = c_e * tk ** 2
    lw = (1 + 0.17 * clouds ** 2) * eps_a * blackbody_rad(temp=temp)
    return lw


def blackbody_rad(rad=None, temp=None, eps=1.0):
    """ Stefan-Boltzmann law

    There are two ways to use this funtion:

    1) If input is radiation, then the function calculates the absolute
    temperature of the body emitting the radiation

    2) If input is temperature, then the function calculates the radiation
    emitted by the body of this temperature

    Parameters
    ----------
    rad : float or numpy.array of floats or None
        radiation [W/m**2]
    temp : float or numpy.array of floats or None
        temperature [deg C]
    eps : float or numpy.array of floats, optional
        emissivity of a grey body, values between 0 and 1, default=1

    Returns
    -------
    either:
    temp : float or numpy.array of floats or None
        temperature [deg C]
    or:
    rad : float or numpy.array of floats or None
        radiation [W/m**2]

    Examples
    --------
    >>> "%.9f" % blackbody_rad(rad=350)
    '7.138805085'

    >>> "%.9f" % blackbody_rad(temp=0)
    '315.683203500'
    """
    sigma = 5.67 * 10 ** -8
    tk0 = 273.16
    if rad is not None:
        return (rad / (eps * sigma)) ** 0.25 - tk0
    elif temp is not None:
        return eps * sigma * (temp + tk0) ** 4

