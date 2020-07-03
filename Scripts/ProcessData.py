# Import packages
import sys
import getopt
import os
from pathlib import Path
from tqdm.autonotebook import tqdm
import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone, utc
import xlrd
import re
import numpy as np
import pickle
import shutil

from config import *

def helper():
    print("Help")

def processArguments():
    global io_dir
    global update
    global verbose
    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:uv", ["io_dir=", "update"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-v":
            verbose = True
        elif opt in ("-h", "--help"):
            helper()
            sys.exit()
        elif opt in ("-d", "--io_dir"):
            io_dir = Path(arg)
        elif opt in ("-o", "--update"):
            update = True
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

def deleteFolderContents(folder):
    if not os.path.exists(folder):
        os.mkdir(folder)
    else:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

def getConfig():
    global config
    pfile_path = io_dir / "Temp" / 'config.pkl'
    if os.path.exists(pfile_path):
        with open(pfile_path, 'rb') as pfile:
            items = pickle.load(pfile)
        for key in list(items.keys()):
            config[key] = items[key]
    else:
        print("No pickled config.pkl data file exists, continuing with full data import!")

def saveConfig():
    temp_folder = io_dir / "Temp"
    deleteFolderContents(temp_folder)
    with open(temp_folder / 'config.pkl', 'wb') as pfile:
        pickle.dump(config, pfile, protocol=-1)

# Info file functions
def setUTCDatetime(date_str, old_tz, dt_format = "%d/%m/%Y %H:%M:%S"):
    date_formats = ["%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]
    if date_str == 'NaT':
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
            print("Set dt_format in function call or date_formats")
            raise
        return datetime_set_utc

def processSetup(df):
    config['project'] = df.loc['project', 'value']
    config['refresh_hours']  = df.loc['refresh_hours', 'value']
    
    #Process start date
    if not pd.isna(df.loc['date_start_utc', 'value']):
        config['date_start'] = setUTCDatetime(str(df.loc['date_start_utc', 'value']), "UTC", "%Y-%m-%d %H:%M:%S")
    else:
        raise ValueError("Set dt_format in function call or date_formats")

    #Process end date
    if not pd.isna(df.loc['date_end_utc', 'value']):
        config['date_end'] = setUTCDatetime(str(df.loc['date_end_utc', 'value']), "UTC", "%Y-%m-%d %H:%M:%S")
    else:
        config['date_end'] = datetime.now(timezone('UTC')).replace(microsecond=0)
    
    df.loc['date_start_utc', 'value'] = config['date_start']
    df.loc['date_end_utc', 'value'] = config['date_end']
    return df

def dateRange(window=-1, start=config['date_start'], end=config['date_end']):
    if pd.isna(start):
        start = config['date_start']
    if pd.isna(end):
        end = config['date_end']
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
            config['charts'][chart] = df.loc[chart, 'chart']
    return df

def createParPlotDict():
    pars = config['info']['parameters']['parameter'].to_list() + config['info']['parameters_ave']['parameter_ave'].to_list()
    plots = config['info']['parameters']['plot'].to_list() + config['info']['parameters_ave']['plot'].to_list()
    config['par_plot_dict'] = dict(zip(pars, plots))

    for style in config['styles']:
        config['par_style_dict'][style] = config['info']['parameters'].query(style + ' == True')['parameter'].to_list() + config['info']['parameters_ave'].query(style + ' == True')['parameter_ave'].to_list()

def processColours(df):
    df['rgb'] = list(zip(
        (df['r'] / 255),
        (df['g'] / 255),
        (df['b'] / 255)))
    df['rgba_str'] = "rgba(" + df['r'].astype(int).astype(str) + "," + df['g'].astype(int).astype(str) + "," + df['b'].astype(int).astype(str) + ",1)"
    return df

def openinfoFile():
    info_fname = "info.xlsx"
    config['info'] = pd.read_excel(io_dir / info_fname, sheet_name=None, index_col=0)
    config['info']['setup'] = processSetup(config['info']['setup'])
    config['info']['charts'] = processCharts(config['info']['charts'])
    createParPlotDict()
    config['info']['colours'] = processColours(config['info']['colours'])

# Data import functions
def selectDatasets():
    selected_cols = []
    for chart in config['charts']:
        selected_cols.append("selected_chart_" + str(chart))
        
    selected_pars_inc = config['info']['parameters'][selected_cols].isin([1]).any(axis=1)
    config['selected_pars'] = list(config['info']['parameters'][selected_pars_inc]['parameter'].values)
    
    selected_pars_ave_inc = config['info']['parameters_ave'][selected_cols].isin([1]).any(axis=1)
    config['selected_pars'] = config['selected_pars'] + list(config['info']['parameters_ave'][selected_pars_ave_inc]['parameter_ave'].values)
    selected_pars_all_inc = pd.concat([selected_pars_inc, selected_pars_ave_inc])

    config['selected_datasets'] = list(selected_pars_all_inc[selected_pars_all_inc].index.unique().values)

def readFile(dataset, folder, filename):
    file_pat = config['info']['datasets'].query('dataset == "' + dataset + '" & folder == "' + str(folder) + '"')['file_pat'][dataset]
    del_rows = config['info']['datasets'].query('dataset == "' + dataset + '" & folder == "' + str(folder) + '"')['Del_unit_rows'][dataset]
    
    for pat in config['filetypes']:
        if re.search(pat, file_pat, re.IGNORECASE):
            df = CustomDataImports.fileImport(dataset, folder, filename, pat)
            break
    if 'df' not in locals():
        raise ValueError("Unknown file type for " + str(dataset) + " folder " + str(folder) + " with " + filename)

    if len(df) > 0:
        if dataset in CustomDataImports.import_functions:
            df = CustomDataImports.import_functions[dataset](df)
        # Name parameter columns
        code_par_dict = dict(zip(config['info']['parameters'].query('dataset == "' + dataset + '"')['code'],
                                    config['info']['parameters'].query('dataset == "' + dataset + '"')['parameter']))
        df = df.rename(columns=code_par_dict)
        # Delete unit rows
        if not pd.isna(del_rows):
            df = df.drop(0).reset_index()
        #Choose parameters included in parameters sheet
        config['selected_pars'] = list(config['info']['parameters'].query('dataset == "' + dataset + '"')['parameter'].values)
        df = df.drop(df.columns.difference(['DateTime'] + config['selected_pars']), axis=1)
        #Make floats
        for col in config['selected_pars']:
            try:
                df.loc[:,col] = df.loc[:,col].astype(float)
            except:
                pass
        # Add blank row between files - to be implemented
        # if len(df) > 0:
        #    if not pd.isna(dataset_f_info['Add_blank_rows'][dataset]):
        #        df = df.append(pd.Series(), ignore_index=True)
        return df

def importFiles(dataset, folder):
    global config
    data_folder_path = Path(config['info']['datasets'].query('dataset == "' + dataset + '" & folder == "' + str(folder) + '"')['data_folder_path'][dataset])
    file_pat = config['info']['datasets'].query('dataset == "' + dataset + '" & folder == "' + str(folder) + '"')['file_pat'][dataset]
    files_imported = config['files_imported'][dataset][folder]
    dataset_in_folder = []
    for filename in tqdm(os.listdir(data_folder_path), desc="Open files to import"):
        if re.search(file_pat, filename) and not filename.startswith('.'):
            if filename not in files_imported:
                df = readFile(dataset, folder, filename)
                # Keep if longer than 0 lines and within timeframe
                if len(df) > 0 and max(df['DateTime']) >= config['date_start'] and min(df['DateTime']) <= config['date_end']:
                    dataset_in_folder.append(df)
                    files_imported.append(filename)
    if dataset_in_folder != [None] and len(dataset_in_folder) > 0:
        df_combined = pd.concat(dataset_in_folder, axis=0, ignore_index=True)
        return df_combined
    #else:
    #    df_combined = None
    

def combineSortData(df_list):
    # Create one dataframe from all days data
    for df in df_list.copy():
        if df_list[df] is None:
            df_list.pop(df)

    if df_list != [None] and len(df_list) > 0:
        df = pd.concat(df_list, axis=0, ignore_index=True)
        df.sort_values(by=['DateTime'], inplace=True)
        cols = ['DateTime']  + [col for col in df if col != 'DateTime']
        df = df[cols]
        df = df.reset_index(drop=True)

        df = df[df['DateTime'] >= config['date_start']]
        df = df[df['DateTime'] <= config['date_end']]
        return df
    else:
        print('No data to combine!')
    

def importData(dataset):
    num_folders = len(config['info']['datasets'].query('dataset == "' + dataset + '"')) + 1
    folder_data_list = []
    if dataset not in config['files_imported']:
        config['files_imported'][dataset] = {}
    for folder in range(1, num_folders):
        if folder not in config['files_imported'][dataset]:
            config['files_imported'][dataset][folder] = []
        # Custom pre-import functions
        if dataset in CustomDataImports.preimport_functions:
            config['supporting_data_dict'][dataset] = CustomDataImports.preimport_functions[dataset](dataset, folder)
        # Import files
        folder_data_list.append(importFiles(dataset, folder))
    if folder_data_list != [None] and len(folder_data_list) > 0:
        df_dataset = combineSortData(folder_data_list)
        return df_dataset

    

def importDatasets():
    selectDatasets()
    dataset_data = {}
    for dataset in tqdm(config['selected_datasets'], desc = "Import data from each dataset"):
        df = importData(dataset)
        if df is not None:
            dataset_data[dataset] = df
    return dataset_data

def averageReps(df):
    #with warnings.catch_warnings():
        #warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
        #warnings.filterwarnings('ignore', r'Degrees of freedom <= 0 for slice.')
    ave_cols = []
    if df is not None:
        for col in df.columns[1:].to_list():
            ave_col = config['info']['parameters'].query('parameter == "' + col + '"')['parameter_ave'][0]
            if ave_col != col:
                if ave_col not in ave_cols:
                    cols = config['info']['parameters'].query('parameter_ave == "' + ave_col + '"')['parameter'].to_list()
                    df[ave_col] = df[cols].mean(axis=1)
                    if len(cols) > 2:
                        df[ave_col + "_err"] = np.nanstd(df[cols], axis=1)
                    elif len(cols) == 2:
                        df[ave_col + "_err"] = np.abs((df[cols[0]] - df[cols[1]])/2)
                    else:
                        df[ave_col + "_err"] = 0
                    ave_cols.append(ave_col)

        err_pars = [ave_col + "_err" for ave_col in ave_cols]
        chosen_pars = config['selected_pars'] + err_pars
        chosen_pars = [par for par in chosen_pars if par in df.columns]

        df = df[["DateTime"]+ chosen_pars]
        return df

def processAllData(df_dict):
    df = combineSortData(df_dict)
    df = averageReps(df)

    if update:
        all_dict = {'all': config['all_data'], 'new': df}
        df = combineSortData(all_dict)

    return df

# Chart functions
def createChartDFs(chart):
    global config
    mask = (config['all_data']['DateTime'] >= config['info']['charts'].loc[chart, 'chart_range_start']) & (
            config['all_data']['DateTime'] <= config['info']['charts'].loc[chart, 'chart_range_end'])
    df = config['all_data'].loc[mask]
    if config['info']['charts'].loc[chart, 'chart_res'] != 0:
        df = df.resample("".join([str(info['charts'].loc[chart, 'chart_res']), 'T']), on='DateTime').mean()
        df = df.reset_index()
    else:
        df = df.reset_index(drop=True)
    
    if len(df) == 0:
        config['info']['charts'].loc[chart, 'chart_status'] = 'OFF'
        config['charts'].pop(chart)
        print("Turning OFF chart " + str(chart) + ": empty dataset within timeframe")
    else:
        config['chart_dfs'][chart] = df

def meltData(chart):
    data_cols = []
    err_cols = ["DateTime"]

    criteria = config['chart_dfs'][chart].isna().all()
    wide_data = config['chart_dfs'][chart][criteria.index[-criteria]]

    for col in wide_data.columns:
        if "_err" not in col:
            data_cols.append(col)
        else:
            err_cols.append(col)

    df = wide_data[data_cols].melt(id_vars=['DateTime'], var_name='Parameter', value_name='Value')
    df_err = wide_data[err_cols].melt(id_vars=['DateTime'], var_name='Parameter', value_name='Error')
    df_err['Parameter'] = df_err['Parameter'].str.replace(r'_err', '')

    df = df.set_index(['DateTime', 'Parameter', df.groupby(['DateTime', 'Parameter']).cumcount()])
    df_err = df_err.set_index(['DateTime', 'Parameter', df_err.groupby(['DateTime', 'Parameter']).cumcount()])

    df3 = (pd.concat([df, df_err], axis=1)
            .sort_index(level=2)
            .reset_index(level=2, drop=True)
            .reset_index())
    df3.sort_values(by=['DateTime', 'Parameter'], inplace=True)


    df3.drop(df3[df3['Parameter'].isin(config['par_style_dict']['point']) & np.isnan(df3['Value'])].index, inplace=True)
    df3.drop(df3[df3['Parameter'].isin(config['par_style_dict']['bar']) & np.isnan(df3['Value'])].index, inplace=True)

    df3.loc[:, 'Plot'] = df3['Parameter'].map(config['par_plot_dict'])
    config['chart_dfs_mlt'][chart] = df3

def chartPlotDicts(chart):
    par_info1 = config['info']['parameters'][
        config['info']['parameters']['parameter'].isin(config['chart_dfs_mlt'][chart].Parameter.unique())].drop(
        columns=["code", "parameter_ave"])
    par_info2 = config['info']['parameters_ave'][
        config['info']['parameters_ave']['parameter_ave'].isin(config['chart_dfs_mlt'][chart].Parameter.unique())].rename(
        columns={"parameter_ave": "parameter"})
    par_info_all = (par_info1.append(par_info2)).query('selected_chart_' + str(chart) + ' == 1')

    # Convert colour id to rgb string
    par_info_all['colour'].replace(config['info']['colours']['rgba_str'].to_dict(), inplace=True)
    par_info_all['fill'].replace(config['info']['colours']['rgba_str'].to_dict(), inplace=True)

    # Set defaults for NAs
    par_info_all['colour'].fillna(config['info']['colours'].query("theme == 'dark'")['rgba_str'].to_list()[0], inplace=True)
    par_info_all['fill'].fillna(config['info']['colours'].query("theme == 'dark'")['rgba_str'].to_list()[0], inplace=True)
    par_info_all['shape'].fillna(1, inplace=True)
    par_info_all['dash'].fillna("solid", inplace=True)
    par_info_all['show_in_legend'].fillna(True, inplace=True)

    par_info_all.loc[par_info_all['ribbon'] == True, 'fill'] = par_info_all.loc[par_info_all['ribbon'] == True, 'fill'].str.replace(",1\)", ",0.25)")

    config['plot_pars'][chart] = par_info_all

def processChartDFs(chart):
    for chart in config['charts'].copy():
        createChartDFs(chart)
    for chart in tqdm(config['charts'], desc="Melt data and create chart dictionaries"):
        meltData(chart)
        chartPlotDicts(chart)

#########

def main():
    processArguments()
    setIOFolder(io_dir)
    
    if not update: # Reimport all data
        openinfoFile()
    else: # Update existing config file data
        getConfig()

    dataset_data = importDatasets() # data dict per dataset
    config['all_data'] = processAllData(dataset_data) # all data combined and averaged
    # Create chart data
    processChartDFs(config['all_data']) # subsetted by chart criteria, melted and plot pars
    saveConfig()

    print(config['all_data'])

if __name__ == "__main__":
    main()

