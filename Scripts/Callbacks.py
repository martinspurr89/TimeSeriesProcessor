import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Output, Dash, Trigger, FileSystemCache
import pandas as pd
import numpy as np
import re
import dash_bootstrap_components as dbc
from copy import deepcopy

import Scripts.config as config
import Scripts.Functions as func

def register_callbacks(app):
    #CALLBACKS

    #SLIDER
    @app.callback(
        Output('slider-content', 'children'), 
        [Input('load', 'children')])
    def update_slider(load):
        startDate = pd.to_datetime(config.config['date_start'])
        endDate = pd.to_datetime(config.config['date_end'])
        content = []
        content.append(
            html.Div(dcc.RangeSlider(
                id='date_slider',
                updatemode='mouseup',
                min=func.unixTimeMillis(startDate),
                max=func.unixTimeMillis(endDate),
                count=1,
                step=60000,
                value=[func.unixTimeMillis(config.config['date_start']), func.unixTimeMillis(config.config['date_end'])],
                marks=func.getMarks(config.config['date_start'], config.config['date_end'], 8),
                className='px-5'),
        id='loading'))
        return content

    #DATETIME PICKER
    @app.callback(
        Output('date_slider', 'value'),
        [Input('datetime-picker', 'startDate'),
        Input('datetime-picker', 'endDate'), Input({'type': 'chart_select', 'index': ALL}, 'n_clicks')])
    def datetime_range(startDate, endDate, chart):
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]
        if "chart" in ctx_input:
            chart = int(re.findall(r'\d+', ctx_input)[0])
            startDate = config.config['info']['charts']['chart_range_start'][chart]
            endDate = config.config['info']['charts']['chart_range_end'][chart]

        startDate = pd.to_datetime(startDate)
        endDate = pd.to_datetime(endDate)
        return [func.unixTimeMillis(startDate), func.unixTimeMillis(endDate)]

    #TIME RANGE
    @app.callback(
        [Output('datetime-picker', 'startDate'), Output('datetime-picker', 'endDate')],
        [Input('date_slider', 'value')])
    def _update_time_range_label(dates_selected):
        return func.unixToDatetime(dates_selected[0]), func.unixToDatetime(dates_selected[1])

    #RESAMPLE SET
    @app.callback(
        [Output('resample_div', 'style'), Output('resample_set', 'disabled')],
        [Input('resample_radio', 'value')])
    def disableinput(value):
        if value == 'SET':
            return {'display': 'block'}, False
        else:
            return {'display': 'none'}, True

    #RESAMPLE SET INVALID
    @app.callback(
        [Output('resample_set', 'invalid'), Output('submit_val', 'disabled')],
        [Input('resampler', 'data')])
    def disableinput(value):
        if value == None:
            return True, True
        else:
            return False, False

    #CALC/STORE RESAMPLER VAL
    @app.callback(
        [Output('hi_res', 'data'), Output('resampler', 'data'), Output('resample_label', 'children')],
        [Input('resample_radio', 'value'), Input('resample_set', 'value'), Input('date_slider', 'value')], State('hi_res', 'data'))
    def calcResampling(resolution, set, dates_selected, hi_res):
        hi_res = func.calcHiRes(dates_selected)
        resampler = func.calcResampler(resolution, set, hi_res)
        return hi_res, resampler, func.resampleAlert(resampler)

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
                if plots == func.getPlots(plot_set):
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
                new_content[plot] = config.config['dcc_plot_names'][plot]
            return new_content
        elif ctx_input == 'plot_set_store':
            if plot_set != -1:
                return func.getPlots(plot_set)
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
                options=[{'label':config.config['dcc_plot_names'][plot], 'value':plot} for plot in config.config['dcc_plot_names']],
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
                    new_content[plot] = config.config['dcc_trace_names'][plot]
            return new_content
        elif ctx_input == 'plot_set_store':
            if plot_set != -1:
                
                traces = {}
                for plot in config.figs['dcc_plot_figs']:
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
        for plot in config.figs['dcc_plot_figs']:
            if plot.id in plots:
                plot_name = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
                content = [dbc.CardHeader(plot_name, className="card-title",)]
                content.append(html.Div(
                    dbc.Checklist(
                        id={
                            'type': 'trace_check',
                            'index': plot.id + '_traces',
                        },
                        options=[{'label':re.sub('<.*?>', '', trace), 'value':trace} for trace in config.config['dcc_trace_names'][plot.id]],
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

    #SUBMIT INTERVAL
    @app.callback(Output('submit_interval', 'disabled'),
                [Input('submit_val', 'n_clicks'), Input('export_submit', 'n_clicks'), Input('chart_store', 'data')])
    def enable_interval(submit, export, chart):
        ctx = dash.callback_context

        for ctx_in in ctx.triggered:
            if ctx_in['prop_id'].split('.')[0] == 'chart_store':
                config.fsc.set("submit_progress", str(0))  # clear progress
                return True
        if submit > 0 or export > 0:
            return False
        else:
            return True

    #SUBMIT CHART
    @app.callback(Output('chart-content', 'children'),
                [Input('chart_store', 'data')])
    def render_content(content):
        return html.Div(id='loading', children=content)

    #SUBMIT CHART
    @app.callback(Output('submit_interval', 'n_intervals'),
                [Input('chart_store', 'data')])
    def render_content(content):
        return 0

    #SUBMIT CHART
    @app.callback(Output('chart_store', 'data'),
                [Input('submit_interval', 'n_intervals')],
                [State('plot_set_store', 'data'), State('date_slider','value'), State('plots_store', 'data'),
                State('resampler', 'data'), State('traces_store', 'data'), State('height_set', 'value'), State('font_set', 'value'),
                State('chart-content', 'children')])
    def create_content(n_intervals, plot_set, dates_selected, plots, resample, traces, height, font, chart_content):
        #time.sleep(2)
        if n_intervals == 1:
            sorted_keys = sorted(sorted(plots.keys()), key=len)
            plots = dict(sorted(plots.items(), key=lambda pair: sorted_keys.index(pair[0])))
            content = func.create_chart_content(dates_selected, plots, resample, traces, height, font)
            return content
        else:
            raise PreventUpdate

    #SUBMIT PROGRESS
    @app.callback(Output("submit_progress", "value"), Trigger("submit_interval", "n_intervals"))
    def update_progress():
        value = config.fsc.get("submit_progress")  # get progress
        if value is None:
            raise PreventUpdate
        return int(float(config.fsc.get("submit_progress")) * 100)

    #PDF
    @app.callback(Output('pdf_grp', 'children'),
                [Input('pdf_on', 'value'), Input({'type': 'pdf_size_select', 'index': ALL}, 'n_clicks')],
                State('pdf_grp', 'children'))
    def pdf_size_update(pdf_on, pdf_drop, pdf_grp):
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

        if ctx_input == 'pdf_on':
            if pdf_on is not None:
                for prop in range(0,len(pdf_grp)):
                    if pdf_grp[prop]['type'] == 'Input' or pdf_grp[prop]['type'] == 'DropdownMenu':
                        pdf_grp[prop]['props']['disabled'] = False
            else:
                for prop in range(0,len(pdf_grp)):
                    if pdf_grp[prop]['type'] == 'Input' or pdf_grp[prop]['type'] == 'DropdownMenu':
                        pdf_grp[prop]['props']['disabled'] = True
        elif "index" in ctx_input:
            size = int(re.findall(r'\d+', ctx_input)[0])
            for prop in range(0,len(pdf_grp)):
                if pdf_grp[prop]['type'] == 'Input':
                    if pdf_grp[prop]['props']['id'] == 'pdf_width':
                        pdf_grp[prop]['props']['value'] = config.config['pdf_size_dict'][size]['width']
                    elif pdf_grp[prop]['props']['id'] == 'pdf_height':
                        pdf_grp[prop]['props']['value'] = config.config['pdf_size_dict'][size]['height']

        return pdf_grp

    #PNG
    @app.callback(Output('png_grp', 'children'),
                [Input('png_on', 'value'), Input({'type': 'png_size_select', 'index': ALL}, 'n_clicks')],
                State('png_grp', 'children'))
    def png_size_update(png_on, png_drop, png_grp):
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

        if ctx_input == 'png_on':
            if png_on is not None:
                for prop in range(0,len(png_grp)):
                    if png_grp[prop]['type'] == 'Input' or png_grp[prop]['type'] == 'DropdownMenu':
                        png_grp[prop]['props']['disabled'] = False
            else:
                for prop in range(0,len(png_grp)):
                    if png_grp[prop]['type'] == 'Input' or png_grp[prop]['type'] == 'DropdownMenu':
                        png_grp[prop]['props']['disabled'] = True
        elif "index" in ctx_input:
            size = int(re.findall(r'\d+', ctx_input)[0])
            for prop in range(0,len(png_grp)):
                if png_grp[prop]['type'] == 'Input':
                    if png_grp[prop]['props']['id'] == 'png_width':
                        png_grp[prop]['props']['value'] = config.config['png_size_dict'][size]['width']
                    elif png_grp[prop]['props']['id'] == 'png_height':
                        png_grp[prop]['props']['value'] = config.config['png_size_dict'][size]['height']
                    elif png_grp[prop]['props']['id'] == 'png_dpi':
                        png_grp[prop]['props']['value'] = config.config['png_size_dict'][size]['png_dpi']

        return png_grp

    #EXPORT ENABLE
    @app.callback(Output('export_submit', 'disabled'),
                [Input('html_on', 'value'), Input('pdf_on', 'value'), Input('png_on', 'value')])
    def export_update(html_on, pdf_on, png_on):
        if html_on is not None or pdf_on is not None or png_on is not None:
            return False
        else:
            return True

    #EXPORT INTERVAL
    @app.callback(Output('export_interval', 'disabled'),
                [Input('export_submit', 'n_clicks'), Trigger("export_interval", "n_intervals")])
    def enable_interval(export):
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

        if ctx_input == 'export_interval':
            value = config.fsc.get("export_progress")  # get progress
            if value is None:
                return True
            if int(float(value) * 100) == 100:
                config.fsc.set("export_progress", str(0))  # clear progress
                return True
            elif int(float(value) * 100) == 0:
                return True

        if export > 0:
            return False
        else:
            return True

    #EXPORT
    @app.callback(Output('export_msg', 'children'),
                [Input('export_submit', 'n_clicks')],
                [State('plot_set_store', 'data'), State('date_slider','value'), State('plots_store', 'data'),
                State('resampler', 'data'), State('traces_store', 'data'), State('height_set', 'value'), State('font_set', 'value'),
                State('html_on', 'value'), State('pdf_on', 'value'), State('png_on', 'value'), State('pdf_grp', 'children'), State('png_grp', 'children')])
    def render_content(n_clicks, plot_set, dates_selected, plots, resample, traces, height, font, html_on, pdf_on, png_on, pdf_grp, png_grp):
        #time.sleep(2)
        sorted_keys = sorted(sorted(plots.keys()), key=len)
        plots = dict(sorted(plots.items(), key=lambda pair: sorted_keys.index(pair[0])))
        content = func.create_chart_content(dates_selected, plots, resample, traces, height, font)

        export_alert = dbc.Alert([html.I(className="bi bi-check-circle-fill me-2"), "Export complete",],
            color="success",
            className="d-flex align-items-center mb-0 py-0")
        return export_alert

    #EXPORT PROGRESS
    @app.callback(Output("export_progress", "value"), Trigger("export_interval", "n_intervals"))
    def update_progress():
        value = config.fsc.get("export_progress")  # get progress
        if value is None:
            raise PreventUpdate
        return int(float(config.fsc.get("export_progress")) * 100)
