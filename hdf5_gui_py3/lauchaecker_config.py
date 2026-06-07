"""This file defines pathnames needed for data retrieval for the
lauchaecker measurement station.

See Also
--------
lhglib.contrib.meteo.fetch_new_data
lhglib.contrib.meteo.fetch_loggerfile
"""

import os

# windows usage
if os.name == 'nt':
    #root = r"J:\website_generation\Data"
    root = r"P:\wetterstation\04_Data"
    #root=r'C:\Users\Jessica\Desktop\Pythonstuff\hdf5gui'
# linux usage
else:
    root = r"/media/data/p_mount/wetterstation/04_Data"
    
server = "http://129.69.227.222:31415"

hdf5_filename = os.path.join(root, "lauchaecker.h5")
log_last_filename = os.path.join(root, "log_last_ts.txt")

meta_xls_filename = os.path.join(root, "HDF5_Variablen_Aufzeichn.xls")
missdata_filename = os.path.join(root, 'data_miss.csv')

patch_folder = os.path.join(root, 'patch_files')
patch_filename = os.path.join(patch_folder, 'patch_hdf5.csv')
patch_filename_orig = os.path.join(patch_folder, 'patch_hdf5_orig.csv')
patch_filename_manual = os.path.join(patch_folder, 'patch_hdf5_manual.csv')
update_patch_filenames = [patch_filename_manual, 
                          os.path.join(patch_folder, 'data_miss_E.csv')]
                     
logger_dir = os.path.join(root, 'CR3000')

print(root)
