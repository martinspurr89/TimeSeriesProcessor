import time
from dash import html
from dash import dcc
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Output, Dash, Trigger, FileSystemCache
import dash_bootstrap_components as dbc

steps, sleep_time = 100, 0.1
# Create example app.
app = Dash(prevent_initial_callbacks=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = html.Div([
    html.Button("Click me", id="btn"),
    dbc.Progress(id="progress", value=0, striped=True, max =100),
    html.Div(id="result"),
    dcc.Interval(id="interval", interval=500),
])
# Create a server side resource.
fsc = FileSystemCache("cache_dir")
fsc.set("progress", None)


@app.callback(Output("result", "children"), Trigger("btn", "n_clicks"))
def run_calculation():
    for i in range(steps):
        fsc.set("progress", str((i + 1) / steps))  # update progress
        time.sleep(sleep_time)  # do actual calculation (emulated by sleep operation)
    return "done"

@app.callback(Output("progress", "value"), Trigger("interval", "n_intervals"))
def update_progress():
    value = fsc.get("progress")  # get progress
    if value is None:
        raise PreventUpdate
    return int(float(fsc.get("progress")) * 100)


if __name__ == '__main__':
    app.run_server()