"""Lauchaecker HDF5 tools: plots soil evapo."""

from ._shared import *


__all__ = ['hdf5_2_soilplot', 'plot_soildata', 'evapo_plot']


def hdf5_2_soilplot(hdf5=lconf.hdf5_filename,
                    end=None, start=None, del_t=60, typ_='_data_raw'):
    """Plots precipitation, soil moisture, and temperature of soil, air and
    precipitation . Only to be used with ``lauchaecker.h5`` file!

    Reads the 1 minute values of the data necessary for the soilplot
    for a selected time period from h5-file, calculates 60 minute
    averages and calls :func:`plot_soildata`.  If `start` and `end`
    are defined, time period is from `start` to `end`. If only `end`
    is defined, time period is the week before `end`. If only `start`
    is defined, time period is from `start` to the last entry in
    `hdf5`. Else (if both `start` and `end` are None), time period is
    the week before the actual time.

    Remark: Under Windows the 'r'(raw string) prefix is recommended
    before the path!

    Parameters
    ----------
    hdf5 : filename, optional
        path and filename of hdf5-file. Default is lconf.hdf5_filename
    start : datestring or None, optional
        start date in format "%Y-%m-%dT%H:%M:%S", default is None
        If None, start time is one week before end time
    end : datestring or None, optional
        end date in format "%Y-%m-%dT%H:%M:%S", default is None
        If None, function uses actual time as end time
    del_t : int, optional
        timestep in minutes: 1-min-data is averaged to this timestep.
        Default is 60

    Returns
    -------
    None

    See Also
    --------
    hdf5_2_pluviogram
    hdf5_2_meteogram
    plot_data

    Examples
    --------

    """
    spath = ['rr_06', 'rr_07', 'Tg_2cm', 'Tg_5cm', 'Tg_10cm', 'Tg_20cm',
             'Tg_50cm', 'VWC_01', 'VWC_02', 'VWC_03', 'VWC_04', 'VWC_05',
             'Ta_2m', 'TC_01']
    var, date = read_hdf5(start, end, spath, del_t=del_t, hdf5=hdf5, typ_=typ_)
    # Niederschlagstemperatur maskieren (NAN wenns nicht regnet):
    ii = np.where(var['rr_06'] == 0)  # Daten von Tropfer verwenden
    var['TC_01'][ii] = np.nan
    # ################################
    # call plotting:
    plot_soildata(date, var['rr_06'], var['rr_07'], var['Tg_2cm'],
                  var['Tg_5cm'], var['Tg_10cm'], var['Tg_20cm'],
                  var['Tg_50cm'], var['VWC_01'], var['VWC_02'],
                  var['VWC_03'], var['VWC_04'], var['VWC_05'],
                  var['Ta_2m'], var['TC_01'])


def plot_soildata(date, rain_t, rain_w, tg2, tg5, tg10, tg20, tg50, bf1, bf2,
                  bf3, bf4, bf5, at, tc):
    r"""
    Internal function called by :func:`hdf5_2_soilplot`

    Parameters
    ----------
    date : np.array of datetime objects
        datum
    rain_t : np.array of floats
        rain Tropfenzaehler [mm]
    rain_w : np.array of floats
        rain Ott Pluvio [mm]
    tg2 : np.array of floats
        soil temperature 2cm [degC]
    tg5 : np.array of floats
        soil temperature 2cm [degC]
    tg10 : np.array of floats
        soil temperature 2cm [degC]
    tg20 : np.array of floats
        soil temperature 2cm [degC]
    tg50 : np.array of floats
        soil temperature 2cm [degC]
    bf1 : np.array of floats
        soil moisture 1 5cm [-]
    bf2 : np.array of floats
        soil moisture 2 5cm [-]
    bf3 : np.array of floats
        soil moisture 3 10cm [-]
    bf4 : np.array of floats
        soil moisture 4 20cm [-]
    bf5 : np.array of floats
        soil moisture 5 50cm [-]
    at : np.array of floats
        air temperature [degC]
    tc : np.array of floats
        precipitation temperature [degC]

    Returns
    -------
    None

    See Also
    --------
    hdf5_2_soilplot
    """
    # set bar_width = time step in days
    del_t = date[1] - date[0]
    bar_width = (del_t.seconds / 3600.0) / 24.0 + del_t.days

    nfig = 3

    fig = plt.figure(figsize=(14, 10), facecolor='w')
    fig.canvas.set_window_title('soil data')
    plt.subplots_adjust(bottom=0.10, top=0.92, left=0.06, right=0.76,
                        wspace=None, hspace=0.0)

    plt1 = plt.subplot(nfig, 1, 1)
    plt.title(u'Soil Data (Rohdaten) Station Lauchäcker 453 m NN')  # 1: rain
    plt.plot(date, np.cumsum(rain_w), label='ND-Summe Waage')
    plt.plot(date, np.cumsum(rain_t), label='ND-Summe Tropfer')
    # barplot von Niederschlag:
    plt.bar(date, rain_w, color='b', bottom=0, width=bar_width,
            label='Niederschlag Waage', alpha=0.5)
    plt.bar(date, rain_t, color='g', bottom=0, width=bar_width,
            label='Niederschlag Tropfer', alpha=0.5)
    plt.grid(True)
    plt.ylabel('[mm]')
    yti, yla = plt.yticks()
    plt.xticks(rotation=90)
    plt.legend(loc='center left', bbox_to_anchor=(1.01, 0.27), frameon=False)

    plt.subplot(nfig, 1, 2, sharex=plt1)  # 2: Bodenfeuchte
    plt.plot(date, bf1, label='Bodenfeuchte 5cm')
    plt.plot(date, bf2, label='Bodenfeuchte 5cm')
    plt.plot(date, bf3, label='Bodenfeuchte 10cm')
    plt.plot(date, bf4, label='Bodenfeuchte 20cm')
    plt.plot(date, bf5, label='Bodenfeuchte 50cm')
    plt.legend(loc='center left', bbox_to_anchor=(1.01, 0.5), frameon=False)
    plt.grid(True)
    yti, yla = plt.yticks()
    plt.yticks(yti[1:-1])
    plt.xticks(rotation=90)

    plt.subplot(nfig, 1, 3, sharex=plt1)  # 3: Temperaturen
    plt.plot(date, tg2, label='T 2cm')
    plt.plot(date, tg5, label='T 5cm')
    plt.plot(date, tg10, label='T 10cm')
    plt.plot(date, tg20, label='T 20cm')
    plt.plot(date, tg50, label='T 50cm')
    plt.plot(date, at, 'k', linewidth=2, label='Lufttemperatur')
    plt.scatter(date, tc, 25, 'b', linewidth=0,
                label='Niederschlagstemperatur')
    plt.legend(loc='center left', bbox_to_anchor=(1.01, 0.5), frameon=False)
    plt.grid(True)
    plt.ylabel(r'[$^{\circ}$C]')
    yti, yla = plt.yticks()
    plt.yticks(yti[1:-1:2])
    matplotlib.dates.AutoDateLocator()
    plt.gcf().autofmt_xdate(rotation=45)


def evapo_plot(start, end, hdf5=lconf.hdf5_filename,
               formulas=['haude', 'turc', 'turc_rad', 'hargreaves', 'penman']):
    # fig=plt.figure(facecolor='w')
    r"""
    plots evapotranspiration curves of evapo_from_hdf5, including turc_rad,
    haude, hargreaves, penman

    Parameters
    ----------
    start : string
       start date in format "%Y-%m-%dT%H:%M:%S"
    end : string
       end date in format "%Y-%m-%dT%H:%M:%S"
    formulas : choice between Haude, Turc, Turc with Radiation, Penman and
    Hargreaves

    Returns
    -------
    None

    See also
    --------
    evapo_from_hdf5

    """
    # plt.plot(date,turc,'k--',linewidth=2,label='Turc')
    # sets bar width to the number of chosen formulas
    bar_width = 1. / (len(formulas) + 0.5)
    timed = timedelta(days=0)
    barcolors = ['b', 'g', 'r', 'k', 'c']
    fig = plt.figure(figsize=(14, 10), facecolor='w')
    fig.canvas.set_window_title('Evapotranspiration')
    plt.subplots_adjust(bottom=0.10, top=0.92, left=0.06, right=0.76,
                        wspace=None, hspace=0.0)

    # zip: parallel loop over both lists
    for formula, barcolor in zip(formulas, barcolors):
        evapo, date = \
            evapo_from_hdf5(start, end, formula=formula, hdf5=hdf5)
        # Formulas are calcutated for 14:00 (-> Haude), this sets time to 00:00
        date = date + timedelta(hours=-14) + timed
        # bars = plt.bar(date,turc, bottom=0, width=bar_width, label='Turc')
        # plt.plot(date,haude,'g',label='Haude')
        evapsum = np.nansum(evapo)
        bars = plt.bar(date, evapo, bottom=0, width=bar_width,
                       label=formula + ": %.1f" % (evapsum,) + " mm",
                       color=barcolor)

        timed = timed + timedelta(days=bar_width)
        # plt.plot(date,hargreaves,'b:',linewidth=2, label='Hargreaves')
        # bars = plt.bar(date+timedelta(days=0.25),hargreaves, bottom=0, width=bar_width, label='Hargreaves')
        # plt.plot(date, penman,'r', label='Penman')
        print('Summe: ', " %.1f" % evapsum, " mm")

    plt.title(u'Verdunstungshoehen an der Station Lauchaecker')
    plt.grid(True)
    # plt.legend(loc = 'upper left')
    plt.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), frameon=False)
    plt.ylabel('Verdunstungshoehe [mm/d]')
    plt.xlabel('Datum')
    # if all(turc<2.5) and all(haude<2.5) and all(hargreaves<2.5) and all(penman<2.5):
    #     plt.ylim(0,3)
    # elif all(turc<5.) and all(haude<5.) and all(hargreaves<5.) and all(penman<5.):
    #     plt.ylim(0,6)
    # else:
    #     plt.ylim(0,10)
    fig.autofmt_xdate()

