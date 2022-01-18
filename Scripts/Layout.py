from dash import html
from dash import dcc
from pytz import timezone, utc
import dash_datetimepicker
import dash_bootstrap_components as dbc
import base64

import Scripts.config as config
import Scripts.Functions as func

def prepare_layout():
    components = {}
    
    image_filename = 'assets\ToOL-PRO-BES.png'
    plot_set = min(config.config['plot_sets'])
    charts = config.config['info']['charts']
    chart = min(charts.index)
    start = min(config.data['all_data'].DateTime)
    end = max(config.data['all_data'].DateTime)

    components["header_card"] = dbc.Card([
        dbc.CardImg(src=image_filename, top=True),
        html.P(func.update_text(), className="card-text", style={'textAlign': 'left'}, id='load'),
    ], className = 'px-3')

    datetime_items = []
    for chart in set(config.config['info']['charts'].index):
        datetime_items.extend(
            dbc.DropdownMenuItem(str(chart)  + ": " + charts['chart_label'][chart], id={
                'type': 'chart_select',
                'index': "chart_" + str(chart),
            }),
            html.P(
                charts['chart_range_start'][chart].strftime("%d/%m/%Y %H:%M") + " ↔ " +
                charts['chart_range_end'][chart].strftime("%d/%m/%Y %H:%M"),
            className="text-muted px-4 mb-1",)
        )

    datetime_dropdown = html.Div(
        [
            dbc.DropdownMenu(
                id='datetime_drop',
                label="Chart Range",
                children=datetime_items,
            ),
        ], className='py-1 px-4', style={'textAlign': 'left'}
    )

    datetime_pick = html.Div(children=[
                        dash_datetimepicker.DashDatetimepicker(id="datetime-picker", 
                        startDate = start, endDate = end, utc=True, locale="en-gb"),
                    ], className='p-1', style = {'align-self': 'center'})

    datetime_slider = html.Div(children=[
                            dcc.Store(id='hi_res'),
                            dbc.Spinner(id='slider-content', color="info")
                        ], className='p-1')

    components['datetime_selector'] = dbc.Card([
        dbc.CardHeader("DateTime Range", className="card-title",),
        dbc.Row([
            dbc.Col([datetime_dropdown]),
            dbc.Col([datetime_pick]),
            dbc.Col([])
        ]),
        dbc.Row([datetime_slider]),
    ])

    components['plot_set_dropdown'] = html.Div(
        [
            dbc.Select(
                id='plot_set_drop',
                options=[
                    {"label": 'Plot Set ' + str(plot_set), "value": plot_set} for plot_set in set(config.config['plot_sets'])] + 
                    [{'label': 'Plot Set Custom', 'value': -1}],
                value=str(plot_set),
            ),
        ], className='p-3', style={'textAlign': 'left'}
    )

    components['resampler_radio'] = html.Div(
        [
            dbc.Row([
                dbc.Col(dbc.RadioItems(
                    id="resample_radio",
                    options=[
                        {'label': 'Low', 'value': 'LOW'},
                        {'label': 'High', 'value': 'HIGH'},
                        {'label': 'None', 'value': 'NONE'},
                        {'label': 'Set', 'value': 'SET'},
                    ],
                    value='HIGH',
                    inline=True
                ), className='py-2'),
                dbc.Col(html.Div(dbc.Input(id='resample_set', type="number", min=1, step=1,
                placeholder="mins"), id="resample_div"), width=3),
            ], align="center"),

        ], className='py-1 px-3'
    )

    components['resampler_input'] = html.Div(
        [
            dcc.Store(id='resampler'),
            dbc.Row([
                dbc.Col(html.Div(dbc.Spinner(id='resample_label')),)
            ]),
        ], className='p-0', style={'textAlign': 'center'}
    )

    pdf_page_sizes = []
    for size in ['A4', 'PPT']:
        pdf_page_sizes.append(dbc.DropdownMenuItem(str(size)  + ": " + size, id={
                            'type': 'pdf_size_select',
                            'index': "size_" + str(size),
                        }))
        pdf_page_sizes.append(html.P(
                size,
                className="text-muted px-4 mb-1",))

    png_page_sizes = []
    for size in ['A4', 'PPT']:
        png_page_sizes.append(dbc.DropdownMenuItem(str(size)  + ": " + size, id={
                            'type': 'png_size_select',
                            'index': "size_" + str(size),
                        }))
        png_page_sizes.append(html.P(
                size,
                className="text-muted px-4 mb-1",))

    components['export_radio'] = html.Div(
        [
            dbc.Col([
                dbc.Row(
                    dbc.Checklist(
                    id="export_radio",
                    options=[{'label': 'Offline HTML', 'value': 'HTML'}],
                    switch=True
                )),
                dbc.Row([
                    dbc.Col(dbc.Checklist(
                        id="html_radio",
                        options=[{'label': 'PDF', 'value': 'PDF'}],
                        switch=True
                    )),
                    dbc.Col(dbc.Input(id='pdf_width', type="number", min=1, step=1,
                    placeholder="width")),
                    dbc.Col(dbc.Input(id='pdf_height', type="number", min=1, step=1,
                    placeholder="height")),
                    dbc.Col(dbc.DropdownMenu(
                        id='pdf_size_drop',
                        label="Preset",
                        children=pdf_page_sizes,
                    ))
                ], id="pdf_div"),
                dbc.Row([
                    dbc.Col(dbc.Checklist(
                        id="pdf_radio",
                        options=[{'label': 'PNG', 'value': 'PNG'}],
                        switch=True
                    )),
                    dbc.Col(dbc.Input(id='png_width', type="number", min=1, step=1,
                    placeholder="width")),
                    dbc.Col(dbc.Input(id='png_height', type="number", min=1, step=1,
                    placeholder="height")),
                    dbc.Col(dbc.DropdownMenu(
                        id='png_size_drop',
                        label="Preset",
                        children=png_page_sizes,
                    ))
                ], id="png_div"),
                dbc.Row(
                )
            ]),

        ], className='p-3', style = {'textAlign': 'left'}
    )

    components['export_input'] = html.Div(
        [
            dcc.Store(id='exporter'),
            dbc.Row([
                #dbc.Col(html.Div(dbc.Spinner(id='export_label'), style = {'align-self': 'center'}),)
            ]),
        ], className='p-0', style={'textAlign': 'center'}
    )

    components['height_input'] = html.Div(
        [
                dbc.Row(html.P("Plot height: ")),
                dbc.Row([
                    dbc.Col(dbc.Input(type="number", min=1, step=1, placeholder="Plot height", value=20, id='height_set'), width=9),
                    dbc.Col(html.P(" %"), width=3)
                ], justify="center")
        ], className='py-1 px-3', style={'textAlign': 'left'}
    )

    components['font_input'] = html.Div(
        [
            dbc.Col([
                dbc.Row(html.P("Font size: ")),
                dbc.Row([
                    dbc.Col(dbc.Input(type="number", min=1, step=1, placeholder="Font size", value=12, id='font_set'), width=9),
                    dbc.Col(html.P(" pt"), width=3)
                ], justify="center")
            ]),
        ], className='py-1 px-3', style={'textAlign': 'left'}
    )

    components['submit_input'] = html.Div(
        [
            dbc.Button(
                "SUBMIT",
                id="submit_val",
                n_clicks=0,
                color='success'
            )
        ], className='p-3',
    )

    components['offcanvas'] = html.Div(
        [
            dbc.Button(
                "Select plots & traces",
                id="open-offcanvas-button",
                n_clicks=0,
            ),
            dcc.Store(id='plot_set_store', data=plot_set),
            dcc.Store(id='plots_store', data = func.getPlots(plot_set)),
            dcc.Store(id='traces_store', data = config.config['plot_set_plots'][plot_set]),
            dbc.Offcanvas([
                    dbc.Spinner(id='plot_chooser-content', color="primary"),
                    dbc.Spinner(id='trace_chooser-content', color="primary"),
                ],
                id="offcanvas-scrollable",
                scrollable=True,
                is_open=False,
                placement='start',
                style = {'width': '600px'}
            ),
        ], className='p-3'
    )
    return components

def serve_layout():
    return dbc.Container([ # Fluid Container
        html.Div([ #Padding & alignment div
            #HEADER
            dbc.Row([
                dbc.Col([
                    config.components['header_card']
                ])
            ]),

            #DATETIME
            dbc.Row([
                dbc.Col([
                    config.components['datetime_selector']
                ])
            ]),

            dbc.Row([ #Settings Row
                dbc.Col([
                    dbc.Row(
                        html.Div(
                            dbc.Card([
                                dbc.CardHeader("Select plots", className="card-title",),
                                dbc.Row([dbc.Col(config.components['plot_set_dropdown']),
                                dbc.Col(config.components['offcanvas'])]),
                            ])
                        )
                    ),
                    dbc.Row([
                        html.Div(
                            dbc.Card([
                                dbc.CardHeader("Display Settings", className="card-title",),
                                dbc.Row([
                                    dbc.Col(config.components['height_input']),
                                    dbc.Col(config.components['font_input'])
                                ]),
                            ])
                        )
                    ])
                ]),
                dbc.Col([
                    dbc.Row([
                        html.Div(
                            dbc.Card([
                                dbc.CardHeader("Resampling Resolution", className="card-title",),
                                config.components['resampler_radio'],
                                config.components['resampler_input']
                            ])
                        )
                    ]),
                    dbc.Row([
                        html.Div(
                            dbc.Card([
                                dbc.CardHeader("Submit", className="card-title",),
                                config.components['submit_input'],
                            ])
                        )
                    ]),
                ]),
                dbc.Col([
                    
                    dbc.Row([
                        html.Div(
                        dbc.Card([
                            dbc.CardHeader("Export Settings", className="card-title",),
                            config.components['export_radio'],
                            config.components['export_input']
                        ])
                    )
                    ]),
                ])
            ], align='start', justify='center'),
        ], className="p-5 mb-0", style={'textAlign': 'center'}),
        dbc.Row([
                    dbc.Col(html.Div([dcc.Loading(id='chart-content'),])),
                ], className = "g-0", style={'textAlign': 'center'}),
    ], fluid=True)
