"""Lauchaecker HDF5 tools: plots pluviogram."""

from ._shared import *


__all__ = ['hdf5_2_pluviogram', 'plot_pluviogram']


def hdf5_2_pluviogram(hdf5=lconf.hdf5_filename,
                      start=None, end=None, del_t=60, typ_='_data_raw'):
    r"""Plots a pluviogram. Only to be used with ``lauchaecker.h5`` file!

    Reads the 1 minute values of precipitation for a selected time
    period from h5-file, calculates 60 minute averages and calls
    :func:`plot_pluviogram`.  If `start` and `end` are defined, time
    period is from `start` to `end`. If only `end` is defined, time
    period is the week before `end`. If only `start` is defined, time
    period is from `start` to the last entry in `hdf5`. Else (if both
    `start` and `end` are None), time period is the week before the
    actual time.

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
    hdf5_2_meteogram
    hdf5_2_soilplot
    plot_data

    Examples
    --------

    """
    spath = [
        # 'rr_01', 'rr_02',
        'rr_03', 'rr_04', 'rr_05', 'rr_06', 'rr_07', 'rr_09', 'rr_10']
    var, date = read_hdf5(start, end, spath, del_t=del_t, hdf5=hdf5, typ_=typ_)
    # ################################
    # call plotting:
    plot_pluviogram(date,
                    # var['rr_01'], var['rr_02'],
                    var['rr_03'],
                    var['rr_04'], var['rr_05'], var['rr_06'],
                    var['rr_07'], var['rr_09'], var['rr_10'])


def plot_pluviogram(*args):  # date,rr_D, rr_E, rr_F, rr_G, rr_N, rr_T, rr_W,):
    r""" Internal function called by :func:`hdf5_2_pluviogram`

    Parameters
    ----------
    date : np.array of datetime objects
        date
    # rr_D : np.array of floats
    #     Precipitation Thies D [mm]
    # rr_E : np.array of floats
    #     Precipitation Thies E [mm]
    rr_F : np.array of floats
        Precipitation Thies F [mm]
    rr_G : np.array of floats
        Precipitation Seba G [mm]
    rr_N : np.array of floats
        Precipitation Thies N [mm]
    rr_T : np.array of floats
        Precipitation Tropfenzaehler [mm]
    rr_W : np.array of floats
        Precipitation Ott Pluvio [mm]

    Returns
    -------
    None

    See Also
    --------
    hdf5_2_pluviogram
    """

    # Anzahl der Plots in der Grafik
    nfig = len(args) - 1

    fig = plt.figure(figsize=(14, 10), facecolor='w')

    fig.canvas.set_window_title('pluviogram')
    plt.subplots_adjust(bottom=0.10, top=0.92, left=0.06, right=0.76,
                        wspace=None, hspace=0.0)

    # set bar width = time step in days
    del_t = args[0][1] - args[0][0]
    bar_width = (del_t.seconds / 3600.0) / 24.0 + del_t.days

    names = [
        # 'Thies D', 'Thies E',
        'Thies F', 'Seba G', 'Thies N', 'Seba T',
        'Ott Pluvio W', 'SBS1000_Tot', 'Pluvio2_Avg']

    i = 1
    for arg, nam in zip(args[1:], names):
        if i == 1:
            plt1 = plt.subplot(nfig, 1, i)
            plt.title('pluviogram')
        else:
            plt1 = plt.subplot(nfig, 1, i, sharex=plt1)
        # Problem:
        # Wenn es nicht regnet (oder mindestens einer der Regenschreiber im
        # gesamten Zeitraum 0 gemessen hat), ist in der linken y-Achse nichts
        # drin, und es zerschiesst den ganzen Plot.
        # Loesung:
        # wir zeichnen erst mal die Null-Linie, dann ist auf jeden Fall was da
        plt.plot((args[0][0], args[0][-1]), (0, 0), 'k')
        bars = plt.bar(args[0], arg, bottom=0, width=bar_width, label=nam)
        plt.grid(True)
        plt.ylabel('mm', color='b')
        plt.ylim(ymin=0)
        yti, yla = plt.yticks()
        plt.yticks(yti[1::2], fontsize=10, color='b')
        plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.66),
                   frameon=False)
        ax2 = plt1.twinx()
        # wir zeichnen erst mal die Null-Linie, dann ist auf jeden Fall was da
        plt.plot((args[0][0], args[0][-1]), (0, 0), 'k')
        sumline = plt.plot(args[0], np.cumsum(arg), 'k', label=nam + ' sum')
        print('Summe (nansum) ', nam, np.nansum(arg))
        if np.sum(np.isnan(np.cumsum(arg))) > 0:
            print('NaN in ', nam, ' on ', args[0][np.isnan(arg)])
        plt.ylabel('mm')
        plt.ylim(ymin=0)
        yti, yla = plt.yticks()
        plt.yticks(yti[1::2], fontsize=10)
        plt.legend(loc='center left', bbox_to_anchor=(1.07, 0.3),
                   frameon=False)
        i = i + 1

