# -*- coding: utf-8 -*-

# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.
import sys
import getopt
import os
from pathlib import Path
import pickle

import dash
#from jupyter_plotly_dash import JupyterDash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import time
from pytz import timezone, utc
import base64
import humanize

from config import *

def helper():
    print("Help")

def processArguments():
    global io_dir
    io_dir = Path('C://Users//nms198//OneDrive - Newcastle University//3_Coding//Python//Rod_BES_BEWISE')
    #global verbose
    #try:
    #    opts, args = getopt.getopt(sys.argv[1:], "d:uv", ["io_dir=", "update"])
    #except getopt.GetoptError as err:
    #    # print help information and exit:
    #    print(str(err))  # will print something like "option -a not recognized"
    #    sys.exit(2)
    #for opt, arg in opts:
    #    if opt == "-v":
    #        verbose = True
    #    elif opt in ("-h", "--help"):
    #        helper()
    #        sys.exit()
    #    elif opt in ("-d", "--io_dir"):
    #        io_dir = Path(arg)
    #        assert os.path.exists(io_dir), "Folder does not exist at, "+str(folder)
    #    else:
    #        assert False, "unhandled option"

def getConfigCharts(io_dir):
    global config
    pfile_path = io_dir / "Temp" / 'config.pkl'
    if os.path.exists(pfile_path):
        with open(pfile_path, 'rb') as pfile:
            items = pickle.load(pfile)
        for key in list(items.keys()):
            config[key] = items[key]
    else:
        print("No pickled config.pkl data file exists - processing data!")
        import ProcessData
        ProcessData.main()


processArguments()
getConfigCharts(io_dir)

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
for chart in config['charts']:
    tab_name = "tab-" + str(t)
    tab_ids[tab_name] = chart
    tabs_init.append(dcc.Tab(label=config['info']['charts']['chart_label'][chart], value=tab_name, style={'backgroundColor': '#f5f5f5'}))
    t += 1

diff = datetime.now(timezone('UTC')) - config['date_end']
last_date = humanize.naturaldelta(diff)
update_text = html.Div(html.P('Data last retrieved ' + last_date + ' ago'))

app.layout = html.Div(children=[
    #html.Div([html.Img(src=app.get_asset_url('ToOL-PRO-BES.png'), style={'width':'90%', 'max-width': '100%'})], style={'textAlign': 'center'}),
    html.Div([html.Img(src='data:image/png;base64,{}'.format(encoded_image.decode()), style={'width':'90%', 'max-width': '100%'})], style={'textAlign': 'center'}),
    update_text,
    html.Div(children=[
        dcc.Tabs(id="tabs",
            value="tab-0",
            children=tabs_init),

        html.Div(children=[
            dcc.Loading(id='tabs-content')
        ]),
    ]),
])

@app.callback(Output('tabs-content', 'children'),
            [Input('tabs', 'value')])
def render_content(tab):
    time.sleep(2)
    content = []
    for plot in range(0,len(config['dcc_chart_figs'][tab_ids[tab]])):
        content.append(html.Div(id='loading', children=config['dcc_chart_figs'][tab_ids[tab]][plot]))
    return html.Div(id='loading', children=content)

print("App ready: " + str(config['date_end']))

app