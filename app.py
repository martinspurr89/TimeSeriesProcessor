import sys
import getopt
import os
from pathlib import Path
import pickle
import bz2

import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State, ALL
import time
from pytz import timezone, utc
import base64
import humanize
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import webbrowser
from threading import Timer
import dash_datetimepicker
import dash_bootstrap_components as dbc
from copy import deepcopy
import math

import config
import ProcessData_resampler as ProcessData
import CreateCharts as CreateCharts

def getConfigData():
    dfile_path = config.io_dir / "Output" / 'all_data.pbz2'
    pfile_path = config.io_dir / "Output" / 'sub_config2.pbz2'
    if os.path.exists(dfile_path) and os.path.exists(pfile_path) and config.update:
        print("Importing processed data...")
        with bz2.open(dfile_path, 'rb') as pfile:
            config.config['all_data'] = pickle.load(pfile)
        print("Importing config...")
        with bz2.open(pfile_path, 'rb') as pfile:
            items = pickle.load(pfile)
        for key in list(items.keys()):
            config.config[key] = items[key]
    else:
        if config.update:
            print("No processed all_data.pbz2 or sub_config2.pbz2 files exist")
        CreateCharts.main()
        config.update = True
        getConfigData()

begin = datetime.now(timezone('UTC')).replace(microsecond=0)
print("Starting processing at: " + str(begin))

ProcessData.processArguments()
getConfigData()
print("Config imported!")

external_stylesheets = [dbc.themes.BOOTSTRAP]#, 'https://codepen.io/chriddyp/pen/bWLwgP.css']
#app = JupyterDash('__name__')
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions = True)

image_filename = 'assets\ToOL-PRO-BES.png'
encoded_image = base64.b64encode(open(image_filename, 'rb').read())

#card_style = {"box-shadow": "0 4px 5px 0 rgba(0,0,0,0.14), 0 1px 10px 0 rgba(0,0,0,0.12), 0 2px 4px -1px rgba(0,0,0,0.3)"}

#app.scripts.config.serve_locally = True

tabs_init = []
plot_sets_dict = {}
t = 0
for plot_set in set(config.config['plot_sets']):
    plot_set_name = config.config['info']['charts']['chart_label'][plot_set]
    plot_sets_dict[t] = {'name':plot_set_name, 'plot_set':plot_set}
    t += 1

def update_text():
    diff = datetime.now(timezone('UTC')) - config.config['date_end']
    last_date = humanize.naturaldelta(diff)
    return html.Div(html.P('Data last retrieved ' + last_date + ' ago'))

###


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
        return dbc.Alert("Set value for resampling in minutes", color="danger")
    if value > 0:
        return dbc.Alert('Resample every ' + str(value) + ' mins', color="light")
    elif value == 0:
        return dbc.Alert('Data not resampled', color="warning")
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
        data_set = config.config['all_data'].query(
            'DateTime > "' + str(unixToDatetime(dates_selected[0])) + '"').query(
            'DateTime < "' + str(unixToDatetime(dates_selected[1])) + '"')
        length = len(data_set)
        return round(length/2800) #mins

def addDatatoPlot(plot, traces_info, chart_data, dates_selected, plots, height):
    plot_name = config.config['dcc_plot_names'][plot.id]
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
            if par + "_err" in config.config['all_data'].columns[1:]:
                error_bars = True
                y_error = chart_data[par + "_err"]

            if trace.mode == "markers" or trace.line.shape == "hv":
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
                trace.y = par_info['bar_order'][0] + y_data.round()/2
            if trace.mode == "none" and par_info['bar'][0]:
                trace.y = par_info['bar_order'][0] - y_data.round()/2
    plot.figure.update_xaxes(range=[unixToDatetime(dates_selected[0]), unixToDatetime(dates_selected[1])], fixedrange=False)
    plot.style['height'] = str(height) + 'vh'
    if plot.id == list(plots.keys())[len(plots)-1]:
        plot.figure.update_xaxes(showticklabels=True, ticks="outside")
        plot.style['height'] = str(height + 5) + 'vh'
    return plot

def getPlots(plot_set):
    plots = {}
    for plot_name in config.config['plot_set_plots'][plot_set].keys():
        for plot in config.config['dcc_plot_set_figs']:
            if plot_name == plot.id:  
                plots[plot.id] = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
    return plots

def modifyPlot(plot_fig, plot):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    plot_fig.figure.update_layout(
        margin=dict(l=100, r=250, b=15, t=15, pad=10),
        template="simple_white",
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Arial",
            #size=config.config['info']['charts']['font_size'][chart],
            color="black"
        ))
    plot_fig.figure.update_yaxes(title_text=plot_info['ylab'][0], mirror=True)
    plot_fig.figure.update_xaxes(showgrid=True, showticklabels=False, ticks="",
        showline=True, mirror=True,
        fixedrange=True) #prevent x zoom
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
            ymin = min(config.config['plot_pars'].query('plot == "' + plot + '"')['bar_order']) - 1
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
            ymax = max(config.config['plot_pars'].query('plot == "' + plot + '"')['bar_order']) + 1
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
        tickvals_list = list(range(int(ymin)+1, int(ymax), 1))
        ticktext_list = [bar_dict[k] for k in tickvals_list if k in bar_dict]
        plot_fig.figure.update_layout(
                yaxis = dict(
                    tickmode = 'array',
                    tickvals = tickvals_list,
                    ticktext = ticktext_list
                )
            )
        plot_fig.figure.update_yaxes(ticklabelposition="inside", ticks="inside")

    return(plot_fig)

all_plots = {}
for plot_id in config.config['dcc_plot_names'].keys():
    plot_name = config.config['dcc_plot_names'][plot_id]
    all_plots[plot_id] = re.sub('<.*?>', ' ', config.config['info']['plots']['ylab'][plot_name])

all_traces = {}
for plot_id in config.config['dcc_plot_names'].keys():
    plot_name = config.config['dcc_plot_names'][plot_id]
    all_traces[plot_id] = list(config.config['plot_pars'].query('plot == "' + plot_name + '"')['parameter_lab'].unique())

plot_set = min(config.config['plot_sets'])
start = min(config.config['all_data'].DateTime)
end = max(config.config['all_data'].DateTime)
def_resample = 15

header_card = dbc.Card([
                dbc.CardImg(src=image_filename, top=True),
                html.P(update_text(), className="card-text", style={'textAlign': 'left'}, id='load'),
                ], className = 'px-3')

datetime_pick = html.Div(children=[
                    dash_datetimepicker.DashDatetimepicker(id="datetime-picker", 
                    startDate=start, endDate=end, utc=True, locale="en-gb"),
                ], className='p-3', style = {'align-self': 'center'})

datetime_slider = html.Div(children=[
                        dcc.Store(id='hi_res'),
                        dbc.Spinner(id='slider-content', color="info")
                     ], className='p-3')

plot_set_dropdown = html.Div(
    [
        dbc.Select(
            id='plot_set_drop',
            options=[
                {"label": 'Plot Set ' + str(plot_set), "value": plot_set} for plot_set in set(config.config['plot_sets'])] + 
                [{'label': 'Plot Set Custom', 'value': -1}],
            value=str(plot_set),
        ),
    ], className='p-3', style={'textAlign': 'left'}
)

resampler_radio = html.Div(
    [
        dbc.Row([
            dbc.Col(dbc.RadioItems(
                id="resample_radio",
                options=[
                    {'label': 'Low', 'value': 'LOW'},
                    {'label': 'High', 'value': 'HIGH'},
                    {'label': 'None', 'value': 'NONE'},
                    {'label': 'Set', 'value': 'SET'},
                ],
                value='HIGH',
                inline=True
            )),
            dbc.Col(html.Div(dbc.Input(id='resample_set', type="number", min=1, step=1,
            placeholder="mins"), id="resample_div"), width=3),
        ], align="center"),

    ], className='p-3'
)

resampler_input = html.Div(
    [
        dcc.Store(id='resampler'),
        dbc.Row([
            dbc.Col(html.Div(dbc.Spinner(id='resample_label')),)
        ]),
    ], className='p-0', style={'textAlign': 'left'}
)

height_input = html.Div(
    [
        dbc.Row([
            dbc.Col(dbc.Input(type="number", min=1, step=1, placeholder="Plot height", value=20, id='height_set'), width=8),
            dbc.Col(html.P(" %"), width=1)
        ], justify="center"),
    ], className='p-3', style={'textAlign': 'left'}
)

submit_input = html.Div(
    [
        dbc.Button(
            "SUBMIT",
            id="submit_val",
            n_clicks=0,
            color='success'
        )
    ], className='p-3',
)

offcanvas = html.Div(
    [
        dbc.Button(
            "Select plots",
            id="open-offcanvas-button",
            n_clicks=0,
        ),
        dcc.Store(id='plot_set_store', data=plot_set),
        dcc.Store(id='plots_store', data = getPlots(plot_set)),
        dcc.Store(id='traces_store', data = config.config['plot_set_plots'][plot_set]),
        dbc.Offcanvas([
                dbc.Spinner(id='plot_chooser-content', color="primary"),
                dbc.Spinner(id='trace_chooser-content', color="primary"),
            ],
            id="offcanvas-scrollable",
            scrollable=True,
            is_open=False,
            placement='start',
            style = {'width': '600px'}
        ),
    ], className='p-3'
)



##APP##
def serve_layout():
    return dbc.Container([
        html.Div([
                #HEADER
                dbc.Row(dbc.Col([
                    header_card
                ])),

                #DATETIME
                dbc.Row(dbc.Col(dbc.Card([
                    dbc.CardHeader("DateTime Range", className="card-title",),
                    datetime_pick,
                    datetime_slider,
                ], className="px-3"))),

                dbc.Row([
                    dbc.Col(html.Div(dbc.Card([
                        dbc.CardHeader("Select Plots", className="card-title",),
                        plot_set_dropdown,
                        offcanvas,
                    ]))),
                    dbc.Col(html.Div(dbc.Card([
                        dbc.CardHeader("Resampling Resolution", className="card-title",),
                        resampler_radio,
                        resampler_input
                    ]))),
                    dbc.Col([dbc.Row([
                        dbc.Col(html.Div(dbc.Card([
                            dbc.CardHeader("Plot Height", className="card-title",),
                            height_input,
                        ]))),
                        dbc.Col(html.Div(dbc.Card([
                            dbc.CardHeader("Submit", className="card-title",),
                            submit_input,
                        ]))),
                    ])]),
                ], align='center'),
            ], className="p-5", style={'textAlign': 'center'}),
            dbc.Row([
                dbc.Col(html.Div([dcc.Loading(id='chart-content'),])),
            ], className = "g-0", style={'textAlign': 'center'}),
    ], fluid=True)

app.layout = serve_layout

#CALLBACKS

#DATETIME PICKER
@app.callback(
    Output('date_slider', 'value'),
    [Input('datetime-picker', 'startDate'),
    Input('datetime-picker', 'endDate')])
def datetime_range(startDate, endDate):
    startDate = pd.to_datetime(startDate)
    endDate = pd.to_datetime(endDate)
    return [unixTimeMillis(startDate), unixTimeMillis(endDate)]


#SLIDER
@app.callback(
    Output('slider-content', 'children'),
    [Input('load', 'children')])
def update_slider(load):
    startDate = pd.to_datetime(start)
    endDate = pd.to_datetime(end)
    content = []
    content.append(
        html.Div(dcc.RangeSlider(
            id='date_slider',
            updatemode='mouseup',
            min=unixTimeMillis(startDate),
            max=unixTimeMillis(endDate),
            count=1,
            step=60000,
            value=[unixTimeMillis(start), unixTimeMillis(end)],
            marks=getMarks(start, end, 8),
            className='px-5'),
    id='loading'))
    return content

#TIME RANGE START
@app.callback(
    Output('datetime-picker', 'startDate'),
    [Input('date_slider', 'value')])
def _update_time_range_label(dates_selected):
    return unixToDatetime(dates_selected[0])

#TIME RANGE END
@app.callback(
    Output('datetime-picker', 'endDate'),
    [Input('date_slider', 'value')])
def _update_time_range_label(dates_selected):
    return unixToDatetime(dates_selected[1])

#INITIAL RES
@app.callback(
    Output('hi_res', 'data'),
    [Input('load', 'children'), Input('date_slider', 'value')])
def _update_res_val(load, dates_selected):
    return calcHiRes(dates_selected)

#RESAMPLE SET DISPLAY
@app.callback(
    Output('resample_div', 'style'),
    [Input('resample_radio', 'value')])
def disableinput(value):
    if value == 'SET':
        return {'display': 'block'}
    else:
        return {'display': 'none'}

#RESAMPLE SET DISABLE
@app.callback(
     Output('resample_set', 'disabled'),
     [Input('resample_radio', 'value')])
def disableinput(value):
     if value == 'SET':
         return False
     else:
         return True

#RESAMPLE SET INVALID
@app.callback(
     Output('resample_set', 'invalid'),
     [Input('resampler', 'data')])
def disableinput(value):
    if value == None:
        return True
    else:
        return False

#RESAMPLE/SUBMIT INVALID
@app.callback(
     Output('submit_val', 'disabled'),
     [Input('resampler', 'data')])
def disableinput(value):
    if value == None:
        return True
    else:
        return False

#CALC/STORE RESAMPLER VAL
@app.callback(
    Output('resampler', 'data'),
    [Input('resample_radio', 'value'), Input('resample_set', 'value'), Input('date_slider', 'value')], State('hi_res', 'data'))
def calcResampling(resolution, set, dates_selected, hi_res):
    if hi_res == None:
        hi_res = calcHiRes(dates_selected)
    return calcResampler(resolution, set, hi_res)

#UPDATE RESAMPLER ALERT
@app.callback(
    Output('resample_label', 'children'),
    [Input('resampler', 'data')])
def printResampler(value):
    return resampleAlert(value)

#OFFCANVAS PLOT CHOOSER
@app.callback(
    Output("offcanvas-scrollable", "is_open"),
    Input("open-offcanvas-button", "n_clicks"),
    State("offcanvas-scrollable", "is_open"))
def toggle_offcanvas_scrollable(n1, is_open):
    if n1:
        return not is_open
    return is_open

#PLOT SET VAL
@app.callback(
    Output('plot_set_store', 'data'),
    [Input('plot_set_drop', 'value'), Input('plots_store', 'data')])
def plot_set_val(plot_set_str, plots):
    ctx = dash.callback_context
    ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]
    if ctx_input == 'plot_set_drop':
        return int(plot_set_str)
    else:
        for plot_set in config.config['plot_sets']:
            if plots == getPlots(plot_set):
                return plot_set
        return -1

#PLOT SET CHOSEN - SET PLOTS
@app.callback(
    Output('plots_store', 'data'),
    [Input("open-offcanvas-button", "n_clicks"), Input('plot_set_store', 'data'), Input('plot_chooser', 'value')],
    [State('plots_store', 'data')])
def update_plots(button, plot_set, plots, content_old):
    ctx = dash.callback_context
    ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

    if ctx_input in ['plot_chooser', 'open-offcanvas-button']:
        new_content = {}
        for plot in plots:
            new_content[plot] = all_plots[plot]
        return new_content
    elif ctx_input == 'plot_set_store':
        if plot_set != -1:
            return getPlots(plot_set)
        else:
            return content_old

#PLOT CHOOSER UPDATE
@app.callback(
    Output('plot_chooser-content', 'children'),
    [Input("open-offcanvas-button", "n_clicks"), Input('plots_store', 'data')])
def update_plot_chooser(button, plots):
    content = [dbc.CardHeader("Select Plots:", className="card-title",)]
    content.append(html.Div(
        dbc.Checklist(
            id='plot_chooser',
            options=[{'label':all_plots[plot], 'value':plot} for plot in all_plots],
            value=list(plots.keys()),
            inline=True,
        ), className="p-3", id='loading2'),
    )
    content_card = dbc.Row(dbc.Col(dbc.Card(content)))
    return content_card

#PLOT SET CHOSEN - SET TRACES
@app.callback(
    Output('traces_store', 'data'),
    [Input('plot_set_store', 'data'), Input('plot_chooser', 'value'), Input({'type': 'trace_check', 'index': ALL}, 'value')],
    [State('traces_store', 'data')])
def update_plots(plot_set, plots, traces_chosen, old_traces):
    ctx = dash.callback_context
    ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

    if ctx_input == 'plot_chooser':
        plots.sort() #sort alpha
        plots.sort(key=len) #sort by length (graph10+)
        new_content = {}
        for plot in plots:
            if plot in old_traces.keys():
                new_content[plot] = old_traces[plot]
            else:
                new_content[plot] = all_traces[plot]
        return new_content
    elif ctx_input == 'plot_set_store':
        if plot_set != -1:
            
            traces = {}
            for plot in config.config['dcc_plot_set_figs']:
                if plot.id in config.config['plot_set_plots'][plot_set].keys():
                    traces[plot.id] = config.config['plot_set_plots'][plot_set][plot.id]
                    traces[plot.id].sort()

            return traces
        else:
            return old_traces
    elif "index" in ctx_input:
            
            plot = ctx.triggered[0]['prop_id'].split('"')[3].split('_')[0]

            old_traces[plot] = ctx.triggered[0]['value']

            return old_traces
    else:
        return old_traces

#TRACE CHOOSER
@app.callback(
    Output('trace_chooser-content', 'children'),
    [Input('plot_chooser', 'value'), Input('traces_store', 'data')], [State('plot_set_store', 'data')])
def update_trace_chooser(plots, traces, plot_set):
    plots.sort() #sort alpha
    plots.sort(key=len) #sort by length (graph10+)
    
    card_contents = [dbc.CardHeader("Select traces:", className="card-title",)]
    for plot in config.config['dcc_plot_set_figs']:
        if plot.id in plots:
            plot_name = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
            content = [dbc.CardHeader(plot_name, className="card-title",)]
            content.append(html.Div(
                dbc.Checklist(
                    id={
                        'type': 'trace_check',
                        'index': plot.id + '_traces',
                    },
                    options=[{'label':re.sub('<.*?>', '', trace), 'value':trace} for trace in all_traces[plot.id]],
                    value=traces[plot.id],
                    inline=True,
                    input_checked_style={
                        "backgroundColor": "#fa7268",
                        "borderColor": "#ea6258",
                    },
                ), className="p-3"))
            card_contents.append(dbc.Col(content, className = 'px-3'))
    return dbc.Row(dbc.Card(card_contents, id='trace_chooser'))

#UPDATE PLOT_SET DROP
@app.callback(
    Output('plot_set_drop', 'value'),
    [Input('offcanvas-scrollable', 'is_open')],
    [State('plot_set_store', 'data'), State('plots_store', 'data'), State('traces_store', 'data'), State('plot_set_drop', 'value')]
)
def update_plot_set_dropdown(is_open, plot_set, plots, traces, drop):
    if not is_open:
        for plot_set in config.config['plot_sets']:
            if traces == config.config['plot_set_plots'][plot_set]:
                return str(plot_set)
        return str(-1)
    return drop

#CHART
@app.callback(Output('chart-content', 'children'),
            [Input('submit_val', 'n_clicks')],
            [State('plot_set_store', 'data'), State('date_slider','value'), State('plots_store', 'data'),
            State('height_set', 'value'), State('resampler', 'data'), State('traces_store', 'data')])
def render_content(n_clicks, plot_set, dates_selected, plots, height, resample, traces):
    #time.sleep(2)
    content = []
    chart_data = config.config['all_data'].query(
            'DateTime > "' + str(unixToDatetime(dates_selected[0])) + '"').query(
            'DateTime < "' + str(unixToDatetime(dates_selected[1])) + '"').set_index('DateTime')
    if resample > 0:
        chart_data = chart_data.groupby(pd.Grouper(freq=str(resample) +'Min')).aggregate(np.mean)
    chart_data = chart_data.reset_index()

    for plot_orig in config.config['dcc_plot_set_figs']:
        if plot_orig.id in plots:
            plot_name = config.config['dcc_plot_names'][plot_orig.id]
            plot = addDatatoPlot(deepcopy(plot_orig), traces, chart_data, dates_selected, plots, height)
            plot = modifyPlot(plot, plot_name)
            plot = setAxisRange(plot, plot_name, chart_data, traces[plot_orig.id])
            content.append(html.Div(id='loading', children=plot))
    return html.Div(id='loading', children=content)


finish = datetime.now(timezone('UTC')).replace(microsecond=0)
print("App ready at: " + str(finish) + " (" + str(finish - begin) + ")")

port = 8050 # or simply open on the default `8050` port

def open_browser():
	webbrowser.open_new("http://localhost:{}".format(port))

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run_server(port=port, debug=True, use_reloader=False)

####
