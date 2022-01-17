def register_callbacks(app):
    #CALLBACKS

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
            startDate = charts['chart_range_start'][chart]
            endDate = charts['chart_range_end'][chart]

        startDate = pd.to_datetime(startDate)
        endDate = pd.to_datetime(endDate)
        return [unixTimeMillis(startDate), unixTimeMillis(endDate)]


    #SLIDER
    @app.callback(
        Output('slider-content', 'children'),
        [Input('load', 'children')])
    def update_slider(load):
        startDate = pd.to_datetime(start)
        endDate = pd.to_datetime(end)
        content = []
        content.append(
            html.Div(dcc.RangeSlider(
                id='date_slider',
                updatemode='mouseup',
                min=unixTimeMillis(startDate),
                max=unixTimeMillis(endDate),
                count=1,
                step=60000,
                value=[unixTimeMillis(start), unixTimeMillis(end)],
                marks=getMarks(start, end, 8),
                className='px-5'),
        id='loading'))
        return content

    #TIME RANGE START
    @app.callback(
        Output('datetime-picker', 'startDate'),
        [Input('date_slider', 'value')])
    def _update_time_range_label(dates_selected):
        return unixToDatetime(dates_selected[0])

    #TIME RANGE END
    @app.callback(
        Output('datetime-picker', 'endDate'),
        [Input('date_slider', 'value')])
    def _update_time_range_label(dates_selected):
        return unixToDatetime(dates_selected[1])

    #INITIAL RES
    @app.callback(
        Output('hi_res', 'data'),
        [Input('load', 'children'), Input('date_slider', 'value')])
    def _update_res_val(load, dates_selected):
        return calcHiRes(dates_selected)

    #RESAMPLE SET DISPLAY
    @app.callback(
        Output('resample_div', 'style'),
        [Input('resample_radio', 'value')])
    def disableinput(value):
        if value == 'SET':
            return {'display': 'block'}
        else:
            return {'display': 'none'}

    #RESAMPLE SET DISABLE
    @app.callback(
        Output('resample_set', 'disabled'),
        [Input('resample_radio', 'value')])
    def disableinput(value):
        if value == 'SET':
            return False
        else:
            return True

    #RESAMPLE SET INVALID
    @app.callback(
        Output('resample_set', 'invalid'),
        [Input('resampler', 'data')])
    def disableinput(value):
        if value == None:
            return True
        else:
            return False

    #RESAMPLE/SUBMIT INVALID
    @app.callback(
        Output('submit_val', 'disabled'),
        [Input('resampler', 'data')])
    def disableinput(value):
        if value == None:
            return True
        else:
            return False

    #CALC/STORE RESAMPLER VAL
    @app.callback(
        Output('resampler', 'data'),
        [Input('resample_radio', 'value'), Input('resample_set', 'value'), Input('date_slider', 'value')], State('hi_res', 'data'))
    def calcResampling(resolution, set, dates_selected, hi_res):
        hi_res = calcHiRes(dates_selected)
        return calcResampler(resolution, set, hi_res)

    #UPDATE RESAMPLER ALERT
    @app.callback(
        Output('resample_label', 'children'),
        [Input('resampler', 'data')])
    def printResampler(value):
        return resampleAlert(value)

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
                if plots == getPlots(plot_set):
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
                new_content[plot] = all_plots[plot]
            return new_content
        elif ctx_input == 'plot_set_store':
            if plot_set != -1:
                return getPlots(plot_set)
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
                options=[{'label':all_plots[plot], 'value':plot} for plot in all_plots],
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
                    new_content[plot] = all_traces[plot]
            return new_content
        elif ctx_input == 'plot_set_store':
            if plot_set != -1:
                
                traces = {}
                for plot in config.config['dcc_plot_set_figs']:
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
        for plot in config.config['dcc_plot_set_figs']:
            if plot.id in plots:
                plot_name = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
                content = [dbc.CardHeader(plot_name, className="card-title",)]
                content.append(html.Div(
                    dbc.Checklist(
                        id={
                            'type': 'trace_check',
                            'index': plot.id + '_traces',
                        },
                        options=[{'label':re.sub('<.*?>', '', trace), 'value':trace} for trace in all_traces[plot.id]],
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

    #CHART
    @app.callback(Output('chart-content', 'children'),
                [Input('submit_val', 'n_clicks')],
                [State('plot_set_store', 'data'), State('date_slider','value'), State('plots_store', 'data'),
                State('resampler', 'data'), State('traces_store', 'data'), State('height_set', 'value'), State('font_set', 'value')])
    def render_content(n_clicks, plot_set, dates_selected, plots, resample, traces, height, font):
        #time.sleep(2)
        sorted_keys = sorted(sorted(plots.keys()), key=len)
        plots = dict(sorted(plots.items(), key=lambda pair: sorted_keys.index(pair[0])))
        
        content = []
        chart_data = config.config['all_data'].query(
                'DateTime > "' + str(unixToDatetime(dates_selected[0])) + '"').query(
                'DateTime < "' + str(unixToDatetime(dates_selected[1])) + '"').set_index('DateTime')
        if resample > 0:
            chart_data = chart_data.groupby(pd.Grouper(freq=str(resample) +'Min')).aggregate(np.mean)
        chart_data = chart_data.reset_index()

        for plot_orig in config.config['dcc_plot_set_figs']:
            if plot_orig.id in plots:
                plot_name = config.config['dcc_plot_names'][plot_orig.id]
                plot = addDatatoPlot(deepcopy(plot_orig), traces, chart_data, dates_selected, plots, height)
                plot = modifyPlot(plot, plot_name, plots, font)
                plot = setAxisRange(plot, plot_name, chart_data, traces[plot_orig.id])
                content.append(html.Div(id='loading', children=plot))
        return html.Div(id='loading', children=content)
