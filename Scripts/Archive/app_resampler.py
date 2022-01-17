import plotly.graph_objects as go; import numpy as np
from plotly_resampler import FigureResampler

import config
import ProcessData

plot = "TEMP"
chart = 2

chart_info = ProcessData.getChartInfo(chart)
plot_info = chart_info.query('plot == "' + plot + '"')
plot_data = config.config['chart_dfs_mlt'][chart].query('Plot == "' + plot + '"')
plot_fig = go.Figure()
#Add traces
for par_id in range(0, len(plot_data.Parameter.unique())):
    par = plot_data.Parameter.unique()[par_id]
    plot_fig = addTrace(par, plot_fig, chart)
#Modify plot layout
plot_fig = modifyPlot(plot_fig, plot, chart)
plot_fig = setAxisRange(plot_fig, plot, chart)
#Add date to last plot in chart
if plot == chart_info['plot'].to_list()[len(chart_info['plot'].to_list())-1]:
    plot_fig.update_xaxes(showticklabels=True, ticks="outside")

x = np.arange(1_000_000)
noisy_sin = (3 + np.sin(x / 200) + np.random.randn(len(x)) / 10) * x / 1_000

fig = FigureResampler(go.Figure())
fig.add_trace(go.Scattergl(name='noisy sine', showlegend=True), hf_x=x, hf_y=noisy_sin)

#fig.show_dash(mode='inline')


fig2 = FigureResampler(go.Figure())
fig2.add_trace(go.Scattergl(name='noisy sine', showlegend=True), hf_x=x, hf_y=noisy_sin)

fig2.show_dash(mode='inline')