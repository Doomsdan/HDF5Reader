import tables
import os
import numpy as np
import pandas as pd
try:
    import matplotlib.pyplot as plt
except ImportError:
    print("No matplotlib available.")

import lauchaecker_config as lconf
import lauchaecker_hdf5_tools as lau


def get_data_linear_interp(hf, itstart, itend, ipath):
    """Linear interpolation of defined data using the data two (!) timesteps
     before and after the definded time period. The reason for two steps, is the
     warmup time of the logger in case of a restart.

     """
    xp = (itstart-2, itend + 2)
    fp = (hf.get_node(ipath)[xp[0]], hf.get_node(ipath)[xp[1]])
    x = np.arange(itstart, itend+1)
    v = np.interp(x, xp, fp)
    return v




def write_patch_file(csv_filename=lconf.missdata_filename,
                     patch_filename_orig=lconf.patch_filename_orig, 
                     fill_info={}):
    """ Reads the missing data file and generates a default patch file.
    This patch file should be used to generate a .csv file that is used to
    patch the HDF5 file using patchhdf5(). It does two jobs:
        - It automatically generates a template marking all timestamps for which
          no data is available.
        - It flags all timestamps which are smaller than 10 min to be
          interpolated
    
    Parameter:
    ----------
        fill_info: dict, optional 
            the information that is filled into the list can be given.
            default:
            {'value':'', 'type':'', 'path':'', 'overwrite':'', 'comment':''}


    Structure:
    ----------
        [tstart, tend, delta, web, value, type, path, overwrite, comment]
        -----------------------------------------------------------------
        tstart/tend: Begin and end of missing data
        delta:       Length of missing data
        web:         If True, some information is used for
                     "errata_info_temp.html" shown on the homepage
        value:       How should the data be patched with?
                     a) single value: e.g. 0 or NaN
                     b) lin_int: linear interpolation between the missing values
                                 (get_data_linear_interp() for more information)
        type:        data type of the value
        path:        path of the data to be patched.
                     a) individual paths seperated by ",": path1,path2,...
                     b) all variables:                     all
        overwrite:   if 1, overwrites the time stamp
                     otherwise, simply add a new line 
                     This is used to add user comments to the time stamps 
                     automatically generated from "patch_hdf5_orig.csv":
                     a) take the desired timestamps from "patch_hdf5_orig.csv"
                     b) copy it to "patch_hdf5_manual.csv"
                     c) add the comment to the line 
                     d) set the overwrite value to 1 
                     e) run merge_patch_files()
        comment:     Some information from the user


    """
    if not any(fill_info):
        fill_info =  {'value':'', 'type':'', 'path':'', 
                      'overwrite':'', 'comment':''}
                      
    df = pd.read_csv(csv_filename, sep = ';', header = 0)
    start_dt = pd.to_datetime(df['tstart'])
    end_dt = pd.to_datetime(df['tend'])
    delta = (end_dt.values - start_dt.values).astype(np.timedelta64(1,'m')
                                                    ).astype(int)+1
    df['delta'] = delta
    df['web'] = 'False'
    columns = ['value', 'type', 'path', 'overwrite', 'comment']
    for icol in columns:
        df[icol] = fill_info[icol]
    mask = delta < 20
    df.loc[mask, 'value'] = 'lin_interp'
    df.loc[mask, 'path'] = 'all'
    df.loc[mask, 'type'] = 'str'
    df.to_csv(patch_filename_orig, sep=';', index=False)

def find_erroneous_ts(var, info, mintime='00:00:00', addtime='00:00:00', 
                    patch_folder=lconf.patch_folder, 
                    hdf5_filename=lconf.hdf5_filename, 
                    meta_xls_filename=lconf.meta_xls_filename, 
                    start=None, end=None, plot=False,
                    fill_info={}):
    """
    df:         Dataframe, containing the HDF5 data
    info:       dictionairy, {Aggregation: {threshold:thershold_value}}
                --> example: {'1Min' : {'minval': 200, 'maxval': 400},
                          '15Min': {'diff':30}}
    var:        variable, which is checked
    info:       dict of the format {aggregation:{thresholds}}
                e.g. {'1Min' : {'minval': 200, 'maxval':800}}
                thresholds can be:
                minval/maxval:   minimum / maximum value for the variable
                diff:            maximum difference between 2 timesteps
    mintime:    If the timedelta between 2 marked timesteps for strange values
                is lower than mintime, the whole period between those 
                timesteps is marked
    addtime:    timedelta which is sub/add to start and end
    start:      string in pandas data convension, start of analyzed period
    end:        string in pandas data convension, end of analyzed period
    dest:       path where csv is saved
    fill_info:  dict with information for the entries saved in the patch_file: 
                e.g. {'value':'nan', 'type':'float', 'path':'E,A', 
                      'overwrite':'', 'comment':''}

    """
    # read the hdf5 data
    df = lau.hdf52df(start=start, stop=end, varnames=[var],
                     hdf5_filename=hdf5_filename, 
                     meta_xls_filename=meta_xls_filename)
    
    if len(df.columns) == 0:
        print("Data not found. Giving up.")
        return
    
    # Save all bools for aggs and variables in 'output'
    output = pd.DataFrame(data = None, index = df.index, dtype = 'bool')
    bools = np.zeros((df.values.shape[0]), dtype = 'bool')
    for agg in info.keys():
        df_agg = df.resample(agg, closed='right', label='right').mean()
        index_agg = df_agg.index
    #-----------------------------------------------------------------
    # A bool is only calculated if the key for the variable is in
    # is given for the agg
    # 1. Create several bools that mark the questionable timesteps with 'True'
        #1.1 High difference between values
        if 'diff' in info[agg].keys():
            aa = np.zeros((df_agg.values.shape))
            aa[:] = np.nan
            aa[:-1] = df_agg[1:]
            difference = abs(df_agg - aa)
            bool_diff = difference > info[agg]['diff']
            bool_diff_1min = bool_diff.resample('1Min').backfill()
            # use the index of the orignal dataframe (relevant, if the 
            # df has not complete indices (e.g. 08:02, instead of 08:00)
            # with respect to the aggregations larger 1 minute
            bool_diff_1min = bool_diff_1min.reindex(df.index)
            output['{}_diff'.format(agg)] = bool_diff_1min.values
            
        #1.2 Minimun value (1min)
        if 'minval' in info[agg].keys():
            bool_min = df_agg[var] < info[agg]['minval']
            bool_min_1min = bool_min.resample('1Min').backfill()
            bool_min_1min = bool_min_1min.reindex(df.index)
            output['{}_minval'.format(agg)] = bool_min_1min.values
        #1.3 Maximum value (1min)
        if 'maxval' in info[agg].keys():
            bool_max = df_agg[var] > info[agg]['maxval']
            bool_max_1min = bool_max.resample('1Min').backfill()
            bool_max_1min = bool_max_1min.reindex(df.index)          
            output['{}_maxval'.format(agg)] = bool_max_1min.values



    #  2. Get the timesteps which are marked by at least one List
    # All values (False/True) are in the Dataframe 'output'
    # If any is True, ts is marked
    data_check = output.any(axis = 1)
    index_1min = df.index
    if  not any (data_check.values):
        print('No questionble Data in Timeperiod for {}'.format(var))
        return
    # Sort the indizes
    ts_var = index_1min[data_check]
    #2.2 Fill indizes, where timedelta is lower than mintime
    ts_fill = []
    print('total data:', ts_var.shape[0])
    for ii in range(int(ts_var.shape[0] -1)):
        if ii%10000 == 0:
            print(ii, end=' ')
        delta = ts_var[ii+1] - ts_var[ii]
        if((delta > pd.Timedelta('0 days 00:01:00')) &
            (delta < pd.Timedelta('0 days {}'.format(mintime)))):
            ts = pd.date_range(start=ts_var[ii], end=ts_var[ii+1], freq='1T')
            ts_fill.append(ts)
    # put timestamps together again
    if len(ts_fill) >0:
        ts_fill = pd.to_datetime(np.concatenate(ts_fill))
        ts_var = pd.to_datetime(ts_var.append(ts_fill))
        ts_var = pd.to_datetime(sorted(ts_var))
        ts_var = pd.to_datetime(np.unique(ts_var))

    #2.3 Create list with start and end
    delta = ts_var[1:] - ts_var[:-1]
    bool_var = delta > pd.Timedelta('0 days 00:01:00')
    # bool marks the start days with True
    starts = np.zeros((bool_var.shape[0] +1), dtype = 'bool')
    starts[0] = True
    starts[1:] = bool_var
    # bool marks the end days with 'True'
    ends = np.zeros((bool_var.shape[0] +1), dtype = 'bool')
    ends[-1] = True
    ends[:-1] = bool_var
    starts = ts_var[starts]
    ends    = ts_var[ends]
    # Sub/Add  x to start/end
    addtime  = pd.Timedelta('0 days {}'.format(addtime))
    starts = starts - addtime
    ends   = ends   + addtime

    print('saving data')
    # 3. Save questionable timeperiods
    # Save start end as csv
    df_var = pd.DataFrame(columns = ['tstart', 'tend'])
    df_var['tstart'] = starts
    df_var['tend'] = ends

    if plot:
        # check: plot data
        plt.figure()
        plt.plot(df[var], label = 'alt')
        for ii, period in enumerate(starts):
            df[var][starts[ii]:ends[ii]] = np.nan
        plt.plot(df[var], label = 'neu')
        plt.legend()
        plt.show()
        plt.close()
        
    # save the erroneous time stamps 
    fn_var = 'data_miss_{}.csv'.format(var)
    fn_full = os.path.join(patch_folder, fn_var)
    df_var.to_csv(fn_full,sep=';', index=False, date_format='%Y-%m-%dT%H:%M:%S')

    # convert the file into a patchfile (adding addtitional columns) 
    write_patch_file(fn_full, fn_full, fill_info)


def merge_patch_files(patch_filename=lconf.patch_filename,
                      patch_filename_orig=lconf.patch_filename_orig, 
                      update_patch_filenames=lconf.update_patch_filenames):
    """Merges different patch files into one final file.
    """
    df = pd.read_csv(patch_filename_orig, sep=';', header=0, na_filter=False)
    # do update for each file
    for ipatch in update_patch_filenames:
        idf = pd.read_csv(ipatch, sep=';', header=0, na_filter=False)
        idf.overwrite = idf.overwrite.astype(bool)
        # do update for each row
        for ii, irow in idf.iterrows():
            # if entry exist and if overwrite = 1, overwrite the file
            # otherwise create an new entry by simply concatenating the dfs
            if ((irow.tstart in df.tstart.values) & (irow.overwrite)):
                    df[df.tstart==irow.tstart] = pd.DataFrame(irow).T.values
            else:
                df = pd.concat((df, pd.DataFrame(irow).T))

    df = df.sort_values(by='tstart')
    df.to_csv(patch_filename, sep = ';', index=False)

def fill_timedelta(patch_file=lconf.patch_filename_manual):
    """ Updates the patch_hdf5 file.
        Can be used to fill in the time delta between tstart/tend of manually
        added data."""

    idf = pd.read_csv(patch_file, sep=';', header=0, na_filter=False)
    start_dt = pd.to_datetime(idf['tstart'])
    end_dt = pd.to_datetime(idf['tend'])
    delta = (end_dt.values - start_dt.values).astype(np.timedelta64(1,'m')
                                                    ).astype(int)+1
    idf['delta'] = delta
    idf.to_csv(patch_file, sep = ';', index=False)

def patchhdf5(hdf5_filename=lconf.hdf5_filename, 
              patch_filename=lconf.patch_filename):
    """Applies patches described in pfname to data in file hfname"""
    types = {'float': float,
            'int': int,
            'str': str,
            }    
    
    with tables.open_file(hdf5_filename, 'r+') as hf:
        df = pd.read_csv(patch_filename, sep = ';',
                         header = 0, na_filter = False)
        tref = '/lauchaecker/min_01'
        paths_all = hf.root.lauchaecker.min_01.data._v_children.keys()
        for ii, irow in df.iterrows():
            tstart = irow['tstart'].strip()
            tend = irow['tend'].strip()
            if not irow['path']:
                print(tstart, tend, 'not changed')
                continue
            else:
                paths = irow['path'].strip().split(',')
            typ = irow['type'].strip()
            value = irow['value'].strip()
            itstart = np.where((hf.get_node(tref).timestamps[:] == tstart))[0][0]
            itend = np.where((hf.get_node(tref).timestamps[:] == tend))[0][0]
            if paths == ['all']:
                paths = paths_all
            ref_path = '{}/data/{}/{}_data_raw'
            paths = [ref_path.format(tref, ipath, ipath) for ipath in paths]

            for ipath in paths:
                if value == 'lin_interp':
                    v = get_data_linear_interp(hf, itstart, itend, ipath)
                elif value in paths_all:
                    # use the values of this variable here
                    fill_path = ref_path.format(tref, value, value)
                    v = hf.get_node(fill_path)[itstart:itend+1]
                else:
                    v = types[typ](value)
                hf.get_node(ipath)[itstart:itend+1] = v
        print(tstart, tend, 'changed to', value, ipath)
    print('HDF5 patched!')


#WARNING: not tested!!
def fill_empty_stamps(hdf5_filename=lconf.hdf5_filename):
    with tables.open_file(hdf5_filename, 'r+') as hf:
        tref = '/lauchaecker/min_01'
        timestamps = hf.get_node(tref).timestamps[:]
        # just for logging purposes
        n_empty = np.sum(timestamps == "")
        date_range = pd.date_range(timestamps[0],
                                   timestamps[-1],
                                   freq="min")
        date_str = (date_range
                    .to_series()
                    .dt
                    .strftime("%Y-%m-%dT%H:%M:%S")
                    .values)
        hf.get_node(tref)[:] = date_str
    print("Replaced %d empty timestamps" % n_empty)


if __name__ == '__main__':
    import sys
    basepath = os.getcwd()
    # hdf5_filename = os.path.join(basepath, 'lauchaecker.h5')
    # patch_file = os.path.join(basepath, 'patch_hdf5.csv')
    # patch_file_orig = os.path.join(basepath, 'patch_hdf5_orig.csv')
    # update_patch_files = [os.path.join(basepath, 'patch_hdf5_manual.csv')]
    # csv_filename = os.path.join(basepath, 'data_miss.csv ')
      
    # er_filename = os.path.join(os.path.dirname(basepath),'Documents',
    #         'Templates','html','errata_info_temp.html')
    
    ## a) Write the patch file using the missing data file
    write_patch_file()
    
    ## b) Generate patch files based on erroneous data definitions
    # so far only the longwave radiation is evaluated
    # and both, incoming and outgoing radiation is masked
    var = 'E'
    info = {'1Min' : {'minval': 200, 'maxval':800}}
    fill_info =  {'value':'nan', 'type':'float', 'path':'E,A', 
                  'overwrite':'', 'comment':''}
    find_erroneous_ts(var, info, mintime = '12:00:00', addtime = '00:30:00', 
                      plot=True, fill_info=fill_info)
             
    ## c) Add manual changes to "patch_hdf5_manual.csv" and run fill_timedelta()
    ## if the time delta is not explicitly given
    fill_timedelta()
    
    ## d) Merge the patch file from before with additional patch files 
    ##    manually or automaticall generated
    merge_patch_files()

    # 
    ## e) Patch the hdf5 file 
    patchhdf5()

    ## f) Check for empty timestamps and fill
    # fill_empty_stamps()
