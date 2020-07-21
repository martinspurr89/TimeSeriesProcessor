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
import plotly.graph_objects as go
import plotly.offline.offline
import math
import humanize
import copy
from PIL import Image
import warnings
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
import dash_core_components as dcc

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
    global config
    global update
    pfile_path = io_dir / "Temp" / 'config.pkl'
    if os.path.exists(pfile_path):
        with open(pfile_path, 'rb') as pfile:
            items = pickle.load(pfile)
        for key in list(items.keys()):
            config[key] = items[key]
    else:
        print("No pickled config.pkl data file exists, continuing with full data import!")
        update = False
        openinfoFile()

def saveConfig():
    temp_folder = io_dir / "Temp"
    deleteFolderContents(temp_folder)
    with open(temp_folder / 'config.pkl', 'wb') as pfile:
        pickle.dump(config, pfile, protocol=-1)

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
    global config
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
    global config
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
    global config
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
    global config
    info_fname = "info.xlsx"
    config['info'] = pd.read_excel(io_dir / info_fname, sheet_name=None, index_col=0)
    config['info']['setup'] = processSetup(config['info']['setup'])
    config['info']['charts'] = processCharts(config['info']['charts'])
    createParPlotDict()
    config['info']['colours'] = processColours(config['info']['colours'])

# Data import functions
def selectDatasets():
    global config
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
    global config
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
        #config['selected_pars'] = list(config['info']['parameters'].query('dataset == "' + dataset + '"')['parameter'].values)
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

        df = df[df['DateTime'] >= config['date_start']]
        df = df[df['DateTime'] <= config['date_end']]
        return df
    else:
        print('No data to combine!')
    

def importData(dataset):
    global config
    num_folders = len(config['info']['datasets'].query('dataset == "' + dataset + '"')) + 1
    folder_data_list = {}
    if dataset not in config['files_imported']:
        config['files_imported'][dataset] = {}
    for folder in range(1, num_folders):
        if folder not in config['files_imported'][dataset]:
            config['files_imported'][dataset][folder] = []
        # Custom pre-import functions
        if dataset in CustomDataImports.preimport_functions:
            config['supporting_data_dict'][dataset] = CustomDataImports.preimport_functions[dataset](dataset, folder)
        # Import files
        folder_data_list[folder] = importFiles(dataset, folder)
    if (not any(df is None for df in folder_data_list)) & (len(folder_data_list) > 0):
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
        df = df.resample("".join([str(config['info']['charts'].loc[chart, 'chart_res']), 'T']), on='DateTime').mean()
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
    global config
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
    global config
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

def getChartInfo(chart):
    chart_info = config['info']['plots'].loc[config['info']['plots'].index == chart]
    chart_info = chart_info[chart_info['plot'].isin(config['chart_dfs_mlt'][chart].Plot.unique().tolist())]
    return(chart_info)

def addTrace(par, plot_fig, chart):
    par_info = config['plot_pars'][chart].query('parameter == "' + par + '"')

    def addLine(plot_fig):
        legend_show = True #default on
        if par_info['show_in_legend'].values == False or par_info['point'].values == True or par_info['bar'].values == True:
            legend_show = False
        trace = trace_base
        trace.update(mode = "lines",
                    line=dict(color=par_info['colour'][0], width=2, dash=par_info['dash'][0]),
                    connectgaps=False,
                    showlegend=legend_show)
        plot_fig.add_trace(trace)
        return(plot_fig)

    def addPoints(plot_fig):
        trace = trace_base
        trace.update(mode = 'markers',
                    marker = dict(color = par_info['fill'][0], symbol = par_info['shape'][0],
                                line = dict(color = par_info['colour'][0],width=1)),
                    showlegend = bool(par_info['show_in_legend'][0]),
                    error_y = dict(type = 'data', array = y_error, visible = True))
        plot_fig.add_trace(trace)
        return(plot_fig)
    
    def addRibbon(plot_fig):
        ribbon_base = go.Scatter(x=x_data,
                                name=par_info['parameter_lab'][0],
                                line=dict(color=par_info['colour'][0], dash = 'dot'),
                                connectgaps=True,
                                legendgroup=par_info['parameter_lab'][0],
                                showlegend=False,
                                hoverinfo='skip')
        trace1 = ribbon_base
        trace1.update(y=y_data + y_error, mode='lines', line=dict(width=0))
        plot_fig.add_trace(trace1)
        trace2 = ribbon_base
        trace2.update(y=y_data - y_error, fill='tonexty', mode='none', fillcolor=par_info['fill'][0],
                    line=dict(width=0.5)) #fill to trace1 y
        plot_fig.add_trace(trace2)
        return(plot_fig)

    if len(par_info) != 0:
        par_data = config['chart_dfs_mlt'][chart][config['chart_dfs_mlt'][chart].Parameter == par]
        x_data = par_data.DateTime
        y_data = par_data.Value
        y_error = par_data.Error

        trace_base = go.Scatter(x=x_data, y=y_data,
                    name=par_info['parameter_lab'][0], 
                    legendgroup=par_info['parameter_lab'][0])

        if par_info['line'].values == True:
            plot_fig = addLine(plot_fig)

        if par_info['point'].values == True:
            plot_fig = addPoints(plot_fig)

        if par_info['ribbon'].values == True:
            plot_fig = addRibbon(plot_fig)
    return(plot_fig)

def modifyPlot(plot_fig, plot, chart):
    plot_info = getChartInfo(chart).query('plot == "' + plot + '"')
    plot_fig.update_layout(
        margin=dict(l=100, r=250, b=15, t=15, pad=10),
        template="simple_white",
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Arial",
            size=config['info']['charts']['font_size'][chart],
            color="black"
        ))
    plot_fig.update_yaxes(title_text=plot_info['ylab'][chart], mirror=True)
    plot_fig.update_xaxes(showgrid=True, showticklabels=False, ticks="",
        showline=True, mirror=True,
        range=[min(config['chart_dfs_mlt'][chart].DateTime), max(config['chart_dfs_mlt'][chart].DateTime)],
        )#fixedrange=True) #prevent x zoom
    return(plot_fig)

def getYMin(plot, chart):
    plot_info = getChartInfo(chart).query('plot == "' + plot + '"')
    plot_data = config['chart_dfs_mlt'][chart].query('Plot == "' + plot + '"')
    if pd.isna(plot_info['ymin'][chart]):
        ymin = min(plot_data['Value'] - plot_data['Error'].fillna(0))
        if any(config['plot_pars'][chart].query('plot == "' + plot + '"')['point']) + any(config['plot_pars'][chart].query('plot == "' + plot + '"')['bar']) > 0:
            if ymin > 0:
                ymin = 0.95 * ymin
            else:
                ymin = 1.05 * ymin
    else:
        ymin = plot_info['ymin'][chart]
    return(ymin)

def getYMax(plot, chart):
    plot_info = getChartInfo(chart).query('plot == "' + plot + '"')
    plot_data = config['chart_dfs_mlt'][chart].query('Plot == "' + plot + '"')
    if pd.isna(plot_info['ymax'][chart]):
        ymax = max(plot_data['Value'] + plot_data['Error'].fillna(0))
        if any(config['plot_pars'][chart].query('plot == "' + plot + '"')['point']) + any(config['plot_pars'][chart].query('plot == "' + plot + '"')['bar']) > 0:
            if ymax > 0:
                ymax = 1.05 * ymax
            else:
                ymax = 0.95 * ymax
    else:
        ymax = plot_info['ymax'][chart]
    return(ymax)

def setAxisRange(plot_fig, plot, chart):
    plot_info = getChartInfo(chart).query('plot == "' + plot + '"')
    ymin = getYMin(plot, chart)
    ymax = getYMax(plot, chart)
    if plot_info['log'][chart] == True:
        plot_fig.update_layout(yaxis_type="log")
        plot_fig.update_yaxes(range=[math.log(ymin, 10), math.log(ymax, 10)])
    else:
        plot_fig.update_yaxes(range=[ymin, ymax])
    return(plot_fig)

def createPlotFig(plot, chart):    
    chart_info = getChartInfo(chart)
    plot_info = chart_info.query('plot == "' + plot + '"')
    plot_data = config['chart_dfs_mlt'][chart].query('Plot == "' + plot + '"')
    plot_fig = go.Figure()
    #Add traces
    for par_id in range(0, len(plot_data.Parameter.unique())):
        par = plot_data.Parameter.unique()[par_id]
        plot_fig = addTrace(par, plot_fig, chart)
    #Modify plot layout
    plot_fig = modifyPlot(plot_fig, plot, chart)
    plot_fig = setAxisRange(plot_fig, plot, chart)
    #Add date to last plot in chart
    if plot == chart_info['plot'].to_list()[len(chart_info['plot'].to_list())-1]:
        plot_fig.update_xaxes(showticklabels=True, ticks="outside")

    return(plot_fig)


#Create plotly chart figures
def createChartFig(chart):
    chart_fig = {}
    # For each plot
    for plot in tqdm(getChartInfo(chart)['plot'].to_list(), desc = "Creating plots for chart " + str(chart)):
        chart_fig[plot] =  createPlotFig(plot, chart)
    return(chart_fig)

#Create offline interactive chart figures
def createOfflineCharts(chart):
    div_chart_fig = {}
    p = 0
    for plot in config['chart_figs'][chart]:
        div_chart_fig[plot] = plotly.offline.plot(config['chart_figs'][chart][plot], include_plotlyjs=False, output_type='div')
        div_chart_fig[plot] = div_chart_fig[plot].replace('style="height:100%; width:100%;"',
        'style="height:20%; width:98%;"')
        if p == len(config['chart_figs'][chart])-1: #if the last chart
            div_chart_fig[plot] = div_chart_fig[plot].replace('style="height:20%;"', 'style="height:25%;"')
        p = p + 1
    return(div_chart_fig)

def exportHTML(chart):
    #Build start and end strings
    html_string_start = '''
    <html>
        <head>
            <style>body{ margin:0 100; background:white; font-family: Arial, Helvetica, sans-serif}</style>
        </head>
        <body>
            <h1>''' + config['project'] + ''' interactive data</h1>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            '''

    html_string_end = '''
        </body>
    </html>'''

    #Create html header
    html_string = html_string_start

    chart_start_date = config['info']['charts']['chart_range_start'][chart]
    chart_end_date = config['info']['charts']['chart_range_end'][chart]
    html_string = html_string + '''<p>''' + humanize.naturaldate(chart_start_date) + ''' to ''' + humanize.naturaldate(chart_end_date)

    resample = config['info']['charts']['chart_res'][chart]
    if resample != 0:
        html_string = html_string + ''' | Data resampled over ''' + str(resample) + ''' minutes'''
    
    html_string = html_string + '''</p>'''

    #Add divs to html string
    for plot in config['div_chart_figs'][chart]:
        html_string = html_string + config['div_chart_figs'][chart][plot]

    #write finished html
    html_string + html_string_end
    html_filename = str(chart) + "_" + config['charts'][chart] + ".html"
    checkFolderExists(io_dir / "Output")
    hreport = open(io_dir / "Output" / html_filename,'w')
    hreport.write(html_string)
    hreport.close()

def createTempChartDir(chart, otype):
    temp_path = io_dir / "Temp" / (otype + "s")
    deleteFolderContents(temp_path)
    odir = temp_path /  (str(chart) + "_" + config['charts'][chart])
    odir.mkdir(parents=True, exist_ok=True)
    return(odir)

def exportImage(chart, otype):
    image_dir = createTempChartDir(chart, otype.upper())
    divisor = len(config['chart_figs'][chart])-1 + config['info']['charts']['last_fig_x'][chart]
    scaler = {'png': config['info']['charts']['dpi'][chart]/96,
              'pdf': 1}
    #Export individual images
    p = 0
    for plot in config['chart_figs'][chart]:
        height = config['info']['charts'][otype + '_height'][chart]/divisor
        if p == len(config['chart_figs'][chart])-1: #if the last chart
            height = height * config['info']['charts']['last_fig_x'][chart]
        
        chart_to_export = copy.copy(config['chart_figs'][chart][plot])
        chart_to_export.update_layout(width=config['info']['charts'][otype + '_width'][chart],
                                            height=height)
        chart_to_export.write_image(str(image_dir / (str(p).zfill(2) + "_" + plot + "." + otype)),
                                            scale=scaler)
        p = p + 1

    #Combine individual images and output to file
    if otype == 'png':
        combinePNG(image_dir, chart)
    elif otype == 'pdf':
        combinePDF(image_dir, chart)
    
    #Delete temp images
    try:
        shutil.rmtree(image_dir)
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))

def combinePNG(png_dir, chart):
    images = [Image.open(png_dir / x) for x in os.listdir(png_dir)]
    widths, heights = zip(*(i.size for i in images))

    max_width = max(widths)
    total_height = sum(heights)

    new_im = Image.new('RGBA', (max_width, total_height))

    y_offset = 0
    for im in images:
        new_im.paste(im, (0,y_offset))
        y_offset += im.size[1]

    png_filename = str(chart) + "_" + config['charts'][chart] + ".png"
    new_im.save(io_dir / "Output" /  png_filename)

def combinePDF(pdf_dir, chart):
    #Combine pdfs
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'.*Multiple definitions in dictionary.*')
        merger = PdfFileMerger(strict=False)
        for filename in os.listdir(pdf_dir):
            merger.append(PdfFileReader(str(pdf_dir / filename), strict=False))
        with open(str(pdf_dir / "all_pages.pdf"), 'wb') as fh:
            merger.write(fh)

        #Create combined pdf on one page
        with open(str(pdf_dir / 'all_pages.pdf'), 'rb') as input_file:
            # load input pdf
            input_pdf = PdfFileReader(input_file, strict=False)
            num_pages = input_pdf.getNumPages()
            output_pdf = input_pdf.getPage(num_pages-1)

            for p in reversed(range(0,num_pages-1)):
                second_pdf = input_pdf.getPage(p)
                # dimensions for offset from loaded page (adding it to the top)
                offset_x = 0 # use for x offset -> output_pdf.mediaBox[2]
                offset_y = output_pdf.mediaBox[3]
                #merge pdf pages
                output_pdf.mergeTranslatedPage(second_pdf, offset_x, offset_y, expand=True)

            # write finished pdf
            output_file = io_dir / "Output" / (str(chart) + "_" + config['charts'][chart] + ".pdf")
            with open(output_file, 'wb') as out_file:
                    write_pdf = PdfFileWriter()
                    write_pdf.addPage(output_pdf)
                    write_pdf.write(out_file)

def createDashCharts(chart):
    dcc_chart_fig = []
    p = 0
    for plot in config['chart_figs'][chart]:
        if p != len(config['chart_figs'][chart])-1: #if not the last chart
            height = '20vh'
        else:
            height = '25vh'
        dcc_chart_fig.append(dcc.Graph(id='graph' + str(p),
                                            figure=config['chart_figs'][chart][plot],
                                            style={'width': '98vw', 'height': ''+ height + ''}))
        p = p + 1
    return(dcc_chart_fig)

#Create offline interactive chart figures
def create_offline_graphs(chart):
    div_chart_fig = OrderedDict()
    p = 0
    for plot in chart_figs[chart]:
        div_chart_fig[plot] = plotly.offline.plot(chart_figs[chart][plot], include_plotlyjs=False, output_type='div')
        div_chart_fig[plot] = div_chart_fig[plot].replace('style="height:100%; width:100%;"',
        'style="height:20%; width:98%;"')
        if p == len(chart_figs[chart])-1: #if the last chart
            div_chart_fig[plot] = div_chart_fig[plot].replace('style="height:20%;"', 'style="height:25%;"')
        p = p + 1
    return(div_chart_fig)

#########

def createApp():
    global app
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    #app = JupyterDash('__name__')
    config['app'] = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    card_style = {
        "box-shadow": "0 4px 5px 0 rgba(0,0,0,0.14), 0 1px 10px 0 rgba(0,0,0,0.12), 0 2px 4px -1px rgba(0,0,0,0.3)"
    }

    #app.scripts.config.serve_locally = True

    # app.layout = dcc.Loading(
    #     children=[html.Div(

    tabs_init = []
    p = 0
    for chart in charts:
        tabs_init.append(dcc.Tab(label=config['charts'][chart], value="".join(["tab-", str(p)]),
                                style={'backgroundColor': '#f5f5f5'}))
        p = p+1

    app.layout = html.Div(className="sans-serif",
                        children=[
                        html.Div(
                            className="w-60 center pt4",
                            children=[
                                dcc.Tabs(
                                    id="tabs",
                                    value="tab-0",
                                    children=tabs_init,
                                    colors={
                                        "primary": "white",
                                        "background": "white",
                                        "border": "#d2d2d2",
                                    },
                                    parent_style=card_style,
                                ),
                                html.Div(
                                    children=[
                                        dcc.Loading(id='tabs-content',
                                                    type='graph', className='pv6')
                                    ],
                                    className='pa4'
                                ),
                            ],
                            style={},
                        ),
                    ],
                )# ], type='default', fullscreen=True)

    @app.callback(Output('tabs-content', 'children'),
                [Input('tabs', 'value')])
    def render_content(tab):
        time.sleep(2)
        if tab == 'tab-0':
            return html.Div(children=[
                # html.Label('From 1994 to 2018', id='time-range-label'),
                html.Div(id='loading-0', children=config['dcc_chart_figs'][0])])
        elif tab == 'tab-1':
            return html.Div(id='loading-1', children=config['dcc_chart_figs'][1])
        elif tab == 'tab-2':
            return html.Div(id='loading-2', children=config['dcc_chart_figs'][2])
        elif tab == 'tab-3':
            return html.Div(id='loading-3', children=config['dcc_chart_figs'][3])

    print("App ready: " + str(date_now))


#########

def main():
    global config
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

    pbar = tqdm(config['charts'])
    for chart in pbar:
        pbar.set_description("Exporting chart %s" % chart)
        config['chart_figs'][chart]  = createChartFig(chart)
        config['div_chart_figs'][chart] = createOfflineCharts(chart)
        exportHTML(chart)
        exportImage(chart, 'png')
        exportImage(chart, 'pdf')
        config['dcc_chart_figs'][chart] = createDashCharts(chart)

if __name__ == "__main__":
    main()
    createApp()
    config['app'].run_server()
    #debug=True, dev_tools_hot_reload_interval=5000)
                   #dev_tools_hot_reload_max_retry=30)

