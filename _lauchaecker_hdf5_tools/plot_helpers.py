"""Lauchaecker HDF5 tools: plot helpers."""

from ._shared import *


__all__ = ['plot_logger_data_reaches', 'plot_data']


def plot_logger_data_reaches(logger_dir, recursive=False, ax=None):
    """This results in a somewhat cluttered staircase-like bar plot,
    showing the temperal redundancy in logger files.

    Parameter
    ---------
    logger_dir : str
        Where to look for the logger files.
    recursive : boolean, optional
        Include subfolders of `logger_dir` if True.
    ax : matplotlib.axes instance, optional
        Plot into this ax.
    """
    find = my.recursive_glob if recursive else glob.glob
    logger_files = find(os.path.join(logger_dir, "*.dat"))
    starts, ends, filenames = [], [], []
    for logger_file in logger_files:
        print("Reading %s" % logger_file)
        try:
            start, end = _loggerfile_reaches(logger_file)
        except times.TimeParseError:
            continue
        filenames.append(logger_file)
        starts.append(start)
        ends.append(end)
    sort_ii = np.argsort(starts)
    starts, ends, filenames = map(lambda x: np.asarray(x)[sort_ii],
                                  (starts, ends, filenames))
    if ax is None:
        _, ax = plt.subplots()
    for y, (start, end, filename) in enumerate(zip(starts, ends, filenames)):
        y_pos = 2 * y
        start, end = map(matplotlib.date2num, (start, end))
        ax.barh(y_pos, end - start, left=start, color="b")
        ax.text(end,  # start + (end - start) / 2,
                y_pos,
                path_basename(filename).decode("utf-8"),
                horizontalalignment="center")
    ax.set_ylim(0, y_pos + 1)
    ax.xaxis_date()
    ax.grid()
    return ax


def plot_data(start, end, varpath,
              hdf5=lconf.hdf5_filename, del_t=60,
              typ_='_data_raw'):
    r"""
    plot selected variables from lauchaecker hdf5

    Parameters
    ----------
    start : string
       start date in format "%Y-%m-%dT%H:%M:%S"
    end : string
       end date in format "%Y-%m-%dT%H:%M:%S"
    varpath : list of str
        list of variable paths in the hdf5-file, without
        '/lauchaecker/min_01/data/', e.g. 'Ta_2m'
    hdf5 : string, optional
        path and filename of data text file. Default is
        r'P:\wetterstation\data\CR3000_data_1min.dat'
    del_t : int, optional
        timestep in minutes: 1-min-data is averaged to this timestep.
        Default is 60

    Returns
    -------
    None

    See Also
    --------
    hdf5_2_meteogram
    hdf5_2_pluviogram
    hdf5_2_soilplot

    """
    var, date = read_hdf5(start, end, varpath, del_t=del_t, hdf5=hdf5,
                          typ_=typ_)
    # wind averaging:
    if 'u_19m' in var and 'dd_19m' in var and del_t > 1:
        u, v = angle2component(var['dd_19m'], var['u_19m'])  # wind 2 uv
        u, v = avrwind(u, v, 60, 60 * del_t)[:2]
        var['dd_19m'], var['u_19m'] = component2angle(u, v)
    if 'u_2m' in var and 'dd_2m' in var and del_t > 1:
        u, v = angle2component(var['dd_2m'], var['u_2m'])  # wind 2 uv
        u, v = avrwind(u, v, 60, 60 * del_t)[:2]
        var['dd_2m'], var['u_2m'] = component2angle(u, v)
    if 'u_2m' in var and 'dd_2m' not in var:
        var['u_2m'] = np.average(var['u_2m'].reshape(-1, del_t), axis=1)
    if 'dd_2m' in var and 'u_2m' not in var:
        var['dd_2m'] = np.average(var['dd_2m'].reshape(-1, del_t), axis=1)
    if 'u_19m' in var and 'dd_19m' not in var:
        var['u_19m'] = np.average(var['u_19m'].reshape(-1, del_t), axis=1)
    if 'dd_19m' in var and 'u_19m' not in var:
        var['dd_19m'] = np.average(var['dd_19m'].reshape(-1, del_t), axis=1)
    # set bar width = time step in days
    del_t = date[1] - date[0]
    bar_width = (del_t.seconds / 3600.0) / 24.0 + del_t.days
    # plot:
    nfig = len(var)
    # some variables should be in same subplot: <<
    if ('u_19m' in var) & ('u_2m' in var):
        nfig = nfig - 1
    if ('dd_19m' in var) & ('dd_2m' in var):
        nfig = nfig - 1
    if ('Ta_18m' in var) & ('Ta_2m' in var):
        nfig = nfig - 1
    if (('TC_01' in var) & ('Ta_2m' in var) |
            ('TC_01' in var) & ('Ta_18m' in var)):
        nfig = nfig - 1
    if ('rh_18m' in var) & ('rh_2m' in var):
        nfig = nfig - 1
    if ('E' in var) & ('A' in var):
        nfig = nfig - 1
    if ('G' in var) & ('RK' in var):
        nfig = nfig - 1
    # >>
    plt.figure(figsize=(16, 1 * nfig + 1))
    if nfig > 4:
        plt.subplots_adjust(hspace=0, left=0.1, right=0.88, top=0.95,
                            bottom=0.05)
    else:
        plt.subplots_adjust(hspace=0, left=0.1, right=0.88, top=0.9,
                            bottom=0.1)
    i = 1
    for va in sorted(var):
        if i == 1:
            plt1 = plt.subplot(nfig, 1, i)
        # some variables should be in same subplot: <<
        elif (va == 'u_2m') & ('u_19m' in var):
            i = i - 1
        elif (va == 'dd_2m') & ('dd_19m' in var):
            i = i - 1
        elif ((va == 'Ta_18m') & ('TC_01' in var) ^
              (va == 'Ta_2m') & ('TC_01' in var)):
            i = i - 1
        elif (va == 'Ta_2m') & ('Ta_18m' in var):
            i = i - 1
        elif (va == 'rh_2m') & ('rh_18m' in var):
            i = i - 1
        elif ((va == 'RK') & ('G' in var)) ^ ((va == 'E') & ('A' in var)):
            i = i - 1
        # >>
        else:
            plt1 = plt.subplot(nfig, 1, i, sharex=plt1)
        if 'rr' in va:
            plt.plot((date[0], date[-1]), (0, 0), 'k')
            bars = plt.bar(date, var[va], bottom=0, width=bar_width, label=va)
            plt.grid(True)
            yti, yla = plt.yticks()
            plt.yticks(yti[1::2], fontsize=10, color='b')
            plt.legend(loc='center left', bbox_to_anchor=(1.01, 0.66),
                       frameon=False)
            ax2 = plt1.twinx()
            plt.plot((date[0], date[-1]), (0, 0), 'k')
            sumline = plt.plot(date, np.cumsum(var[va]), 'k',
                               label=va + ' sum')
            print('Summe ', va, np.sum(var[va]))
            if np.sum(np.isnan(np.cumsum(var[va]))) > 0:
                print('NaN in ', va, ' on ', date[np.isnan(var[va])])
            plt.legend(loc='center left', bbox_to_anchor=(1.01, 0.3),
                       frameon=False)
        else:
            print(date.shape, var[va].shape, va)
            plt.plot(date, var[va], label=va)
            plt.legend(loc='center left', bbox_to_anchor=(1.01, 0.5),
                       frameon=False)
            plt.grid(True)
            if 'dd_' in va:
                plt.ylim((0, 360))
#            if i>1:
#                yti,yla = plt.yticks()
#                plt.yticks(yti[:-1])#,fontsize=10)
        i = i + 1

