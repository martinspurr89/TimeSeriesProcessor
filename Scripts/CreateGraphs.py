import pandas as pd
from pandas.io.common import EmptyDataError
from tqdm.autonotebook import trange, tqdm

import chart_studio.plotly as py
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.offline.offline
import datetime
from datetime import datetime, timedelta, timezone
from pytz import timezone
import humanize

import os
import shutil
import re

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import time
import numpy as np
import math
import seaborn as sns

import requests
import io
import warnings
import copy

from collections import OrderedDict
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from PIL import Image
from pdf2image import convert_from_path, convert_from_bytes

def import_df(filename, index = False):
    try:
        if index == False:
            df = pd.read_csv(filename)
        else:
            df = pd.read_csv(filename, index_col=0)
    except EmptyDataError:
        df = pd.DataFrame()
    return df

def set_date(date_str, old_tz, dt_format = "%d/%m/%Y %H:%M:%S"):
    date_formats = ["%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]
    if date_str == 'NaT':
        return pd.NaT
    else:
        date_formats.append(dt_format)
        for format in date_formats:
            try:
                datetime_set_naive = datetime.strptime(date_str, format)
                break
            except ValueError:
                continue
        try:
            datetime_set_old = timezone(old_tz).localize(datetime_set_naive)
            datetime_set_utc = datetime_set_old.astimezone(timezone('UTC'))
        except UnboundLocalError:
            print("Set dt_format in function call or date_formats")
            raise
        return datetime_set_utc

#Get latest data if older than refresh limit in info
def refresh_data():
    try:
        with open("Temp/Data/info/info_setup.csv") as file:
            info = OrderedDict()
            info['setup'] = import_df(file, index = True)
            date_end = set_date(info['setup'].loc['date_end_utc','value'].replace('+00:00',''), "UTC")
            diff = datetime.now(timezone('UTC')) - date_end
        file.closed
        #if temp info file is older than 4 hours get data for the first time
        if diff > timedelta(hours = int(info['setup'].loc['refresh_hours','value'])):
            import GetLatestData

    except IOError: #if temp info file doesn't exist get data for the first time
        import GetLatestData

def import_temp_data(collection, col_type, index_bool, data_folder = "Temp/Data/"):
    if col_type == "odict":
        col = OrderedDict()
        for filename in os.listdir(data_folder + collection):
            file_id = filename.replace(collection + '_', '').replace('.csv', '')
            col[file_id] = import_df(data_folder + collection + "/" + filename, index = index_bool)
    elif col_type == "list":
        col = []
        for filename in os.listdir(data_folder + collection):
            col.append(import_df(data_folder + collection + "/" + filename, index = index_bool))
    else:
        col = ""
    return col

#Create plotly chart figures
def create_chart_fig(chart):
    chart_fig = OrderedDict()
    chart_info = info['plots'].loc[info['plots'].index == chart][info['plots'].loc[info['plots'].index == chart]['plot'].isin(chart_dfs_mlt[chart].Plot.unique().tolist())]
    # For each plot
    for plot in tqdm(chart_info['plot'].to_list(), desc = "Creating plots for chart " + str(chart)):
        
        plot_info = info['plots'].loc[info['plots'].index == chart].query('plot == "' + plot + '"')
        plot_fig = go.Figure()
        
        #Add traces
        for par_id in range(0, len(chart_dfs_mlt[chart].query('Plot == "' + plot + '"').Parameter.unique())):
            par = chart_dfs_mlt[chart].query('Plot == "' + plot + '"').Parameter.unique()[par_id]
            par_info = plot_pars[chart].query('parameter == "' + par + '"')
            if len(par_info) != 0:
                x_data = chart_dfs_mlt[chart][chart_dfs_mlt[chart].Parameter == par].DateTime
                y_data = chart_dfs_mlt[chart][chart_dfs_mlt[chart].Parameter == par].Value
                y_error = chart_dfs_mlt[chart][chart_dfs_mlt[chart].Parameter == par].Error

                trace_base = go.Scatter(x=x_data, y=y_data,
                            name=par_info['parameter_lab'][0], 
                            legendgroup=par_info['parameter_lab'][0])

                if par_info['line'].values == True:
                    legend_show = True #default on
                    if par_info['show_in_legend'].values == False or par_info['point'].values == True or par_info['bar'].values == True:
                        legend_show = False
                    trace = trace_base
                    trace.update(mode = "lines",
                                line=dict(color=par_info['colour'][0], width=2, dash=par_info['dash'][0]),
                                connectgaps=False,
                                showlegend=legend_show)
                    plot_fig.add_trace(trace)

                if par_info['point'].values == True:
                    trace = trace_base
                    trace.update(mode = 'markers',
                                marker = dict(color = par_info['fill'][0], symbol = par_info['shape'][0],
                                            line = dict(color = par_info['colour'][0],width=1)),
                                showlegend = bool(par_info['show_in_legend'][0]),
                                error_y = dict(type = 'data', array = y_error, visible = True))
                    plot_fig.add_trace(trace)

                if par_info['ribbon'].values == True:
                    ribbon_base = go.Scatter(x=x_data,
                                            name=par_info['parameter_lab'][0],
                                            line=dict(color=par_info['colour'][0], dash = 'dot'),
                                            connectgaps=True,
                                            legendgroup=par_info['parameter_lab'][0],
                                            showlegend=False,
                                            hoverinfo='skip')
                    trace1 = ribbon_base
                    trace1.update(y=y_data + y_error, mode='lines', line=dict(width=0))
                    plot_fig.add_trace(trace1)
                    trace2 = ribbon_base
                    trace2.update(y=y_data - y_error, fill='tonexty', mode='none', fillcolor=par_info['fill'][0],
                                line=dict(width=0.5)) #fill to trace1 y
                    plot_fig.add_trace(trace2)

        #Modify plot
        plot_fig.update_layout(
            margin=dict(l=100, r=250, b=15, t=15, pad=10),
            template="simple_white",
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(
                family="Arial",
                size=info['charts']['font_size'][chart],
                color="black"
            ))
        plot_fig.update_yaxes(title_text=plot_info['ylab'][chart], mirror=True)
        plot_fig.update_xaxes(showgrid=True, showticklabels=False, ticks="",
            showline=True, mirror=True,
            range=[min(chart_dfs_mlt[chart].DateTime), max(chart_dfs_mlt[chart].DateTime)],
            )#fixedrange=True) #prevent x zoom
        
        #Special plot mods
        if pd.isna(plot_info['ymin'][chart]):
            ymin = min(chart_dfs_mlt[chart].query('Plot == "' + plot + '"')['Value'] - chart_dfs_mlt[chart].query('Plot == "' + plot + '"')['Error'].fillna(0))
            if any(plot_pars[chart].query('plot == "' + plot + '"')['point']) + any(plot_pars[chart].query('plot == "' + plot + '"')['bar']) > 0:
                if ymin > 0:
                    ymin = 0.95 * ymin
                else:
                    ymin = 1.05 * ymin
        else:
            ymin = plot_info['ymin'][chart]
        if pd.isna(plot_info['ymax'][chart]):
            ymax = max(chart_dfs_mlt[chart].query('Plot == "' + plot + '"')['Value'] + chart_dfs_mlt[chart].query('Plot == "' + plot + '"')['Error'].fillna(0))
            if any(plot_pars[chart].query('plot == "' + plot + '"')['point']) + any(plot_pars[chart].query('plot == "' + plot + '"')['bar']) > 0:
                if ymax > 0:
                    ymax = 1.05 * ymax
                else:
                    ymax = 0.95 * ymax
        else:
            ymax = plot_info['ymax'][chart]
        if plot_info['log'][chart] == True:
            plot_fig.update_layout(yaxis_type="log")
            plot_fig.update_yaxes(range=[math.log(ymin, 10), math.log(ymax, 10)])
        else:
            plot_fig.update_yaxes(range=[ymin, ymax])

        if plot == chart_info['plot'].to_list()[len(chart_info['plot'].to_list())-1]: #Add date to last chart
            plot_fig.update_xaxes(showticklabels=True, ticks="outside")

        chart_fig[plot] = plot_fig
    return(chart_fig)

#Create dash interactive chart figures
def create_dash_graphs(chart):
    dcc_chart_fig = []
    p = 0
    for plot in chart_figs[chart]:
        if p != len(chart_figs[chart])-1: #if not the last chart
            height = '20vh'
        else:
            height = '25vh'
        dcc_chart_fig.append(dcc.Graph(id='graph' + str(p),
                                            figure=chart_figs[chart][plot],
                                            style={'width': '98vw', 'height': ''+ height + ''}))
        p = p + 1
    return(dcc_chart_fig)

#Create offline interactive chart figures
def create_offline_graphs(chart):
    div_chart_fig = OrderedDict()
    p = 0
    for plot in chart_figs[chart]:
        div_chart_fig[plot] = plotly.offline.plot(chart_figs[chart][plot], include_plotlyjs=False, output_type='div')
        div_chart_fig[plot] = div_chart_fig[plot].replace('style="height:100%; width:100%;"',
        'style="height:20%; width:98%;"')
        if p == len(chart_figs[chart])-1: #if the last chart
            div_chart_fig[plot] = div_chart_fig[plot].replace('style="height:20%;"', 'style="height:25%;"')
        p = p + 1
    return(div_chart_fig)

def delete_folder_contents(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def check_folder_exists(folder):
    if not os.path.exists(folder):
        os.mkdir(folder)
        return(False)
    else:
        return(True)

def export_html(chart):
    #Build start and end strings
    html_string_start = '''
    <html>
        <head>
            <style>body{ margin:0 100; background:white; font-family: Arial, Helvetica, sans-serif}</style>
        </head>
        <body>
            <h1>''' + info['setup'].loc['project','value'] + ''' interactive data</h1>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            '''

    html_string_end = '''
        </body>
    </html>'''

    #Create html header
    html_string = html_string_start

    chart_start_date = set_date(info['charts']['chart_range_start'][chart].replace('+00:00',''), "UTC")
    chart_end_date = set_date(info['charts']['chart_range_end'][chart].replace('+00:00',''), "UTC")
    html_string = html_string + '''<p>''' + humanize.naturaldate(chart_start_date) + ''' to ''' + humanize.naturaldate(chart_end_date)

    resample = info['charts']['chart_res'][chart]
    if resample != 0:
        html_string = html_string + ''' | Data resampled over ''' + str(resample) + ''' minutes</p>'''
    else:
        html_string = html_string + '''</p>'''

    #Add divs to html string
    for plot in chart_figs[chart]:
        html_string = html_string + div_chart_figs[chart][plot]

    #write finished html
    html_string + html_string_end
    hreport = open('Output/' + str(chart) + "_" + info['charts'].loc[chart, 'chart'] + ".html",'w')
    hreport.write(html_string)
    hreport.close()

def export_png(chart):
    #Export PNGs
    if check_folder_exists("Temp"):
        if check_folder_exists("Temp/PNGs/"):
            delete_folder_contents("Temp/PNGs")

    png_folder = "Temp/PNGs/" + str(chart) + "_" + info['charts'].loc[chart, 'chart'] + "/"
    os.mkdir(png_folder)

    divisor = len(chart_figs[chart])-1 + info['charts']['last_fig_x'][chart]

    p = 0
    #Export individual pngs
    for plot in chart_figs[chart]:
        height = info['charts']['png_height'][chart]/divisor
        if p == len(chart_figs[chart])-1: #if the last chart
            height = height * info['charts']['last_fig_x'][chart]
        
        chart_to_export = copy.copy(chart_figs[chart][plot])
        chart_to_export.update_layout(width=info['charts']['png_width'][chart],
                                            height=height)
        chart_to_export.write_image(png_folder + str(p).zfill(2) + "_" + plot + ".png",
                                            scale=info['charts']['dpi'][chart]/96)
        p = p + 1

    images = [Image.open(png_folder + x) for x in os.listdir(png_folder)]
    widths, heights = zip(*(i.size for i in images))

    max_width = max(widths)
    total_height = sum(heights)

    new_im = Image.new('RGBA', (max_width, total_height))

    y_offset = 0
    for im in images:
        new_im.paste(im, (0,y_offset))
        y_offset += im.size[1]

    new_im.save("Output/" + str(chart) + "_" + info['charts'].loc[chart, 'chart'] + ".png")

    #Delete temp pngs
    try:
        shutil.rmtree(png_folder)
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))

def export_pdf(chart):
    #Export PDFs and PNGs
    if check_folder_exists("Temp"):
        if check_folder_exists("Temp/PDFs/"):
            delete_folder_contents("Temp/PDFs")

    pdf_folder = "Temp/PDFs/" + str(chart) + "_" + info['charts'].loc[chart, 'chart'] + "/"
    os.mkdir(pdf_folder)

    divisor = len(chart_figs[chart])-1 + info['charts']['last_fig_x'][chart]

    p = 0
    #Export individual pdfs
    for plot in chart_figs[chart]:
        height = info['charts']['pdf_height'][chart]/divisor
        if p == len(chart_figs[chart])-1: #if the last chart
            height = height * info['charts']['last_fig_x'][chart]

        chart_to_export = copy.copy(chart_figs[chart][plot])
        chart_to_export.update_layout(width=info['charts']['pdf_width'][chart],
                                            height=height)

        chart_to_export.write_image(pdf_folder + str(p).zfill(2) + "_" + plot + ".pdf",
                                            scale=1)
        p = p + 1

    #Combine pdfs
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'.*Multiple definitions in dictionary.*')
        merger = PdfFileMerger(strict=False)
        for filename in os.listdir(pdf_folder):
            merger.append(PdfFileReader(pdf_folder + filename, strict=False))
        with open(pdf_folder + "all_pages.pdf", 'wb') as fh:
            merger.write(fh)

        #Create combined pdf on one page
        with open(pdf_folder + 'all_pages.pdf', 'rb') as input_file:
            # load input pdf
            input_pdf = PdfFileReader(input_file, strict=False)
            num_pages = input_pdf.getNumPages()
            output_pdf = input_pdf.getPage(num_pages-1)

            for p in reversed(range(0,num_pages-1)):
                second_pdf = input_pdf.getPage(p)
                # dimensions for offset from loaded page (adding it to the top)
                offset_x = 0 # use for x offset -> output_pdf.mediaBox[2]
                offset_y = output_pdf.mediaBox[3]
                #merge pdf pages
                output_pdf.mergeTranslatedPage(second_pdf, offset_x, offset_y, expand=True)

            # write finished pdf
            output_file = "Output/" + str(chart) + "_" + info['charts'].loc[chart, 'chart'] + ".pdf"
            with open(output_file, 'wb') as out_file:
                    write_pdf = PdfFileWriter()
                    write_pdf.addPage(output_pdf)
                    write_pdf.write(out_file)

    #Delete temp pdfs
    try:
        shutil.rmtree(pdf_folder)
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))

#Refresh data in temp folder if older than refresh limit or first run
refresh_data()

#Import data from temp_files
info = import_temp_data("info", "odict", index_bool=True)
chart_dfs_mlt = import_temp_data("chart_dfs_mlt", "list", index_bool=False)
plot_pars = import_temp_data("plot_pars", "list", index_bool=True)

#Create useful shortcuts
charts = info['charts'].index.to_list()
date_end = set_date(info['setup'].loc['date_end_utc','value'].replace('+00:00',''), "UTC")

#Create chart figures for plotly, dash and offline interactive
chart_figs = []
dcc_chart_figs = []
div_chart_figs = []
pbar = tqdm(charts)
for chart in pbar:
    pbar.set_description("Exporting chart %s" % chart)
    if info['charts'].loc[chart, 'chart_status'] == 'ON':
        chart_figs.append(create_chart_fig(chart))
        div_chart_figs.append(create_offline_graphs(chart))
        export_html(chart)
        export_png(chart)
        export_pdf(chart)
        dcc_chart_figs.append(create_dash_graphs(chart))
    else:
        chart_figs.append("")