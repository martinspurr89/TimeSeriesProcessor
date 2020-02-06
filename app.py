# !jupyter serverextension list
from jupyter_plotly_dash import JupyterDash
###

import pandas as pd
# from tqdm import trange, tqdm
from tqdm.notebook import trange, tqdm

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import datetime
from datetime import datetime, timedelta
from pytz import timezone

import os
import re

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import time
import numpy as np


# Date Functions
def set_date(date_str, old_tz, dt_format = "%d/%m/%Y %H:%M:%S"):
    if date_str == 'NaT':
        return pd.NaT
    else:
        datetime_set_naive = datetime.strptime(date_str, dt_format)
        datetime_set_old = timezone(old_tz).localize(datetime_set_naive)
        datetime_set_utc = datetime_set_old.astimezone(timezone('UTC'))
        return datetime_set_utc

def date_parser(date_, time_, dt_format = "%d/%m/%Y %H:%M:%S"):
    return set_date(date_ + " " + time_, 'UTC', dt_format)


# Experiment start date
date_start = set_date("2019-06-04 13:03:17", "UTC", "%Y-%m-%d %H:%M:%S")
date_now = datetime.now(timezone('UTC'))

# Date Functions continued
def date_range(window=-1, start=date_start, end=date_now):
    if pd.isna(start):
        start = date_start
    if pd.isna(end):
        end = date_now
    if window != -1:
        if not pd.isna(window):
            start = end - timedelta(days=window)
    return start, end

def test():
    print("Test")