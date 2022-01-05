import sys
import getopt
import os
from pathlib import Path
import pickle
import bz2

import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State
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
        print("Fetching all data (or no processed all_data.pbz2 or sub_config2.pbz2 files exist)")
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
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

image_filename = 'assets\ToOL-PRO-BES.png'
encoded_image = base64.b64encode(open(image_filename, 'rb').read())

#card_style = {"box-shadow": "0 4px 5px 0 rgba(0,0,0,0.14), 0 1px 10px 0 rgba(0,0,0,0.12), 0 2px 4px -1px rgba(0,0,0,0.3)"}

#app.scripts.config.serve_locally = True

tabs_init = []
plot_sets_dict = {}
t = 0
for plot_set in set(config.config['plot_sets'].values()):
    plot_set_name = config.config['info']['charts']['chart_label'][plot_set]
    plot_sets_dict[t] = {'name':plot_set_name, 'plot_set':plot_set}
    t += 1

diff = datetime.now(timezone('UTC')) - config.config['date_end']
last_date = humanize.naturaldelta(diff)
update_text = html.Div(html.P('Data last retrieved ' + last_date + ' ago'))

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
    plot_name = config.config['dcc_plot_names'][plot_set][plot.id]
    for trace in plot.figure.data:
        if trace.name in traces_info[plot.id]:
            par = config.config['plot_pars'][plot_set].query(
                "plot == '" + plot_name + "'").query(
                "parameter_lab == '" + trace.name + "'")['parameter'][0]
            par_info = config.config['plot_pars'][plot_set].query('parameter == "' + par + '"')
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
    if plot.id == plots[len(plots)-1]:
        plot.figure.update_xaxes(showticklabels=True, ticks="outside")
        plot.style['height'] = str(height + 5) + 'vh'
    return plot


plot_set = min(config.config['plot_sets'].values())
start = min(config.config['all_data'].DateTime)
end = max(config.config['all_data'].DateTime)
def_resample = 15

header_card = dbc.Card([
                dbc.CardImg(src=image_filename, top=True),
                html.P(update_text, className="card-text", style={'textAlign': 'left'}, id='load'),
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
                {"label": 'Plot Set ' + str(plot_set), "value": plot_set} for plot_set in set(config.config['plot_sets'].values())],
            value=plot_set,
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
            id="open-offcanvas-scrollable",
            n_clicks=0,
        ),
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
app.layout = dbc.Container([
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
    [Input('load', 'value')])
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

#TIME RANGE END
@app.callback(
    Output('hi_res', 'value'),
    [Input('load', 'value'), Input('date_slider', 'value')])
def _update_time_range_label(load, dates_selected):
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
    [Input('resample_radio', 'value'), Input('resample_set', 'value'), Input('date_slider', 'value')], State('hi_res', 'value'))
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
    Input("open-offcanvas-scrollable", "n_clicks"),
    State("offcanvas-scrollable", "is_open"))
def toggle_offcanvas_scrollable(n1, is_open):
    if n1:
        return not is_open
    return is_open

#PLOT CHOOSER
@app.callback(
    Output('plot_chooser-content', 'children'),
    [Input('plot_set_drop', 'value')])
def update_plot_chooser(plot_set):
    plots = {}
    for plot in config.config['dcc_plot_set_figs'][plot_set]:
        plots[plot.id] = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)

    content = [dbc.CardHeader("Select Plots:", className="card-title",)]
    content.append(html.Div(
        dbc.Checklist(
            id='plot_chooser',
            options=[{'label':plots[plot], 'value':plot} for plot in plots],
            value=list(plots.keys()),
            inline=True,
        ), className="p-3", id='loading2'),
    )
    content_card = dbc.Row(dbc.Col(dbc.Card(content)))
    return content_card

#TRACE CHOOSER
@app.callback(
    Output('trace_chooser-content', 'children'),
    [Input('plot_chooser', 'value')], [State('plot_set_drop', 'value'), State('plot_chooser', 'value')])
def update_trace_chooser(n1, plot_set, plots):
    plots.sort() #sort alpha
    plots.sort(key=len) #sort by length (graph10+)
    
    card_contents = [dbc.CardHeader("Select traces:", className="card-title",)]
    for plot in config.config['dcc_plot_set_figs'][plot_set]:
        if plot.id in plots:
            plot_name = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
            content = [dbc.CardHeader(plot_name, className="card-title",)]
            traces = list(set(trace.name for trace in plot.figure.data))
            traces.sort()
            content.append(html.Div(
                dbc.Checklist(
                    id=plot.id + '_traces',
                    options=[{'label':trace, 'value':trace} for trace in traces],
                    value=traces,
                    inline=True,
                    input_checked_style={
                        "backgroundColor": "#fa7268",
                        "borderColor": "#ea6258",
                    },
                ), className="p-3"))
            card_contents.append(dbc.Col(content, className = 'px-3'))
    #for plot in config.config['dcc_plot_set_figs'][plot_set]:
    #    plots[plot.id] = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
    #card = sum(card_contents, [])

    return dbc.Row(dbc.Card(card_contents, id='trace_chooser'))

#CHART
@app.callback(Output('chart-content', 'children'),
            [Input('submit_val', 'n_clicks'), Input('plot_set_drop', 'value')],
            [State('plot_set_drop', 'value'), State('date_slider','value'), State('plot_chooser', 'value'),
            State('height_set', 'value'), State('resampler', 'data'), State('trace_chooser', 'children')])
def render_content(n_clicks, plot_set_click, plot_set, dates_selected, plots, height, resample, traces):
    #time.sleep(2)
    traces_info = {}
    for plot_id in range(1,len(traces)):
        plot_name = traces[plot_id]['props']['children'][1]['props']['children']['props']['id']
        plot_name = plot_name.replace("_traces", "")
        traces_info[plot_name] = traces[plot_id]['props']['children'][1]['props']['children']['props']['value']


    content = []
    plots.sort() #sort alpha
    plots.sort(key=len) #sort by length (graph10+)
    chart_data = config.config['all_data'].query(
            'DateTime > "' + str(unixToDatetime(dates_selected[0])) + '"').query(
            'DateTime < "' + str(unixToDatetime(dates_selected[1])) + '"').set_index('DateTime')
    if resample > 0:
        chart_data = chart_data.groupby(pd.Grouper(freq=str(resample) +'Min')).aggregate(np.mean)
    chart_data = chart_data.reset_index()

    for plot_orig in config.config['dcc_plot_set_figs'][plot_set]:
        if plot_orig.id in plots:
            plot = addDatatoPlot(deepcopy(plot_orig), traces_info, chart_data, dates_selected, plots, height)
            content.append(html.Div(id='loading', children=plot))
    return html.Div(id='loading', children=content)


finish = datetime.now(timezone('UTC')).replace(microsecond=0)
print("App ready at: " + str(finish) + " (" + str(finish - begin) + ")")

port = 8050 # or simply open on the default `8050` port

def open_browser():
	webbrowser.open_new("http://localhost:{}".format(port))

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run_server(port=port)

####
