"""Meteorological conversions: evaporation."""

from ._shared import *


__all__ = ['haude', 'turc', 'turc_rad', 'hargreaves', 'penman_monteith']


def haude(svp, vp, mon):
    """calculates the evapotranspiration following Haude (1955) [1]_
    as described in the Hydrologie-I-Skript

    Parameters
    ----------
    svp : float or numpy.array of floats
        saturation vapour pressure [hPa], measured at 2pm
    vp : float or numpy.array of floats
        vapour pressure [hPa], measured at 2pm
    mon : int or numpy.array of ints
        month: 1=january, 12=december

    Returns
    -------
    etp : float or numpy.array of floats
        evapotranspiration [mm] daily values

    See Also
    --------
    turc : potential evapotranspiration following Turc

    Notes
    -----
    The Haude formula is only valid in temperate humid climate

    References
    ----------
    .. [1] Haude, W. (1955): Zur Bestimmung der Verdunstung auf moeglichst
       einfache Weise. - Mitt. Dt. Wetterd. 2 (11), Bad Kissingen (Dt.
       Wetterd.)

    Examples
    --------
    >>> haude(12.28,8.83,5)
    1.0004999999999999

    >>> haude(12.28,8.83,12)
    0.75900000000000001

    >>> svp = np.array([ 11.87809345,  12.28364703,  12.70132647])
    >>> vp = np.array([ 8.55222728,  8.84422586,  9.14495506])
    >>> haude(svp,vp,12)
    array([ 0.73169056,  0.75667266,  0.78240171])

    >>> mon = np.array([2,3,4])
    >>> haude(svp,vp,mon)
    array([ 0.73169056,  0.75667266,  1.03134771])
    """
    mon = mon - 1
    hfs = (0.0022, 0.0022, 0.0022, 0.0029, 0.0029, 0.0028, 0.0026, 0.0029,
           0.0023, 0.0022, 0.0022, 0.0022)  # monthly Haude factor
    try:
        hf = hfs[mon]
    except TypeError:
        hf = np.array([hfs[mo] for mo in mon])
    svp, vp = np.array(svp) * 100, np.array(vp) * 100  # hPa -> Pa
    etp = hf * (svp - vp)
    return etp


def turc(at, ts, mon):
    """calculates the potential evapotranspiration following Turc [1]_ as
    described in the Hydrologie-I-Skript (p. 55)

    Parameters
    ----------
    at : float or numpy.array of floats
        daily average air temperature [degC]
    ts : float or numpy.array of floats
        number of sunshine hours per day
    mon : int or numpy.array of ints
        month: 1=january, 12=december

    Returns
    -------
    etp : float or numpy.array of floats
        potential evapotranspiration [mm] daily values

    See Also
    --------
    haude : evapotranspiration following Haude

    Notes
    -----
    The Turc formula is only valid for `at` > 0 deg C

    References
    ----------
    .. [1] TURC??

    Examples
    --------
    >>> "%.9f" % turc(10,0,5)
    '1.104000000'

    >>> "%.9f" % turc(10,0,12)
    '0.408000000'
    """
    mon = mon - 1
    # Konstanten C1, C2 fuer etwa 53 deg N in Mitteleuropa
    # warum auch immer
    cs = ((1.09, 0.18), (1.4, 0.259), (1.86, 0.35), (2.36, 0.429),
          (2.76, 0.476), (3, 0.489), (2.93, 0.484), (2.58, 0.448),
          (2.1, 0.39), (1.57, 0.21), (1.19, 0.21), (1.02, 0.158))
    try:
        c1, c2 = cs[mon]
    except TypeError:
        c1 = np.array([cs[mo][0] for mo in mon])
        c2 = np.array([cs[mo][1] for mo in mon])
    etp = (c1 + c2 * ts) * at / (at + 15)
    return etp


def turc_rad(at, rh, G):
    """calculates the potential evapotranspiration following Turc

    with the global radiation instead of the empiric factors according to
    Hydrologie und Wasserwirtschaft by Maniak

    Parameters
    ----------
    at : numpy.array of floats
        mean daily air temperature [deg C]
    rh : numpy.array of floats
        relative humidity [%]
    G  : numpy.array of floats
        global radiation [W/m^2]

    Returns
    -------
    etp : numpy.array of floats
        potential evapotranspiration [mm/d]

    Notes
    -----
    - For etp < 0.1 mm/d the evapotranspiration rate is set to 0.1 mm/d.
      [DVWK 1996]
    - According to the energetic limit of 7 mm/d in Germany, ETPmax is set to
      7 mm/d.
    """

    rh = np.array(rh, float)
    C = np.ones_like(rh)
    ii = np.where(rh < 50.)
    C[ii] = 1. + ((50. - rh[ii]) / 70.)

    G = G * 86400. / 10000.  # W/m^2 in J/(cm^2*d)

    etp = 0.0031 * C * (G + 209.) * (at / (at + 15.))
    ii = np.where(etp > 7.)
    etp[ii] = 7.
    jj = np.where(etp < 0.1)
    etp[jj] = 0.1

    return etp


def hargreaves(tmax, tmin, date, in_format='%Y-%m-%dT%H:%M:%S'):
    """calculates the potential evapotranspiration rate [mm/d] following
    Hargreaves & Samani 1985 according to THE ASCE STANDARDIZED REFERENCE
    EVAPOTRANSPIRATION EQUATION

    Parameters
    ----------
    tmax : np.array of floats
        maximum of the daily air temperature [deg C]
    tmin : np.array of floats
        minimum of the daily air temperature [deg C]
    date : np.array of strings
        date strings in format in_format
    in_format : format string
        default: '%Y-%m-%dT%H:%M:%S'

    Returns
    -------
    etp : numpy.array of floats
        potential evapotranspiration [mm/d]

    Notes
    -----
    - equation needs the extraterrestrial radiation Ra, which depends on:

      - inverse relative distance factor for the earth-sun dr []
      - solar declination delta [rad]
      - sunset hour angle [rad]
        with latitude Lauchaecker lat=48.738 deg => pi/180 * 48.738
        deg = 0.8506 rad

    - conversion of date in day of year (j)
    - ETPmax = 7.0 mm/d due to energetic limit (Germany)

    References
    ----------
    """

    j = []
    for dat in date:
        t = datetime.strptime(dat, in_format)
        doy = float(datetime.strftime(t, format='%j'))  # day of year
        j.append(doy)

    # inverse relative distance factor for the earth-sun []
    dr = 1. + 0.033 * np.cos(np.multiply((2 * np.pi / 365.), j))
    # solar declination [rad]
    delta = 0.409 * np.sin(np.multiply((2 * np.pi / 365.), j) - 1.39)
    # sunset hour angle [rad]
    omega_s = np.arccos(-np.tan(0.8506) * np.tan(delta))
    # extraterrestrial radiation [MJ m^-2 d^-1]
    Ra = (24. / np.pi * 4.92 * dr * (omega_s * np.sin(0.8506)
        * np.sin(delta) + np.cos(0.8506) * np.cos(delta) * np.sin(omega_s)))
    # [MJ m^-2 d^-1]
    etp = (0.0023 * (tmax - tmin) ** (0.5) * ((tmax + tmin) / 2. + 17.8)
           * Ra / 2.45)  # 2.45: factor for calculating mm/d

    ii = np.where(etp > 7.)
    etp[ii] = 7.

    return etp


def penman_monteith(at, u, Rn, rh):
    """Calculates the reference crop evaporation following the Penman-Monteith
    method and the FAO-56 determinations published in ASCE
    Standardized Reference Evapotranspiration Equation

    Parameters
    ----------
    at : np.array of floats
        mean daily air temperature at 2m-height [deg C]
    u  : np.array of floats
        mean daily wind speed at 2m-height [m/s]
    Rn : np.array of floats
        measured net radiation at the crop surface [MJ m^-2 d^-1]
    rh : np.array of floats
        relative humidity [%]

    Returns
    -------
    eto : np.array of floats
        FAO Penman-Monteith standardized reference crop evapotranspiration for
          short (~=0.12m) surfaces [mm d^-1]

    Notes
    -----
    - Units for the 0.408 coefficient are m^2 mm MJ^-1
    - The FAO-56 Penman-Monteith equation is a grass reference equation that
      was derived from the Penman-Monteith form of the combination equation
      (Monteith 1965, 1981) by fixing h = 0.12 m for clipped grass and by
      assuming measurement heights of z = 2 m (at, rh, u) and using a latent
      heat of vaporization of 2.45 MJ kg-1.
      The result is an equation that defines the reference evapotranspiration
      from a hypothetical grass surface having a fixed height of 0.12 m, bulk
      surface resistance of 70 s m-1, and albedo of 0.23.
    - in relationship to the net radiation, the soil heat flux is very small
      and is fixed with G = 0.1*Rn
    """
    rh = rh / 100.  # relative humidity in decimal[0,1]
    y = 0.000665 * 101.3 * ((293. - 0.0065 * 453.) / 293.) ** 5.26

    G = 0.1 * Rn
    S = slope_sat_p(at)
    Cn = 900
    Cd = 0.34
    es = sat_vap_p(at)
    ea = rel2vap_p(rh, at)

    eto = (0.408 * S * (Rn - G) + y * (Cn / (at + 273.15)) * u *
           ((es - ea) / 10.)) / (S + y * (1 + Cd * u))

    ii = np.where(eto > 7.)
    eto[ii] = 7.

    return eto

