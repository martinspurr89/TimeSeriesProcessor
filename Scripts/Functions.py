import os
import shutil
import time
import pandas as pd
import numpy as np
import re
import webbrowser
import dash_bootstrap_components as dbc
from dash import html
from pytz import timezone
import math
import humanize
from datetime import datetime
from copy import deepcopy
import plotly
from PIL import Image
import warnings
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter

import Scripts.config as config

def update_text():
    diff = datetime.now(timezone('UTC')) - config.config['date_end']
    last_date = humanize.naturaldelta(diff)
    return html.Div(html.P(config.config['project'] + ' | Data last retrieved ' + last_date + ' ago'))


def unixTimeMillis(dt):
    ''' Convert datetime to unix timestamp '''
    return int(time.mktime(dt.timetuple()))

def unixToDatetime(unix):
    ''' Convert unix timestamp to datetime. '''
    return pd.to_datetime(unix,unit='s',utc=True)

def getMarks(start, end, periods):
    ''' Returns the marks for labeling. 
        Every Nth value will be used.
    '''
    daterange = pd.date_range(start=start,end=end,periods=periods)
    result = {}
    for i, date in enumerate(daterange):
        # Append value to dict
        result[unixTimeMillis(date)] = str(date.strftime('%d/%m/%y'))
    return result

def rangeString(start, end):
    return '{} ⬌ {}'.format(unixToDatetime(start).strftime("%d/%m/%Y %H:%M"),
                                  unixToDatetime(end).strftime("%d/%m/%Y %H:%M"))

def resampleAlert(value):
    if value == None:
        return dbc.Alert("Set value for resampling in minutes", color="danger", class_name = "mb-0 py-0")
    if value > 0:
        return dbc.Alert('Resample every ' + str(value) + ' mins', color="secondary", class_name = "mb-0 py-0")
    elif value == 0:
        return dbc.Alert('Data not resampled', color="warning", class_name = "mb-0 py-0")
    else:
        return ""

def calcResampler(resolution, set, hi_res):
    if resolution == 'HIGH':
        value = hi_res
    elif resolution == 'LOW':
        if hi_res == 0:
            value = 4
        else:
            value = hi_res*4
    elif resolution == 'NONE':
        value = 0
    elif resolution == 'SET':
        value = set
    return(value)

def calcHiRes(dates_selected):
        data_set = config.data['all_data'].query(
            'DateTime > "' + str(unixToDatetime(dates_selected[0])) + '"').query(
            'DateTime < "' + str(unixToDatetime(dates_selected[1])) + '"')
        length = len(data_set)
        return round(length/2800) #mins

def addDatatoPlot(plot, traces_info, chart_data, dates_selected, plots, height):
    plot_name = config.config['dcc_plot_codes'][plot.id]
    if any(config.config['plot_pars'].query("plot == '" + plot_name + "'")['bar']):
        plot_traces = traces_info[plot.id]
        bars = list(config.config['plot_pars'].query(
            "plot == '" + plot_name + "'").query(
            "parameter_lab in @plot_traces")['bar_order'].unique())
        bar_orders = {}
        for b in range(0, len(bars), 1):
            bar_orders[bars[b]] = len(bars) - 1 - b
    for trace in plot.figure.data:
        if trace.name in traces_info[plot.id]:
            par = config.config['plot_pars'].query(
                "plot == '" + plot_name + "'").query(
                "parameter_lab == '" + trace.name + "'")['parameter'][0]
            par_info = config.config['plot_pars'].query('parameter == "' + par + '"')
            x_data = deepcopy(chart_data.DateTime)
            y_data = deepcopy(chart_data[par])
            error_bars = False
            y_error = None
            if par + "_err" in config.data['all_data'].columns[1:]:
                error_bars = True
                y_error = deepcopy(chart_data[par + "_err"])

            if trace.mode == "markers" or trace.line.shape == "hv" or par_info['point'][0] or par_info['bar'][0]:
                if error_bars:
                    y_error.drop(y_error[np.isnan(y_data)].index, inplace=True)
                x_data.drop(x_data[np.isnan(y_data)].index, inplace=True)
                y_data.drop(y_data[np.isnan(y_data)].index, inplace=True)
            trace.x = x_data
            trace.y = y_data
            if trace.mode == "markers":
                trace.update(error_y = dict(type = 'data', visible = True, array = y_error, color = par_info['colour'][0]))
            if trace.mode == "none" and par_info['ribbon'][0]:
                trace.y = y_data - y_error
            if trace.line.width == 0 and par_info['ribbon'][0]:
                trace.y = y_data + y_error
            if trace.line.shape == "hv" and par_info['bar'][0]:
                trace.y = bar_orders[par_info['bar_order'][0]] + y_data.round()/2
            if trace.mode == "none" and par_info['bar'][0]:
                trace.y = bar_orders[par_info['bar_order'][0]] - y_data.round()/2
    plot.figure.update_xaxes(range=[unixToDatetime(dates_selected[0]), unixToDatetime(dates_selected[1])], fixedrange=False)
    plot.style['height'] = str(height) + 'vh'
    if plot.id == list(plots.keys())[len(plots)-1]:
        plot.style['height'] = str(height + 5) + 'vh'
    return plot

def getPlots(plot_set):
    plots = {}
    for plot_name in config.config['plot_set_plots'][plot_set].keys():
        for plot in config.figs['dcc_plot_figs']:
            if plot_name == plot.id:  
                plots[plot.id] = re.sub('<.*?>', ' ', plot.figure.layout.yaxis.title.text)
    return plots

def modifyPlot(plot_fig, plot, plots, font):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    plot_fig.figure.update_layout(
        margin=dict(l=125, r=250, b=15, t=15, pad=10),
        template="simple_white",
        paper_bgcolor='rgba(0,0,0,0)',
        legend_tracegroupgap=0,
        font=dict(
            family = "Arial",
            size = font,
            color = "black"
        ))
    plot_fig.figure.update_yaxes(title_text=plot_info['ylab'][0], mirror=True)
    plot_fig.figure.update_xaxes(showgrid=True, showticklabels=False, ticks="",
        showline=True, mirror=True,
        fixedrange=True) #prevent x zoom
    if plot_fig.id == list(plots.keys())[len(plots)-1]:
        plot_fig.figure.update_xaxes(showticklabels=True, ticks="outside", automargin=False)
        plot_fig.figure.update_layout(margin=dict(l=125, r=250, b=60, t=15, pad=10))
    return(plot_fig)

def getYMin(plot, chart_data, traces_info):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    if pd.isna(plot_info['ymin'][0]):
        par_codes = config.config['plot_pars'].query("plot == '" + plot + "'").query("parameter_lab in @traces_info")['parameter'].unique()
        min_data = []
        for par in par_codes:
            if par + "_err" in chart_data.columns:
                min_data.append(min(chart_data[par] - chart_data[par + "_err"]))
            else:
                min_data.append(min(chart_data[par]))
        ymin = min(min_data)
        if any(config.config['plot_pars'].query('plot == "' + plot + '"')['point']):
            if ymin > 0:
                ymin = 0.95 * ymin
            else:
                ymin = 1.05 * ymin
        elif any(config.config['plot_pars'].query('plot == "' + plot + '"')['bar']) > 0:
            ymin = - 1
    else:
        ymin = plot_info['ymin'][0]
    return(ymin)

def getYMax(plot, chart_data, traces_info):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    if pd.isna(plot_info['ymax'][0]):
        par_codes = config.config['plot_pars'].query("plot == '" + plot + "'").query("parameter_lab in @traces_info")['parameter'].unique()
        max_data = []
        for par in par_codes:
            if par + "_err" in chart_data.columns:
                max_data.append(max(chart_data[par] + chart_data[par + "_err"]))
            else:
                max_data.append(max(chart_data[par]))
        ymax = max(max_data)
        if any(config.config['plot_pars'].query('plot == "' + plot + '"')['point']):
            if ymax > 0:
                ymax = 1.05 * ymax
            else:
                ymax = 0.95 * ymax
        elif any(config.config['plot_pars'].query('plot == "' + plot + '"')['bar']) > 0:
            bars = list(config.config['plot_pars'].query(
                "plot == '" + plot + "'").query(
                "parameter_lab in @traces_info")['bar_order'].unique())
            ymax = len(bars)
    else:
        ymax = plot_info['ymax'][0]
    return(ymax)

def setAxisRange(plot_fig, plot, chart_data, traces_info):
    plot_info = config.config['info']['plots'].query("index == '" + plot + "'")
    ymin = getYMin(plot, chart_data, traces_info)
    ymax = getYMax(plot, chart_data, traces_info)
    if plot_info['log'][0] == True:
        plot_fig.figure.update_layout(yaxis_type="log")
        plot_fig.figure.update_yaxes(range=[math.log(ymin, 10), math.log(ymax, 10)])
    else:
        plot_fig.figure.update_yaxes(range=[ymin, ymax])

    if any(config.config['plot_pars'].query('plot == "' + plot + '"')['bar'].values == True):
        bar_dict = config.config['plot_pars'].query('plot == "' + plot + '"').set_index('bar_order')['parameter_lab'].to_dict()
        bars = list(config.config['plot_pars'].query(
            "plot == '" + plot + "'").query(
            "parameter_lab in @traces_info")['bar_order'].unique())
        bar_orders = {}
        for b in range(0, len(bars), 1):
            bar_orders[bars[b]] = len(bars) - 1 - b
        bar_dict2 = {}
        for key in bar_orders:
            bar_dict2[bar_orders[key]] = bar_dict[key]
        
        #tickvals_list = list(range(int(ymin)+1, int(ymax), 1))
        #tickvals_list = list(config.config['plot_pars'].query('parameter_lab in @traces_info').query('plot == "' + plot + '"')['bar_order'].unique())
        tickvals_list = list(bar_dict2.keys())
        tickvals_list.sort()
        ticktext_list = [bar_dict2[k] for k in tickvals_list if k in bar_dict2]
        plot_fig.figure.update_layout(
                yaxis = dict(
                    tickmode = 'array',
                    tickvals = tickvals_list,
                    ticktext = ticktext_list
                )
            )
        plot_fig.figure.update_yaxes(ticklabelposition="inside", ticks="inside", automargin=False)

    return(plot_fig)

def create_chart_data(dates_selected, resample, traces):
    chart_data = config.data['all_data'].query(
            'DateTime > "' + str(unixToDatetime(dates_selected[0])) + '"').query(
            'DateTime < "' + str(unixToDatetime(dates_selected[1])) + '"').set_index('DateTime')

    trace_codes = []
    for plot_id in traces:
        plot_name = config.config['dcc_plot_codes'][plot_id]
        trace_list = traces[plot_id]
        par_codes = list(config.config['plot_pars'].query('plot == "' + plot_name + '"').query('parameter_lab in @trace_list')['parameter'].unique())
        err_codes = [p + "_err" for p in par_codes]
        codes = chart_data.columns[chart_data.columns.isin(par_codes + err_codes)]
        trace_codes.extend(codes)
    chart_data = chart_data[trace_codes]
    if resample > 0:
        chart_data = chart_data.groupby(pd.Grouper(freq=str(resample) +'Min')).aggregate(np.mean)
        chart_data = chart_data.dropna(thresh=1)
    chart_data = chart_data.reset_index()
    return chart_data

def create_chart_content(chart_data, dates_selected, plots, traces, height, font):
    content = []
    for plot_orig in config.figs['dcc_plot_figs']:
        if plot_orig.id in plots:
            plot_name = config.config['dcc_plot_codes'][plot_orig.id]
            plot = addDatatoPlot(deepcopy(plot_orig), traces, chart_data, dates_selected, plots, height)
            plot = modifyPlot(plot, plot_name, plots, font)
            plot = setAxisRange(plot, plot_name, chart_data, traces[plot_orig.id])
            content.append(html.Div(id='loading', children=plot))
            progress_pc = (list(plots.keys()).index(plot_orig.id) + 2) / (len(plots.keys()) + 1)
            config.fsc.set("submit_progress", str(progress_pc))  # update progress
    return content

def open_browser(port):
    webbrowser.open_new("http://localhost:{}".format(port))

def createOfflineCharts(content, plots, height, export_progress, export_denom):
    div_chart_fig = {}
    p = 0
    for plot in content:
        div_chart_fig[plot.children.id] = plotly.offline.plot(plot.children.figure, include_plotlyjs=False, output_type='div')
        div_chart_fig[plot.children.id] = div_chart_fig[plot.children.id].replace('style="height:100%; width:100%;"',
        'style="height:' + str(height) + '%; width:98%;"')
        if p == len(plots)-1: #if the last chart
            div_chart_fig[plot.children.id] = div_chart_fig[plot.children.id].replace('style="height:' + str(height) + '%;"', 'style="height:' + str(height * 1.25) + '%;"')
        p += 1
        export_progress_new = export_progress + (p / (len(content) + 1))
        config.fsc_e.set("export_progress", str(export_progress_new / export_denom))  # update progress
    return(div_chart_fig)

def exportHTML(offline_chart, dates_selected, resample, export_name):
    #Build start and end strings
    html_string_start = '''
    <html>
        <head>
            <style>body{ margin:0 100; background:white; font-family: Arial, Helvetica, sans-serif}</style>
        </head>
        <body>
            <h1>''' + config.config['project'] + ''' interactive data</h1>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            '''

    html_string_end = '''
        </body>
    </html>'''

    #Create html header
    html_string = html_string_start

    chart_start_date = unixToDatetime(dates_selected[0])
    chart_end_date = unixToDatetime(dates_selected[1])
    html_string = html_string + '''<p>''' + humanize.naturaldate(chart_start_date) + ''' to ''' + humanize.naturaldate(chart_end_date)

    if resample != 0:
        html_string = html_string + ''' | Data resampled over ''' + str(resample) + ''' minutes'''
    
    html_string = html_string + '''</p>'''

    #Add divs to html string
    for plot in offline_chart:
        html_string = html_string + offline_chart[plot]

    #write finished html
    html_string + html_string_end
    html_filename = export_name + ".html"
    hreport = open(config.io_dir / "Output" / html_filename,'w', encoding='utf-8')
    hreport.write(html_string)
    hreport.close()

def deleteFolderContents(folder):
    if not os.path.exists(folder):
        folder.mkdir(parents=True, exist_ok=True)
    else:
        for filename in os.listdir(folder):
            file_path = folder / filename
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

def createTempChartDir(export_name, otype):
    temp_path = config.io_dir / "Temp" / (otype + "s")
    deleteFolderContents(temp_path)
    odir = temp_path /  export_name
    odir.mkdir(parents=True, exist_ok=True)
    return(odir)

def exportImage(export_progress, export_denom, export_name, content, plots, otype, owidth, oheight, odpi = 300):
    image_dir = createTempChartDir(export_name, otype.upper())
    divisor = len(plots)-1 + 1.25
    scaler = {'png': odpi/96,
              'pdf': 1}
    #Export individual images
    p = 0
    for plot in content:
        height = oheight/divisor
        if p == len(plots)-1: #if the last chart
            height = height * 1.25
        
        chart_to_export = deepcopy(plot.children.figure)
        chart_to_export.update_layout(width=owidth,
                                            height=height)
        chart_to_export.write_image(str(image_dir / (str(p).zfill(2) + "_" + plot.children.id + "." + otype)),
                                            scale=scaler)
        p = p + 1

    #Combine individual images and output to file
    if otype == 'png':
        combinePNG(image_dir, export_name, export_progress, export_denom)
    elif otype == 'pdf':
        combinePDF(image_dir, export_name, export_progress, export_denom)
    
    #Delete temp images
    try:
        shutil.rmtree(image_dir)
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))

def combinePNG(png_dir, export_name, export_progress, export_denom):
    images = [Image.open(png_dir / x) for x in os.listdir(png_dir)]
    widths, heights = zip(*(i.size for i in images))

    max_width = max(widths)
    total_height = sum(heights)

    new_im = Image.new('RGBA', (max_width, total_height))

    y_offset = 0
    i = 0
    for im in images:
        new_im.paste(im, (0,y_offset))
        y_offset += im.size[1]
        i += 1
        export_progress_new = export_progress + (i) / (len(images) + 1)
        config.fsc_e.set("export_progress", str(export_progress_new / export_denom))  # update progress

    png_filename = export_name + ".png"
    new_im.save(config.io_dir / "Output" /  png_filename)
    export_progress += 1
    config.fsc_e.set("export_progress", str(export_progress / export_denom))  # update progress

def combinePDF(pdf_dir, export_name, export_progress, export_denom):
    #Combine pdfs
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', r'.*Multiple definitions in dictionary.*')
        merger = PdfFileMerger(strict=False)
        for filename in sorted(os.listdir(pdf_dir)):
            merger.append(PdfFileReader(str(pdf_dir / filename), strict=False))
        with open(str(pdf_dir / "all_pages.pdf"), 'wb') as fh:
            merger.write(fh)

        #Create combined pdf on one page
        with open(str(pdf_dir / 'all_pages.pdf'), 'rb') as input_file:
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
                export_progress_new = export_progress + (num_pages - p) / (num_pages + 1)
                config.fsc_e.set("export_progress", str(export_progress_new / export_denom))  # update progress

            # write finished pdf
            output_file = config.io_dir / "Output" / (export_name + ".pdf")
            with open(output_file, 'wb') as out_file:
                    write_pdf = PdfFileWriter()
                    write_pdf.addPage(output_pdf)
                    write_pdf.write(out_file)
            export_progress += 1
            config.fsc_e.set("export_progress", str(export_progress / export_denom))  # update progress