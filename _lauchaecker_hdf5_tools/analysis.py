"""Lauchaecker HDF5 tools: analysis."""

from ._shared import *


__all__ = ['kenntage', 'evapo_from_hdf5', 'compare_year']


def kenntage(start, end, del_t=60,
             hdf5=lconf.hdf5_filename,
             meta_xls_filename=lconf.meta_xls_filename,
             typ_='_data_raw'):
    r"""
    bestimmt klimatologische Kenntage anhand von Temperaturmessdaten im
    angegebenen Zeitraum. Ausgabe auf den Bildschirm.

    Parameters
    ----------
    start : string
       start date in format "%Y-%m-%dT%H:%M:%S"
    end : string
       end date in format "%Y-%m-%dT%H:%M:%S"
    del_t : int, optional
        timestep in minutes: 1-min-data is averaged to this timestep.
        Default is 60
    hdf5 : string, optional
        path and filename of data text file. Default is
        r'P:\wetterstation\data\CR3000_data_1min.dat'

    Returns
    -------
    data: dict of integers
        contains number of different kenntage as dictionary
    """
    var, date = read_hdf5(start, end, ('Ta_2m', 'rr_07', 'rh_2m'),
                          del_t=del_t, hdf5=hdf5,
                          meta_xls_filename=meta_xls_filename, typ_=typ_)
    var['dp'] = mxy.dewpoint(var['Ta_2m'], rh=var['rh_2m'] / 100.0)
    temp = var['Ta_2m'].reshape(-1, 1440 / del_t)
    prec = var['rr_07'].reshape(-1, 1440 / del_t)
    dew = var['dp'].reshape(-1, 1440 / del_t)

    tage = date.reshape(-1, 1440 / del_t)[:, 12]

    # print '\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nKenntage:\n*********'
    # heisser Tag:
    i_heiss = np.where(np.max(temp, axis=1) >= 30.0)
    heisser_tag = tage[i_heiss]

    # Tropentag:
    i_trop = np.where(np.average(temp, axis=1) >= 25.0)
    tropentag = tage[i_trop]

    # Tropennacht: noch nicht perfekt: man weiss nicht, ob fruehs oder abends
    i_tropn = np.where(np.min(temp, axis=1) >= 20.0)
    tropennacht = tage[i_tropn]

    # Sommertag:
    i_sommer = np.where(np.max(temp, axis=1) >= 25.0)
    sommertag = tage[i_sommer]

    # Biergartentag:
    cl_21 = (1440.0 / del_t) * 0.875 - 1
    # 21 Uhr, sollte wohl nicht der Stundenmittelwert sein?
    i_bier = np.where(temp[:, int(cl_21)] >= 20.0)
    biertag = tage[i_bier]

    # Heiztag:
    i_heiz = np.where(np.average(temp, axis=1) < 12.0)
    heiztag = tage[i_heiz]

    # Frosttag:
    i_frost = np.where(np.min(temp, axis=1) <= 0.0)
    frosttag = tage[i_frost]

    # strenger Frosttag:
    i_frost_s = np.where(np.min(temp, axis=1) <= -10.0)
    frosttag_s = tage[i_frost_s]

    # Eistag:
    i_eis = np.where(np.max(temp, axis=1) <= 0.0)
    eistag = tage[i_eis]

    # Regentag
    i_regen = np.where((np.sum(prec, axis=1) >= 0.1))
    regentag = tage[i_regen]

    # schwueler Tag, wenn in einer Stunde der Taupunkt > 17 Grad
    i_schwuel = np.sum((dew >= 17), axis=1) > 0
    schwuelertag = tage[i_schwuel]

    data = {
        'HeisseTage': heisser_tag,
        'Tropentage': tropentag,
        'Tropennaechte': tropennacht,
        'Sommertage': sommertag,
        'Biergartentage': biertag,
        'Heiztage': heiztag,
        'Frosttage': frosttag,
        'StrengeFrosttage': frosttag_s,
        'Eistage': eistag,
        'Regentage': regentag,
        'Schwueletage': schwuelertag
    }
    return data


def evapo_from_hdf5(start, end, formula='haude',
                    hdf5=lconf.hdf5_filename,
                    typ_='_data_raw'):
    r"""
    calculates the evapotranspiration [mm/d] following Haude (1955) or Turc as
    described in the Hydrologie-I-Skript as well as the Turc equation
    including global radiation. Further, the reference evapotranspiration
    following Hargreaves & Samani (1985) and FAO Penman-Monteith.

    Parameters
    ----------
    start: datestring
       start date in format "%Y-%m-%dT00:00:00", should be 00:00:00!
    end: datestring
       end date in format "%Y-%m-%dT00:00:00", should be 00:00:00!
    formula: {'haude','turc','turc_rad','hargreaves','penman'}, optional
        formula to use, default: 'haude'
    hdf5 : string, optional
        path and filename of hdf5-file. Default is
        lconf.hdf5_filename

    Returns
    -------
    evapo : np.array of floats
        evapotranspiration [mm/d]
    dat : np.array of datetime objects

    See Also
    --------
    meteox2y.haude : evapotranspiration following Haude (1955) as described in
        the Hydrologie-I-Skript
    meteox2y.turc : evapotranspiration following Turc as described in
        the Hydrologie-I-Skript
    meteox2y.turc_rad : evapotranspiration following Turc including
        global radiation
    meteox2y.hargreaves : evapotranspiration following Hargreaves & Samani 1985
        according to THE ASCE STANDARDIZED REFERENCE EVAPOTRANSPIRATION
        EQUATION
    meteox2y.penman_monteith : reference crop evaporation following the
        Penman-Monteith method and the FAO-56 determinations

    Examples
    --------
    >>> lht.evapo_from_hdf5("2011-09-25T00:00:00","2011-09-28T00:00:00",'haude')
    calculating daily evaporation using haude formula
    (array([ 2.63848717,  4.85231157,  3.37390908]),
     array([2011-09-25 14:01:00, 2011-09-26 14:01:00, 2011-09-27 14:01:00], dtype=object))

    >>> lht.evapo_from_hdf5("2011-09-25T00:00:00","2011-09-28T00:00:00",'turc')
    calculating daily evaporation using turc formula
    (array([ 3.06540059,  3.21869311,  3.23241459]),
     array([2011-09-25 14:01:00, 2011-09-26 14:01:00, 2011-09-27 14:01:00], dtype=object))

    """
    var, date = read_hdf5(start, end,
                          ['Ta_2m', 'rh_2m', 'u_2m', 'G', 'A', 'RK', 'E'],
                          del_t=1, hdf5=hdf5, typ_=typ_)
    print('calculating daily evaporation using', formula, 'formula')
    dat = date.reshape(-1, 1440)[:, 14 * 60]
    mon = np.array([da.month for da in dat])
    if formula == 'haude':
        ta14 = var['Ta_2m'].reshape(-1, 1440)[:, 14 * 60]  # 14:00
        rh14 = var['rh_2m'].reshape(-1, 1440)[:, 14 * 60]  # 14:00
        svp = mxy.sat_vap_p(ta14)
        vp = rh14 / 100. * svp
        evapo = mxy.haude(svp, vp, mon)
    elif formula == 'turc':
        datum = times.datetime2str(date, d_format="%Y-%m-%dT%H:%M")
        at = my.nanavg(var['Ta_2m'].reshape(-1, 1440), axis=1)  # daily mean
        ts = np.nansum(
            mxy.sunshine(var['G'], datum).reshape(-1, 1440), axis=1) / 60.
        evapo = mxy.turc(at, ts, mon)
    elif formula == 'turc_rad':
        at = my.nanavg(var['Ta_2m'].reshape(-1, 1440), axis=1)  # daily mean
        rh = my.nanavg(var['rh_2m'].reshape(-1, 1440), axis=1)  # daily mean
        ii = np.where(var['G'] < 0)
        var['G'][ii] = 0
        G = my.nanavg(var['G'].reshape(-1, 1440), axis=1)  # daily mean
        evapo = mxy.turc_rad(at, rh, G)
    elif formula == 'hargreaves':
        tmax = np.nanmax(var['Ta_2m'].reshape(-1, 1440), axis=1)  # daily max
        tmin = np.nanmin(var['Ta_2m'].reshape(-1, 1440), axis=1)  # daily min
        date = date.reshape(-1, 1440)[:, 0]
        date = times.datetime2str(date, d_format="%Y-%m-%dT%H:%M:%S")
        evapo = mxy.hargreaves(tmax, tmin, date, in_format='%Y-%m-%dT%H:%M:%S')
    elif formula == 'penman':
        at = my.nanavg(var['Ta_2m'].reshape(-1, 1440), axis=1)  # daily mean
        rh = my.nanavg(var['rh_2m'].reshape(-1, 1440), axis=1)  # daily mean
        u = my.nanavg(var['u_2m'].reshape(-1, 1440), axis=1)  # daily mean
        # negative Werte eliminieren (da Messungenauigkeiten)
        ii = np.where(var['G'] < 0)
        var['G'][ii] = 0
        ii = np.where(var['RK'] < 0)
        var['RK'][ii] = 0
        G = my.nanavg(var['G'].reshape(-1, 1440), axis=1)
        A = my.nanavg(var['A'].reshape(-1, 1440), axis=1)
        RK = my.nanavg(var['RK'].reshape(-1, 1440), axis=1)
        E = my.nanavg(var['E'].reshape(-1, 1440), axis=1)
        # Strahlungsbilanz Rn in MJ m^-2 d^-1
        Rn = (G + A - RK - E) * 3600 * 24 / 1000000
        evapo = mxy.penman_monteith(at, u, Rn, rh)

    return evapo, dat


def compare_year(year=None,
                 long_data=r'P:\wetterstation\data\temp_le_61_90.txt',
                 hdf5=r'P:\wetterstation\data\lauchaecker.h5',
                 typ_='_data_raw'):
    """ plots daily average air temperature of year compared to 30-year-data

    Parameters
    ----------
    year : None or int, optional
        if None, current year is used
    long_data : string, optional
        path and filename of txt-file with 30-year-data. Default is
        r'P:\\wetterstation\\data\\temp_le_61_90.txt'
    hdf5 : string, optional
        path and filename of hdf5-file. Default is
        r'P:\\wetterstation\\data\\lauchaecker.h5'
    -------
    None
    """
    if year is None:
        year = time.gmtime().tm_year
    print(year)
    start = str(year) + "-01-01T00:00:00"
    end = str(year + 1) + "-01-01T00:00:00"
    var, date = read_hdf5(start, end, ["Ta_2m"], del_t=1440, hdf5=hdf5,
                          typ_=typ_)
    # date = date + timedelta(days=-1) # date from read_hdf5 is at the end of timestep
    le_data = np.loadtxt(long_data, skiprows=1, usecols=(1, 2, 3))
    ii = len(date)
    if calendar.isleap(year):
        data = np.append(var["Ta_2m"][:59], var["Ta_2m"][60:])
        date = np.append(date[:59], date[60:])
        if ii > 59:
            print('Warning! leap year: all 29 Feb skipped')
    else:
        data = var["Ta_2m"]
    # indices of values lower than min
    drun = np.where((le_data[:ii, 0] - data) > 0)
    # indices of values higher than max
    drueb = np.where((le_data[:ii, 1] - data) < 0)
    #
    plt.figure(figsize=(12, 6))
    plt.plot(date, data, 'k', label='Lauchaecker ' + str(year), linewidth=2)
    plt.plot(date, le_data[:ii, 0], 'b', label='Minimum 1961-1990')
    plt.plot(date, le_data[:ii, 2], c=[.5, .5, .5], label='Average 1961-1990')
    plt.plot(date, le_data[:ii, 1], 'r', label='Maximum 1961-1990')
    if len(drun[0]) > 0:
        plt.scatter(date[drun], data[drun], c='b',
                    label='drunter (%i)' % drun[0].shape)
    if len(drueb[0]) > 0:
        plt.scatter(date[drueb], data[drueb], c='r',
                    label='drueber (%i)' % drueb[0].shape)
    plt.legend(loc='lower center')
    plt.fill_between(date, le_data[:ii, 0], le_data[:ii, 1],
                     facecolor='k', alpha=0.2)
    plt.grid()
    plt.xticks(rotation=30)
    plt.title('Lauchaecker data compared to Leinfelden-Echterdingen (DWD)')
    plt.ylabel(r'$^{\circ}$C')
    #
    print('\n************************\ndrunter: ')
    print(date[drun])
    print('drueber: ')
    print(date[drueb])
    print(('average: %5.2f (%i), %5.2f (1961-1990)' %
           (my.nanavg(data), year, np.average(le_data[:ii, 2]))))
    if ii < 365:
        print('(up to now)')
    print('************************')

