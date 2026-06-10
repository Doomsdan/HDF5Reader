"""Lauchaecker HDF5 tools: plots meteogram."""

from ._shared import *


__all__ = ['hdf5_2_meteogram', 'plot_meteogram']


def hdf5_2_meteogram(hdf5=lconf.hdf5_filename,
                   meta_xls_filename=lconf.meta_xls_filename,
                   end=None, title=None, typ_='_data_raw',
                   figpath=None):
    r"""Plots a meteogram with a length of 7 days. Only to be used with
    ``lauchaecker.h5`` file!

    Reads the 1 minute values for 7 days preceding the end date from h5-file,
    calculates 60 minute averages and calls :func:`plot_meteogram`.

    Remark: Under Windows the 'r'(raw string) prefix is recommended before the
    path!

    Parameters
    ----------
    hdf5 : filename, optional
        path and filename of hdf5-file. Default is
        lconf.hdf5_filename
    end : datestring or None, optional
        end date in format "%Y-%m-%dT%H:%M:%S", default is None
        If None, function uses actual time as end time
    title: str, optional
        titel is just past to plot_meteogram
    typ_ : ['_data_raw', '_data_processed']
        type of data
    figpath, str, optional
        Filepath of figure for savefig.

    Returns
    -------
    None

    See Also
    --------
    hdf5_2_pluviogram
    hdf5_2_soilplot
    plot_data

    Examples
    --------

    >>> #hdf5_2_meteogram(hdf5=lconf.hdf5_filename, end = None)

    Plots a meteogram from 7 days before last entry in .h5 file

    >>> #hdf5_2_meteogram(hdf5=lconf.hdf5_filename,
    end='2011-09-25T09:00:00')

    Plots a meteogram from 2011-09-18T09:00:00 to 2011-09-25T09:00:00
    """

    spath = ['Ta_2m', 'rh_2m', 'G', 'A', 'u_19m',
             'dd_19m', 'rr_07', 'RK', 'E', 'p']
    var, date = read_hdf5(None, end, spath, del_t=60, hdf5=hdf5, typ_=typ_,
                          full=True, meta_xls_filename=meta_xls_filename)
    if not any(date):
        print('Warning, no data available')
        return

    else:
        date = times.datetime2unix(date)
        # convert data:
        dp = mxy.dewpoint(var['Ta_2m'], rh=var['rh_2m'] / 100.0)
        u, v = angle2component(var['dd_19m'], var['u_19m'])  # wind 2 uv
        u, v = avrwind(u, v, 60, 3600)[:2]  # wind averaging
        wind = np.array([u, v]).transpose(1, 0)
    # ################################
    # call plotting:
    plot_meteogram(date, var['Ta_2m'], var['rh_2m'], var['G'],
                   var['A'], wind, var['rr_07'], dp, var['RK'], var['E'],
                   var['p'], figpath=figpath, title=title)


def plot_meteogram(date, at, rh, sw, lw, wind, rain, dp, rk, lw_E, bp,
                   figpath=None, title=None, barb_skip=6):
    r"""
    Internal function called by :func:`hdf5_2_meteogram`

    Parameters
    ----------
    date : np.array of floats
        datum in unix timestamps
    at : np.array of floats
        air temperature [degC]
    rh : np.array of floats
        relative humidity [%]
    sw : np.array of floats
        short wave radiation [W/m**2]
    lw : np.array of floats
        incident long wave radiation [W/m**2]
    wind : np.array of floats (2D)
        wind components (u, v) in 2columns [m/s]
    rain : np.array of floats
        rain [mm]
    dp : np.array of floats
        dew point [degC]
    rk : np.array of floats
        reflected short wave rad [W/m**2]
    lw_E : np.array of floats
        reflected long wave rad [W/m**2]
    bp : np.array of floats
        barometric pressure [hPa]
    figpath: str
        path and filename, where the plot will be stored
        e.g. ..\xx\xx.jpg
    titel: str, optional
        default is Meteogramm (Rohdaten) Station Lauchäcker 453 m NN
    barb_skip : int, optional
        interval for plotting wind barbs (e.g. 1: plot every barb), default = 6

    Returns
    -------
    None

    See Also
    --------
    hdf5_2_meteogram
    """
    nfig = 6

    if title is None:
        title = u'Meteogramm (Rohdaten) Station Lauchäcker 453 m NN'

    # calculate max short wave radiation:
    # Stundenwerte: Minutenwerte berechnen, mitteln wie bei Messwerten
    if date[1] - date[0] == 3600:
        date_sw = np.arange(date[0] - 3600, date[-1] + 1, 60)
        # date_sw in datetime for max sw + xticks
        date_sw2 = times.unix2datetime(date_sw)
        swdate = np.array([ds.strftime(format='%Y-%m-%dT%H:%M')
                           for ds in date_sw2])
        swmax = mxy.pot_s_rad(swdate[:-1])
        swmax = np.average(swmax.reshape(len(swmax) / 60, 60), axis=1)
        date_sw2 = date_sw2[60::60]
    else:
        # date_sw in datetime for max sw + xticks
        date_sw2 = times.unix2datetime(date)
        swdate = np.array([ds.strftime(format='%Y-%m-%dT%H:%M')
                           for ds in date_sw2])
        swmax = np.array([mxy.pot_s_rad([sd], tz_mer=30) for sd in swdate])

    fig = plt.figure(figsize=(14, 10), facecolor='w')

    # the wind barbs do not want to have a datetime x-axis, therefore the whole
    # plot is in unix timestamps. To get nice locations for the xticks, we make
    # a temporary subplot with datetime x-axis for xticks, will be deleted:
    plt.subplot(nfig, 1, 1)
    plt.plot(date_sw2, swmax)
    matplotlib.dates.AutoDateLocator()
    fig.autofmt_xdate(rotation=45)
    # get xtick locations and convert to unix timestamp
    locs, labs = plt.xticks()
    locs = times.datetime2unix(np.array(num2date(locs)))
    labs = times.unix2datetime(locs)
    lab_fmt = '%d.%m.%Y'  # Format fuer Datum in xticklabels
    labs = np.array([lab.strftime(lab_fmt) for lab in labs])
    plt.clf()  # delete temporary subplot

    fig.canvas.set_window_title('Meteogramm')
    plt.subplots_adjust(bottom=0.10, top=0.95, left=0.07, right=0.76,
                        wspace=None, hspace=0.0)

    plt1 = plt.subplot(nfig, 1, 1)  # 1: temp + dewpoint + relhum
    plt.title(title)
    plt.plot(date, at, 'r', label='T$_{a}$ Lufttemperatur 2m')
    plt.plot(date, dp, 'g', label='T$_{d}$ Taupunkt 2m')
    plt.fill_between(date, dp, at, facecolor='b', alpha=0.2)
    # 0-Grad-Linie nur, wenn ymin < 0 and ymax > 0
    ymin, ymax = plt.ylim()
#    if ymin < 0 and ymax > 0: plt.plot(date, np.zeros(len(date)), 'b')
    if ymin < 0 and ymax > 0:
        plt.axhline(0, ls='--', color='k')
    plt.grid(True)
    plt.ylabel(r'[$^{\circ}$C]')
    yti, yla = plt.yticks()
    plt.yticks(yti[1:-1])
    plt.xticks(locs, labs, rotation=90)
    plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.75),
               frameon=False, prop={'size': 12})
    ax2 = plt1.twinx()
    plt.plot(date, rh, 'c', label='rh Luftfeuchte')
    plt.ylabel('[%]', color='c')
    yti, yla = plt.yticks()
    plt.yticks(yti[1:-1], color='c')
    plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.45),
               frameon=False, prop={'size': 12})

    plt.subplot(nfig, 1, 2, sharex=plt1)  # 2: sw
    plt.plot(date, swmax, c=[0.8, 0.8, 0.8], alpha=0.5,
             label=u'G$_{max}$ max. theoretische\n      Solarstrahlung au-\n      ßerhalb Atmosphäre\n\n')  # max SW-Radiation
    plt.plot(date, sw, 'b', label=r'K$\downarrow$ Globalstrahlung')
    plt.plot(date, rk, c=[1, 0.5, 0], label=r'K$\uparrow$ Reflexstrahlung')
    plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.5),
               frameon=False, prop={'size': 12})
    plt.grid(True)
    plt.ylabel('[W/m$^{2}$]')
    yti, yla = plt.yticks()
    plt.yticks(yti[1:-1])
    plt.xticks(locs, labs, rotation=90)

    plt.subplot(nfig, 1, 3, sharex=plt1)  # 3: lw
    if np.sum(np.isfinite(lw)) == 0:
        plt.plot((date[0], date[-1]), (0, 0), 'k')
    plt.plot(date, lw, 'b',
             label=r'L$\downarrow$ atmosphärische\n      Gegenstrahlung')
    plt.plot(date, lw_E, c=[1, 0.5, 0],
             label=r'L$\uparrow$ terrestrische\n      Strahlung ')
    plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.4),
               frameon=False, prop={'size': 12})
    plt.grid(True)
    plt.ylabel('[W/m$^{2}$]')
    yti, yla = plt.yticks()
    plt.yticks(yti[1:-1:2])
    plt.xticks(locs, labs, rotation=90)

    plt.subplot(nfig, 1, 4, sharex=plt1)  # 4: Strahlungsbilanz
    net_lw = lw - lw_E
    net_sw = sw - rk
    net = net_lw + net_sw
    if np.sum(np.isfinite(net_lw)) == 0:
        plt.plot((date[0], date[-1]), (0, 0), 'k')
    plt.plot(date, net_sw, 'k:',
             label='K$^{*}$ kurzwellige\n      Strahlungsbilanz')
    plt.plot(date, net_lw, 'k--',
             label='L$^{*}$ langwellige\n      Strahlungsbilanz')
    plt.plot(date, net, 'k', linewidth=1.5,
             label='R$_{n}$ Gesamtstrahlungs-\n      bilanz')
    plt.fill_between(date, net, 0, where=net < 0, facecolor='b', alpha=0.2)
    plt.fill_between(date, net, 0, where=net > 0, facecolor='r', alpha=0.2)
    plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.5),
               frameon=False, prop={'size': 12})
    plt.grid(True)
    plt.ylabel('[W/m$^{2}$]')
    yti, yla = plt.yticks()
    plt.yticks(yti[1:-1])
    plt.xticks(locs, labs, rotation=90)

    ax1 = plt.subplot(nfig, 1, 5, sharex=plt1)  # 5: rain and pressure
    # barplot von Niederschlag: width=3600 bei Stundenwerten
    dt = date[1] - date[0]
    plt.bar(date, rain, bottom=0, width=dt,
            label=u'N Niederschlagsinten-\n    sität')
    # Damit die Step-Funktionen mit den Balken uebereinstimmen,
    # muessen diese um dt nach rechts verschoben werden. Cumsum
    # funktioniert nicht mit nan Werten, daher werden diese für die
    # Cumsum auf 0 gesetzt und danach wieder auf nan
    bool_nan = np.isnan(rain)
    rain[bool_nan] = 0
    prec_cumsum = np.cumsum(rain)
    prec_cumsum[bool_nan] = np.nan
    plt.step(date + dt, prec_cumsum, label=r'$\Sigma$ Niederschlagssumme')
    plt.grid(True)
    plt.ylabel('[mm]', color='b')
    yti, yla = plt.yticks()
    # wenn keine werte vorhanden sind, entstehen negative y-achsen abschnitte
    # diese werden ausgeblendet
    if ((np.nansum(rain) == 0) | (np.isnan(np.nansum(rain)))):
        plt.yticks(yti[yti >= 0][:-1], color='b')
    else:
        plt.yticks(yti[1:-1], color='b')
    plt.xticks(locs, labs, rotation=90)
    plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.27),
               frameon=False, prop={'size': 12})
    slp = mxy.norm_pressure(bp, at)
    ax2 = ax1.twinx()
    plt.plot(date, slp, 'g--', label='p Luftdruck NN')
    plt.ylabel('[hPa]', color='g')
    yti, yla = plt.yticks()
    plt.yticks(yti[1:-1], color='g')
    plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.7),
               frameon=False, prop={'size': 12})

    plt.subplot(nfig, 1, nfig, sharex=plt1)  # 6: wind barbs:
    X, Y = np.meshgrid(date[::barb_skip], [1])
    u, v = wind[::barb_skip, 0], wind[::barb_skip, 1]
    U, V = u * Y, v * Y
    Y = Y * 8  # barbs are fixed to 8 m/s - gridline
    plt.barbs(X, Y, U, V, rounding=False,
              barb_increments={'half': 1, 'full': 2, 'flag': 10})
    if np.sum(np.isfinite(wind[:, 0])) == 0:
        plt.plot((date[0], date[-1]), (0, 0), 'k')
    speed = (wind[:, 0] ** 2 + wind[:, 1] ** 2) ** 0.5
    plt.plot(date, speed, 'r', label='v Windgeschwindig-\n    keit 19m')
    plt.ylabel('[m/s]', color='r')
    plt.grid(True)
    plt.xticks(locs, labs, rotation=45)
    ymin, ymax = plt.ylim()
    if ymax < 11.0:
        plt.ylim(ymax=11)
    plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.5),
               frameon=False, prop={'size': 12})
    # Fixes Fenster mit fixem Abstand zu der rechten/linken
    # Y-Achse. Dadurch sind x-ticklabels der anderen axes immer
    # verdeckt
    plt.xlim(date[0] - 5000, date[-1] + 5000)
    # plt.xlim(date[0],date[-1])

    if figpath is not None:
        plt.savefig(figpath, dpi=80)
        plt.close()

