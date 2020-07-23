# -*- coding: utf-8 -*-

# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
import sys
import getopt
import os
from pathlib import Path
import pickle

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import time
from pytz import timezone, utc
import base64
import humanize
import pandas as pd
from datetime import datetime, timedelta

import config
import ProcessData

def getConfigCharts():
    pfile_path = config.io_dir / "Temp" / 'config.pkl'
    if os.path.exists(pfile_path) and config.update:
        with open(pfile_path, 'rb') as pfile:
            items = pickle.load(pfile)
        for key in list(items.keys()):
            config.config[key] = items[key]
    else:
        print("No pickled config.pkl data file exists - processing data!")
        ProcessData.main()


ProcessData.processArguments()
getConfigCharts()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
#app = JupyterDash('__name__')
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

image_filename = 'assets\ToOL-PRO-BES.png' # replace with your own image
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
    return pd.to_datetime(unix,unit='s')

def getMarks(start, end):
    ''' Returns the marks for labeling. 
        Every Nth value will be used.
    '''
    daterange = pd.date_range(start=start,end=end,periods=4)
    result = {}
    for i, date in enumerate(daterange):
        # Append value to dict
        result[unixTimeMillis(date)] = str(date.strftime('%Y-%m-%d'))
    return result

start = min(config.config['chart_dfs_mlt'][0][config.config['chart_dfs_mlt'][0].Parameter == config.config['chart_dfs_mlt'][0].Parameter.unique()[1]].DateTime)
end = max(config.config['chart_dfs_mlt'][0][config.config['chart_dfs_mlt'][0].Parameter == config.config['chart_dfs_mlt'][0].Parameter.unique()[1]].DateTime)
dates_ = config.config['chart_dfs_mlt'][0][config.config['chart_dfs_mlt'][0].Parameter == config.config['chart_dfs_mlt'][0].Parameter.unique()[1]].DateTime
###

app.layout = html.Div(children=[
    #html.Div([html.Img(src=app.get_asset_url('ToOL-PRO-BES.png'), style={'width':'90%', 'max-width': '100%'})], style={'textAlign': 'center'}),
    html.Div([html.Img(src='data:image/png;base64,{}'.format(encoded_image.decode()), style={'width':'90%', 'max-width': '100%'})], style={'textAlign': 'center'}),
    update_text,
    html.Div(children=[
        dcc.Tabs(id="tabs",
            value="tab-0",
            children=tabs_init),
        html.Label('', id='time-range-label'), 
        dcc.RangeSlider(
            id='date_slider',
            updatemode='mouseup',
            min=unixTimeMillis(start),
            max=unixTimeMillis(end),
            count=1,
            step=60000,
            value=[unixTimeMillis(start), unixTimeMillis(end)],
            marks=getMarks(start, end)),
        # dcc.RangeSlider(
        #     id='date_slider',
        #     updatemode='mouseup',
        #     min=0,
        #     max=len(dates_) - 1,
        #     count=1,
        #     step=1,
        #     value=[0, len(dates_) - 1],
        #     marks=getMarks(start, end)),
        html.Div(children=[
            dcc.Loading(id='tabs-content'),
        ]),
    ]),
])

@app.callback(
    Output('time-range-label', 'children'),
    [Input('tabs', 'value'), Input('date_slider', 'value')])
def _update_time_range_label(value):
    return '{} --- {}'.format(dates_.iloc[value[0]].strftime("%d/%m/%Y %H:%M"),
                                  dates_.iloc[value[1]].strftime("%d/%m/%Y %H:%M"))

@app.callback(Output('tabs-content', 'children'),
            [Input('tabs', 'value'), Input('date_slider','value')])
def render_content(tab, dates_selected):
    #time.sleep(2)
    content = []
    for plot in range(0,len(config.config['dcc_chart_figs'][tab_ids[tab]])):
        config.config['dcc_chart_figs'][tab_ids[tab]][plot].figure.update_xaxes(range=[unixToDatetime(dates_selected[0]), unixToDatetime(dates_selected[0])])
        content.append(html.Div(id='loading', children=config.config['dcc_chart_figs'][tab_ids[tab]][plot]))
    return html.Div(id='loading', children=content)

print("App ready: " + str(config.config['date_end']))


if __name__ == '__main__':
    app.run_server()

####
