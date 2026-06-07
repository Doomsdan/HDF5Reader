# -*- coding: utf-8 -*-
r"""
Tools for the Lauchaecker hdf5 file (:mod:`meteo.lauchaecker_hdf5_tools`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This module was written to work with the data of the
lauchaecker meteo station, stored in the file
lconf.hdf5_filename

It contains functions to get the data in and out of the file, and some plotting
routines to produce pre-defined plots such as meteogram and pluviogram.


   create_hdf5
   logger2hdf5
   hdf52df
   plot_logger_data_reaches
   compare_year
   data2hdf5
   data_reaches
   evapo_from_hdf5
   evapo_plot
   hdf52txt
   hdf5_2_meteogram
   hdf5_2_pluviogram
   hdf5_2_soilplot
   kenntage
   read_hdf5
"""
import matplotlib
matplotlib.use("Agg")

# import a lot of tools that are or may be of use (but importing is slow)
import os
import calendar
import time
from datetime import timedelta
import datetime
from collections import namedtuple
import warnings
import glob
from contextlib import closing
import tables
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib.dates import num2date
import pandas as pd
import distutils
import times
# enthaelt div. Funktionen zur Be- und Umrechung von Meteodaten (-> Magda)
import meteox2y as mxy
import lauchaecker_config as lconf
# Funktionen zur Mittelung von Windaten (-> Raphael, Dirk)
from avrwind import (angle2component, avrwind, component2angle)
import dirks_globals as my


def open_hdf5(x, *arg, **kw):
    """this enables using the with statement when opening an hdf5 file.
    """
    return closing(tables.open_file(x, *arg, **kw))


def path_dirname(x):
    """os.path.dirname analogue"""
    return tables.path.split_path(x)[0]


def path_basename(x):
    """os.path.basename analogue"""
    return tables.path.split_path(x)[1]


def create_hdf5(hdf5_filename=lconf.hdf5_filename,
                meta_xls_filename=lconf.meta_xls_filename,
                missdata_filename=lconf.missdata_filename,
                logger_dir=lconf.logger_dir,
                ignore=("*.backup", "*.bak", "*last_date.dat"),
                recursive=True, verbose=True, overwrite=False,
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
        message = ('Warning, HDF5-file already exists. Please delete '
                   'the file manually and restart create_hdf5()\n'
                   '(%s)' % hdf5_filename)
        if overwrite:
            warnings.warn(message)
        else:
            raise Exception(message)
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


def read_metadata(meta_xls_filename=lconf.meta_xls_filename):
    """Reads the `meta_xls_filename` and returns a cleaned pandas DataFrame.

    We expect quite a number of things from the xls file:
    - all information is in the first sheet
    - the presence of the following cells in the first row:
      "Variablenname", "Variablenname(n)",  "Aufzeichnungen"
      (with sub-columns "ab" and "bis"),  "Beschreibung", "HDF5 Pfad und Name"
    - rows that contain "Dateien: " will be parsed for starting patterns of
      logger file names
    - variables that have a non-empty path will be included in the hdf5 file.
    - empty "ab" cells are interpreted as the beginning of records.
    - empty "bis" cells are interpreted as the end of records.
    """
    # sheetname=0 for backward compatibility1
    metadata = pd.read_excel(meta_xls_filename, sheet_name=0)

    # in which logger file do we have to look for what?
    # we look for a cell with a comma-separated list of filenames
    metadata["merged"] = [";".join(str(col) if pd.notnull(col) else ";"
                                    for col in row[1].tolist())
                          for row in metadata.iterrows()]
    files = metadata.merged.str.extract(r"Dateien\: ([^;]*)", expand=False)
    files = files.str.split(",")
    files = files.fillna(False)
    # the aim is to have an empty list as default value
    files_ = last_valid, = [[]]
    for i in range(1, len(files)):
        if files[i]:
            last_valid = [fi.strip() for fi in files[i]]
        files_.append(last_valid)
    metadata["files"] = files_

    cols = {u"Variablenname in h5 Datei": "varname",
            u"Variablenname(n) logger": "logname",
            u"Aufzeichnungen ab": "startdate",
            u"bis": "enddate",
            u"Beschreibung": "description_units",
            u"HDF5 Pfad und Name": "path",
            u"Konversion [multip. x]": "conversion_factor",
            u"files": "files"}
    # merge second row to column names, so that we get the right
    # columns more reliably
    # metadata.ix[0] = metadata.ix[0].fillna("")
    metadata.iloc[0] = metadata.iloc[0].fillna("")
    metadata.columns = [" ".join(["" if col.startswith("Unnamed") else col,
                                  rowcol if rowcol else ""]).strip()
                        for col, rowcol in zip(metadata.columns,
                                               # metadata.ix[0]
                                               metadata.iloc[0]
                                               )]
    metadata = metadata.rename(columns=cols)
    # we also loose the extended header row
    # metadata = metadata.ix[1:, cols.values()]
    metadata = metadata.loc[:, cols.values()].iloc[1:]
    # these two columns hold more information on the columns
    # metadata = metadata.iloc[2:]
    # rows without h5-path are not of interest here
    metadata = metadata.dropna(subset=("path",))

    # extract the varname from the path if vacant (happens when a
    # logger variable is renamed)
    mask_noname = pd.isnull(metadata.varname)

    def naming(x):
        return path_basename(x)[:-len("_data_raw")]

    metadata.varname[mask_noname] = metadata.path[mask_noname].apply(naming)
    # the path also contains the data_raw-array. this information is
    # also present in the varname
    mask_raw = metadata.path.str.endswith("_data_raw")
    metadata.path[mask_raw] = metadata.path[mask_raw].apply(path_dirname)

    # split description and units into two columns
    # you have to write the regex by yourself if you want to understand it! ;)
    pattern = r"(?P<description>[^[]*)\[?(?P<units>[^]]*)\]?"
    dscr_units = metadata.description_units.str.extract(pattern, expand=False)
    metadata = metadata.join(dscr_units)
    metadata = metadata.drop("description_units", 1)
    metadata.description = metadata.description.str.strip()

    # find alternative lognames (renamed variables)
    varname_appearence = metadata.groupby("varname").groups
    alternatives = []
    for row_i, row in metadata.iterrows():
        # we do a 'slice-copy' here, because the remove below would
        # otherwise mess with the groups-dictionary values
        alt_row_ii = list(varname_appearence[row.varname][:])
        alt_row_ii.remove(row_i)
        # alternatives.append([metadata.ix[alt_row_i, "logname"]
        #                      for alt_row_i in alt_row_ii])
        alternatives.append([metadata.loc[alt_row_i]["logname"]
                             for alt_row_i in alt_row_ii])
    metadata["alt_lognames"] = alternatives

    # reuse information of alternatives if it is missing
    for row_i, row in metadata.iterrows():
        mask_cur = row.isnull()
        for row_i_alt in varname_appearence[row.varname][:]:
            # mask_alt = ~metadata.ix[row_i_alt].isnull()
            mask_alt = ~metadata.loc[row_i_alt].isnull()
            mask = mask_cur & mask_alt
            # metadata.ix[row_i, mask] = metadata.ix[row_i_alt][mask]
            metadata.loc[row_i][mask] = metadata.loc[row_i_alt][mask]

    # column-specific fillings for nans
    metadata.conversion_factor = metadata.conversion_factor.fillna(1.)
    metadata.startdate = metadata.startdate.fillna(pd.NaT)
    metadata.enddate = metadata.enddate.fillna(pd.NaT)
    return metadata


def read_missing_data(hdf5_filename=lconf.hdf5_filename,
                      missdata_filename=lconf.missdata_filename):
    """ Read the timestamps for which no data is available at all

    Parameter
    ---------
    hdf5_filename : str, optional
        hdf5_filename of the hdf5-file
    missdata_filename : str, optional, default = lconf.missdata_filename
        filename of a .csv file
        if given, writes a file with timestamps, otherwise prints and
        return the timestamps

    Return
    ------
    timestamp_miss : array of str
        if missdata_filename is not given, returns the timestamps

    """
    with open_hdf5(hdf5_filename, "r+") as h5f:
        timestamp_miss = h5f.get_node("/lauchaecker/min_01/timestamps_miss")[:]
        if not missdata_filename:
            print('Missing time stamps [tstart, tend]')
            print(timestamp_miss)
            return timestamp_miss
        else:
            with open(missdata_filename, "w") as outfile:
                outfile.write('tstart;tend\n')
                np.savetxt(outfile, timestamp_miss, fmt='%s', delimiter=';')


def read_last_timestamp(hdf5_filename, meta_xls_filename=lconf.meta_xls_filename):
    """ Find last timestamp in the hdf5 file

    We rely on the metadata to find the timestamp path

    Parameter
    ---------
    hdf5_filename : str
    server : str
        E.g. "http://localhost:3333"

    Returns
    -------
        end : dtr
            timestamp of latest data
    """
    return _read_nth_timestamp(-1, hdf5_filename, meta_xls_filename)


def read_first_timestamp(hdf5_filename, meta_xls_filename=lconf.meta_xls_filename):
    """ Find last timestamp in the hdf5 file

    We rely on the metadata to find the timestamp path

    Parameter
    ---------
    hdf5_filename : str
    server : str
        E.g. "http://localhost:3333"

    Returns
    -------
        end : dtr
            timestamp of first data
    """
    return _read_nth_timestamp(0, hdf5_filename, meta_xls_filename)


def _hdf5_integrity(hdf5_filename, metadata, path="/lauchaecker/min_01",
                    verbose=False):
    """Check and repair (if possible) the hdf5 file."""
    refts = metadata.startdate.dropna().min()
    period = timedelta(minutes=1)
    with open_hdf5(hdf5_filename, "r+") as h5f:
        # make sure that there are no empty timestamps
        time_node = h5f.get_node(tables.path.join_path(path, "timestamps"))
        no_time_toulouse = time_node[:] == ""
        for start_i, stop_i in my.gaps(no_time_toulouse):
            start = times.index2timestamp(start_i, period, refts)
            stop = times.index2timestamp(stop_i, period, refts)
            dti = pd.date_range(start, stop, freq="1min")
            timestamps = pd.Series(dti.format()).str.replace(" ", "T")
            time_node[start_i:stop_i + 1] = timestamps.tolist()
            if verbose:
                print("Missing data from %s to %s" % (start, stop))
            # save missing time periods in hdf5-file
            data_miss = np.array((start, stop))
            earray = h5f.get_node(
                tables.path.join_path(path, "timestamps_miss"))
            earray.append(data_miss[np.newaxis, :])
            h5f.flush()


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
        start = str2datetime(start)
    if type(stop) == str:
        stop = str2datetime(stop)

    meta = read_metadata(meta_xls_filename)

    variables = {}
    with open_hdf5(hdf5_filename, "r") as h5f:
        time_node = h5f.get_node(tables.path.join_path(path, "timestamps"))
        total_timesteps = len(time_node)
        refts = time_node[0]
        period = timedelta(minutes=1)

        def stamp2index(stamp):
            index = times.timestamp2index(stamp, period, refts)
            # wrap around to indices that actually exist
            return min(total_timesteps - 1, max(0, index))

        # Wenn kein Enddatum angegeben ist wird
        if stop is None:
            # first get time in utc, then add 1 hour -> no problems
            # with dst (at least i hope so)
            stop = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
            stop = times.datetimefromisoformat(stop)
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
            start_i = stamp2index(start)
        start = times.index2timestamp(start_i, period, refts)

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
            if convert:
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
        start = str2datetime(start)
    if isinstance(end, str):
        end = str2datetime(end)

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

        # average other
        varnames_other = [varname
                          for varname in df_minutes.columns
                          if (varname not in varnames_rain and
                              varname not in varnames_wind)]
        if varnames_other:
            other_dict, index = agg_to_dict(varnames_other,
                                            np.mean)
            values_dict.update(other_dict)

        # if we are only asked for wind, we need to take care of the
        # index ourself.
        if varnames_wind and not varnames_rain and not varnames_other:
            index = df_minutes.resample("%sT" % del_t).first().index
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

    # if ('u_' in varpath[0]) or ('dd_' in varpath[0]):
    #     index = index[::del_t]
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
#        end = end[:-5]+'00:00' # round to last full hour
        end = times.datetimefromisoformat(end)
        i_end = times.timestamp2index(end, dt, refts)
        i_end = i_end + 60  # utc -> cet
    # Wenn Enddatum angegeben ist dann das hier:
    else:
        end = times.datetimefromisoformat(end)
        i_end = times.timestamp2index(end, dt, refts)
    # Wenn kein Startdatum angegeben ist wird
    if start is None:
        i_start = i_end - 7 * 1440 - 60
    # Wenn Startdatum angegeben ist dann das hier:
    else:
        start = times.datetimefromisoformat(start)
        i_start = times.timestamp2index(start, dt, refts)
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


def _remove_quotes(str_):
    # triple-quoted double and single quote
    quotes = """"''"""
    return str_.lstrip(quotes).rstrip(quotes)


def _loggerfile_reaches(loggerfilename, sep=",", col=0):
    """Returns datetime representation of first and last date in a CR3000
    file.

    Raises
    ------
    lhglib.contrib.times.TimeParseError
        If time string could not be parsed.
    """
    def line2dt(line):
        stamp = _remove_quotes(line.split(sep)[col])
        try:
            return times.str2datetime(stamp, d_format="%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                return times.str2datetime(stamp, d_format="%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                try:
                    return times.str2datetime(stamp, d_format="%d/%m/%Y %H:%M")
                except ValueError:
                    return times.str2datetime(stamp, d_format="%d.%m.%Y %H:%M")
    try:
        if isinstance(loggerfilename, str):
            fi = open(loggerfilename)
        else:
            fi = loggerfilename
        # skip over the header
        for _ in range(5):
            try:
                first_line = fi.next()
            except StopIteration:
                continue
        last_line = my.last_lines(loggerfilename, 1)
    finally:
        fi.close()
    try:
        return line2dt(first_line), line2dt(last_line)
    except ValueError:
        raise times.TimeParseError


def _set_hdf_structure(metadata, filename=lconf.hdf5_filename, verbose=True):
    """Ensure that all groups and arrays as specified in metadata are
    present in the hdf5 file.

    Parameter
    ---------
    metadata : pandas DataFrame or str
        If a str is passed, it is passed as the `meta_xls_filename` to
        `read_metadata`.
    filename : str
        Filepath of the hdf5-file
    verbose : boolean, optional
    """
    if type(metadata) is str:
        metadata = read_metadata(meta_xls_filename=metadata)

    filter_ = tables.Filters(complevel=2, complib="zlib")
    h5f = tables.open_file(filename,
                           "r+" if os.path.exists(filename) else "w",
                           filters=filter_)

    for _, row in metadata.iterrows():
        # first ensure the group are there
        try:
            group_data_varname = h5f.get_node(row.path)
        except tables.NoSuchNodeError:
            try:
                where = path_dirname(row.path)
                name = row.varname
                if name == "timestamps":
                    # only create the parent!
                    name = path_basename(where)
                    where = path_dirname(where)
                if verbose:
                    print("Creating group %s/%s" % (where, name))
                group_data_varname = \
                    h5f.create_group(where, name, row.logname, filters=filter_,
                                     createparents=True)
                h5f.set_node_attr(group_data_varname, "Units", row.units)
                h5f.set_node_attr(group_data_varname, "Description",
                                  row.description)
            except (tables.HDF5ExtError, tables.NodeError):
                print("Could not create group %s/%s" % (where, name))

        # we store the paths of logger-files in here
        try:
            h5f.create_earray(
                name="loggerfiles", where="/",
                title="Pathname of the logger files used as data source",
                shape=(0,), filters=filter_,
                atom=tables.StringAtom(1024, dflt=""),
                expectedrows=100)
        except tables.NodeError:
            pass

        # create all the arrays on top of the group
        defaults = dict(where=group_data_varname, shape=(0,),
                        title=row.logname, filters=filter_,
                        expectedrows=60 * 24 * 366 * 10)

        if row.varname == "timestamps":
            try:
                defaults["where"] = path_dirname(row.path)
                # nat = np.datetime64("nat")
                array = h5f.create_earray(name=row.varname,
                                          atom=tables.StringAtom(19, dflt=""),
                                          # atom=tables.Int64Atom(dflt=nat),
                                          **defaults)
                h5f.set_node_attr(array, "Units", row.units)
                h5f.set_node_attr(array, "Description", row.description)
                array = h5f.create_earray(name=row.varname + '_miss',
                                          atom=tables.StringAtom(19, dflt=""),
                                          where=group_data_varname,
                                          shape=((0, 2)),
                                          title='Missing data',
                                          filters=filter_,
                                          expectedrows=100)
                h5f.set_node_attr(array, "Description",
                                  '[Start_date, End_date]')
            except tables.NodeError:
                pass
            continue

        try:
            array = h5f.create_earray(name=row.varname + "_data_raw",
                                      atom=tables.Float32Atom(dflt=np.nan),
                                      **defaults)
            h5f.set_node_attr(array, "Units", row.units)
            h5f.set_node_attr(array, "Description", row.description)
        except tables.NodeError:
            pass

        try:
            h5f.create_earray(name=row.varname + "_flags",
                              atom=tables.UIntAtom(dflt=0),
                              **defaults)
        except tables.NodeError:
            pass

        try:
            h5f.create_earray(name=row.varname + "_is_processed",
                              atom=tables.BoolAtom(dflt=False),
                              **defaults)
        except tables.NodeError:
            pass

        try:
            h5f.create_earray(name=row.varname + "_logfile",
                              atom=tables.IntAtom(dflt=-1),
                              **defaults)
        except tables.NodeError:
            pass

    h5f.close()


def _parse_header(datafile, metadata, sep_possibilities=",\t", verbose=False):
    """Internal function to be called from logger2hdf5.

    Reads the header of a logger file and decides based on what is
    there and what is configured to be read what pandas should parse
    later.

    Returns
    -------
    header : namedtuple
        with elements: "usecols", "names", "missing_names", "foreign_names",
        "sep"

    Exceptions
    ----------
    Raises ValueError if no variables that should be read are in this file.
    """
    # we first make sure that everything we expect (configured in the
    # meta_xls_filename file) is present in the logger files. this requires a bit
    # of string wrangling
    lognames = metadata.logname.tolist()
    Header = namedtuple("Header", ("usecols", "names", "missing_names",
                                   "foreign_names", "sep", "dayfirst"))

    with open(datafile) as file_:
        # we  expect the header to be in the second row, but check if
        # the data is in 'dayfirst' timestamp convention
        line = file_.next()
        if line.split()[-1] == 'dayfirst':
            dayfirst = True
        else:
            dayfirst = False
        # the separator possibility that produces the most columns wins
        sep_ncols = {len(line.split(sep_pos)): sep_pos
                     for sep_pos in sep_possibilities}
        max_ncols = max(sep_ncols.keys())
        if max_ncols == 1:
            warnings.warn("Could not determine separator!")
        sep = sep_ncols[max_ncols]
        header = [_remove_quotes(col.strip())
                  for col in file_.next().split(sep)]
    start, end = _loggerfile_reaches(datafile, sep, header.index("TIMESTAMP"))
    # arrays for missing_names will be filled with nans later
    # foreign names are variables found in other logger files. we have
    # to track them, so we can keep the lengths of the corresponding
    # hdf5-arrays in sync.
    usecols, names, missing_names, foreign_names = [], [], [], []
    # makes the access based on logname more convenient
    metadata.index = metadata.logname
    # is the logname not in any of the alternative lognames?

    def log_not_in_alt(log):
        return np.all([alt_name not in header
                  for alt_name in metadata.loc[log].alt_lognames])
        # return np.all([alt_name not in header
        #           for alt_name in metadata.ix[log].alt_lognames])
        # should we look for this variables in the current file at all?

    def file_match_single(fi, fi_pattern):
        return glob.fnmatch.fnmatch(os.path.basename(
            (fi.decode("utf-8"))), fi_pattern)

    def file_match(fi, log):
        # is it the right time for this logname?
        # return np.any([file_match_single(fi, fi_pattern)
        #           for fi_pattern in metadata.ix[log].files])
        return np.any([file_match_single(fi, fi_pattern)
                  for fi_pattern in metadata.loc[log].files])

    def time_for_log(log, meta_start, meta_end):
        return ((pd.isnull(meta_start) or start >= meta_start) and
           (pd.isnull(meta_end) or end <= meta_end))
    
    for logname in lognames:
        if ((str(logname) not in header) and
                log_not_in_alt(logname) and
                file_match(datafile, logname) and
                # time_for_log(logname, metadata.ix[logname].startdate,
                #              metadata.ix[logname].enddate)
                time_for_log(logname,
                             metadata.loc[logname].startdate,
                             metadata.loc[logname].enddate)
            ):
            if verbose:
                # we sort to hack our way around having double warning
                # messages
                # all_names = \
                #     sorted([logname] + metadata.ix[logname].alt_lognames)
                all_names = sorted([logname] +
                                   metadata.loc[logname].alt_lognames)
                all_names = " or ".join(all_names)
                warnings.warn("Could not find %s in %s!" %
                              (all_names, datafile))
            missing_names += [logname]
        elif logname in header and file_match(datafile, logname):
            # yes, there it happens that there is a variable in the
            # file but we are supposed to get it from another file...
            names += [logname]
            usecols += [header.index(logname)]
        elif not file_match(datafile, logname):
            foreign_names += [logname]
        else:
            foreign_names += [logname]
    if not names:
        raise ValueError("Nothing to read in this file!")

    if "TIMESTAMP" not in names:
        # this happens with logger_wind files
        names = ["TIMESTAMP"] + names
        usecols = [header.index("TIMESTAMP")] + usecols

    # sure monotonic columns for pandas reading
    arg_sort = np.argsort(usecols)
    usecols = list(np.array(usecols)[arg_sort])
    names = list(np.array(names)[arg_sort])

    return Header(usecols, names, missing_names, foreign_names, sep, dayfirst)


def _read_nth_timestamp(nth, hdf5_filename, meta_xls_filename=lconf.meta_xls_filename):
    """ Find nth timestamp in the hdf5 file

    We rely on the metadata to find the timestamp path

    Parameter
    ---------
    nth : int
        index
    hdf5_filename : str
    server : str
        E.g. "http://localhost:3333"

    Returns
    -------
        end : dtr
            timestamp of latest data
    """
    metadata = read_metadata(meta_xls_filename)
    metadata.index = metadata.varname
    # time_path = metadata.ix["timestamps"].path
    time_path = metadata.loc["timestamps"].path
    with open_hdf5(hdf5_filename) as h5f:
        time_node = h5f.get_node(time_path)
        nth_time = time_node[nth]
    nth_time = nth_time.replace("T", " ")

    return nth_time


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
    if 'u_19m' and 'dd_19m' in var:
        u, v = angle2component(var['dd_19m'], var['u_19m'])  # wind 2 uv
        u, v = avrwind(u, v, 60, 60 * del_t)[:2]
        var['dd_19m'], var['u_19m'] = component2angle(u, v)
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
        varpath = np.unique(read_metadata(meta_xls_filename)['varname'])
        varpath = list(varpath .astype('str'))
        for ivar in ['CaseTemp', 'timestamps']:
            varpath.remove(ivar)
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

    # plt.show()


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

    # plt.show()


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

    # plt.show()


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
    # plt.show()


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


# ##############################################################################
# Dirk: below are old functions. I have not checked yet if they
# work on hdf5-files generated with the above functions!
# ##############################################################################


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


if __name__ == "__main__":
    import lauchaecker_config as conf

    # logger2hdf5("/home/meteo/data_raw/CR3000_data_1min.dat")
    
    create_hdf5(hdf5_filename="/media/data/p_mount/wetterstation/04_Data/lauchaecker.h5",
                meta_xls_filename="/media/data/p_mount/wetterstation/04_Data/HDF5_Variablen_Aufzeichn.xls",
                missdata_filename="/media/data/p_mount/wetterstation/04_Data/data_miss.csv",
                # log_last_filename="/media/data/p_mount/wetterstation/04_Data/log_last_ts.txt",
                log_last_filename=None,
                logger_dir="/media/data/p_mount/wetterstation/04_Data/CR3000",
                overwrite=True)

#    #missing data
#    read_missing_data(hdf5_filename, csv_filename = csv_filename)

#     hdf5_filename=r"J:\website_generation\Data\lauchaecker.h5"
#     meta_xls_filename = r"J:\website_generation\Data\HDF5_Variablen_Aufzeichn.xls"
# #    color = ['b','b','b','g','r','orange','r']
# 
#     # issues tipping bucketb
#     start = '2018-05-12T12:00:00'
#     end  = '2018-06-12T13:55:00'
#     
#     
#     # issues pluvio
#     #start = '2016-02-12T12:00:00'
#    # end  = '2017-06-12T13:55:00'
#     
#     
#     varpath = {'rr_03':'tipp_F',
#   #  'rr_04':'tipp_G',
#    # 'rr_05':'tipp_N',
#     'rr_06':'drop',
#     'rr_07':'pluvio_old',
#     'rr_09':'tipp_eng',
#     'rr_10':'pluvio_new'
#     }
#     df = hdf52df(start=start, stop=end, varnames=varpath.keys(), 
#                  hdf5_filename = hdf5_filename, 
#                  meta_xls_filename= meta_xls_filename, convert=True)
#     df = df.resample('5Min').sum()
#     
#     for ii, icol in enumerate (df.columns):
#         plt.plot(df.index, df[icol].values+ii/300., 
#                  label = varpath[icol], alpha = 0.5)
#         
#         print varpath[icol],df[icol].sum()
#     plt.legend()
#     plt.show()

    
    
    # kenntage(start, end, del_t = 60,
    #          hdf5=lconf.hdf5_filename,
    #          meta_xls_filename = lconf.meta_xls_filename,
    #          typ_='_data_raw')
    #data = read_hdf5(start, end, varpath.keys(), del_t=60)
    #date = pd.date_range(start, end, freq = '1Min')
    #plot_pluviogram(date, data)
    #read_last_timestamp(hdf5_filename, meta_xls_filename=meta_xls_filename)
    
    # start = '2010-01-01T00:00:00'
    # end  = '2018-12-10T23:55:00'
    # varpath = ['Ta_2m','G', 'RK', 'A', 'E']
    # hdf52txt(start, end, varpath, r'X:\exchange\Dhiraj\radiation.txt', 
    #          del_t = 5)


#    start = '2015-08-14T17:00:00'
#    end  = '2015-08-14T20:00:00'
#    df = hdf52df(start=start, stop=end, varnames=varpath, hdf5_filename = hdf5_filename, meta_xls_filename= meta_xls_filename)
#    df_h = df.resample('H','sum')
#    df_h.plot(color = color)
#    print df_h.sum()

   # data_reaches(hdf5=hdf5_filename)

    # evapo_from_hdf5(start, end, hdf5=hdf5_filename)
    # evapo_plot(start, end, hdf5_filename)
    #plot_data(start, end, varpath, conf.hdf5_filename)

    # kwds = {'start': '2019-11-17T00:00:00',
    #         'end': '2019-11-18T13:59:00',
    #         'hdf5':
    #         '/home/meteo/website_generation/Data/lauchaecker.h5',
    #         # '/tmp/lauchaecker.h5',
    #         'varpath':
    #         ['Ta_2m', 'rh_2m', 'G', 'A', 'u_19m', 'dd_19m', 'rr_07', 'RK',
    #          'E', 'p', 'max_u_19m'], 'meta_xls_filename':
    #         '/home/meteo/website_generation/Data/HDF5_Variablen_Aufzeichn.xls',
    #         'del_t': 60}
    # read_hdf5(**kwds)

