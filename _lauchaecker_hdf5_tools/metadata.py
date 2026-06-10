"""Lauchaecker HDF5 tools: metadata."""

from ._shared import *


__all__ = ['read_metadata', 'read_missing_data', 'read_last_timestamp', 'read_first_timestamp', '_hdf5_integrity', '_remove_quotes', '_loggerfile_reaches', '_set_hdf_structure', '_parse_header', '_read_nth_timestamp']


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

