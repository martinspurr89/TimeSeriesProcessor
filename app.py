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
        print("Fetching all data (or no pickled sub_config2.pbz2 file exists)")
        CreateCharts.main()
        config.update = True
        getConfigData()

begin = datetime.now(timezone('UTC')).replace(microsecond=0)
print("Starting processing at: " + str(begin))

ProcessData.processArguments()
getConfigData()
print("Config imported!")

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
#app = JupyterDash('__name__')
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

image_filename = 'assets\ToOL-PRO-BES.png'
encoded_image = base64.b64encode(open(image_filename, 'rb').read())

card_style = {"box-shadow": "0 4px 5px 0 rgba(0,0,0,0.14), 0 1px 10px 0 rgba(0,0,0,0.12), 0 2px 4px -1px rgba(0,0,0,0.3)"}

#app.scripts.config.serve_locally = True

tabs_init = []
tab_ids = {}
t = 0
for plot_set in set(config.config['plot_sets'].values()):
    tab_name = "tab-" + str(t)
    tab_ids[tab_name] = plot_set
    tabs_init.append(dcc.Tab(label=config.config['info']['charts']['chart_label'][plot_set], value=tab_name, style={'backgroundColor': '#f5f5f5'}))
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
        result[unixTimeMillis(date)] = str(date.strftime('%Y-%m-%d'))
    return result

def rangeString(start, end):
    return '{} ⬌ {}'.format(unixToDatetime(start).strftime("%d/%m/%Y %H:%M"),
                                  unixToDatetime(end).strftime("%d/%m/%Y %H:%M"))

plot_set = min(config.config['plot_sets'].values())
start = min(config.config['all_data'].DateTime)
end = max(config.config['all_data'].DateTime)

#dates_ = config.config['chart_dfs_mlt'][chart].DateTime
###

##APP##
CreateCharts.startT()
app.layout = html.Div(children=[
    #html.Div([html.Img(src=app.get_asset_url('ToOL-PRO-BES.png'), style={'width':'90%', 'max-width': '100%'})], style={'textAlign': 'center'}),
    html.Div([html.Img(src='data:image/png;base64,{}'.format(encoded_image.decode()), style={'width':'75%', 'max-width': '100%'})], style={'textAlign': 'center'}),
    update_text,
    html.Div(children=[
        dcc.Tabs(id="tabs",
            value="tab-0",
            children=tabs_init),
        html.Div(children=[
            html.Div(children=[
                dcc.Loading(id='slider-content'),
            ]),
            html.Div(children=[
                dcc.Loading(id='plot_chooser-content'),
            ], className="six columns"),
            html.Div(children=[
                html.I("Plot height: "),
                dcc.Input(
                    id="height_set", type="number", placeholder="Height set input",
                    min=1, max=50, step=1,
                    value=20,
                    style={'width':'40%'}
                ), html.I("%")
            ], className="two columns"),
            html.Div(children=[
                html.I("Resample: "),
                dcc.RadioItems(
                    options=[
                        {'label': 'Low', 'value': 'LOW'},
                        {'label': 'High', 'value': 'HIGH'}
                    ],
                    value='LOW',
                    labelStyle={'display': 'inline-block'}
                )
            ], className="two columns"),
            html.Div(children=[
                html.I("Resample: "),
                dcc.Input(
                    id="resample_set", type="number", placeholder="Resample set input",
                    min=0, max=180, step=1,
                    value=120,
                    style={'width':'40%'}
                ), html.I("mins")
            ], className="two columns"),
            html.Div(children=
                html.Button('Submit', id='submit-val', n_clicks=0),
                className="one columns"),
            html.Br(), html.Br(), html.Br()]),
        html.Div(children=[
            dcc.Loading(id='chart-content'),
        ]),
    ]),
])

##CALLBACKS##

#SLIDER
@app.callback(
    Output('slider-content', 'children'),
    [Input('tabs', 'value')])
def update_slider(tab):

    start = min(config.config['all_data'].DateTime)
    end = max(config.config['all_data'].DateTime)

    content = [html.Label(rangeString(start, end), id='time-range-label')]
    content.append(html.Div(id='loading', children=
        dcc.RangeSlider(
            id='date_slider',
            updatemode='mouseup',
            min=unixTimeMillis(start),
            max=unixTimeMillis(end),
            count=1,
            step=60000,
            value=[unixTimeMillis(start), unixTimeMillis(end)],
            marks=getMarks(start, end, 8)),
    ))
    return content

#TIME RANGE
@app.callback(
    Output('time-range-label', 'children'),
    [Input('date_slider', 'value')])
def _update_time_range_label(dates_selected):
    return rangeString(dates_selected[0], dates_selected[1])

#PLOT CHOOSER
@app.callback(
    Output('plot_chooser-content', 'children'),
    [Input('tabs', 'value')])
def update_plot_chooser(tab):
    plots = {}
    for plot in config.config['dcc_plot_set_figs'][tab_ids[tab]]:
        plots[plot.id] = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)

    content = [html.Div(html.Label('Select plots:', id='plot_chooser-label'),
            className="one columns")]
    content.append(html.Div(id='loading2', children=
        dcc.Checklist(
            id='plot_chooser',
            options=[{'label':plots[plot], 'value':plot} for plot in plots],
            value=list(plots.keys()),
            labelStyle={'display': 'inline-block'}
        ), className="eleven columns")
    )
    return content

#CHART
@app.callback(Output('chart-content', 'children'),
            [Input('submit-val', 'n_clicks'), Input('tabs', 'value')],
            [State('tabs', 'value'), State('date_slider','value'), State('plot_chooser', 'value'),
            State('height_set', 'value'), State('resample_set', 'value')])
def render_content(n_clicks, tab_click, tab, dates_selected, plots, height, resample):
    #time.sleep(2)
    content = []
    plots.sort() #sort alpha
    plots.sort(key=len) #sort by length (graph10+)
    chart_data = config.config['all_data'].set_index('DateTime').groupby(pd.Grouper(freq=str(resample) +'Min')).aggregate(np.mean)
    chart_data = chart_data.reset_index()

    CreateCharts.endT()
    for plot in config.config['dcc_plot_set_figs'][tab_ids[tab]]:
        if plot.id in plots:
            plot_name = config.config['dcc_plot_names'][tab_ids[tab]][plot.id]
            for trace in plot.figure.data:
                par = config.config['plot_pars'][tab_ids[tab]].query(
                    "plot == '" + plot_name + "'").query(
                    "parameter_lab == '" + trace.name + "'")['parameter'][0]
                par_info = config.config['plot_pars'][tab_ids[tab]].query('parameter == "' + par + '"')
                x_data = chart_data.DateTime
                y_data = chart_data[par]
                error_bars = False
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
            content.append(html.Div(id='loading', children=plot))
    return html.Div(id='loading', children=content)


finish = datetime.now(timezone('UTC')).replace(microsecond=0)
print("App ready at: " + str(finish) + " (" + str(finish - begin) + ")")

port = 8050 # or simply open on the default `8050` port

import webbrowser
from threading import Timer
def open_browser():
	webbrowser.open_new("http://localhost:{}".format(port))

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run_server(port=port)

####
