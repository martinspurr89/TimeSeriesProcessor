# Load modules
from pathlib import Path
import pandas as pd

import Scripts.config as config
import Scripts.ProcessData_resampler as ProcessData

### Generic script for importing files

# Available data import file types
config.importer['filetypes'] = ['xls', 'csv', 'txt']

# For importing each data file
def fileImport(dataset, folder, filename, pat):
    # Set the folder containing the data file
    data_folder_path = Path(config.config['info']['datasets'].query('dataset == "' + dataset + '" & folder == ' + str(folder))['data_folder_path'][dataset])
    # Number of rows to skip from top of imported data file
    skiprows = config.config['info']['datasets'].query('dataset == "' + dataset + '" & folder == ' + str(folder))['skiprows'][dataset]
    # If file to be imported is of type of the 1st available filetype (xls)
    if pat == config.importer['filetypes'][0]:
        # Read excel file
        df = pd.read_excel(data_folder_path / filename, skiprows=skiprows)
    # Else if file to be imported is of type of the 2nd available filetype (csv)
    elif pat == config.importer['filetypes'][1]:
        # Open file temporarily to indentify encoding
        with open(data_folder_path / filename) as csv_file:
            enc = csv_file.encoding
        # Read csv file
        df = pd.read_csv(data_folder_path / filename, skiprows=skiprows, encoding = enc)
     # Else if file to be imported is of type of the 3rd available filetype (txt)
    elif pat == config.importer['filetypes'][2]:
        # Read text file with tab delimited separator
        df = pd.read_csv(data_folder_path / filename, sep="\t", skiprows=skiprows)
    else:
        # If data file to be imported is none of those filetypes then raise and print an error
        raise ValueError("Unknown file type!")
    return df

### Optional Pre-import scripts for datasets which need supporting data imported first rather than with every data file.

def get_Test_support_data(dataset, folder):
    ### Not used in example
    ### Available to get a non-data supporting file, e.g. may contain parameter dictionary or data file timestamp information
    # Set folder containing supporting file
    supp_data_filepath = config.config['info']['datasets'].query('dataset == "' + dataset + '" & folder == ' + str(folder))['supp_data_filepath'][dataset]
    # Read in here as a tab-delimited text file
    Test_info = pd.read_csv(supp_data_filepath, sep="\t", index_col="Code")
    # Return dataframe to main script
    return Test_info

# Dictionary containing dataset ID and supporting data function (if needed)
preimport_functions = {'Test': get_Test_support_data}

### Custom Imported Data Functions - one per dataset ID with nomenclature "mod_imported_xxx_data" where "xxx" is the dataset ID

def mod_imported_TimeSeries_data(dataset, folder, filename, pat):
    # Import files
    df = fileImport(dataset, folder, filename, pat)
    # Create combined DateTime column
    df['DateTime'] = df['Date'] + " " + df['Time']
    # Format as a datetime type
    df['DateTime'] = pd.to_datetime(df['DateTime'], format='%d/%m/%Y %H:%M:%S')
    # Set datetime timezone as UTC
    df['DateTime'] = df['DateTime'].dt.tz_localize('UTC')

    ### INSERT DATA MODIFIERS HERE ###
    ### To call supporting data use this code:
    ### supporting_data = config.data['supporting_data_dict'][dataset]

    # Return Dataframe to script
    return df

def mod_imported_SampleLog_data(dataset, folder, filename, pat):
    # Import python modules needed for this specific import
    import re

    # Import file using above function
    df = fileImport(dataset, folder, filename, pat)

    # Format DateTime column as a datetime type
    df['DateTime'] = pd.to_datetime(df['DateTime'], format='%d/%m/%Y %H:%M')
    # Set DateTime timezone to the timezone it was recorded in
    df['DateTime'] = df['DateTime'].dt.tz_localize('Europe/London')
    # Convert DateTime timezone to UTC (used throughout rest of script)
    df['DateTime'] = df['DateTime'].dt.tz_convert('UTC')

    # Set read columns
    selected_read_cols = ['R1', 'R2', 'R3']
    # Read values as numeric type
    df[selected_read_cols] = df[selected_read_cols].apply(pd.to_numeric, errors='coerce')

    # Average readings
    df['Read_ave'] = df[selected_read_cols].mean(axis=1, skipna=True)

    # Widen DF
    df_wide = pd.pivot_table(df, values='Read_ave', index=['DateTime', 'Location'], columns=['Type', 'Vial'])

    # Fix col header and names
    df_wide.columns = map(''.join, (str(v) for v in df_wide.columns))
    df_wide.columns = [re.sub(r'\W', '', i) for i in df_wide.columns]
    df_wide.columns = [s[:len(s) - 1] + "_" + s[len(s) - 1:] for s in df_wide.columns]
    
    # Separate data into each sampling location
    # Create location dataframe dictionary
    loc_dfs = {}
    # For each location
    for loc in df_wide.index.get_level_values('Location').unique():
        # Store dataframe
        loc_dfs[loc] = df_wide.loc[df_wide.index.get_level_values('Location') == loc]
        # Rename columns with location ID
        loc_dfs[loc].columns = loc + "_" + loc_dfs[loc].columns

    # Combine location dataframes into one dataframe
    df_wide_locs = pd.concat(loc_dfs)
    # Reset index and drop location column
    df_wide_locs = df_wide_locs.reset_index()
    df_wide_locs = df_wide_locs.drop(['level_0', 'Location'], axis=1)

    # Return dataframe to main script
    return df_wide_locs

import_functions = {'TimeSeries': mod_imported_TimeSeries_data,
                    'SampleLog': mod_imported_SampleLog_data}

### POST IMPORT SCRIPT

def mod_post_import_data(df):
    ### Modify data after import here
    ### e.g. where 2 datasets can produce a combined/interaction parameter
    ### e.g. to produce a new SUM parameter etc.

    # Select parameters with bar plot
    for par in config.config['bar_pars']:
        # If parameter being used
        if par in df.keys():
            # Fill NA (blank values)
            df[par] = df[par].fillna(method='ffill')

    # Return dataframe to main script
    return(df)

