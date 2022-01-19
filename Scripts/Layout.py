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
        datetime_items.extend([
            dbc.DropdownMenuItem(str(chart)  + ": " + charts['chart_label'][chart], id={
                'type': 'chart_select',
                'index': "chart_" + str(chart),
            }),
            html.P(
                charts['chart_range_start'][chart].strftime("%d/%m/%Y %H:%M") + " ↔ " +
                charts['chart_range_end'][chart].strftime("%d/%m/%Y %H:%M"),
            className="text-muted px-4 mb-1",)
        ])

    datetime_dropdown = dbc.DropdownMenu(
        id='datetime_drop',
        label="Chart Range",
        children=datetime_items,
        class_name = 'py-1 px-4',
        style={'textAlign': 'left'},
    )

    datetime_pick = html.Div(children=[
        dash_datetimepicker.DashDatetimepicker(id="datetime-picker", 
        startDate = start, endDate = end, utc=True, locale="en-gb"),
    ], style = {'align-self': 'center'})

    datetime_slider = dbc.Spinner(id='slider-content', color="info")

    components['datetime_selector'] = dbc.Card([
        dbc.CardHeader("DateTime Range", className="card-title",),
        html.Div([
            dbc.Row([
                dbc.Col([datetime_dropdown]),
                dbc.Col([datetime_pick]),
                dbc.Col([])
            ]),
            dcc.Store(id='hi_res'),
            dbc.Row([datetime_slider]),
        ], className='p-1')
    ])

    plot_set_dropdown = dbc.Select(
        id='plot_set_drop',
        options=[
            {"label": 'Plot Set ' + str(plot_set), "value": plot_set} for plot_set in set(config.config['plot_sets'])] + 
            [{'label': 'Plot Set Custom', 'value': -1}],
        value=str(plot_set),
        className='p-1',
        style={'textAlign': 'left'}
    )

    offcanvas_button = dbc.Button(
        "Select plots & traces",
        id="open-offcanvas-button",
        n_clicks=0,
    )

    offcanvas = dbc.Offcanvas([
        dbc.Spinner(id='plot_chooser-content', color="primary"),
        dbc.Spinner(id='trace_chooser-content', color="primary"),
        ],
        id="offcanvas-scrollable",
        scrollable=True,
        is_open=False,
        placement='start',
        style = {'width': '600px'}
    )

    components['plots_selector'] = dbc.Card([
        dbc.CardHeader("Select plots", className="card-title",),
        html.Div([
            dbc.Row([
                dcc.Store(id='plot_set_store', data=plot_set),
                dcc.Store(id='plots_store', data = func.getPlots(plot_set)),
                dcc.Store(id='traces_store', data = config.config['plot_set_plots'][plot_set]),
                dbc.Col([plot_set_dropdown]),
                dbc.Col([offcanvas_button, offcanvas])
            ]),
        ], className='p-3')
    ])

    height_input = html.Div([
        dbc.Label("Plot height:", className = 'mb-0', style={'textAlign': 'left'}),
        dbc.InputGroup([
            dbc.Input(type="number", min=1, step=1, placeholder="Plot height", value=20, id='height_set'),
            dbc.InputGroupText("%")
        ])
    ])

    font_input = html.Div([
            dbc.Label("Font size:", className = 'mb-0', style={'textAlign': 'left'}),
            dbc.InputGroup([
                dbc.Input(type="number", min=1, step=1, placeholder="Font size", value=12, id='font_set'),
                dbc.InputGroupText("pt")
            ])
    ])
    
    components['display_selector'] = dbc.Card([
        dbc.CardHeader("Display Settings", class_name="card-title",),
        html.Div([
            dbc.Row([
                dbc.Col(height_input),
                dbc.Col(font_input)
            ]),
        ], className='p-3')
    ])

    resampler_radio = dbc.RadioItems(
        id="resample_radio",
        options=[
            {'label': 'Low', 'value': 'LOW'},
            {'label': 'High', 'value': 'HIGH'},
            {'label': 'None', 'value': 'NONE'},
            {'label': 'Set', 'value': 'SET'},
        ],
        value='HIGH',
        inline=True,
        class_name = 'pb-3'
    )

    resample_set_input = html.Div(dbc.Input(id='resample_set', type="number", min=1, step=1,
                placeholder="mins"), id="resample_div")

    resampler_label = html.Div(dbc.Spinner(id='resample_label'), style={'textAlign': 'center'})

    
    components['resample_selector'] = dbc.Card([
        dbc.CardHeader("Resampling Resolution", class_name="card-title",),
        html.Div([
            dcc.Store(id='resampler'),
            dbc.Row([
                dbc.Col(resampler_radio, style = {'align-self': 'center'}),
                dbc.Col(resample_set_input, style = {'align-self': 'center'}, width=3)
            ]),
            dbc.Row([resampler_label])
        ], className = 'p-3')
    ])

    submit_input = html.Div([
        dbc.Button(
            "SUBMIT",
            id="submit_val",
            n_clicks=0,
            color='success'
        )
    ], className='p-3')

    components['submit_card'] = dbc.Card([
        dbc.CardHeader("Load Charts", class_name="card-title",),
        submit_input,
    ])

    pdf_page_sizes = []
    for size in config.config['pdf_size_dict']:
        pdf_page_sizes.extend([
            dbc.DropdownMenuItem(config.config['pdf_size_dict'][size]['size_name'], id={
                'type': 'pdf_size_select',
                'index': "size_" + str(size),
            }),
            html.P(str(config.config['pdf_size_dict'][size]['width']) + 
            " × " + 
            str(config.config['pdf_size_dict'][size]['height']), 
            className="text-muted px-4 mb-1")
        ])
    def_pdf_width = config.config['pdf_size_dict'][min(config.config['pdf_size_dict'].keys())]['width']
    def_pdf_height = config.config['pdf_size_dict'][min(config.config['pdf_size_dict'].keys())]['height']

    png_page_sizes = []
    for size in config.config['png_size_dict']:
        png_page_sizes.extend([
            dbc.DropdownMenuItem(config.config['png_size_dict'][size]['size_name'], id={
                'type': 'png_size_select',
                'index': "size_" + str(size),
            }),
            html.P(str(config.config['png_size_dict'][size]['width']) + 
            " × " + 
            str(config.config['png_size_dict'][size]['height']) + 
            " | " + 
            str(round(config.config['png_size_dict'][size]['png_dpi'])) + 
            " dpi", 
            className="text-muted px-4 mb-1")
        ])
    def_png_width = config.config['png_size_dict'][min(config.config['png_size_dict'].keys())]['width']
    def_png_height = config.config['png_size_dict'][min(config.config['png_size_dict'].keys())]['height']
    def_png_dpi = config.config['png_size_dict'][min(config.config['png_size_dict'].keys())]['png_dpi']

    html_check = dbc.InputGroup([
        dbc.InputGroupText(dbc.Checklist(
                id="html_on",
                options=[{'label': 'HTML', 'value': 'HTML'}],
                switch=True,
                input_checked_style={
                    "backgroundColor": "#ffc107",
                    "borderColor": "#ffc107",
                },
            ), style = {'max-width': '20%', 'width': '20%'}),
    ])

    pdf_check = dbc.InputGroup([
        dbc.InputGroupText(dbc.Checklist(
                id="pdf_on",
                options=[{'label': 'PDF', 'value': 'PDF'}],
                switch=True,
                input_checked_style={
                    "backgroundColor": "#ffc107",
                    "borderColor": "#ffc107",
                },
            ), style = {'max-width': '20%', 'width': '20%'}),
        dbc.DropdownMenu(
            id='pdf_size_drop',
            label="Preset",
            color='secondary',
            children=pdf_page_sizes,
            disabled=True,
        ),
        dbc.InputGroupText("w"),
        dbc.Input(id='pdf_width', type="number", min=1, step=1, placeholder="width", style={'max-width':'15%'}, value = def_pdf_width, disabled=True),
        dbc.InputGroupText("h"),
        dbc.Input(id='pdf_height', type="number", min=1, step=1, placeholder="height", style={'max-width':'15%'}, value = def_pdf_height, disabled=True),
    ], id="pdf_grp")

    png_check = dbc.InputGroup([
        dbc.InputGroupText(dbc.Checklist(
                id="png_on",
                options=[{'label': 'PNG', 'value': 'PNG'}],
                switch=True,
                input_checked_style={
                    "backgroundColor": "#ffc107",
                    "borderColor": "#ffc107",
                },
            ), style = {'max-width': '20%', 'width': '20%'}),
        dbc.DropdownMenu(
            id='png_size_drop',
            label="Preset",
            color='secondary',
            children=png_page_sizes,
            disabled=True,
        ),
        dbc.InputGroupText("w"),
        dbc.Input(id='png_width', type="number", min=1, step=1, placeholder="width", style={'max-width':'15%'}, value = def_png_width, disabled=True),
        dbc.InputGroupText("h"),
        dbc.Input(id='png_height', type="number", min=1, step=1, placeholder="height", style={'max-width':'15%'}, value = def_png_height, disabled=True),
        dbc.InputGroupText("dpi"),
        dbc.Input(id='png_dpi', type="number", min=1, step=1, placeholder="dpi", style={'max-width':'13%'}, value = def_png_dpi, disabled=True),
    ], id="png_grp")

    export_div = [
        dbc.Col(
            html.Div([
                dbc.Button(
                    "EXPORT",
                    id="export_submit",
                    n_clicks=0,
                    color="warning",
                    disabled = True
                )
            ], className='pt-3'),
        style={'max-width': '20%'})
    ]
        
    components['export_card'] = dbc.Card([
        dbc.CardHeader("Export Settings", class_name="card-title",),
        dcc.Store(id='exporter'),
        html.Div([
            dbc.Col([
                dbc.Row(html_check, class_name = "g-0"),
                dbc.Row(pdf_check, class_name = "g-0"),
                dbc.Row(png_check, class_name = "g-0"),
                dbc.Row(export_div, class_name = "g-0")
            ]),
        ], className = 'p-3')
    ])

    return components

def serve_layout():
    return dbc.Container([ # Fluid Container
        html.Div([ #Padding & alignment div
            #HEADER
            dbc.Row([
                dbc.Col([
                    html.Div(config.components['header_card'])
                ])
            ]),
            #DATETIME
            dbc.Row([
                dbc.Col([
                    html.Div(config.components['datetime_selector'])
                ])
            ]),
            #SETTINGS ROW
            dbc.Row([
                dbc.Col([
                    #PLOTS SELECT
                    dbc.Row([
                        html.Div(config.components['plots_selector'])
                    ]),
                    #RESAMPLING
                    dbc.Row([
                        html.Div(config.components['resample_selector'])
                    ])
                ], width = 4),
                dbc.Col([
                    #DISPLAY
                    dbc.Row([
                        html.Div(config.components['display_selector'])
                    ]),
                    #SUBMIT
                    dbc.Row([
                        html.Div(config.components['submit_card'])
                    ]),
                ], width=3),
                dbc.Col([
                    #EXPORT
                    dbc.Row([
                        html.Div(config.components['export_card'])
                    ]),
                ])
            ]),
        ], className="p-5 mb-0", style={'textAlign': 'center'}),
        #CHART
        dbc.Row([
            dbc.Col(
                html.Div(dcc.Loading(id='chart-content'))
            ),
        ], class_name = 'g-0', style={'textAlign': 'center'}),
    ], fluid=True)
