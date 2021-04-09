import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html

fig = go.Figure()
fig.layout.yaxis.ticklabelposition = "inside"
fig
fig.write_image("img.png")

dash_fig = dcc.Graph(id='graph', figure=fig)

app = dash.Dash(__name__)

app.layout = html.Div(children=[dash_fig])

if __name__ == '__main__':
    app.run_server()