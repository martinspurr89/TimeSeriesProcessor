import sys
import getopt
import os
from pathlib import Path
import pickle

import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State
import time
from pytz import timezone, utc
import base64
import humanize
import pandas as pd
from datetime import datetime, timedelta
import re

import config
import ProcessData as ProcessData

def getConfigCharts():
    pfile_path = config.io_dir / "Output" / 'sub_config.pkl'
    if os.path.exists(pfile_path) and config.update:
        print("Importing config...")
        with open(pfile_path, 'rb') as pfile:
            items = pickle.load(pfile)
        for key in list(items.keys()):
            config.config[key] = items[key]
    else:
        print("Fetching all data (or no pickled sub_config.pkl file exists)")
        ProcessData.main()
        config.update = True
        getConfigCharts()

begin = datetime.now(timezone('UTC')).replace(microsecond=0)
print("Starting processing at: " + str(begin))

ProcessData.processArguments()
getConfigCharts()
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
for chart in config.config['charts']:
    tab_name = "tab-" + str(t)
    tab_ids[tab_name] = chart
    tabs_init.append(dcc.Tab(label=config.config['info']['charts']['chart_label'][chart], value=tab_name, style={'backgroundColor': '#f5f5f5'}))
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

chart = min(config.config['charts'])
start = min(config.config['chart_dfs_mlt'][chart].DateTime)
end = max(config.config['chart_dfs_mlt'][chart].DateTime)

#dates_ = config.config['chart_dfs_mlt'][chart].DateTime
###

##APP##

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
            ], className="eight columns"),
            html.Div(children=[
                html.I("Plot height: "),
                dcc.Input(
                    id="height_set", type="number", placeholder="Height set input",
                    min=1, max=50, step=1,
                    value=20,
                    style={'width':'50%'}
                ), html.I("%")
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

    start = min(config.config['chart_dfs_mlt'][tab_ids[tab]].DateTime)
    end = max(config.config['chart_dfs_mlt'][tab_ids[tab]].DateTime)

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
    for plot in config.config['dcc_chart_figs'][tab_ids[tab]]:
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
            [State('tabs', 'value'), State('date_slider','value'), State('plot_chooser', 'value'), State('height_set', 'value')])
def render_content(n_clicks, tab_click, tab, dates_selected, plots, height):
    #time.sleep(2)
    content = []
    plots.sort() #sort alpha
    plots.sort(key=len) #sort by length (graph10+)
    for plot in config.config['dcc_chart_figs'][tab_ids[tab]]:
        if plot.id in plots:
            plot.figure.update_xaxes(range=[unixToDatetime(dates_selected[0]), unixToDatetime(dates_selected[1])], fixedrange=True)
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
