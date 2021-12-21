# Import packages
import sys
import getopt
import os
from pathlib import Path
from tqdm.autonotebook import tqdm
import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone
import re
import numpy as np
import pickle
import bz2
import shutil
import warnings

import config

def helper():
    print("Help")

def processArguments():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:uv", ["io_dir=", "update"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-v":
            config.verbose = True
        elif opt in ("-h", "--help"):
            helper()
            sys.exit()
        elif opt in ("-d", "--io_dir"):
            config.io_dir = Path(arg)
        elif opt in ("-o", "--update"):
            config.update = True
        else:
            assert False, "unhandled option"

#Set Input/Output directory
def setIOFolder(folder):
    # Check directory exists
    assert os.path.exists(folder), "Folder does not exist at, "+str(folder)
    # Check scripts directory exists and append to path for script access
    scripts_dir = folder / "Scripts"
    assert os.path.exists(scripts_dir), "Custom import Scripts folder does not exist at, "+str(scripts_dir)
    sys.path.append(str(scripts_dir))
    global CustomDataImports
    CustomDataImports = __import__('CustomDataImports', globals(), locals())
    checkFolderExists(config.io_dir / "Output")

def deleteFolderContents(folder):
    if not os.path.exists(folder):
        folder.mkdir(parents=True, exist_ok=True)
    else:
        for filename in os.listdir(folder):
            file_path = folder / filename
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

def checkFolderExists(folder):
    if not os.path.exists(folder):
        folder.mkdir(parents=True, exist_ok=True)
        return(False)
    else:
        return(True)

def getConfig():
    pfile_path = config.io_dir / "Temp" / 'config.pkl'
    if os.path.exists(pfile_path):
        with open(pfile_path, 'rb') as pfile:
            items = pickle.load(pfile)
        for key in list(items.keys()):
            config.config[key] = items[key]
    else:
        print("No pickled config.pkl data file exists, continuing with full data import!")
        config.update = False
        openinfoFile()

def saveObject(object_to_save, filepath):
    with bz2.BZ2File(filepath, 'wb') as f:
        pickle.dump(object_to_save, f)

# Info file functions
def setUTCDatetime(date_str, old_tz, dt_format = "%d/%m/%Y %H:%M:%S"):
    date_formats = ["%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]
    if date_str == 'NaT' or date_str == 'nan':
        return pd.NaT
    else:
        if dt_format not in date_formats: date_formats.append(dt_format)
        for format in date_formats:
            try:
                datetime_set_naive = datetime.strptime(date_str, format)
                break
            except ValueError:
                continue
        try:
            datetime_set_old = timezone(old_tz).localize(datetime_set_naive)
            datetime_set_utc = datetime_set_old.astimezone(timezone('UTC'))
        except UnboundLocalError:
            raise ValueError("Set dt_format in function call or date_formats")
        return datetime_set_utc

def processSetup(df):
    config.config['project'] = df.loc['project', 'value']
    config.config['refresh_hours']  = df.loc['refresh_hours', 'value']
    
    #Process start date
    if not pd.isna(df.loc['date_start_utc', 'value']):
        config.config['date_start'] = setUTCDatetime(str(df.loc['date_start_utc', 'value']), "UTC", "%Y-%m-%d %H:%M:%S")
    else:
        raise ValueError("Set dt_format in function call or date_formats")

    #Process end date
    if not pd.isna(df.loc['date_end_utc', 'value']):
        config.config['date_end'] = setUTCDatetime(str(df.loc['date_end_utc', 'value']), "UTC", "%Y-%m-%d %H:%M:%S")
    else:
        config.config['date_end'] = datetime.now(timezone('UTC')).replace(microsecond=0)
    
    df.loc['date_start_utc', 'value'] = config.config['date_start']
    df.loc['date_end_utc', 'value'] = config.config['date_end']
    return df

def dateRange(window=-1, start=config.config['date_start'], end=config.config['date_end']):
    if pd.isna(start):
        start = config.config['date_start']
    if pd.isna(end):
        end = config.config['date_end']
    if window != -1:
        if not pd.isna(window):
            start = end - timedelta(days=window)
    return start, end

def processCharts(df):
    for chart, row in df.iterrows():
        chart_range = dateRange(window=row['chart_range_window'],
                                start=setUTCDatetime(str(row['chart_range_start']), "UTC", "%Y-%m-%d %H:%M:%S"),
                                end=setUTCDatetime(str(row['chart_range_end']), "UTC", "%Y-%m-%d %H:%M:%S"))
        df.loc[chart, 'chart_range_start'] = chart_range[0]
        df.loc[chart, 'chart_range_end'] = chart_range[1]
        df.loc[chart, 'chart_range_window'] = chart_range[1] - chart_range[0]
        if df.loc[chart, 'chart_status'] == "ON":
            config.config['charts'][chart] = df.loc[chart, 'chart']
            config.config['plot_sets'][chart] = df.loc[chart, 'plot_set']
    return df

def createParPlotDict():
    pars = config.config['info']['parameters']['parameter'].to_list() + config.config['info']['parameters_ave']['parameter_ave'].to_list()
    plots = config.config['info']['parameters']['plot'].to_list() + config.config['info']['parameters_ave']['plot'].to_list()
    config.config['par_plot_dict'] = dict(zip(pars, plots))

    for style in config.config['styles']:
        config.config['par_style_dict'][style] = config.config['info']['parameters'].query(style + ' == True')['parameter'].to_list() + config.config['info']['parameters_ave'].query(style + ' == True')['parameter_ave'].to_list()

def processColours(df):
    df['rgb'] = list(zip(
        (df['r'] / 255),
        (df['g'] / 255),
        (df['b'] / 255)))
    df['rgba_str'] = "rgba(" + df['r'].astype(int).astype(str) + "," + df['g'].astype(int).astype(str) + "," + df['b'].astype(int).astype(str) + ",1)"
    return df

def openinfoFile():
    info_fname = "Info2.xlsx"
    config.config['info'] = pd.read_excel(config.io_dir / info_fname, sheet_name=None, index_col=0)
    config.config['info']['setup'] = processSetup(config.config['info']['setup'])
    config.config['info']['charts'] = processCharts(config.config['info']['charts'])
    createParPlotDict()
    config.config['info']['colours'] = processColours(config.config['info']['colours'])

# Data import functions
def selectDatasets():
    selected_plots = []
    for plot in set(config.config['plot_sets'].values()):
        selected_plots.append("selected_plot_" + str(plot))
        
    selected_pars_inc = config.config['info']['parameters'][selected_plots].isin([1]).any(axis=1)
    selected_pars = list(config.config['info']['parameters'][selected_pars_inc]['parameter'].values)
    
    selected_pars_ave_inc = config.config['info']['parameters_ave'][selected_plots].isin([1]).any(axis=1)
    selected_pars_ave = list(config.config['info']['parameters_ave'][selected_pars_ave_inc]['parameter_ave'].values)

    selected_reps = list(config.config['info']['parameters'][config.config['info']['parameters']['parameter_ave'].isin(selected_pars_ave)]['parameter'])

    config.config['bar_pars'] = config.config['info']['parameters'][selected_pars_inc & config.config['info']['parameters']['bar'] == True]['parameter'].to_list() + config.config['info']['parameters_ave'][selected_pars_ave_inc & config.config['info']['parameters_ave']['bar'] == True]['parameter_ave'].to_list()

    config.config['selected_pars'] = list(set(selected_pars + selected_pars_ave + selected_reps))
    selected_pars_all_inc = pd.concat([selected_pars_inc, selected_pars_ave_inc])

    config.config['selected_datasets'] = list(selected_pars_all_inc[selected_pars_all_inc].index.unique().values)

def readFile(dataset, folder, filename):
    file_pat = config.config['info']['datasets'].query('dataset == "' + dataset + '" & folder == ' + str(folder))['file_pat'][dataset]
    
    for pat in config.config['filetypes']:
        if re.search(pat, file_pat, re.IGNORECASE):
            if dataset in CustomDataImports.import_functions:
                df = CustomDataImports.import_functions[dataset](dataset, folder, filename, pat)
                break
    if 'df' not in locals():
        raise ValueError("Unknown file type for " + str(dataset) + " folder " + str(folder) + " with " + filename)

    if len(df) > 0:
        # Name parameter columns
        code_par_dict = dict(zip(config.config['info']['parameters'].query('dataset == "' + dataset + '"')['code'],
                                    config.config['info']['parameters'].query('dataset == "' + dataset + '"')['parameter']))

        if len(code_par_dict.values()) == len(set(code_par_dict.values())): # check for duplicate values to set
            df = df.rename(columns=code_par_dict) ## Could duplicate column names
        else:
            df = df.reset_index(drop=True).reset_index()
            df = pd.melt(df, id_vars=['index', 'DateTime'])
            df = df.replace({'variable': code_par_dict})
            df = df.reset_index().pivot(index=['level_0','DateTime'], columns='variable', values='value').reset_index().drop('level_0', axis=1) # Safe rename to avoid duplicate columns
            df.columns.name = None

        #Choose parameters included in parameters sheet
        #config.config['selected_pars'] = list(config.config['info']['parameters'].query('dataset == "' + dataset + '"')['parameter'].values)
        df = df.drop(df.columns.difference(['DateTime'] + config.config['selected_pars']), axis=1)
        #Make floats
        for col in config.config['selected_pars']:
            try:
                df.loc[:,col] = df.loc[:,col].astype(float)
            except:
                pass
        # Add blank row between files - to be implemented
    return df

def importFiles(dataset, folder):
    data_folder_path = Path(config.config['info']['datasets'].query('dataset == "' + dataset + '" & folder == ' + str(folder))['data_folder_path'][dataset])
    file_pat = config.config['info']['datasets'].query('dataset == "' + dataset + '" & folder == ' + str(folder))['file_pat'][dataset]
    files_imported = config.config['files_imported'][dataset][folder]
    dataset_in_folder = []
    for filename in tqdm(os.listdir(data_folder_path), desc="Open files to import"):
        if re.search(file_pat, filename) and not filename.startswith('.'):
            if filename not in files_imported:
                df = readFile(dataset, folder, filename)
                # Keep if longer than 0 lines and within timeframe
                if len(df) > 0 and max(df['DateTime']) >= config.config['date_start'] and min(df['DateTime']) <= config.config['date_end']:
                    dataset_in_folder.append(df)
                    files_imported.append(filename)
    if (not all(df is None for df in dataset_in_folder)) and (len(dataset_in_folder) > 0):
        df_combined = pd.concat(dataset_in_folder, axis=0, ignore_index=True)
        return df_combined
    #else:
    #    df_combined = None
    

def combineSortData(df_dict):
    # Create one dataframe from all days data
    df_dict_filtered = {k: v for k, v in df_dict.items() if v is not None}

    if len(df_dict_filtered) > 0:
        df = pd.concat(df_dict_filtered, axis=0, ignore_index=True)
        df.sort_values(by=['DateTime'], inplace=True)
        cols = ['DateTime']  + [col for col in df if col != 'DateTime']
        df = df[cols]
        df = df.reset_index(drop=True)

        df = df[df['DateTime'] >= config.config['date_start']]
        df = df[df['DateTime'] <= config.config['date_end']]
        return df
    else:
        print('No data to combine!')
    

def importData(dataset):
    num_folders = len(config.config['info']['datasets'].query('dataset == "' + dataset + '"'))
    folder_data_list = {}
    if dataset not in config.config['files_imported']:
        config.config['files_imported'][dataset] = {}
    for folder in range(1, num_folders + 1):
        if folder not in config.config['files_imported'][dataset]:
            config.config['files_imported'][dataset][folder] = []
        # Custom pre-import functions
        if dataset in CustomDataImports.preimport_functions:
            config.config['supporting_data_dict'][dataset] = CustomDataImports.preimport_functions[dataset](dataset, folder)
        # Import files
        folder_data_list[folder] = importFiles(dataset, folder)
    if (not any(df is None for df in folder_data_list)) & (len(folder_data_list) > 0):
        df_dataset = combineSortData(folder_data_list)
        return df_dataset

def importDatasets():
    selectDatasets()
    for dataset in tqdm(config.config['selected_datasets'], desc = "Import data from each dataset"):
        df = importData(dataset)
        if df is not None:
            config.config['dataset_data'][dataset] = df

def averageReps(df):
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
        warnings.filterwarnings('ignore', r'Degrees of freedom <= 0 for slice.')
        ave_cols = []
        if df is not None:
            for col in df.columns[1:].to_list():
                ave_col = config.config['info']['parameters'].query('parameter == "' + col + '"')['parameter_ave'][0]
                if ave_col != col:
                    if ave_col not in ave_cols:
                        cols = config.config['info']['parameters'].query('parameter_ave == "' + ave_col + '"')['parameter'].to_list()
                        
                        df[ave_col] = df[cols].mean(axis=1)
                        if len(cols) > 2:
                            df[ave_col + "_err"] = np.nanstd(df[cols], axis=1)
                        elif len(cols) == 2:
                            df[ave_col + "_err"] = np.abs((df[cols[0]] - df[cols[1]])/2)
                        else:
                            df[ave_col + "_err"] = 0
                        ave_cols.append(ave_col)

            err_pars = [ave_col + "_err" for ave_col in ave_cols]
            chosen_pars = config.config['selected_pars'] + err_pars
            chosen_pars = [par for par in chosen_pars if par in df.columns]

            df = df[["DateTime"]+ chosen_pars]
            return df

def processAllData():
    df = combineSortData(config.config['dataset_data'])

    if "mod_post_import_data" in dir(CustomDataImports):
        df = CustomDataImports.mod_post_import_data(df)

    df = averageReps(df)

    if config.update:
        all_dict = {'all': config.config['all_data'], 'new': df}
        df = combineSortData(all_dict)

    #Sort columns
    df = df.reindex(sorted(df.columns), axis=1)
    cols = list(df)
    cols.insert(0, cols.pop(cols.index('DateTime')))
    df = df.loc[:, cols]

    return df

#########

def main():
    processArguments()
    setIOFolder(config.io_dir)
    
    if not config.update: # Reimport all data
        openinfoFile()
    else: # Update existing config file data
        getConfig()

    importDatasets() # data dict per dataset
    
    config.config['all_data'] = processAllData() # all data combined and averaged

    all_data_grouped = config.config['all_data'].set_index('DateTime').groupby(pd.Grouper(freq='15Min')).aggregate(np.mean)
    all_data_grouped.to_csv(config.io_dir / 'Output' / 'all_data_15Min.csv')

    # Create storage object with filename `processed_data`
    saveObject(config.config['all_data'], (config.io_dir / 'Output' / 'all_data.pbz2'))

if __name__ == "__main__":
    main()
