import pandas as pd
from tqdm import trange, tqdm

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import datetime
from datetime import datetime, timedelta
from pytz import timezone

import os
import re

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import time
import numpy as np

# Date Functions
def set_date(date_str, old_tz, dt_format = "%d/%m/%Y %H:%M:%S"):
    if date_str == 'NaT':
        return pd.NaT
    else:
        datetime_set_naive = datetime.strptime(date_str, dt_format)
        datetime_set_old = timezone(old_tz).localize(datetime_set_naive)
        datetime_set_utc = datetime_set_old.astimezone(timezone('UTC'))
        return datetime_set_utc

def date_parser(date_, time_, dt_format = "%d/%m/%Y %H:%M:%S"):
    return set_date(date_ + " " + time_, 'UTC', dt_format)

# Experiment start date
date_start = set_date("2019-06-04 13:03:17", "UTC", "%Y-%m-%d %H:%M:%S")
date_now = datetime.now(timezone('UTC'))

# Date Functions continued
def date_range(window=-1, start=date_start, end=date_now):
    if pd.isna(start):
        start = date_start
    if pd.isna(end):
        end = date_now
    if window != -1:
        if not pd.isna(window):
            start = end - timedelta(days=window)
    return start, end

info = pd.read_excel("Info/Info.xlsx", sheet_name=None, index_col=0)

plots = []
for plot, row in info['plots'].iterrows():
    plot_range = date_range(window = row['plot_range_window'], start = set_date(str(row['plot_range_start']), "UTC", "%Y-%m-%d %H:%M:%S"), end = set_date(str(row['plot_range_end']), "UTC", "%Y-%m-%d %H:%M:%S"))
    info['plots'].loc[plot, 'plot_range_start'] = plot_range[0]
    info['plots'].loc[plot, 'plot_range_end'] = plot_range[1]
    info['plots'].loc[plot, 'plot_range_window'] = plot_range[1] - plot_range[0]
    plots.append(plot)

this_dataset_info = info['datasets'].iloc[5]
data_path = info['datasets']['data_folder_path'][5]

selected_pars = ['A1 C', 'A2 C', 'A3 C', 'A4 C',
                 'B1 C', 'B2 C', 'B3 C', 'B4 C',
                 'C1 C', 'C2 C', 'C3 C', 'C4 C',
                 'TEMP SETPOINT', 'A TEMP', 'B TEMP', 'C TEMP',
                 'BOX TEMP', 'WATER TEMP', 'AMBIENT TEMP',
                 'PUMP FR',
                 'HOSE A TEMP', 'HOSE B TEMP', 'HOSE C TEMP',
                 'MAT 1 TEMP', 'MAT 2 TEMP', 'MAT 3 TEMP',
                 'TILT']

all_days = []

for filename in tqdm(os.listdir(data_path), desc="Open files"):
    if re.search(this_dataset_info['file_pat'], filename) and not filename.startswith('.'):
        df = pd.read_csv("".join([data_path, filename]), parse_dates=[['Date', 'Time']], dayfirst=True,
                         date_parser=date_parser)
        df_selected = df[['Date_Time'] + selected_pars]
        all_days.append(df_selected)

all_data = pd.concat(all_days, axis=0, ignore_index=True)
all_data.sort_values(by=['Date_Time'], inplace=True)
all_data = all_data.reset_index(drop=True)

plot_dfs = []

for plot in tqdm(plots, desc="Create plot DFs"):
    if info['plots'].loc[plot, 'plot_status'] == 'ON':
        mask = (all_data['Date_Time'] >= info['plots'].loc[plot, 'plot_range_start']) & (all_data['Date_Time'] <= info['plots'].loc[plot, 'plot_range_end'])
        df = all_data.loc[mask]
        if info['plots'].loc[plot, 'plot_res'] != 0:
            df = df.resample("".join([str(info['plots'].loc[plot, 'plot_res']), 'T']), on='Date_Time').mean()
            df = df.reset_index()
        else:
            df = df.reset_index(drop=True)
        plot_dfs.append(df)
    else:
        plot_dfs.append("")

plot_dfs_mlt = []

a = 0
for plot in tqdm(plots, desc="Melt DFs"):
    if info['plots'].loc[plot, 'plot_status'] == 'ON':
        df = plot_dfs[a].melt(id_vars=['Date_Time'], var_name='Parameter', value_name='Value')
        plot_dfs_mlt.append(df)
    else:
        plot_dfs_mlt.append("")
    a = a + 1

# Assign chart etc
colors = ["red", "orange", "green", "blue",
          "red", "orange", "green", "blue",
          "red", "orange", "green", "blue",
          "black", "red", "green", "blue",
          "cadetblue", "chartreuse", "darkviolet",
          "black",
          "red", "green", "blue",
          "orange", "cyan", "darkviolet",
         "black"]
line_sizes = [1, 1, 1, 1,
              1, 1, 1, 1,
              1, 1, 1, 1,
              1, 1, 1, 1,
              1, 1, 1,
              1,
              1, 1, 1,
              1, 1, 1,
             1]
rows = [1, 1, 1, 1,
        2, 2, 2, 2,
        3, 3, 3, 3,
        4, 4, 4, 4,
        4, 4, 4,
        5,
        6, 6, 6,
        6, 6, 6,
       7]
labels = ["1", "2", "3", "4",
          "1", "2", "3", "4",
          "1", "2", "3", "4",
          "SP", "A", "B", "C",
          "BOX", "WATER", "AMBIENT", 
          "PUMP",
          "HA", "HB", "HC",
          "M1", "M2", "M3",
         "TILT"]
legend_shows = [True, True, True, True,
                False, False, False, False,
                False, False, False, False,
                True, True, True, True,
                True, True, True,
                True,
                True, True, True,
                True, True, True,
               True]

if not os.path.exists("Images"):
    os.mkdir("Images")

figs = []
a = 0

for plot in tqdm(plots, desc="Make subplots"):
    if info['plots'].loc[plot, 'plot_status'] == 'ON':
        fig = make_subplots(
            rows=max(rows[0:len(plot_dfs_mlt[a].Parameter.unique())]), cols=1, shared_xaxes=True, vertical_spacing=0.05
        )

        for i in range(0, len(plot_dfs_mlt[a].Parameter.unique())):
            x_data = plot_dfs_mlt[a][plot_dfs_mlt[a].Parameter == plot_dfs_mlt[a].Parameter.unique()[i]].Date_Time
            y_data = plot_dfs_mlt[a][plot_dfs_mlt[a].Parameter == plot_dfs_mlt[a].Parameter.unique()[i]].Value
            name = labels[i]

            fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines',
                                     name=name, line=dict(color=colors[i], width=line_sizes[i]),
                                     connectgaps=True, legendgroup=labels[i], showlegend=legend_shows[i]
                                     ), row=rows[i], col=1)

        # Update yaxis properties
        fig.update_yaxes(title_text="BES A (uA)", range=[0, max(plot_dfs_mlt[a]['Value'])], row=1, col=1)
        fig.update_yaxes(title_text="BES B (uA)", range=[0, max(plot_dfs_mlt[a]['Value'])], row=2, col=1)
        fig.update_yaxes(title_text="BES C (uA)", range=[0, max(plot_dfs_mlt[a]['Value'])], row=3, col=1)
        fig.update_yaxes(title_text="Temp (°C)",  range=[0, 38], row=4, col=1)
        fig.update_yaxes(title_text="Pump FR (ml/min)", range=[0, 33], row=5, col=1)
        fig.update_yaxes(title_text="Heater Temp (°C)", row=6, col=1)
        fig.update_yaxes(title_text="Tilt (°)", row=7, col=1)

        fig.update_layout(
            paper_bgcolor='rgb(255,255,255,0)',
            legend_bgcolor='rgb(255,255,255,0)',
            font=dict(
                family="Arial", size=11, color="#000000"))
        figs.append(fig)
    else:
        figs.append("")
    a = a + 1

a = 0
for plot in tqdm(plots, desc="Export PDFs"):
    if info['plots'].loc[plot, 'plot_status'] == 'ON':
        figs[a].write_image("Images/fig_" + plot + ".pdf", width=774, height=1052.4, scale=10 / 3)
    a = a + 1

a = 0
for plot in tqdm(plots, desc="Export PNGs"):
    if info['plots'].loc[plot, 'plot_status'] == 'ON':
        figs[a].write_image("Images/fig_" + plot + ".png", width=800, height=450, scale=5)
    a = a + 1

a = 0
for plot in tqdm(plots, desc="Update app for interactivity"):
    if info['plots'].loc[plot, 'plot_status'] == 'ON':
        figs[a].update_layout(
            # height=600,
            # width=900,
            **{"".join(
                ["xaxis", str(max(rows[0:len(plot_dfs_mlt[a].Parameter.unique())])), "_rangeslider_visible"]): True})

        # figs[a].show()
    a = a + 1

# Dash app

dfs = [pd.DataFrame({"xaxis": ["thing", "otherthing", "anotherthing"],
                     "yaxis": [64, 14, 62]}),
       pd.DataFrame({"xaxis": ["newthing", "newotherthing", "newanotherthing"],
                     "yaxis": [344, 554, 112]})]

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

i = 0
output = []
# here you can define your logic on how many times you want to loop
a = 0
for plot in tqdm(plots, desc="Make subplots for app"):
    if info['plots'].loc[plot, 'plot_status'] == 'ON':
        fig = make_subplots(
            rows=max(rows[0:len(plot_dfs_mlt[a].Parameter.unique())]), cols=1, shared_xaxes=True, vertical_spacing=0.05
        )

        for i in range(0, len(plot_dfs_mlt[a].Parameter.unique())):
            x_data = plot_dfs_mlt[a][plot_dfs_mlt[a].Parameter == plot_dfs_mlt[a].Parameter.unique()[i]].Date_Time
            y_data = plot_dfs_mlt[a][plot_dfs_mlt[a].Parameter == plot_dfs_mlt[a].Parameter.unique()[i]].Value
            name = labels[i]

            fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines',
                                     name=name, line=dict(color=colors[i], width=line_sizes[i]),
                                     connectgaps=True, legendgroup=labels[i], showlegend=legend_shows[i]
                                     ), row=rows[i], col=1)

        # Update yaxis properties
        fig.update_yaxes(title_text="BES A (uA)", range=[0, max(plot_dfs_mlt[a]['Value'])], row=1, col=1)
        fig.update_yaxes(title_text="BES B (uA)", range=[0, max(plot_dfs_mlt[a]['Value'])], row=2, col=1)
        fig.update_yaxes(title_text="BES C (uA)", range=[0, max(plot_dfs_mlt[a]['Value'])], row=3, col=1)
        fig.update_yaxes(title_text="Temp (°C)",  range=[0, 38], row=4, col=1)
        fig.update_yaxes(title_text="Pump FR (ml/min)", range=[0, 33], row=5, col=1)
        fig.update_yaxes(title_text="Heater Temp (°C)", row=6, col=1)
        fig.update_yaxes(title_text="Tilt (°)", row=7, col=1)
        
        fig.update_xaxes(range=[min(plot_dfs_mlt[a]['Date_Time']), max(plot_dfs_mlt[a]['Date_Time'])])

        fig.update_layout(
            paper_bgcolor='rgb(255,255,255,0)',
            legend_bgcolor='rgb(255,255,255,0)',
            font=dict(
                family="Arial", size=11, color="#000000"),
            yaxis=dict(
                scaleanchor="x",
                scaleratio=0.2)
            #**{"".join(
            #    ["xaxis", str(max(rows[0:len(plot_dfs_mlt[a].Parameter.unique())])), "_rangeslider_visible"]): True}
            )

        output.append(
            dcc.Graph(id='graph' + str(a),
                      figure=fig,
                      style={'width': '98vw', 'height': '196vh'})
        )
    else:
        output.append("Plot switched off in Info")
    a = a + 1

#app = JupyterDash('__name__')
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

card_style = {
    "box-shadow": "0 4px 5px 0 rgba(0,0,0,0.14), 0 1px 10px 0 rgba(0,0,0,0.12), 0 2px 4px -1px rgba(0,0,0,0.3)"
}

#app.scripts.config.serve_locally = True

# app.layout = dcc.Loading(
#     children=[html.Div(

tabs_init = []
p = 0
for plot in plots:
    if info['plots'].loc[plot, 'plot_status'] == 'ON':
        tabs_init.append(dcc.Tab(label=info['plots']['plot_label'][plot], value="".join(["tab-", str(p)]),
                                            style={'backgroundColor': '#f5f5f5'}))
    p = p+1

app.layout = html.Div(className="sans-serif",
                      children=[
                    html.Div(
                        className="w-60 center pt4",
                        children=[
                            dcc.Tabs(
                                id="tabs",
                                value="tab-0",
                                children=tabs_init,
                                colors={
                                    "primary": "white",
                                    "background": "white",
                                    "border": "#d2d2d2",
                                },
                                parent_style=card_style,
                            ),
                            html.Div(
                                children=[
                                    dcc.Loading(id='tabs-content',
                                                type='graph', className='pv6')
                                ],
                                className='pa4'
                            ),
                        ],
                        style={},
                    ),
                ],
            )# ], type='default', fullscreen=True)

@app.callback(Output('tabs-content', 'children'),
              [Input('tabs', 'value')])
def render_content(tab):
    time.sleep(2)
    if tab == 'tab-0':
        return html.Div(children=[
            # html.Label('From 1994 to 2018', id='time-range-label'),
            html.Div(id='loading-0', children=output[0])])
    elif tab == 'tab-1':
        return html.Div(id='loading-1', children=output[1])
    elif tab == 'tab-2':
        return html.Div(id='loading-2', children=output[2])
    elif tab == 'tab-3':
        return html.Div(id='loading-3', children=output[3])

print("App ready: " + str(date_now))

if __name__ == '__main__':
    app.run_server()
    #debug=True, dev_tools_hot_reload_interval=5000)
                   #dev_tools_hot_reload_max_retry=30)