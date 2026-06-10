"""Lauchaecker HDF5 tools: creation."""

from ._shared import *


__all__ = ['create_hdf5', 'logger2hdf5']


def create_hdf5(hdf5_filename='fhbgknkbm,d.h5',
                meta_xls_filename=lconf.meta_xls_filename,
                missdata_filename=lconf.missdata_filename,
                logger_dir=lconf.logger_dir,
                ignore=("*.backup", "*.bak", "*last_date.dat"),
                recursive=True, verbose=True, overwrite=True,
                log_last_filename=lconf.log_last_filename):
    """Creates or updates the lauchaecker hdf5-file using the descriptions
    from the `meta_xls_filename` and fills it with all available
    logger-files.

    Parameter
    ---------
    hdf5_filename : str, optional, default = lconf.hdf5_filename
        Filename of the hdf5-file
    meta_xls_filename : str, optional, default = lconf.meta_xls_filename
        Filename of the excel file containing all necesarry meta-data.
    missdata_filename : str, optional, default = lconf.missdata_filename
        filename of a .csv file
        if given, writes a file with timestamps,
        else  print and return the timestamps
    logger_dir : str, optional
        Where to look for the logger files.
    ignore : sequence of str, optional
        Files matching these glob patterns are not read.
    recursive : boolean, optional
        If True include subfolders of `logger_dir`.
    verbose : boolean, optional
        Be verbose.
    log_last_filename : str, default = lconf.log_last_filename
        if a file is given, save the last timestamp in the file
    """
    if os.path.exists(hdf5_filename):
        raise Exception('Warning, HDF5-file already exists. Please delete '
                        'the file manually and restart create_hdf5()\n'
                        '(%s)' % hdf5_filename)
    metadata = read_metadata(meta_xls_filename)
    _set_hdf_structure(metadata, hdf5_filename, verbose=verbose)
    find = my.recursive_glob if recursive else glob.glob
    file_patterns = set(my.flatten(metadata.files))
    for file_pattern in file_patterns:
        pattern = "%s*" % file_pattern
        logger_files = find(os.path.join(logger_dir, pattern))
        for ig_pattern in ignore:
            ig_files = glob.fnmatch.filter(logger_files, ig_pattern)
            logger_files = list(set(logger_files) - set(ig_files))
        # prefer large files
        logger_files = sorted(logger_files, key=os.path.getsize,
                              reverse=(not overwrite))
        for logger_file in logger_files:
            print("Reading %s" % logger_file)
            # tables does not eat unicode
            logger_file = logger_file.encode(errors="ignore")
            logger2hdf5(logger_file, hdf5_filename=hdf5_filename,
                        metadata=metadata, verbose=verbose,
                        overwrite=overwrite,
                        meta_xls_filename=meta_xls_filename)
    _hdf5_integrity(hdf5_filename, metadata=metadata, verbose=verbose)
    read_missing_data(hdf5_filename=hdf5_filename,
                      missdata_filename=missdata_filename)
    if log_last_filename:
        last_ts = read_last_timestamp(hdf5_filename, meta_xls_filename)
        with open(log_last_filename, 'w') as f_log:
            f_log.write('Last update:\n')
            f_log.write(last_ts.replace(' ', 'T'))


def logger2hdf5(datafile='CR3000_data_1min.dat',
                hdf5_filename=lconf.hdf5_filename,
                meta_xls_filename=lconf.meta_xls_filename,
                metadata=None, verbose=True, overwrite=True,
                log_last_filename=''):
    r"""Transfers the values from datalogger file (1 minute values) into hdf5
    file

    This function tries to achieve the same thing as the older
    data2hdf5, but uses an xls-file for configuration. Additionally,
    _set_hdf_structure is used to ensure that changes in the meta_xls_filename
    are reflected in the hdf5-file (e.g. changes in instrumentation).
    It also uses pandas and might be faster.


    Parameters
    ----------
    datafile : string, optional
        path and filename of data text file. Default is
        ``r'P:\wetterstation\data\CR3000_data_1min.dat'``
        If it is a file-like object, a filename has to be given with the
        `filename` parameter
    hdf5 : string, optional
        path and filename of hdf5-file. Default is
        ``lconf.hdf5_filename``
    meta_xls_filename : string, optional
        path and filename of configuration file. Default is
        ``r'P:\wetterstation\data\config_2.txt'``
    log_last_filename : str, default = ''
        if a path is given, only data newer than this time stamp are updated
        updates the path at the end of the hdf5 update

    Returns
    -------
    None

    """
    if metadata is None:
        metadata = read_metadata(meta_xls_filename)

    try:
        header = _parse_header(datafile, metadata, verbose=verbose)
    except ValueError as ex:
        warnings.warn(str(ex))
        return

    _set_hdf_structure(metadata, filename=hdf5_filename)
    data = pd.read_csv(datafile, header=1, skiprows=(2, 3),
                       sep=header.sep, index_col=0,
                       usecols=header.usecols, names=header.names,
                       parse_dates=True, na_values=("NAN", "NaN", ""),
                       error_bad_lines=False, warn_bad_lines=verbose,
                       dayfirst=header.dayfirst)
    try:
        # we cannot rely on the file to have values at every minute
        # TODO if the time discretization in the logger file is
        # different than 1 minute, this resampling step has to
        # aggregate rain differently!
        if (distutils.version.LooseVersion(pd.__version__) <
                (distutils.version.LooseVersion('0.18'))):
            _data = data.resample("1min")
        else:
            _data = data.resample("1min").mean()
        # find dates where no data is available. These dates are set to empty
        # strings in a few lines later in the code,
        # such that _hdf5_integrity is able to flag them
        # as missing data
        date_miss = list(set(_data.index) - set(data.index))
        data = _data

    except pd.core.groupby.DataError:
        warnings.warn("Could not aggregate! No data?")
        return
    # awkward: we first parse the dates in read_csv, resample, then
    # convert to strings. there might be a quicker way
    data["TIMESTAMP"] = data.index.format()
    # all the other functions rely on the "T" between date and time.
    data["TIMESTAMP"] = data.TIMESTAMP.str.replace(" ", "T")
    # set strings of all missing data to empty strings
    # data.ix[date_miss, "TIMESTAMP"] = ''
    data.loc[date_miss, "TIMESTAMP"] = ''
    

    # cut the raw data using the last time stamp such that only new data is
    # filled into the hdf5 file
    if log_last_filename:
        with open(log_last_filename, 'r') as f_log:
            f_log.readline()  # header
            log_last = f_log.readline()
        hdf5_last = read_last_timestamp(
            hdf5_filename, meta_xls_filename=meta_xls_filename)
        if log_last.replace("T", " ") != hdf5_last:
            print('WARNING, Last time stamps in hdf5 and log are not identical!')
        # check if the second to last line is already in the hdf5
        # if data.ix[-2, "TIMESTAMP"] == hdf5_last.replace(" ", "T"):
        if data.iloc[-2].loc["TIMESTAMP"] == hdf5_last.replace(" ", "T"):
            print('HDF5 is up to date, nothing changed')
            return
        idx_last = np.where(data.index == log_last)[0][0]
        # use only data up to the second to last line, to avoid issues in cases
        # where the line was not fully written
        # data = data.ix[idx_last + 1:-1, :]
        data = data.iloc[idx_last + 1:-1, :]

    # finding the right slice using thomas' lhglib.contrib.times-nomenclature
    refts = metadata.startdate.dropna().min()
    period = timedelta(minutes=1)

    def my_index(stamp):
        return times.timestamp2index(stamp, period, refts)

    try:
        start_i = my_index(data.index[0])
    except IndexError as ex:
        print("No timestamps in ", datafile)
        print(str(ex))
        return

    # the two hardest problems in computer science are variable
    # naming, cache invalidation and off-by-one errors
    stop_i = my_index(data.index[-1]) + 1

    with open_hdf5(hdf5_filename, "r+") as h5f:
        try:
            logfiles = h5f.get_node("/loggerfiles")
        except tables.NoSuchNodeError:
            raise ValueError("Could not find /loggerfiles. "
                             "Something is seriously wrong.")

        for name in header.names + header.missing_names + header.foreign_names:
            # path = metadata.ix[name].path
            path = metadata.loc[name].path
            if name == "TIMESTAMP":
                nodename = None
                nodename_logfile = None

            else:
                # nodename = metadata.ix[name].varname + "_data_raw"
                nodename = metadata.loc[name].varname + "_data_raw"
                # nodename_logfile = metadata.ix[name].varname + "_logfile"
                nodename_logfile = metadata.loc[name].varname + "_logfile"
                
            try:
                # earray: enlargeable array, this one for the values
                earray = h5f.get_node(path, nodename)
                earray_logfile = h5f.get_node(path, nodename_logfile)
            except tables.NoSuchNodeError:
                warnings.warn("Could not find node '%s/%s'!" %
                              (path, nodename))
                continue
            # first, it must be ensured that the earrays have the right lengths
            if stop_i > len(earray):
                earray.append(np.full(stop_i - len(earray),
                                      earray.atom.dflt,
                                      dtype=earray.atom.dtype))
                if nodename_logfile:
                    earray_logfile.append(np.full(stop_i - len(earray_logfile),
                                                  earray_logfile.atom.dflt,
                                                  dtype=earray.atom.dtype))
            if name in header.foreign_names:
                # the append made sure that we have the right length
                # even for foreign variables. that is necessary, to
                # keep the hdf5 file sane. but now we have to stop,
                # before the alternative (foreign) overwrites possibly
                # good values with nans
                h5f.flush()
                continue
            if name in header.missing_names:
                # all arrays have to have the same shape, so we also
                # have to make sure that the variables not encountered in this
                # logger file are filled up with the right amount of nans
                values = earray.atom.dflt
            else:
                values = data[name].values
                if nodename_logfile:
                    try:
                        log_index = list(logfiles[:]).index(datafile)
                    except ValueError:
                        log_index = len(logfiles[:])
                        logfiles.append([datafile])

            if not overwrite and name != "TIMESTAMP":
                written_values = date_miss[start_i:stop_i]
                finite_mask = ~np.isnan(written_values)
                if np.any(finite_mask):
                    if np.all(np.isclose(written_values[finite_mask],
                                         values[finite_mask])):
                        continue
                    warnings.warn("Overwrites are not allowed! "
                                  "variable: %s, %s to %s" %
                                  (name, data.index[0], data.index[-1]))
                    finite_indices = np.where(finite_mask)[0]
                    start_fin = start_i + np.min(finite_indices)
                    stop_fin = start_i + np.max(finite_indices)
                    log_indices = set(earray_logfile[start_fin:stop_fin])
                    written_logfiles = [logfiles[log_i]
                                        for log_i in log_indices]
                    warnings.warn("Written values came from: %s" %
                                  ", ".join(written_logfiles))

            earray[start_i:stop_i] = values

            if nodename_logfile:
                earray_logfile[start_i:stop_i] = log_index
            h5f.flush()

            if log_last_filename:
                with open(log_last_filename, 'w') as f_log:
                    f_log.write('Last update:\n')
                    f_log.write(data.index[-1].isoformat())

