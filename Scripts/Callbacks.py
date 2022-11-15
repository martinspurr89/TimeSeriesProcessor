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
import time

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
        Output('dates', 'data'),
        [Input('datetime-picker', 'startDate'), Input('datetime-picker', 'endDate'),
        Input({'type': 'chart_select', 'index': ALL}, 'n_clicks'), Input('date_slider', 'value')], 
        State('dates', 'data'))
    def update_datetime_range(startDate, endDate, chart, dates_selected, old_dates):
        start = func.unixToDatetime(old_dates[0])
        end = func.unixToDatetime(old_dates[1])
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id']
        if "chart" in ctx_input:
            chart = int(re.findall(r'\d+', ctx_input)[0])
            start = config.config['info']['charts']['chart_range_start'][chart]
            end = config.config['info']['charts']['chart_range_end'][chart]
        elif "datetime-picker.startDate" in ctx_input:
            start = pd.to_datetime(startDate)
        elif "datetime-picker.endDate" in ctx_input:
            end = pd.to_datetime(endDate)
        elif "date_slider" in ctx_input:
            start = func.unixToDatetime(dates_selected[0])
            end = func.unixToDatetime(dates_selected[1])
        return [func.unixTimeMillis(start), func.unixTimeMillis(end)]
    
    @app.callback(
        [Output('datetime-picker', 'startDate'), Output('datetime-picker', 'endDate'),
        Output('date_slider', 'value')], 
        Input('dates', 'data'))
    def update_datetime_sel(dates):
        return func.unixToDatetime(dates[0]), func.unixToDatetime(dates[1]), dates

    #VALIDITY
    @app.callback(
        [Output('resample_set', 'invalid'), 
        Output('height_set', 'invalid'), Output('font_set', 'invalid'), 
        Output('submit_val', 'disabled'), Output('export_submit', 'disabled')],
        [Input('html_on', 'value'), Input('csv_on', 'value'), Input('pdf_on', 'value'), Input('png_on', 'value'),
        Input('height_set', 'value'), Input('font_set', 'value'), Input('resample_radio', 'value'), Input('resample_set', 'value')])
    def calcValidity(html_on, csv_on, pdf_on, png_on, height, font, resolution, resample_set):
        if resolution == 'SET' and resample_set == None:
            r_invalid = True
        else:
            r_invalid = False
        if height == None:
            h_invalid = True
        else:
            h_invalid = False
        if font == None:
            f_invalid = True
        else:
            f_invalid = False
        if r_invalid or h_invalid or f_invalid:
            exp_disabled = True
            sub_disabled = True
        else:
            sub_disabled = False
            if not html_on and not csv_on and not pdf_on and not png_on:
                exp_disabled = True
            else:
                exp_disabled = False
        return r_invalid, h_invalid, f_invalid, sub_disabled, exp_disabled

    #CALC/STORE RESAMPLER VAL
    @app.callback(
        [Output('hi_res', 'data'), Output('resampler', 'data'), Output('resample_label', 'children'),
        Output('resample_div', 'style')],
        [Input('resample_radio', 'value'), Input('resample_set', 'value'), Input('dates', 'data')])
    def calcResampling(resolution, set, dates):
        hi_res = func.calcHiRes(dates)
        resampler = func.calcResampler(resolution, set, hi_res)
        if resolution == 'SET':
            style = {'display': 'block'}
        else:
            style = {'display': 'none'}
        alert = func.resampleAlert(resampler)

        return hi_res, resampler, alert, style


    #PLOT SET CHOSEN - SET PLOTS & TRACES
    @app.callback(
        [Output('plots_store', 'data'), Output('plot_chooser-content', 'children'),
        Output('traces_store', 'data'), Output('trace_chooser-content', 'children'),
        Output('plot_set_store', 'data'), Output('plot_set_drop', 'value'),
        Output("offcanvas-scrollable", "is_open")],
        [Input("open-offcanvas-button", "n_clicks"), Input('plot_set_drop', 'value'),
        Input({'type': 'plot_check', 'index': ALL}, 'value'), Input({'type': 'trace_check', 'index': ALL}, 'value')],
        [State('plots_store', 'data'), State('traces_store', 'data'), State('plot_set_store', 'data'), State("offcanvas-scrollable", "is_open"),
        State('plot_chooser-content', 'children'), State('trace_chooser-content', 'children')])
    def update_plots(n1, plot_set_str, plots_chosen, traces_chosen, plots, traces, plot_set_old, is_open, old_plot_content, old_trace_content):
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

        if ctx.triggered[0]['value'] is None:
            raise PreventUpdate

        if 'plot_check' in ctx_input:
            n1 = 0
            plots_chosen[0].sort() #sort alpha
            plots_chosen[0].sort(key=len) #sort by length (graph10+)
            new_plots = {}
            new_traces = {}
            for plot in plots_chosen[0]:
                new_plots[plot] = config.config['dcc_plot_names'][plot]
                if plot in traces.keys():
                    new_traces[plot] = traces[plot]
                else:
                    new_traces[plot] = config.config['dcc_trace_names'][plot]
            
            for plot_set_id in config.config['plot_sets']:
                if new_traces == config.config['plot_set_plots'][plot_set_id]:
                    plot_set = plot_set_id
                    break
                else:
                    plot_set = -1
        elif ctx_input == 'plot_set_drop':
            n1 = 0
            plot_set = int(plot_set_str)
            if plot_set != -1:
                new_plots = func.getPlots(plot_set)
                new_traces = {}
                for plot in config.figs['dcc_plot_figs']:
                    if plot.id in config.config['plot_set_plots'][plot_set].keys():
                        new_traces[plot.id] = config.config['plot_set_plots'][plot_set][plot.id]
                        new_traces[plot.id].sort()
            else:
                new_plots = plots
                new_traces = traces
        elif "trace_check" in ctx_input:
            new_plots = plots
            n1 = 0
            new_traces = deepcopy(traces)
            plot = ctx.triggered[0]['prop_id'].split('"')[3].split('_')[0]
            new_traces[plot] = ctx.triggered[0]['value']

            for plot_set_id in config.config['plot_sets']:
                if new_traces == config.config['plot_set_plots'][plot_set_id]:
                    plot_set = plot_set_id
                    break
                else:
                    plot_set = -1
        else:
            new_plots = plots
            new_traces = traces
            plot_set = plot_set_old

        plot_content = [dbc.CardHeader("Select Plots:", className="card-title",)]
        plot_content.append(html.Div(
            dbc.Checklist(
                id={
                    'type': 'plot_check',
                    'index': 'plots',
                },
                options=[{'label':config.config['dcc_plot_names'][plot], 'value':plot} for plot in config.config['dcc_plot_names']],
                value=list(new_plots.keys()),
                inline=True,
            ), className="p-3", id='loading2'),
        )
        plot_content_card = dbc.Row(dbc.Col(dbc.Card(plot_content)))

        card_contents = [dbc.CardHeader("Select traces:", className="card-title",)]
        for plot in config.figs['dcc_plot_figs']:
            if plot.id in new_plots:
                plot_name = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
                trace_content = [dbc.CardHeader(plot_name, className="card-title",)]
                trace_content.append(html.Div(
                    dbc.Checklist(
                        id={
                            'type': 'trace_check',
                            'index': plot.id + '_traces',
                        },
                        options=[{'label':re.sub('<.*?>', '', trace), 'value':trace} for trace in config.config['dcc_trace_names'][plot.id]],
                        value=new_traces[plot.id],
                        inline=True,
                        input_checked_style={
                            "backgroundColor": "#fa7268",
                            "borderColor": "#ea6258",
                        },
                    ), className="p-3"))
                card_contents.append(dbc.Col(trace_content, className = 'px-3'))
        trace_content_card = dbc.Row(dbc.Card(card_contents, id='trace_chooser'))

        if new_plots == plots:
            new_plots = dash.no_update
            if old_plot_content is not None:
                plot_content_card = dash.no_update
        if new_traces == traces:
            new_traces = dash.no_update
            if old_trace_content is not None:
                trace_content_card = dash.no_update
        plot_set_str = str(plot_set)
        if plot_set == plot_set_old:
            plot_set = dash.no_update
            plot_set_str = dash.no_update
        if n1:
            is_open = not is_open

        return new_plots, plot_content_card, new_traces, trace_content_card, plot_set, plot_set_str, is_open
    
    #SUBMIT CHART
    @app.callback([Output('chart-content', 'children'), Output('export_msg', 'children')],
                [Input('submit_flag', 'data'), Input('export_flag', 'data')],
                [State('dates','data'), State('resampler', 'data'),
                State('plots_store', 'data'), State('traces_store', 'data'), State('plot_set_store', 'data'),
                State('height_set', 'value'), State('font_set', 'value'),
                State('chart-content', 'children'), State('export_msg', 'children'), 
                State('html_on', 'value'), State('csv_on', 'value'), State('pdf_on', 'value'), State('png_on', 'value'),
                State('pdf_grp', 'children'), State('png_grp', 'children')])
    def create_content(submit, export, dates_selected, resample, plots, traces, plot_set, height, font, chart_content, export_msg,
                        html_on, csv_on, pdf_on, png_on, pdf_grp, png_grp):
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

        if ctx.triggered[0]['value'] is None:
            raise PreventUpdate

        if ctx_input == "submit_flag":
            if not submit and not export:
                raise PreventUpdate
        if ctx_input == "export_flag":
            if not export:
                raise PreventUpdate
        
        chart_data = func.create_chart_data(dates_selected, resample, traces)
        if export:
            export_progress = 0
            export_denom = (len([csv_on + html_on + pdf_on + png_on]))
            export_alert = dbc.Alert([html.I(className="bi bi-check-circle-fill me-2"), "Export complete",],
                color="success",
                className="d-flex align-items-center mb-0 py-0")
            
            start = func.unixToDatetime(dates_selected[0]).strftime("%Y%m%d")
            end = func.unixToDatetime(dates_selected[1]).strftime("%Y%m%d")
            export_name = start + "-" + end + "_"
            if resample > 0:
                export_name += str(resample) + "Min_"
            if plot_set > 0:
                export_name += "PS" + str(plot_set)
            else:
                export_name += "P" + str(len(plots))
            if csv_on:
                filename = export_name + '_data.csv'
                chart_data_to_export = chart_data.set_index('DateTime')
                chart_data_to_export.to_csv(config.io_dir / 'Output' / filename)
                export_progress += 1
                config.fsc_e.set("export_progress", str(export_progress / export_denom))  # update progress
                if not any([submit,html_on,pdf_on,png_on]):
                    return dash.no_update, export_alert
        
        if submit or all([export,any([html_on,pdf_on,png_on])]):
            if submit:
                progress_pc = 1 / (len(plots.keys()) + 1)
                config.fsc.set("submit_progress", str(progress_pc))  # update progress
            sorted_keys = sorted(sorted(plots.keys()), key=len)
            plots = dict(sorted(plots.items(), key=lambda pair: sorted_keys.index(pair[0])))
            content = func.create_chart_content(chart_data, dates_selected, plots, traces, height, font)
            if submit:
                load_card = html.Div(id='loading', children=content)
            if not all([export,any([html_on,pdf_on,png_on])]):
                return load_card, dash.no_update
            else:
                if html_on:
                    offline_chart = func.createOfflineCharts(content, plots, height, export_progress, export_denom)
                    func.exportHTML(offline_chart, dates_selected, resample, export_name)
                    config.fsc_e.set("export_progress", str(export_progress / export_denom))  # update progress
                if pdf_on:
                    for row in range(0,len(pdf_grp)):
                        for prop in pdf_grp[row]['props']['children']:
                            if prop['type'] == 'Input':
                                if prop['props']['id'] == "pdf_width":
                                    pdf_width = prop['props']['value']
                                if prop['props']['id'] == "pdf_height":
                                    pdf_height = prop['props']['value']
                    func.exportImage(export_progress, export_denom, export_name, content, plots, "pdf", pdf_width, pdf_height)
                if png_on:
                    for row in range(0,len(png_grp)):
                        for prop in png_grp[row]['props']['children']:
                            if prop['type'] == 'Input':
                                if prop['props']['id'] == "png_width":
                                    png_width = prop['props']['value']
                                if prop['props']['id'] == "png_height":
                                    png_height = prop['props']['value']
                                if prop['props']['id'] == "png_dpi":
                                    png_dpi = prop['props']['value']
                    func.exportImage(export_progress, export_denom, export_name, content, plots, "png", png_width, png_height, png_dpi)
                config.fsc_e.set("export_progress", str(1))  # update progress
                if submit:
                    return load_card, export_alert
                else:
                    return dash.no_update, export_alert
        else:
            time.sleep(2)
            raise PreventUpdate

    #SUBMIT PROGRESS
    @app.callback(
        [Output('submit_val', 'n_clicks'), Output('submit_flag', 'data'),
        Output("submit_progress", "value"), Output('submit_interval', 'disabled'),
        Output('export_submit', 'n_clicks'), Output('export_flag', 'data'),
        Output("export_progress", "value"), Output('export_interval', 'disabled')],
        [Input('submit_val', 'n_clicks'), Input('export_submit', 'n_clicks')],
        [Trigger("submit_interval", "n_intervals"), Trigger("export_interval", "n_intervals")],
        State('csv_on', 'value'), State('html_on', 'value'), State('pdf_on', 'value'), State('png_on', 'value'))
    def update_progress(submit, export, csv_on, html_on, pdf_on, png_on):
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]
        if ctx.triggered[0]['value'] is None:
            raise PreventUpdate

        if ctx_input == 'submit_interval' or ctx_input == 'submit_val':
            if submit > 0:
                config.fsc.set("submit_progress", str(0))  # clear progress
                return 0, True, 0, False, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            s_value = config.fsc.get("submit_progress")  # get progress
            if s_value is None:
                raise PreventUpdate
            s_progress = int(float(s_value) * 100)
            if s_progress is 100:
                if submit:
                    return dash.no_update, False, 100, True, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                else:
                    return dash.no_update, dash.no_update, 100, True, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            return dash.no_update, dash.no_update, s_progress, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        elif ctx_input == 'export_interval' or ctx_input == 'export_submit':
            if export > 0:
                config.fsc_e.set("export_progress", str(0))  # clear progress
                if any([html_on, pdf_on, png_on]):
                    config.fsc.set("submit_progress", str(0))  # clear progress
                    return 0, False, 0, False, 0, True, 0, False
                else:
                    return 0, False, 0, True, 0, True, 0, False
            if any([html_on, pdf_on, png_on]):
                s_value = config.fsc.get("submit_progress")  # get progress
                if s_value is None:
                    raise PreventUpdate
                s_progress = int(float(s_value) * 100)
                if s_progress is not 100:
                    return dash.no_update, dash.no_update, s_progress, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            e_value = config.fsc_e.get("export_progress")  # get progress
            if e_value is None:
                raise PreventUpdate
            e_progress = int(float(e_value) * 100)
            if e_progress is 100:
                return dash.no_update, dash.no_update, 100, dash.no_update, dash.no_update, False, 100, True
            else:
                return dash.no_update, dash.no_update, 100, dash.no_update, dash.no_update, dash.no_update, e_progress, dash.no_update
            
    #PDF
    @app.callback(Output('pdf_grp', 'children'),
                [Input('pdf_on', 'value'), Input({'type': 'pdf_size_select', 'index': ALL}, 'n_clicks')],
                State('pdf_grp', 'children'))
    def pdf_size_update(pdf_on, pdf_drop, pdf_grp):
        ctx = dash.callback_context
        ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

        if ctx_input == 'pdf_on':
            if pdf_on is not None:
                for row in range(0,len(pdf_grp)):
                    for prop in pdf_grp[row]['props']['children']:
                        if prop['type'] == 'Input' or prop['type'] == 'DropdownMenu':
                            if not pdf_on:
                                prop['props']['disabled'] = True
                            else:
                                prop['props']['disabled'] = False
        elif "index" in ctx_input:
            size = int(re.findall(r'\d+', ctx_input)[0])
            for row in range(0,len(pdf_grp)):
                for prop in pdf_grp[row]['props']['children']:
                    if prop['type'] == 'Input':
                        if prop['props']['id'] == 'pdf_width':
                            prop['props']['value'] = config.config['pdf_size_dict'][size]['width']
                        elif prop['props']['id'] == 'pdf_height':
                            prop['props']['value'] = config.config['pdf_size_dict'][size]['height']

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

    # #EXPORT INTERVAL
    # @app.callback(Output('export_interval', 'disabled'),
    #             [Input('export_submit', 'n_clicks'), Trigger("export_interval", "n_intervals")])
    # def enable_interval(export):
    #     ctx = dash.callback_context
    #     ctx_input = ctx.triggered[0]['prop_id'].split('.')[0]

    #     if ctx_input == 'export_interval':
    #         value = config.fsc_e.get("export_progress")  # get progress
    #         if value is None:
    #             return True
    #         if int(float(value) * 100) == 100:
    #             config.fsc_e.set("export_progress", str(0))  # clear progress
    #             return True
    #         elif int(float(value) * 100) == 0:
    #             return True

    #     if export > 0:
    #         return False
    #     else:
    #         return True

    # #EXPORT
    # @app.callback(Output('export_msg', 'children'),
    #             [Input('export_submit', 'n_clicks')],
    #             [State('plot_set_store', 'data'), State('date_slider','value'), State('plots_store', 'data'),
    #             State('resampler', 'data'), State('traces_store', 'data'), State('height_set', 'value'), State('font_set', 'value'),
    #             State('html_on', 'value'), State('pdf_on', 'value'), State('png_on', 'value'), State('pdf_grp', 'children'), State('png_grp', 'children')])
    # def render_content(n_clicks, plot_set, dates_selected, plots, resample, traces, height, font, html_on, pdf_on, png_on, pdf_grp, png_grp):
    #     #time.sleep(2)
    #     sorted_keys = sorted(sorted(plots.keys()), key=len)
    #     plots = dict(sorted(plots.items(), key=lambda pair: sorted_keys.index(pair[0])))
    #     content = func.create_chart_content(dates_selected, plots, resample, traces, height, font)

    #     export_alert = dbc.Alert([html.I(className="bi bi-check-circle-fill me-2"), "Export complete",],
    #         color="success",
    #         className="d-flex align-items-center mb-0 py-0")
    #     return export_alert

    # #EXPORT PROGRESS
    # @app.callback(Output("export_progress", "value"), Trigger("export_interval", "n_intervals"))
    # def update_progress():
    #     value = config.fsc_e.get("export_progress")  # get progress
    #     if value is None:
    #         raise PreventUpdate
    #     return int(float(config.fsc_e.get("export_progress")) * 100)
