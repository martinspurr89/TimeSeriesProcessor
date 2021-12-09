# Import packages
import sys
import getopt
import os
from pathlib import Path
from tqdm.autonotebook import tqdm
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pytz import timezone, utc
import bz2
import pickle
import plotly.graph_objects as go

import config
import ProcessData_resampler as ProcessData

def getNow():
    return datetime.now(timezone('UTC')).replace(microsecond=0)

def startT():
    global startT
    startT = getNow()

def endT(desc=""):
    global startT
    endT = getNow() - startT
    print(desc, endT)

def getData():
    pfile_path = config.io_dir / "Output" / 'all_data.pbz2'
    if os.path.exists(pfile_path) and config.update:
        print("Importing processed data...")
        with bz2.open(pfile_path, 'rb') as pfile:
            config.config['all_data'] = pickle.load(pfile)
    else:
        print("Fetching all data (or no processed all_data.pbz2 file exists)")
        ProcessData.main()
        config.update = True
        getData()

def meltAllData(wide_data):
    criteria = config.config['all_data'].isna().all()
    wide_data = config.config['all_data'][criteria.index[-criteria]]
    
    data_cols = []
    err_cols = ["DateTime"]
    for col in wide_data.columns:
        if "_err" not in col:
            data_cols.append(col)
        else:
            err_cols.append(col)

    df_dict = {}
    for col in tqdm(data_cols[1:], desc="Melt data cols"):
        df_dict[col] = wide_data[['DateTime', col]].melt(id_vars=['DateTime'], var_name = 'Parameter', value_name='Value')
        err_col = col + "_err"
        if err_col in err_cols:
            df_err = wide_data[['DateTime', err_col]].melt(id_vars=['DateTime'], var_name = 'Parameter', value_name='Error')
            df_err['Parameter'] = df_err['Parameter'].str.replace(r'_err', '')
            df_dict[col] = pd.concat([df_dict[col], df_err['Error']], axis=1)
        else:
            df_dict[col]['Error'] = np.nan
        if col in (config.config['par_style_dict']['point']) or col in (config.config['par_style_dict']['bar']):
            df_dict[col].drop(df_dict[col][np.isnan(df_dict[col]['Value'])].index, inplace=True)
    df_long = pd.concat(df_dict)
    df_long = df_long.reset_index(drop=True)
        
    df_long.sort_values(by=['DateTime', 'Parameter'], inplace=True)
    df_long.loc[:, 'Plot'] = df_long['Parameter'].map(config.config['par_plot_dict'])

    return(df_long)

def chartPlotDicts(plot_set):
    par_info1 = config.config['info']['parameters'][
        config.config['info']['parameters']['parameter'].isin(config.config['all_data_mlt'].Parameter.unique())].drop(
        columns=["code", "parameter_ave"])
    par_info2 = config.config['info']['parameters_ave'][
        config.config['info']['parameters_ave']['parameter_ave'].isin(config.config['all_data_mlt'].Parameter.unique())].rename(
        columns={"parameter_ave": "parameter"})
    par_info_all = (par_info1.append(par_info2)).query('selected_plot_' + str(plot_set) + ' == 1')

    # Convert colour id to rgb string
    par_info_all['colour'].replace(config.config['info']['colours']['rgba_str'].to_dict(), inplace=True)
    par_info_all['fill'].replace(config.config['info']['colours']['rgba_str'].to_dict(), inplace=True)

    # Set defaults for NAs
    par_info_all['colour'].fillna(config.config['info']['colours'].query("theme == 'dark'")['rgba_str'].to_list()[0], inplace=True)
    par_info_all['fill'].fillna(config.config['info']['colours'].query("theme == 'dark'")['rgba_str'].to_list()[0], inplace=True)
    par_info_all['shape'].fillna(1, inplace=True)
    par_info_all['dash'].fillna("solid", inplace=True)
    par_info_all['show_in_legend'].fillna(True, inplace=True)

    par_info_all.loc[par_info_all['ribbon'] == True, 'fill'] = par_info_all.loc[par_info_all['ribbon'] == True, 'fill'].str.replace(",1\)", ",0.25)", regex=True)
    par_info_all.loc[par_info_all['bar'] == True, 'fill'] = par_info_all.loc[par_info_all['bar'] == True, 'fill'].str.replace(",1\)", ",0.75)", regex=True)

    config.config['plot_pars'][plot_set] = par_info_all

def getPlotSetInfo(plot_set):
    plot_set_info = config.config['info']['plots'].loc[config.config['info']['plots'].index == plot_set]
    plot_set_info = plot_set_info[plot_set_info['plot'].isin(config.config['all_data_mlt'].Plot.unique().tolist())]
    return(plot_set_info)

def addTrace(par, plot_fig, plot_set):
    par_info = config.config['plot_pars'][plot_set].query('parameter == "' + par + '"')

    def addLine(plot_fig):
        legend_show = True #default on
        if any(par_info['show_in_legend'].values == False) or any(par_info['point'].values == True) or any(par_info['bar'].values == True):
            legend_show = False
        trace = trace_base
        trace.update(mode = "lines",
                    line=dict(color=par_info['colour'][0], width=2, dash=par_info['dash'][0], shape=par_info['line'][0]),
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
    
    def addBars(plot_fig):
        bar_base = go.Scatter(x=x_data,
                                name=par_info['parameter_lab'][0],
                                line=dict(color=par_info['colour'][0], dash = 'dot'),
                                connectgaps=True,
                                legendgroup=par_info['parameter_lab'][0],
                                showlegend=False,
                                hoverinfo='skip')
        trace1 = bar_base
        trace1.update(y=par_info['bar_order'][0] + y_data.round()/2, mode='lines', line=dict(width=0), line_shape = "hv")
        plot_fig.add_trace(trace1)
        trace2 = bar_base
        trace2.update(y=par_info['bar_order'][0] - y_data.round()/2, fill='tonexty', mode='none', fillcolor=par_info['fill'][0],
                    line=dict(width=0.5), line_shape = "hv", showlegend=True, hoverinfo='all') #fill to trace1 y
        plot_fig.add_trace(trace2)

        return(plot_fig)

    if len(par_info) != 0:
        par_data = config.config['chart_dfs_mlt'][chart][config.config['chart_dfs_mlt'][chart].Parameter == par]
        x_data = par_data.DateTime
        y_data = par_data.Value
        y_error = par_data.Error

        trace_base = go.Scatter(x=x_data, y=y_data,
                    name=par_info['parameter_lab'][0], 
                    legendgroup=par_info['parameter_lab'][0])

        if not any(pd.isna(par_info['line'].values)):
            plot_fig = addLine(plot_fig)

        if any(par_info['point'].values == True):
            plot_fig = addPoints(plot_fig)

        if any(par_info['ribbon'].values == True):
            plot_fig = addRibbon(plot_fig)

        if any(par_info['bar'].values == True):
            plot_fig = addBars(plot_fig)
    return(plot_fig)

def createPlotFig(plot, plot_set):    
    plot_set_info = getPlotSetInfo(plot_set)
    plot_set_pars = config.config['plot_pars'][plot_set].query('plot == "' + plot + '"').parameter.unique()
    plot_info = plot_set_info.query('plot == "' + plot + '"')
    plot_data = config.config['all_data_mlt'].query('Plot == "' + plot + '"')
    plot_fig = go.Figure()
    #Add traces
    for par_id in range(0, len(plot_data.Parameter.unique())):
        par = plot_data.Parameter.unique()[par_id]
        if par in plot_set_pars:
            plot_fig = addTrace(par, plot_fig, plot_set)
    #Modify plot layout
    plot_fig = modifyPlot(plot_fig, plot, chart)
    plot_fig = setAxisRange(plot_fig, plot, chart)
    #Add date to last plot in chart
    if plot == chart_info['plot'].to_list()[len(chart_info['plot'].to_list())-1]:
        plot_fig.update_xaxes(showticklabels=True, ticks="outside")

    plot_fig = FigureResampler(plot_fig)

    return(plot_fig)

def createPlotSetFig(plot_set):
    plot_set_fig = {}
    # For each plot
    for plot in tqdm(getPlotSetInfo(plot_set)['plot'].to_list(), desc = "Creating plots for plot_set " + str(plot_set)):
        plot_set_fig[plot] =  createPlotFig(plot, plot_set)
    return(chart_fig)


startT = getNow()
print("Starting processing at: " + str(startT))

ProcessData.processArguments()
ProcessData.openinfoFile()
getData()

config.config['all_data_mlt'] = meltAllData(config.config['all_data'])
for plot_set in set(config.config['plot_sets'].values()):
    chartPlotDicts(plot_set)
endT()

pbar = tqdm(set(config.config['plot_sets'].values()))
for plot_set in pbar:
    pbar.set_description("Creating plot_set %s" % plot_set)
    config.config['plot_set_figs'][plot_set]  = createPlotSetFig(plot_set)

for chart in config.config['charts']:
    if config.config['info']['charts'].loc[chart, 'html_on'] == "ON":
        config.config['div_chart_figs'][chart] = createOfflineCharts(chart)
        exportHTML(chart)
    if config.config['info']['charts'].loc[chart, 'png_on'] == "ON":
        exportImage(chart, 'png')
    if config.config['info']['charts'].loc[chart, 'pdf_on'] == "ON":
        exportImage(chart, 'pdf')
    config.config['dcc_chart_figs'][chart] = createDashCharts(chart)

# # saveObject(config.config, (config.io_dir / 'Temp' / 'config.pbz2'))
export_config = {k: config.config[k] for k in ['charts', 'info', 'date_end', 'date_start', 'chart_dfs_mlt', 'dcc_chart_figs'] if k in config.config}
saveObject(export_config, (config.io_dir / 'Output' / 'sub_config.pbz2'))

