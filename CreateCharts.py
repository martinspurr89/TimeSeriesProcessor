# Import packages
import os
from tqdm.autonotebook import tqdm
import pandas as pd
import numpy as np
from datetime import datetime
from pytz import timezone
import bz2
import pickle
import plotly.graph_objects as go
from dash import dcc

import config
import ProcessData_resampler as ProcessData

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

def plotParDicts(plot_set):
    all_data_pars = [c for c in config.config['all_data'].columns[1:] if not "_err" in c]
    par_info1 = config.config['info']['parameters'][
        config.config['info']['parameters']['parameter'].isin(all_data_pars)].drop(
        columns=["code", "parameter_ave"])
    par_info2 = config.config['info']['parameters_ave'][
        config.config['info']['parameters_ave']['parameter_ave'].isin(all_data_pars)].rename(
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
    plot_set_info = plot_set_info[plot_set_info['plot'].isin(config.config['plot_pars'][plot_set]['plot'].unique())]
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
        trace.update(#x = x_data, y = y_data,
                    mode = 'markers',
                    marker = dict(color = par_info['fill'][0], symbol = par_info['shape'][0],
                                line = dict(color = par_info['colour'][0],width=1)),
                    showlegend = bool(par_info['show_in_legend'][0]))
        if error_bars:
            trace.update(error_y = dict(type = 'data', visible = True))#, array = y_error))
        plot_fig.add_trace(trace)
        return(plot_fig)
    
    def addRibbon(plot_fig):
        ribbon_base = go.Scatter(#x=x_data,
                                name=par_info['parameter_lab'][0],
                                line=dict(color=par_info['colour'][0], dash = 'dot'),
                                connectgaps=True,
                                legendgroup=par_info['parameter_lab'][0],
                                showlegend=False,
                                hoverinfo='skip')
        trace1 = ribbon_base
        trace1.update(mode='lines', line=dict(width=0))
        plot_fig.add_trace(trace1)
        trace2 = ribbon_base
        trace2.update(fill='tonexty', mode='none', fillcolor=par_info['fill'][0],
                    line=dict(width=0.5)) #fill to trace1 y
        plot_fig.add_trace(trace2)
        return(plot_fig)
    
    def addBars(plot_fig):
        bar_base = go.Scatter(name=par_info['parameter_lab'][0],
                                line=dict(color=par_info['colour'][0], dash = 'dot'),
                                connectgaps=True,
                                legendgroup=par_info['parameter_lab'][0],
                                showlegend=False,
                                hoverinfo='skip')
        trace1 = bar_base
        trace1.update(#x = x_data, y=par_info['bar_order'][0] + y_data.round()/2, 
                        mode='lines', line=dict(width=0), line_shape = "hv")
        plot_fig.add_trace(trace1)
        trace2 = bar_base
        trace2.update(#x = x_data, y=par_info['bar_order'][0] - y_data.round()/2,
                    fill='tonexty', mode='none', fillcolor=par_info['fill'][0],
                    line=dict(width=0.5), line_shape = "hv", showlegend=True, hoverinfo='all') #fill to trace1 y
        plot_fig.add_trace(trace2)

        return(plot_fig)

    if len(par_info) != 0:
        all_data_pars = [c for c in config.config['all_data'].columns[1:] if not "_err" in c]


        x_data = config.config['all_data'].DateTime
        y_data = config.config['all_data'][par]
        error_bars = False
        if par + "_err" in all_data_pars:
            error_bars = True
            y_error = config.config['all_data'][par + "_err"]

        if any(par_info['point'] ==True) or any(par_info['bar'] ==True):
            if error_bars:
                y_error.drop(y_error[np.isnan(y_data)].index, inplace=True)
            x_data.drop(x_data[np.isnan(y_data)].index, inplace=True)
            y_data.drop(y_data[np.isnan(y_data)].index, inplace=True)

        trace_base = go.Scatter(x=[], y=[],
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

def modifyPlot(plot_fig, plot, chart):
    plot_info = getPlotSetInfo(chart).query('plot == "' + plot + '"')
    plot_fig.update_layout(
        margin=dict(l=100, r=250, b=15, t=15, pad=10),
        template="simple_white",
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Arial",
            color="black"
        ))
    plot_fig.update_yaxes(title_text=plot_info['ylab'][chart], mirror=True)
    plot_fig.update_xaxes(showgrid=True, showticklabels=False, ticks="",
        showline=True, mirror=True,
        range=[min(config.config['all_data'].DateTime), max(config.config['all_data'].DateTime)])
        #fixedrange=True) #prevent x zoom
    return(plot_fig)

def createPlotFig(plot, plot_set):    
    plot_set_info = getPlotSetInfo(plot_set)
    plot_set_pars = config.config['plot_pars'][plot_set].query('plot == "' + plot + '"').parameter.unique().tolist()
    plot_info = plot_set_info.query('plot == "' + plot + '"')
    plot_data = config.config['all_data'][['DateTime'] + plot_set_pars]
    plot_fig = go.Figure()
    #Add traces
    for par in plot_set_pars:
        plot_fig = addTrace(par, plot_fig, plot_set)
    #Modify plot layout
    plot_fig = modifyPlot(plot_fig, plot, plot_set)
    return(plot_fig)

def createPlotSetFig(plot_set):
    plot_set_fig = {}
    # For each plot
    for plot in tqdm(getPlotSetInfo(plot_set)['plot'].to_list(), desc = "Creating plots for plot_set " + str(plot_set)):
        plot_set_fig[plot] =  createPlotFig(plot, plot_set)
    return(plot_set_fig)

def editPlotforChart(plot, chart):
    #fontsize
    plot_fig = setAxisRange(plot_fig, plot, chart)
    #Add date to last plot in chart
    if plot == plot_set_info['plot'].to_list()[len(plot_set_info['plot'].to_list())-1]:
        plot_fig.update_xaxes(showticklabels=True, ticks="outside")

def createDashCharts(plot_set):
    dcc_chart_fig = []
    p = 0
    config.config['dcc_plot_names'][plot_set] = {}
    for plot in config.config['plot_set_figs'][plot_set]:
        if p != len(config.config['plot_set_figs'][plot_set])-1: #if not the last plot
            height = '20vh'
        else:
            height = '25vh'
        dcc_chart_fig.append(dcc.Graph(id='graph' + str(p),
                                            figure=config.config['plot_set_figs'][plot_set][plot],
                                            style={'width': '98vw', 'height': ''+ height + ''}))
        config.config['dcc_plot_names'][plot_set]['graph' + str(p)] = plot
        p = p + 1
    return(dcc_chart_fig)

def saveObject(object_to_save, filepath):
    with bz2.BZ2File(filepath, 'wb') as f:
        pickle.dump(object_to_save, f)

def main():
    ProcessData.processArguments()
    ProcessData.openinfoFile()
    getData()

    pbar = tqdm(set(config.config['plot_sets'].values()))
    for plot_set in pbar:
        pbar.set_description("Creating plot_set %s" % plot_set)
        plotParDicts(plot_set)
        config.config['plot_set_figs'][plot_set]  = createPlotSetFig(plot_set)
        config.config['dcc_plot_set_figs'][plot_set] = createDashCharts(plot_set)

        #pbar.set_description("Exporting chart %s" % plot_set)
        #if config.config['info']['charts'].loc[chart, 'html_on'] == "ON":
        #    config.config['div_chart_figs'][chart] = createOfflineCharts(chart)
        #    exportHTML(chart)
        #if config.config['info']['charts'].loc[chart, 'png_on'] == "ON":
        #    exportImage(chart, 'png')
        #if config.config['info']['charts'].loc[chart, 'pdf_on'] == "ON":
        #    exportImage(chart, 'pdf')
        

    # # saveObject(config.config, (config.io_dir / 'Temp' / 'config.pbz2'))
    export_config = {k: config.config[k] for k in ['plot_sets', 'info', 'date_end', 'date_start', 'dcc_plot_set_figs', 'plot_pars', 'dcc_plot_names'] if k in config.config}
    saveObject(export_config, (config.io_dir / 'Output' / 'sub_config2.pbz2'))

if __name__ == "__main__":
    main()