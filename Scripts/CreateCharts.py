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
import re
from copy import deepcopy

import Scripts.config as config
import Scripts.ProcessData_resampler as ProcessData

def getData():
    pfile_path = config.io_dir / "Output" / 'all_data.pbz2'
    if os.path.exists(pfile_path) and config.update:
        print("Importing processed data...")
        with bz2.open(pfile_path, 'rb') as pfile:
            config.data['all_data'] = pickle.load(pfile)
    else:
        if config.update:
            print("No processed all_data.pbz2 file exists - fetching all data")
        else:
            print("Fetching all data")
        ProcessData.main()
        config.update = True
        getData()

def plotSetParDict(df):
    for plot_set in config.config['plot_sets']:
        for plot in config.config['plot_set_plots'][plot_set]:
            df_pars = list(df.query('plot == "' + plot + '"').query("selected_plot_set_" + str(plot_set) + " == " + str(1))['parameter_lab'])
            config.config['plot_set_plots'][plot_set][plot] = list(dict.fromkeys(config.config['plot_set_plots'][plot_set][plot] + df_pars))


def plotParDicts():
    all_data_pars = [c for c in config.data['all_data'].columns[1:] if not "_err" in c]
    par_info1 = config.config['info']['parameters'][
        config.config['info']['parameters']['parameter'].isin(all_data_pars)].drop(
        columns=["code", "parameter_ave"])
    par_info2 = config.config['info']['parameters_ave'][
        config.config['info']['parameters_ave']['parameter_ave'].isin(all_data_pars)].rename(
        columns={"parameter_ave": "parameter"})
    par_info_all = par_info1.append(par_info2)

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

    config.config['plot_pars'] = par_info_all
    plotSetParDict(par_info_all)

def getPlotsInfo():
    plots_info = config.config['info']['plots']
    plots_info = plots_info[plots_info.index.isin(config.config['plot_pars']['plot'].unique())]
    return(plots_info)

def addTrace(par, plot_fig):
    par_info = config.config['plot_pars'].query('parameter == "' + par + '"')

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
        all_data_pars = [c for c in config.data['all_data'].columns[1:] if not "_err" in c]


        x_data = deepcopy(config.data['all_data'].DateTime)
        y_data = deepcopy(config.data['all_data'][par])
        error_bars = False
        if par + "_err" in all_data_pars:
            error_bars = True
            y_error = deepcopy(config.data['all_data'][par + "_err"])

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

def modifyPlot(plot_fig, plot):
    plot_info = getPlotsInfo().query('plot == "' + plot + '"')
    plot_fig.update_layout(
        margin=dict(l=100, r=250, b=15, t=15, pad=10),
        template="simple_white",
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Arial",
            color="black"
        ))
    plot_fig.update_yaxes(title_text=plot_info['ylab'][plot], mirror=True)
    plot_fig.update_xaxes(showgrid=True, showticklabels=False, ticks="",
        showline=True, mirror=True,
        range=[min(config.data['all_data'].DateTime), max(config.data['all_data'].DateTime)])
        #fixedrange=True) #prevent x zoom
    return(plot_fig)

def createPlotFig(plot):    
    plot_pars = config.config['plot_pars'].query('plot == "' + plot + '"').parameter.unique().tolist()
    plot_fig = go.Figure()
    #Add traces
    for par in plot_pars:
        plot_fig = addTrace(par, plot_fig)
    #Modify plot layout
    plot_fig = modifyPlot(plot_fig, plot)
    return(plot_fig)

def createPlotFigs():
    plot_figs = {}
    # For each plot
    for plot in tqdm(getPlotsInfo().index.to_list(), desc = "Creating plot figure bases"):
        plot_figs[plot] =  createPlotFig(plot)
    return(plot_figs)

def createDashCharts():
    dcc_chart_fig = []
    p = 0
    for plot in config.figs['plot_figs']:
        if p != len(config.figs['plot_figs'])-1: #if not the last plot
            height = '20vh'
        else:
            height = '25vh'
        dcc_chart_fig.append(dcc.Graph(id='graph' + str(p),
                                            figure=config.figs['plot_figs'][plot],
                                            style={'width': '98vw', 'height': ''+ height + ''}))
        config.config['dcc_plot_codes']['graph' + str(p)] = plot
        config.config['dcc_plot_names']['graph' + str(p)] = re.sub('<.*?>', ' ', config.config['info']['plots']['ylab'][plot])
        config.config['dcc_trace_names']['graph' + str(p)] = list(config.config['plot_pars'].query('plot == "' + plot + '"')['parameter_lab'].unique())
        p = p + 1
    return(dcc_chart_fig)

def modPlotSetPlots(dict):
    new_dict = {}
    for plot_set in config.config['plot_sets']:
        new_dict[plot_set] = {}
        for graph in config.config['dcc_plot_codes'].keys():
            if config.config['dcc_plot_codes'][graph] in dict[plot_set].keys():
                new_dict[plot_set][graph] = dict[plot_set][config.config['dcc_plot_codes'][graph]]
                if len(new_dict[plot_set][graph]) == 0:
                    new_dict[plot_set].pop(graph)
    return new_dict

def saveObject(object_to_save, filepath):
    with bz2.BZ2File(filepath, 'wb') as f:
        pickle.dump(object_to_save, f)

def main():
    ProcessData.processArguments()
    ProcessData.openinfoFile()
    getData()

    plotParDicts()
    config.figs['plot_figs']  = createPlotFigs()
    config.figs['dcc_plot_figs'] = createDashCharts()
    config.config['plot_set_plots'] = modPlotSetPlots(config.config['plot_set_plots'])

        #pbar.set_description("Exporting chart %s" % plot_set)
        #if config.config['info']['charts'].loc[chart, 'html_on'] == "ON":
        #    config.config['div_chart_figs'][chart] = createOfflineCharts(chart)
        #    exportHTML(chart)
        #if config.config['info']['charts'].loc[chart, 'png_on'] == "ON":
        #    exportImage(chart, 'png')
        #if config.config['info']['charts'].loc[chart, 'pdf_on'] == "ON":
        #    exportImage(chart, 'pdf')
        

    # # saveObject(config.config, (config.io_dir / 'Temp' / 'config.pbz2'))
    export_config = [config.config, config.figs]
    
    print("Exporting sub_config2.pbz2 to Output")
    saveObject(export_config, (config.io_dir / 'Output' / 'sub_config2.pbz2'))

if __name__ == "__main__":
    main()