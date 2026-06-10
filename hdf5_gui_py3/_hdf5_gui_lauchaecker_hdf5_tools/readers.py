"""Lauchaecker HDF5 tools: readers."""

from ._shared import *


__all__ = ['hdf52df', 'read_hdf5', 'read_hdf5_', 'hdf52txt', 'data_reaches']


def hdf52df(start=None, stop=None, varnames=None,
            hdf5_filename=lconf.hdf5_filename,
            path="/lauchaecker/min_01",
            meta_xls_filename=lconf.meta_xls_filename, convert=True):
    """Returns a pandas.DataFrame representation of the lauchaecker hdf5 file.

    Parameter
    ---------
    start : str, datetime or None, optional
        Start time representation. None: start from the beginning of records.
        If it is a string, pandas' very tolerant parsing will be used.
    stop : str, datetime or None, optional
        End time representation. None: end at the end of records.
        If it is a string, pandas' very tolerant parsing will be used.
    varnames : sequence of str or None, optional
        Which variables to read.
    path : str (valid hdf5-path), optional
        Where to find the root of the data in the hdf5-file.
        (this might allow the reading of different time discretizations later.)
    meta_xls_filename: str, optional
        Where the metainformation of the hdf5 file is stored.
    convert: bool, optional
        if True, use the convertion factors of the different precipitation
        and convert from pulses to milimeters


    Returns
    -------
    df : pandas.DataFrame
    """
    def str2datetime(x):
        return pd.core.tools.datetimes.parse_time_string(x)[0]

    if type(start) == str:
        forma="%Y-%m-%dT%H:%M:%S"
        start=datetime.datetime.strptime(start,forma)
        #start = str2datetime(start)
    if type(stop) == str:
        forma="%Y-%m-%dT%H:%M:%S"
        stop=datetime.datetime.strptime(stop,forma)
        #stop = str2datetime(stop)

    try:
        meta = read_metadata(meta_xls_filename)
    except Exception:
        meta = None
        convert = False

    variables = {}
    with open_hdf5(hdf5_filename, "r") as h5f:
        time_node = h5f.get_node(tables.path.join_path(path, "timestamps"))
        total_timesteps = len(time_node)
        refts = time_node[0]
        period = timedelta(minutes=1)

        def stamp2index(stamp):
            
            liste=pd.date_range(datetime.datetime.strptime(str(refts),"b'%Y-%m-%dT%H:%M:%S'"), datetime.datetime.now(),freq=str(int(period.total_seconds()/60))+'Min')
            index=(liste == stamp).argmax()
            
            #index = times.timestamp2index(stamp, period, refts)
            if index==0 and stamp!=refts:
                index=total_timesteps - 1
            #print(index)
            # wrap around to indices that actually exist
            return min(total_timesteps - 1, max(0, index))
        
        def stamp2index_start(stamp):
            
            liste=pd.date_range(datetime.datetime.strptime(str(refts),"b'%Y-%m-%dT%H:%M:%S'"), datetime.datetime.now(),freq=str(int(period.total_seconds()/60))+'Min')
            index=(liste == stamp).argmax()
            
            #index = times.timestamp2index(stamp, period, refts)
            #print(index)
            # wrap around to indices that actually exist
            return min(total_timesteps - 1, max(0, index))

        # Wenn kein Enddatum angegeben ist wird
        if stop is None:
            # first get time in utc, then add 1 hour -> no problems
            # with dst (at least i hope so)
            stop = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
            stop=datetime.datetime.strptime(stop, "%Y-%m-%dT%H:%M")
            #stop = times.datetimefromisoformat(stop)
            stop_i = stamp2index(stop)
            stop_i = stop_i + 60  # utc -> cet
        # Wenn Enddatum angegeben ist dann das hier:
        else:
            stop_i = stamp2index(stop)
        # Wenn kein Startdatum angegeben ist wird
        if start is None:
            start_i = stop_i - 7 * 1440 - 60
        # Wenn Startdatum angegeben ist dann das hier:
        else:
            start_i = stamp2index_start(start)
            
            
        def index2timestamp(stamp_i,period,refts):
            liste=pd.date_range(datetime.datetime.strptime(str(refts),"b'%Y-%m-%dT%H:%M:%S'"), datetime.datetime.now(),freq=str(int(period.total_seconds()/60))+'Min')
            return liste[stamp_i]
        
        start = index2timestamp(start_i, period, refts)
        
        n_timesteps = stop_i - start_i
        # we do not read the timestamps, and convert them to
        # datetimeindices for pandas. it is faster to let pandas
        # generate them with pd.date_range (see below)
        # timestamps = time_node[start_i:stop_i]
        
        data_path = tables.path.join_path(path, "data")
    
        if varnames is None:
            groups = h5f.walkGroups(data_path)
            varnames = [path_basename(group._v_pathname)
                        for group in groups]
            # the first element is "data", the currrent root itself
            varnames = varnames[1:]

        for varname in varnames:
            data_node = h5f.get_node(tables.path.join_path(data_path,
                                                           varname),
                                     varname + "_data_raw")
            values = data_node[start_i:stop_i]
            if convert and meta is not None:
                f = meta[meta['varname'] == varname]['conversion_factor']
                # Check if conversion factors did not change for changing
                # parameter names of the same meassurement
                assert(np.unique(f).shape[0] == 1)
                values *= float(f.values[0])
            if len(values) == n_timesteps:
                variables[varname] = values
            else:
                print ("%s: unexpected length (%d instead of %d)" %
                       (varname, len(values), n_timesteps))

    if start in (None, ""):
        start = refts
    datetimeindex = pd.date_range(start, periods=n_timesteps, freq="1min")
    return pd.DataFrame(variables, index=datetimeindex)


def read_hdf5(start, end, varpath, del_t=60, hdf5=lconf.hdf5_filename,
              meta_xls_filename=lconf.meta_xls_filename,
              typ_='_data_raw', full=False):
    # ##############################
    # uerberpruefe, ob bp (barometric pressure) gesucht wird,
    # dann werden druck und temperatur benoetigt. ergaenzen, falls nicht
    # zusaetzlich gesucht
    # erstelle zunaechst eine Kopie, damit ausserhalb der Funktion
    # die liste nicht veraendert wird
    _varpath = list(varpath)
    if 'bp' in varpath:
        for ivar in ['p', 'Ta_2m']:
            if ivar not in varpath:
                varpath.append(ivar)
        varpath.remove('bp')

    def str2datetime(x):
        return pd.core.tools.datetimes.parse_time_string(x)[0]

    if isinstance(start, str):
        forma="%Y-%m-%dT%H:%M:%S"
        start=datetime.datetime.strptime(start,forma)
        #start = str2datetime(start)
    if isinstance(end, str):
        forma="%Y-%m-%dT%H:%M:%S"
        end=datetime.datetime.strptime(end,forma)
        #end = str2datetime(end)

    if del_t < 1440 and start is not None and end is not None:
        # this is weird, but what is expected of us
        start += datetime.timedelta(minutes=del_t)
        end += datetime.timedelta(minutes=del_t)
    
    df_minutes = hdf52df(start, end, varpath, hdf5,
                         meta_xls_filename=meta_xls_filename,
                         convert=True)

    def agg_to_dict(varnames, agg_func):
        df = (df_minutes[varnames]
              .resample("%sT" % del_t)
              .apply(agg_func))
        dict_ = {varname: np.array(values)
                 for varname, values in
                 df.to_dict("list").items()}
        return dict_, df.index

    if del_t != 1:
        values_dict = {}
        # add up rain
        varnames_rain = [varname
                         for varname in df_minutes.columns
                         if varname.startswith("rr_")]
        if varnames_rain:
            rain_dict, index = agg_to_dict(varnames_rain,
                                           np.sum)
            values_dict.update(rain_dict)

        # do not touch wind
        varnames_wind = [varname
                         for varname in df_minutes.columns
                         if varname.startswith(("u_", "dd_"))]
        if varnames_wind:
            values_dict.update(df_minutes[varnames_wind].to_dict("list"))
            index=df_minutes[varnames_wind[0]].index
        # varnames_wind = []

        # average other
        varnames_other = [varname
                          for varname in df_minutes.columns
                          if (varname not in varnames_rain and
                              varname not in varnames_wind)]
        if varnames_other:
            other_dict, index = agg_to_dict(varnames_other,
                                            np.mean)
            values_dict.update(other_dict)
    else:
        values_dict = {varname: np.array(values)
                       for varname, values in
                       df_minutes.to_dict("list").items()}
        index = df_minutes.index

    if not full:
        # return values only up to the first nan
        new_values_dict = {}
        for varname, values in values_dict.items():
            
            try:
                i = np.where(np.isfinite(values))[0][-1]
            except IndexError:
                print("all nans in %s!" % varname)
                i = 0
            new_values_dict[varname] = values[:i + 1]
        values_dict = new_values_dict
    if ('u_' in varpath[0]) or ('dd_' in varpath[0]):
        index = index[::del_t]
    index = index[:len(values_dict[varpath[0]])]

    if 'bp' in _varpath:
        values_dict['bp'] = mxy.norm_pressure(var['p'], var['Ta_2m'])
        # loesche Hilfsvariablen, wenn nicht zusaetzlich gesucht
        for ivar in ['Ta_2m', 'p']:
            if ivar not in _varpath:
                del values_dict[ivar]

    dtimes = index.to_pydatetime()
    return values_dict, dtimes


def read_hdf5_(start, end, varpath, del_t=60, hdf5=lconf.hdf5_filename,
               meta_xls_filename=lconf.meta_xls_filename,
               typ_='_data_raw', full=False):
    r"""
    read selected variables (raw data) from lauchaecker hdf5 file

    This function is outdated; use hdf52df instead.
    As historically most of the webside is based on this function, it is still
    be in use for the webside.

    Parameters
    ----------
    start : datestring
        start date in format "%Y-%m-%dT%H:%M:%S"
    end : datestring
        end date in format "%Y-%m-%dT%H:%M:%S"
    varpath : list ``[]`` of strings
        list of variable names in the hdf5-file
    del_t : int, optional
        timestep in minutes: 1-min-data is averaged to this timestep.
        Default is 60
    hdf5 : string, optional
        path and filename of hdf5-file. Default is lconf.hdf5_filename
    typ_ : ['_data_raw', '_data_processed', '_is_processed', '_flags']
        type of data or flag
    full : bool, optional
        if False, returns the data set up the first nan value,
        if True, return all data from defined start to end
        Default is False

    Returns
    -------
    var : dictionary
        dictionary of np.arrays of the varpath variables
    date : np.array
        np.array of datetime objects

    Note
    ----
    the time in date is the end of the time interval, e. g.: hourly values,
    XXXX-XX-XXT01:00:00 means 00:01:00 - 01:00:00
    BUT: when del_t >= 1440 (daily and more), date gives the begin of
    timestep!!

    Examples
    --------
    >>> start = "2011-09-25T00:00:00"
    >>> end = "2011-09-25T02:00:00"
    >>> lht.read_hdf5(start,end,['rh_2m','Ta_2m'])
    ({'Ta_2m': array([ 10.16566658,  10.00498676], dtype=float32),
      'rh_2m': array([ 99.14710999,  99.58892059], dtype=float32)},
     array([2011-09-25 01:00:00, 2011-09-25 02:00:00], dtype=object))
    """
    print("read_hdf5 called with: ", start, end, del_t, varpath)
    hd = tables.open_file(hdf5, 'r')
    # ##############################
    # uerberpruefe, ob bp (barometric pressure) gesucht wird,
    # dann werden druck und temperatur benoetigt. ergaenzen, falls nicht
    # zusaetzlich gesucht
    if 'bp' in varpath:
        # erstelle zunaechst eine Kopie, damit ausserhalb der Funktion
        # die liste nicht veraendert wird
        _varpath = list(varpath)
        varpath = list(varpath)
        for ivar in ['p', 'Ta_2m']:
            if ivar not in varpath:
                varpath.append(ivar)
        varpath.remove('bp')

    from datetime import timedelta
    dt = timedelta(minutes=1)
    # refts = times.datetimefromisoformat('2009-08-25T13:42:00')
    refts = read_first_timestamp(hdf5_filename=hdf5,
                                 meta_xls_filename=meta_xls_filename
                                 ).replace(" ", "T")
    # Wenn kein Enddatum angegeben ist wird
    if end is None:
        # first get time in utc, then add 1 hour -> no problems with dst (at
        # least i hope so)
        end = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
#       end = end[:-5]+'00:00' # round to last full hour
        end=datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M")
        #stop = times.datetimefromisoformat(stop)
        i_end = stamp2index(end)
        #end = times.datetimefromisoformat(end)
        #i_end = times.timestamp2index(end, dt, refts)
        i_end = i_end + 60  # utc -> cet
    # Wenn Enddatum angegeben ist dann das hier:
    else:
        end = datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M")
        i_end = stamp2index(end, dt, refts)
    # Wenn kein Startdatum angegeben ist wird
    if start is None:
        i_start = i_end - 7 * 1440 - 60
    # Wenn Startdatum angegeben ist dann das hier:
    else:
        start = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M")
        i_start = stamp2index(start, dt, refts)
    # ##############################
    # get data:
    dpath = '/lauchaecker/min_01/data/'
    var = dict.fromkeys(varpath)

    for path in varpath:
        pth = dpath + path + '/' + path + typ_
        va = path
        var[va] = hd.get_node(pth)[i_start:i_end]
        # find last not-nan value
        try:
            ii = np.where(np.isfinite(var[va]))[0][-1]
        except IndexError:
            # all nans!
            print("all nans in %s!" % path)
            ii = 0
        if not full:
            j = len(var[va][:ii + 1]) / del_t * del_t
            var[va] = var[va][:j]
        # average, except wind and rain:
        if ('rr_' not in va) & ('u_' not in va) & ('dd_' not in va):
            var[va] = np.nanmean(var[va].reshape(-1, del_t), axis=1)
        elif 'rr_06' in va:  # Tropfer
            var[va] = np.sum(var[va].reshape(-1, del_t), axis=1) * 0.005
        elif 'rr_07' in va:  # Waage
            var[va] = np.sum(var[va].reshape(-1, del_t), axis=1) * 0.01
        elif 'rr_09' in va:
            var[va] = np.sum(var[va].reshape(-1, del_t), axis=1) * 0.1
        elif 'rr_10' in va:  # pluvio is right per default
            var[va] = np.sum(var[va].reshape(-1, del_t), axis=1)
        elif 'rr_' in va:  # andere Niederschlagsschreiber
            var[va] = np.sum(var[va].reshape(-1, del_t), axis=1) * 0.1

    # date
    if i_start == 0:
        date1 = '2009-08-25T13:42:00'  # for function data_reaches
    elif del_t >= 1440:
        # get first date (begin of timestep)
        date1 = hd.root.lauchaecker.min_01.timestamps[i_start]
    else:
        date1 = hd.root.lauchaecker.min_01.timestamps[
            i_start + del_t]  # get first date (end of timestep)
    # convert to unix timestamp
    # date1 = calendar.timegm(time.strptime(date1, "%Y-%m-%dT%H:%M:%S"))
    try:
        date1 = calendar.timegm(time.strptime(date1, "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        print(hd.root.lauchaecker.min_01.timestamps[i_start:i_start+del_t])
        # calculate based on index
        stamp0 = hd.root.lauchaecker.min_01.timestamps[0]
        date0 = datetime.datetime.strptime(stamp0, "%Y-%m-%dT%H:%M:%S")
        date1 = date0 + i_start * dt
        if del_t < 1440:
            date1 += dt
        date1 = times.datetime2unix(date1)
        print ("No timestamp for index %d, inferred %s" %
               (i_start,
                times.unix2str(date1, "%Y-%m-%dT%H:%M:%S")))
    # produce date array of unix timestamps
    date = np.array([(date1 + i * del_t * 60)
                     for i in range(len(var[varpath[0]]))])
    if ('u_' in varpath[0]) or ('dd_' in varpath[0]):
        date = np.array([(date1 + i * 60)
                         for i in range(len(var[varpath[0]]))])
        date = date.reshape(-1, del_t)[:, 0]
    date = times.unix2datetime(date)
    hd.close()

    # berechne bp (barometric pressure) falls gesucht
    try:
        if 'bp' in _varpath:
            var['bp'] = mxy.norm_pressure(var['p'], var['Ta_2m'])
            # loesche Hilfsvariablen, wenn nicht zusaetzlich gesucht
            for ivar in ['Ta_2m', 'p']:
                if ivar not in _varpath:
                    del var[ivar]
                    # var.pop(ivar)
            varpath = _varpath
    except:
        pass

    return var, date


def hdf52txt(start, end, varpath, outfile,
             hdf5=lconf.hdf5_filename, del_t=60,
             typ_='_data_raw'):
    r"""
    export selected variables from lauchaecker hdf5 to txtfile

    Parameters
    ----------
    start : string
       start date in format "%Y-%m-%dT%H:%M:%S"
    end : string
       end date in format "%Y-%m-%dT%H:%M:%S"
    varpath : list of str
        list of variable paths in the hdf5-file, without
        '/lauchaecker/min_01/data/', e.g. 'Ta_2m'
    outfile : filename
        path and filename of txtfile to save data in
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
    read_hdf5 : read selected variables (raw data) from lauchaecker hdf5 file

    Notes
    -----
    Remarks from the murky bottom of the "I don't know any Python" gene pool:
        "List" means [] around the parameters and the goddamn outfile needs an
        "r" before the path.
        E.g:
        hdf52txt(start='2011-05-01T00:00:00', end='2011-06-01T00:00:00',
        varpath=['Ta_2m','Ta_18m'], del_t=60, outfile=r"d:\temp\00test.txt")
    """
    var, date = read_hdf5(start, end, varpath, del_t=del_t, hdf5=hdf5,
                          typ_=typ_)
    # wind averaging:
    if ('u_19m' and 'dd_19m' in var) and del_t!=1:
        u, v = angle2component(var['dd_19m'], var['u_19m'])  # wind 2 uv
        u, v = avrwind(u, v, 60, 60 * del_t)[:2]
        var['dd_19m'], var['u_19m'] = component2angle(u, v)
    if ('u_2m' and 'dd_2m' in var) and del_t!=1:
        u, v = angle2component(var['dd_2m'], var['u_2m'])  # wind 2 uv
        u, v = avrwind(u, v, 60, 60 * del_t)[:2]
        var['dd_2m'], var['u_2m'] = component2angle(u, v)
    # save to txtfile:
    outfile = open(outfile, 'w')
    outfile.write('date')
    # dictionary has no inherent order, so we use sorted (--> alphanumeric),
    # just to be sure
    for va in sorted(var):
        outfile.write('\t%s' % va.split('/')[-1])
    outfile.write('\n')
    for i in range(len(var[varpath[0]])):
        outfile.write('%s' % date[i])
        for va in sorted(var):
            outfile.write('\t%7.2f' % var[va][i])
        outfile.write('\n')
    outfile.close()


def data_reaches(varpath='all',
                 hdf5=lconf.hdf5_filename,
                 typ_='_data_raw',
                 meta_xls_filename=lconf.meta_xls_filename,
                 ):
    r"""finds and plots times with existing raw data of selected variables

    Parameters
    ----------
    varpath : list ``[]`` of strings or 'all', optional
        list of variable names in the hdf5-file, default is 'all': use all
    hdf5 : string, optional
        path and filename of hdf5-file. Default is
        lconf.hdf5_filename
    meta_xls_filename: str, optional
        Where the metainformation of the hdf5 file is stored.

    Returns
    -------
    None

    """
    if varpath == 'all':
        try:
            varpath = np.unique(read_metadata(meta_xls_filename)['varname'])
            varpath = list(varpath .astype('str'))
            for ivar in ['CaseTemp', 'timestamps']:
                if ivar in varpath:
                    varpath.remove(ivar)
        except Exception:
            with open_hdf5(hdf5) as h5f:
                groups = h5f.walkGroups("/lauchaecker/min_01/data")
                varpath = [path_basename(group._v_pathname) for group in groups][1:]
    end = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    var, date = read_hdf5('2009-08-26T00:01:00', end, varpath, del_t=1,
                          hdf5=hdf5, typ_=typ_)
    plt.figure(figsize=(16, 1 * len(var) + 1))
    if len(var) > 4:
        plt.subplots_adjust(hspace=0, left=0.01, right=0.88, top=0.95,
                            bottom=0.05)
    else:
        plt.subplots_adjust(hspace=0, left=0.01, right=0.88, top=0.9,
                            bottom=0.1)
    i = 0
    for va in sorted(var):
        i = i + 1
        if i == 1:
            plt1 = plt.subplot(len(var), 1, i)
            plt.title('data in hdf5')
        else:
            plt1 = plt.subplot(len(var), 1, i, sharex=plt1)
        ii = np.where(np.isfinite(var[va]))[0]  # find not-nan values
        date_ = date[ii]
        ones = np.ones(len(ii))
        print(va, ':', len(ii), 'entries in hdf5')
        delta_i = ii[1:] - ii[:-1]  # find gaps
        jj = np.where(delta_i > 1)[0]
        if len(jj) > 0:
            plt.plot(date_[:jj[0] + 1], ones[:jj[0] + 1], 'b', linewidth=3)
            for j in range(0, len(jj) - 2):
                plt.plot(date_[jj[j] + 1:jj[j + 1] + 1],
                         ones[jj[j] + 1:jj[j + 1] + 1], 'b', linewidth=3)
            plt.plot(date_[jj[-1] + 1:], ones[jj[-1] + 1:], 'b',
                     linewidth=3, label=va)
            plt.plot(date_[jj], ones[jj], 'r|', linewidth=0, markersize=12)
            plt.plot(date_[jj + 1], ones[jj + 1], 'r|', linewidth=0,
                     markersize=12)
        else:
            plt.plot(date_, ones, 'b', linewidth=3, label=va)
        # plt.scatter(date_,ones,2,'m',linewidth=0)
        plt.scatter((date[0], date[-1]), (1, 1), 1, 'w', linewidth=0)
        plt.grid(True)
        plt.legend(loc='center left', bbox_to_anchor=(1., 0.5))
        plt.yticks((1,), ('',))

    plt.show()

