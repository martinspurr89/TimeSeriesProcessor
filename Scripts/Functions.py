import time
import pandas as pd
import numpy as np
import re
import webbrowser
import dash_bootstrap_components as dbc
from dash import html
from pytz import timezone, utc
import math
import humanize
from datetime import datetime, timedelta

import Scripts.config as config

def update_text():
    diff = datetime.now(timezone('UTC')) - config.config['date_end']
    last_date = humanize.naturaldelta(diff)
    return html.Div(html.P(config.config['project'] + ' | Data last retrieved ' + last_date + ' ago'))


def unixTimeMillis(dt):
    ''' Convert datetime to unix timestamp '''
    return int(time.mktime(dt.timetuple()))

def unixToDatetime(unix):
    ''' Convert unix timestamp to datetime. '''
    return pd.to_datetime(unix,unit='s',utc=True)

def getMarks(start, end, periods):
    ''' Returns the marks for labeling. 
        Every Nth value will be used.
    '''
    daterange = pd.date_range(start=start,end=end,periods=periods)
    result = {}
    for i, date in enumerate(daterange):
        # Append value to dict
        result[unixTimeMillis(date)] = str(date.strftime('%d/%m/%y'))
    return result

def rangeString(start, end):
    return '{} ⬌ {}'.format(unixToDatetime(start).strftime("%d/%m/%Y %H:%M"),
                                  unixToDatetime(end).strftime("%d/%m/%Y %H:%M"))

def resampleAlert(value):
    if value == None:
        return dbc.Alert("Set value for resampling in minutes", color="danger", class_name = "mb-0")
    if value > 0:
        return dbc.Alert('Resample every ' + str(value) + ' mins', color="light", style = {'textAlign': 'left'}, class_name = "mb-0")
    elif value == 0:
        return dbc.Alert('Data not resampled', color="warning", class_name = "mb-0")
    else:
        return ""

def calcResampler(resolution, set, hi_res):
    if resolution == 'HIGH':
        value = hi_res
    elif resolution == 'LOW':
        if hi_res == 0:
            value = 4
        else:
            value = hi_res*4
    elif resolution == 'NONE':
        value = 0
    elif resolution == 'SET':
        value = set
    return(value)

def calcHiRes(dates_selected):
        data_set = config.data['all_data'].query(
            'DateTime > "' + str(unixToDatetime(dates_selected[0])) + '"').query(
            'DateTime < "' + str(unixToDatetime(dates_selected[1])) + '"')
        length = len(data_set)
        return round(length/2800) #mins

def addDatatoPlot(plot, traces_info, chart_data, dates_selected, plots, height):
    plot_name = config.config['dcc_plot_codes'][plot.id]
    if any(config.config['plot_pars'].query("plot == '" + plot_name + "'")['bar']):
        plot_traces = traces_info[plot.id]
        bars = list(config.config['plot_pars'].query(
            "plot == '" + plot_name + "'").query(
            "parameter_lab in @plot_traces")['bar_order'].unique())
        bar_orders = {}
        for b in range(0, len(bars), 1):
            bar_orders[bars[b]] = len(bars) - 1 - b
    for trace in plot.figure.data:
        if trace.name in traces_info[plot.id]:
            par = config.config['plot_pars'].query(
                "plot == '" + plot_name + "'").query(
                "parameter_lab == '" + trace.name + "'")['parameter'][0]
            par_info = config.config['plot_pars'].query('parameter == "' + par + '"')
            x_data = chart_data.DateTime
            y_data = chart_data[par]
            error_bars = False
            y_error = None
            if par + "_err" in config.data['all_data'].columns[1:]:
                error_bars = True
                y_error = chart_data[par + "_err"]

            if trace.mode == "markers" or trace.line.shape == "hv" or par_info['point'][0] or par_info['bar'][0]:
                if error_bars:
                    y_error.drop(y_error[np.isnan(y_data)].index, inplace=True)
                x_data.drop(x_data[np.isnan(y_data)].index, inplace=True)
                y_data.drop(y_data[np.isnan(y_data)].index, inplace=True)
            trace.x = x_data
            trace.y = y_data
            if trace.mode == "markers":
                trace.update(error_y = dict(type = 'data', visible = True, array = y_error, color = par_info['colour'][0]))
            if trace.mode == "none" and par_info['ribbon'][0]:
                trace.y = y_data - y_error
            if trace.line.width == 0 and par_info['ribbon'][0]:
                trace.y = y_data + y_error
            if trace.line.shape == "hv" and par_info['bar'][0]:
                trace.y = bar_orders[par_info['bar_order'][0]] + y_data.round()/2
            if trace.mode == "none" and par_info['bar'][0]:
                trace.y = bar_orders[par_info['bar_order'][0]] - y_data.round()/2
    plot.figure.update_xaxes(range=[unixToDatetime(dates_selected[0]), unixToDatetime(dates_selected[1])], fixedrange=False)
    plot.style['height'] = str(height) + 'vh'
    if plot.id == list(plots.keys())[len(plots)-1]:
        plot.style['height'] = str(height + 5) + 'vh'
    return plot

def getPlots(plot_set):
    plots = {}
    for plot_name in config.config['plot_set_plots'][plot_set].keys():
        for plot in config.figs['dcc_plot_figs']:
            if plot_name == plot.id:  
                plots[plot.id] = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
    return plots

def modifyPlot(plot_fig, plot, plots, font):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    plot_fig.figure.update_layout(
        margin=dict(l=125, r=250, b=15, t=15, pad=10),
        template="simple_white",
        paper_bgcolor='rgba(0,0,0,0)',
        legend_tracegroupgap=0,
        font=dict(
            family = "Arial",
            size = font,
            color = "black"
        ))
    plot_fig.figure.update_yaxes(title_text=plot_info['ylab'][0], mirror=True)
    plot_fig.figure.update_xaxes(showgrid=True, showticklabels=False, ticks="",
        showline=True, mirror=True,
        fixedrange=True) #prevent x zoom
    if plot_fig.id == list(plots.keys())[len(plots)-1]:
        plot_fig.figure.update_xaxes(showticklabels=True, ticks="outside", automargin=False)
        plot_fig.figure.update_layout(margin=dict(l=125, r=250, b=60, t=15, pad=10))
    return(plot_fig)

def getYMin(plot, chart_data, traces_info):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    if pd.isna(plot_info['ymin'][0]):
        par_codes = config.config['plot_pars'].query("plot == '" + plot + "'").query("parameter_lab in @traces_info")['parameter'].unique()
        min_data = []
        for par in par_codes:
            if par + "_err" in chart_data.columns:
                min_data.append(min(chart_data[par] - chart_data[par + "_err"]))
            else:
                min_data.append(min(chart_data[par]))
        ymin = min(min_data)
        if any(config.config['plot_pars'].query('plot == "' + plot + '"')['point']):
            if ymin > 0:
                ymin = 0.95 * ymin
            else:
                ymin = 1.05 * ymin
        elif any(config.config['plot_pars'].query('plot == "' + plot + '"')['bar']) > 0:
            ymin = - 1
    else:
        ymin = plot_info['ymin'][0]
    return(ymin)

def getYMax(plot, chart_data, traces_info):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    if pd.isna(plot_info['ymax'][0]):
        par_codes = config.config['plot_pars'].query("plot == '" + plot + "'").query("parameter_lab in @traces_info")['parameter'].unique()
        max_data = []
        for par in par_codes:
            if par + "_err" in chart_data.columns:
                max_data.append(max(chart_data[par] + chart_data[par + "_err"]))
            else:
                max_data.append(max(chart_data[par]))
        ymax = max(max_data)
        if any(config.config['plot_pars'].query('plot == "' + plot + '"')['point']):
            if ymax > 0:
                ymax = 1.05 * ymax
            else:
                ymax = 0.95 * ymax
        elif any(config.config['plot_pars'].query('plot == "' + plot + '"')['bar']) > 0:
            bars = list(config.config['plot_pars'].query(
                "plot == '" + plot + "'").query(
                "parameter_lab in @traces_info")['bar_order'].unique())
            ymax = len(bars)
    else:
        ymax = plot_info['ymax'][0]
    return(ymax)

def setAxisRange(plot_fig, plot, chart_data, traces_info):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    ymin = getYMin(plot, chart_data, traces_info)
    ymax = getYMax(plot, chart_data, traces_info)
    if plot_info['log'][0] == True:
        plot_fig.figure.update_layout(yaxis_type="log")
        plot_fig.figure.update_yaxes(range=[math.log(ymin, 10), math.log(ymax, 10)])
    else:
        plot_fig.figure.update_yaxes(range=[ymin, ymax])

    if any(config.config['plot_pars'].query('plot == "' + plot + '"')['bar'].values == True):
        bar_dict = config.config['plot_pars'].query('plot == "' + plot + '"').set_index('bar_order')['parameter_lab'].to_dict()
        bars = list(config.config['plot_pars'].query(
            "plot == '" + plot + "'").query(
            "parameter_lab in @traces_info")['bar_order'].unique())
        bar_orders = {}
        for b in range(0, len(bars), 1):
            bar_orders[bars[b]] = len(bars) - 1 - b
        bar_dict2 = {}
        for key in bar_orders:
            bar_dict2[bar_orders[key]] = bar_dict[key]
        
        #tickvals_list = list(range(int(ymin)+1, int(ymax), 1))
        #tickvals_list = list(config.config['plot_pars'].query('parameter_lab in @traces_info').query('plot == "' + plot + '"')['bar_order'].unique())
        tickvals_list = list(bar_dict2.keys())
        tickvals_list.sort()
        ticktext_list = [bar_dict2[k] for k in tickvals_list if k in bar_dict2]
        plot_fig.figure.update_layout(
                yaxis = dict(
                    tickmode = 'array',
                    tickvals = tickvals_list,
                    ticktext = ticktext_list
                )
            )
        plot_fig.figure.update_yaxes(ticklabelposition="inside", ticks="inside", automargin=False)

    return(plot_fig)

def open_browser():
    port = 8050
    webbrowser.open_new("http://localhost:{}".format(port))
