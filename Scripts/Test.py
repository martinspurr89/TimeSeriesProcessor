# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

import ProcessData


# %%
def setupIOFolder(folder):
    scripts_dir = folder / "Scripts"
    if not os.path.exists(folder):
        os.mkdir(folder)
        print("Created Project folder: folder.name")
    else: print("Using already existing Project folder (" + folder.name + ")")
    if not os.path.exists(scripts_dir):
        os.mkdir(scripts_dir)
        print("Created Scripts folder")
    else: print("Using already existing Scripts folder")
    sys.path.append(str(scripts_dir))
    
    cdi_path = scripts_dir / "CustomDataImports.py"
    if not os.path.exists(cdi_path):
        with open(cdi_path, 'w') as f:
            f.write('''from config import *
from pathlib import Path
import pandas as pd

config['filetypes'] = ['xls', 'csv', 'txt']
def fileImport(dataset, folder, filename, pat):
    data_folder_path = Path(config['info']['datasets'].query('dataset == "' + dataset + '" & folder == "' + str(folder) + '"')['data_folder_path'][dataset])
    skiprows = config['info']['datasets'].query('dataset == "' + dataset + '" & folder == "' + str(folder) + '"')['skiprows'][dataset]
    if pat == config['filetypes'][0]:
        df = pd.read_excel(data_folder_path / filename, skiprows=skiprows)
    elif pat == config['filetypes'][1]:
        df = pd.read_csv(data_folder_path / filename, skiprows=skiprows)
    elif pat == config['filetypes'][2]:
        df = pd.read_csv(data_folder_path / filename, sep="\t", skiprows=skiprows)
    else:
        raise ValueError("Unknown file type!")
    return df

### Insert pre-import functions here: names as -> get_DATASET_support_data()

###

# Set pre-import functions inside dictionary separated by commas as -> 'DATASET': get_DATASET_support_data

preimport_functions = {}

### Insert data import functions here: names as -> mod_imported_DATASET_data()

###

# Set data import functions inside dictionary separated by commas as -> 'DATASET': mod_imported_DATASET_data

import_functions = {}                 
''')
        print("Created CustomDataImports script placeholder")
    else: print("Using already existing CustomDataImports script")

# %% [markdown]
# ## Set analysis folder and project name
# %% [markdown]
# C:\Users\nms198\OneDrive - Newcastle University\3_Coding\Python
# 
# Rod BES BEWISE

# %%
setup_dict = {}

path = Path(input("Enter the path to create your analysis folder in: "))
setup_dict['project'] = input("Enter the name of this project: ")
folder = path / setup_dict['project'].replace(" ", "_")
setupIOFolder(folder)

# %% [markdown]
# ## Setup
# %% [markdown]
# 01/12/2017 13:15:00
# 
# 14/01/2019 10:27:00
# 
# 4

# %%
setup_dict['date_start_utc'] = ProcessData.setUTCDatetime(input("Enter the START datetime in UTC timezone (format dd/mm/yyyy  hh:mm:ss): "), "UTC")
setup_dict['date_end_utc'] = ProcessData.setUTCDatetime(input("Enter the END datetime in UTC timezone (format dd/mm/yyyy  hh:mm:ss) [leave blank if ongoing experiment]: "), "UTC")
setup_dict['refresh_hours'] = int(input("Enter after how many hours data should be refreshed when processing data: "))


# %%
setup_df = pd.DataFrame(setup_dict.items(), columns = ['id','value'])


# %%
for row in range(0,len(setup_df)):
    if isinstance(setup_df.loc[row,'value'], datetime):
        setup_df.loc[row,'value'] = setup_df.loc[row,'value'].replace(tzinfo=None)
setup_df


# %%
with pd.ExcelWriter(folder / 'Info_test.xlsx',
                        engine = 'xlsxwriter',
                        datetime_format = 'dd/mm/yyyy  hh:mm:ss') as writer:
    setup_df.to_excel(writer, sheet_name='setup', index = False)


# %%
folder / 'Info_test.xlsx'

