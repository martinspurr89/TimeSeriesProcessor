# ## Import packages
import datetime
import io
import math
import os
import shutil
import re
import warnings
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests
from pytz import timezone
from tqdm.autonotebook import tqdm

# ## Setup from Info.xlsx
info = pd.read_excel("Info/Info.xlsx", sheet_name=None, index_col=0)


# ## Functions
# Date Functions
def set_date(date_str, old_tz, dt_format="%d/%m/%Y %H:%M:%S"):
    if date_str == 'NaT':
        return pd.NaT
    else:
        datetime_set_naive = datetime.strptime(date_str, dt_format)
        datetime_set_old = timezone(old_tz).localize(datetime_set_naive)
        datetime_set_utc = datetime_set_old.astimezone(timezone('UTC'))
        return datetime_set_utc


def date_parser(date_, time_, dt_format="%d/%m/%Y %H:%M:%S"):
    return set_date(date_ + " " + time_, 'UTC', dt_format)


def date_parserYMD(date_, time_, dt_format="%Y-%m-%d %H:%M:%S"):
    return set_date(date_ + " " + time_, 'UTC', dt_format)


# Experiment start/end date
date_start = set_date(str(info['setup'].loc['date_start_utc', 'value']), "UTC", "%Y-%m-%d %H:%M:%S")
if pd.isna(info['setup'].loc['date_end_utc', 'value']):
    date_now = datetime.now(timezone('UTC'))
    info['setup'].loc['date_end_utc', 'value'] = date_now
else:
    date_now = set_date(str(info['setup'].loc['date_end_utc', 'value']), "UTC", "%Y-%m-%d %H:%M:%S")


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


# ## Process Information sheets from Info.xlsx
# ### Chartxs:
charts = []
for chart, row in info['charts'].iterrows():
    chart_range = date_range(window=row['chart_range_window'],
                             start=set_date(str(row['chart_range_start']), "UTC", "%Y-%m-%d %H:%M:%S"),
                             end=set_date(str(row['chart_range_end']), "UTC", "%Y-%m-%d %H:%M:%S"))
    info['charts'].loc[chart, 'chart_range_start'] = chart_range[0]
    info['charts'].loc[chart, 'chart_range_end'] = chart_range[1]
    info['charts'].loc[chart, 'chart_range_window'] = chart_range[1] - chart_range[0]
    charts.append(chart)

del chart, chart_range, row

# ### Colours:

info['colours']['rgb'] = list(
    zip((info['colours']['r'] / 255), (info['colours']['g'] / 255), (info['colours']['b'] / 255)))
info['colours']['rgba_str'] = "rgba(" + info['colours']['r'].astype(int).astype(str) + "," + info['colours']['g'].astype(
    int).astype(str) + "," + info['colours']['b'].astype(int).astype(str) + ",1)"


# ## Import Data
# ### Custom Support Data Functions

def get_UO_support_data(dataset_f_info, dataset="UO"):
    def import_UO_log_dates():
        UO_log_dates = pd.read_csv(dataset_f_info['supp_data_filepath'][dataset], sep="\t")
        UO_log_dates['start'] = pd.to_datetime(UO_log_dates['start'], format="%Y-%m-%d")
        UO_log_dates['end'] = pd.to_datetime(UO_log_dates['end'], format="%Y-%m-%d")
        return UO_log_dates

    UO_log_dates = import_UO_log_dates()

    # Check LogDates file
    if max(UO_log_dates['end']) < date_now.date() - timedelta(days=1):
        # print("Retrieving latest Urban Observatory data...")
        # api-endpoint
        URL = "http://uoweb3.ncl.ac.uk/api/v1.1/sensors/data/csv/?"
        # location given here
        poly = '0103000000010000000600000001000020a2baf9bf58094ee3a2764b4001000020f268fbbf90c059b5b5714b4000000020ba37fbbfc4e78445c6704b4001000020b203fbbf9ce8d60e68714b40010000209a59f9bf346a0efd06714b4001000020a2baf9bf58094ee3a2764b40'
        # defining a params dict for the parameters to be sent to the API
        PARAMS = {'polygon_wkb': poly,
                  'starttime': max(UO_log_dates['end']).strftime("%Y%m%d%H%M%S"),  # "%Y%m%d%H%M%S"
                  'endtime': date_now.strftime("%Y%m%d%H%M%S"),  # "%Y%m%d%H%M%S"
                  'data_variable': 'River Level,Temperature,Rainfall'}
        # sending get request and saving the response as response object
        data_content = requests.get(url=URL, params=PARAMS).content
        UO_data = pd.read_csv(io.StringIO(data_content.decode("utf-8")))
        min_date = pd.to_datetime(min(UO_data['Timestamp'])).strftime("%Y-%m-%d")
        max_date = pd.to_datetime(max(UO_data['Timestamp'])).strftime("%Y-%m-%d")

        if pd.to_datetime(max_date) > max(UO_log_dates['end']):
            UO_data.to_csv(dataset_f_info['data_folder_path'][dataset] + "UO_data_" + str(min_date) + "_to_" + str(
                max_date) + ".csv",
                           index=False)
            UO_Files = []
            for filename in tqdm(os.listdir(str(dataset_f_info['data_folder_path'][dataset])),
                                 desc="Open existing UO files"):
                if re.search(dataset_f_info['file_pat'][dataset], filename) and not filename.startswith('.'):
                    UO_Files.append(filename)
            UO_starts = []
            for string in UO_Files: UO_starts.append(string[8:18])
            UO_ends = []
            for string in UO_Files: UO_ends.append(string[22:32])

            new_UO_file_data = {'file': UO_Files,
                                'start': UO_starts,
                                'end': UO_ends}
            UO_log_dates_new = pd.DataFrame(new_UO_file_data, columns=['file', 'start', 'end'])
            UO_log_dates_new.to_csv(dataset_f_info['supp_data_filepath'][dataset], index=False, sep="\t")
            print("Urban Observatory data updated!")
        else:
            print("Urban Observatory data up-to-date!")

    UO_log_dates = import_UO_log_dates

    return UO_log_dates


def get_Events_support_data(dataset_f_info, dataset="Events"):
    Events_info = pd.read_csv(dataset_f_info['supp_data_filepath'][dataset], sep="\t", index_col="Code")
    return Events_info


custom_preimport_functions = {'UO': get_UO_support_data,
                              'Events': get_Events_support_data}


# ### Custom Imported Data Functions
def mod_imported_Sensor_data(day_df, filename, dataset_supp_data, dataset_f_info, dataset="Sensor"):
    day_df['DateTime'] = day_df['Date'] + " " + day_df['Time']
    day_df['DateTime'] = pd.to_datetime(day_df['DateTime'], format='%d/%m/%Y %H:%M:%S')
    day_df['DateTime'] = day_df['DateTime'].dt.tz_localize('UTC')

    # Make on/off events integer binary numbers 1/0
    # on_events = ["^ON$", "^RUNNING$", "^CW$", "^AUTO$"]
    # off_events = ["^OFF$", "^STOP$", "^CCW$", "^MANUAL$"]

    # all_rgx = re.compile("|".join(on_events + off_events))
    # on_rgx = re.compile("|".join(on_events))
    # off_rgx = re.compile("|".join(off_events))

    # Sensor_events = {'ON': 1,
    #                 'RUNNING': 1,
    #                 'CW': 1,
    #                 'AUTO': 1,
    #                 'OFF': 0,
    #                 'STOP': 0,
    #                 'CCW': 0,
    #                 'MANUAL': 0}

    # string_cols = (day_df.applymap(type) == str).all(0).values
    # for col in day_df.iloc[:, string_cols]:
    #    if day_df[col].str.contains(all_rgx).any():
    #        day_df[col] = day_df[col].replace(on_rgx, '1', regex=True)
    #        day_df[col] = day_df[col].replace(off_rgx, '0', regex=True)
    #        day_df[col] = day_df[col].astype(int)
    # for col in day_df.iloc[:, string_cols]:
    # if day_df.iloc[:, string_cols].str.contains(all_rgx).any():
    # day_df[[i for i in list(day_df.columns) if i not in ['DateTime', 'Date', 'Time']]] = \
    # day_df[[i for i in list(day_df.columns) if i not in ['DateTime', 'Date', 'Time']]].replace(Sensor_events).apply(pd.to_numeric)
    # day_df.iloc[:, string_cols] = day_df.astype(int)

    # Current density
    day_df.iloc[:, day_df.columns.str.contains("__C")] = day_df.iloc[:, day_df.columns.str.contains("__C")] / (
            math.pi * 0.6 ** 2 * 10)
    # Sum Current density
    day_df.iloc[:, day_df.columns.str.contains("SUM__C")] = day_df.iloc[:, day_df.columns.str.contains("SUM__C")] / 4

    # Sensible tilt (up = positive)
    day_df['SENSOR_TILT'] = -day_df['SENSOR_TILT']

    return day_df


def mod_imported_Skid_data(day_df, filename, dataset_supp_data, dataset_f_info, dataset="Skid"):
    day_df = day_df.rename(columns={"TIME": "DateTime"})
    day_df['DateTime'] = pd.to_datetime(day_df['DateTime'], format='%Y/%m/%d %H:%M:%S.%f')
    day_df['DateTime'] = day_df['DateTime'].dt.tz_localize('UTC')
    selected_pars = list(info['parameters'][selected].query('dataset == "' + dataset + '"')['parameter'].values)
    day_df = day_df[day_df[selected_pars].sum(axis=1, skipna=True) != 0]
    return day_df


def mod_imported_SampLog_data(day_df, filename, dataset_supp_data, dataset_f_info, dataset="SampLog"):
    day_df = day_df.rename(columns={"Date": "DateTime"})
    day_df['DateTime'] = pd.to_datetime(day_df['DateTime'], format='%d/%m/%Y %H:%M')
    day_df['DateTime'] = day_df['DateTime'].dt.tz_localize('Europe/London')
    day_df['DateTime'] = day_df['DateTime'].dt.tz_convert('UTC')

    selected_read_cols = ['R1', 'R2', 'R3']
    day_df[selected_read_cols] = day_df[selected_read_cols].apply(pd.to_numeric, errors='coerce')

    # Average readings
    day_df['Read_ave'] = day_df[selected_read_cols].mean(axis=1, skipna=True)

    # Widen DF
    day_df_wide = pd.pivot_table(day_df, values='Read_ave', index=['DateTime', 'Location'], columns=['Type', 'Vial'])
    # Fix col header and names
    day_df_wide.columns = map(''.join, (str(v) for v in day_df_wide.columns))
    day_df_wide.columns = [re.sub(r'\W', '', i) for i in day_df_wide.columns]
    day_df_wide.columns = [s[:len(s) - 1] + "_" + s[len(s) - 1:] for s in day_df_wide.columns]
    day_df_wide = day_df_wide.reset_index()

    return day_df_wide


def mod_imported_NWL_data(day_df, filename, dataset_supp_data, dataset_f_info, dataset="NWL"):
    day_df['DateTime'] = day_df['DATE'].astype(str) + " " + day_df['TIME']
    day_df['DateTime'] = pd.to_datetime(day_df['DateTime'], format='%Y-%m-%d %H:%M')
    day_df['DateTime'] = day_df['DateTime'].dt.tz_localize('Europe/London')
    day_df['DateTime'] = day_df['DateTime'].dt.tz_convert('UTC')

    day_df = day_df[day_df['SITE'].str.contains('SETTLED')]

    return day_df


def mod_imported_UO_data(day_df, filename, dataset_supp_data, dataset_f_info, dataset="UO"):
    day_df['DateTime'] = pd.to_datetime(day_df['Timestamp'], format='%Y-%m-%d %H:%M:%S')
    day_df['DateTime'] = day_df['DateTime'].dt.tz_localize('UTC')

    # Create Type column
    day_df['Type'] = day_df['Sensor Name'].astype(str) + "_" + day_df['Variable']

    # Widen DF
    day_df_wide = pd.pivot_table(day_df, values='Value', index=['DateTime'], columns=['Type'])
    # Fix col header and names
    day_df_wide = day_df_wide.reset_index()
    day_df_wide = day_df_wide.rename(columns=dict(zip(info['parameters'].query('dataset == "' + dataset + '"')['code'],
                                                      info['parameters'].query('dataset == "' + dataset + '"')[
                                                          'parameter'])))
    return day_df_wide


custom_import_functions = {'Sensor': mod_imported_Sensor_data,
                           'Skid': mod_imported_Skid_data,
                           'SampLog': mod_imported_SampLog_data,
                           'NWL': mod_imported_NWL_data,
                           'UO': mod_imported_UO_data}


# ### Data Import Functions
# Data import
def import_data(dataset):
    dataset_all_days = []
    for folder in range(1, len(info['datasets'].query('dataset == "' + dataset + '"')) + 1):
        # print(dataset + ": Folder " + str(folder))

        # Shorthand info:
        dataset_f_info = info['datasets'].query('dataset == "' + dataset + '" & folder == "' + str(folder) + '"')
        # File format to import
        f_file_import = select_file_importer(dataset, dataset_f_info)

        # Custom pre-import functions
        if dataset in custom_preimport_functions:
            dataset_supp_data = custom_preimport_functions[dataset](dataset_f_info)
        else:
            dataset_supp_data = ""
        # Import files
        for filename in tqdm(os.listdir(str(dataset_f_info['data_folder_path'][dataset])), desc="Open files to import"):
            if re.search(dataset_f_info['file_pat'][dataset], filename) and not filename.startswith('.'):
                day_df = file_import_handler(dataset, dataset_f_info, filename, dataset_supp_data, f_file_import)
                # Keep if longer than 0 lines
                if len(day_df) > 0:
                    # Keep if within DateTime range in Info file
                    if max(day_df['DateTime']) >= min(info['charts']['chart_range_start']) and min(
                            day_df['DateTime']) <= max(info['charts']['chart_range_end']):
                        dataset_all_days.append(day_df)

    # Create one dataframe from all days data
    dataset_all_data = pd.concat(dataset_all_days, axis=0, ignore_index=True)
    dataset_all_data.sort_values(by=['DateTime'], inplace=True)
    dataset_all_data = dataset_all_data.reset_index(drop=True)

    dataset_all_data = dataset_all_data[dataset_all_data['DateTime'] >= min(info['charts']['chart_range_start'])]
    dataset_all_data = dataset_all_data[dataset_all_data['DateTime'] <= max(info['charts']['chart_range_end'])]

    return dataset_all_data


# File Import functions
def select_file_importer(dataset, dataset_f_info):
    if re.search("xls", dataset_f_info['file_pat'][dataset], re.IGNORECASE):
        return file_import_functions["xls"]
    elif re.search("csv", dataset_f_info['file_pat'][dataset], re.IGNORECASE):
        return file_import_functions["csv"]
    elif re.search("txt", dataset_f_info['file_pat'][dataset], re.IGNORECASE):
        return file_import_functions["txt"]
    else:
        raise ValueError("Unknown file pattern!")


def file_import_xls(dataset, dataset_f_info, filename):
    df = pd.read_excel("".join([str(dataset_f_info['data_folder_path'][dataset]), filename]),
                       skiprows=dataset_f_info['skiprows'][dataset])
    return df


def file_import_csv(dataset, dataset_f_info, filename):
    df = pd.read_csv("".join([str(dataset_f_info['data_folder_path'][dataset]), filename]),
                     skiprows=dataset_f_info['skiprows'][dataset])
    return df


def file_import_txt(dataset, dataset_f_info, filename):
    df = pd.read_csv("".join([str(dataset_f_info['data_folder_path'][dataset]), filename]),
                     sep="\t", skiprows=dataset_f_info['skiprows'][dataset])
    return df


file_import_functions = {'xls': file_import_xls,
                         'csv': file_import_csv,
                         'txt': file_import_txt}


def file_import_handler(dataset, dataset_f_info, filename, dataset_supp_data, f_file_import):
    day_df = f_file_import(dataset, dataset_f_info, filename)
    if len(day_df) > 0:
        # Name parameter columns
        day_df = day_df.rename(columns=dict(zip(info['parameters'].query('dataset == "' + dataset + '"')['code'],
                                                info['parameters'].query('dataset == "' + dataset + '"')['parameter'])))
        # Delete unit rows
        if not pd.isna(dataset_f_info['Del_unit_rows'][dataset]):
            day_df = day_df.drop(0).reset_index()
        ##Load custom data mod function?
        if dataset in custom_import_functions:
            day_df = custom_import_functions[dataset](day_df, filename, dataset_supp_data, dataset_f_info, dataset)

        #Choose parameters included in parameters sheet
        selected_pars = list(info['parameters'].query('dataset == "' + dataset + '"')['parameter'].values)
        day_df = day_df[['DateTime'] + selected_pars]
        # Add blank row between files - to be implemented
        # if len(day_df) > 0:
        #    if not pd.isna(dataset_f_info['Add_blank_rows'][dataset]):
        #        day_df = day_df.append(pd.Series(), ignore_index=True)

    return day_df


# ### Data Import
selected_cols = [s for s in info['parameters'].columns.to_list() if "selected" in s]
selected = info['parameters'][selected_cols].isin([1]).any(axis=1)

selected_cols_ave = [s for s in info['parameters_ave'].columns.to_list() if "selected" in s]
selected_ave = info['parameters_ave'][selected_cols_ave].isin([1]).any(axis=1)

selected_datasets = list(selected[selected].index.unique().values) + list(selected_ave[selected_ave].index.unique().values)
selected_datasets = [x for i, x in enumerate(selected_datasets) if i == selected_datasets.index(x)]

del selected_cols, selected_cols_ave

dataset_data = []
for dataset in tqdm(selected_datasets, desc = "Import data from each dataset"):
    dataset_data.append(import_data(dataset))

all_data = pd.concat(dataset_data, axis=0, ignore_index=True, sort=False)
all_data.sort_values(by=['DateTime'], inplace=True)
cols = ['DateTime']  + [col for col in all_data if col != 'DateTime']
all_data = all_data[cols]
all_data = all_data.reset_index(drop=True)

del selected_datasets, cols, dataset_data, dataset

with warnings.catch_warnings():
    warnings.filterwarnings('ignore', r'All-NaN (slice|axis) encountered')
    warnings.filterwarnings('ignore', r'Degrees of freedom <= 0 for slice.')
    ave_cols = []
    for col in all_data.columns[1:].to_list():
        ave_col = info['parameters'].query('parameter == "' + col + '"')['parameter_ave'][0]
        if ave_col != col:
            if ave_col not in ave_cols:
                cols = info['parameters'].query('parameter_ave == "' + ave_col + '"')['parameter'].to_list()
                all_data[ave_col] = all_data[cols].mean(axis=1)
                if len(cols) > 2:
                    all_data[ave_col + "_err"] = np.nanstd(all_data[cols], axis=1)
                elif len(cols) == 2:
                    all_data[ave_col + "_err"] = np.abs((all_data[cols[0]] - all_data[cols[1]])/2)
                else:
                    all_data[ave_col + "_err"] = 0
                ave_cols.append(info['parameters'].query('parameter == "' + col + '"')['parameter_ave'][0])

del ave_col, col, ave_cols, cols

ave_pars = list(info['parameters_ave'][selected_ave]['parameter_ave'].values)
err_pars = [ave_par + "_err" for ave_par in ave_pars]
selected_pars = list(info['parameters'][selected]['parameter'].values) + ave_pars + err_pars

del selected, selected_ave, ave_pars, err_pars

all_data = all_data[["DateTime"]+ selected_pars]

del selected_pars

chart_dfs = []
for chart in tqdm(charts, desc="Assign data to chart DFs"):
    if info['charts'].loc[chart, 'chart_status'] == 'ON':
        mask = (all_data['DateTime'] >= info['charts'].loc[chart, 'chart_range_start']) & (
                all_data['DateTime'] <= info['charts'].loc[chart, 'chart_range_end'])
        df = all_data.loc[mask]
        if info['charts'].loc[chart, 'chart_res'] != 0:
            df = df.resample("".join([str(info['charts'].loc[chart, 'chart_res']), 'T']), on='DateTime').mean()
            df = df.reset_index()
        else:
            df = df.reset_index(drop=True)
        chart_dfs.append(df)
    else:
        chart_dfs.append("")

del df, chart, mask, all_data

# Create plot dictionary
plot_dict = dict(zip(info['parameters']['parameter'], info['parameters']['plot']))
plot_dict2 = dict(zip(info['parameters_ave']['parameter_ave'], info['parameters_ave']['plot']))
plot_dict.update(plot_dict2)

chart_dfs_mlt = []
for chart in tqdm(charts, desc="Melting data"):
    if info['charts'].loc[chart, 'chart_status'] == 'ON':
        data_cols = []
        err_cols = ["DateTime"]

        criteria = chart_dfs[chart].isna().all()
        wide_data = chart_dfs[chart][criteria.index[-criteria]]

        for col in wide_data.columns:
            if "_err" not in col:
                data_cols.append(col)
            else:
                err_cols.append(col)

        df = wide_data[data_cols].melt(id_vars=['DateTime'], var_name='Parameter', value_name='Value')
        df_err = wide_data[err_cols].melt(id_vars=['DateTime'], var_name='Parameter', value_name='Error')

        df = df.set_index(['DateTime', 'Parameter', df.groupby(['DateTime', 'Parameter']).cumcount()])
        df_err['Parameter'] = df_err['Parameter'].str.replace(r'_err', '')
        df_err = df_err.set_index(['DateTime', 'Parameter', df_err.groupby(['DateTime', 'Parameter']).cumcount()])

        df3 = (pd.concat([df, df_err], axis=1)
               .sort_index(level=2)
               .reset_index(level=2, drop=True)
               .reset_index())
        df3.sort_values(by=['DateTime', 'Parameter'], inplace=True)

        # Assign plots
        df3.loc[:, 'Plot'] = df3['Parameter'].map(plot_dict)

        chart_dfs_mlt.append(df3)
    else:
        chart_dfs_mlt.append(pd.DataFrame())

del chart, data_cols, err_cols, col, df, df_err, df3, chart_dfs, plot_dict, plot_dict2, wide_data, criteria

plot_pars = []
for chart in tqdm(charts, desc="Creating plot dictionaries"):
    if info['charts'].loc[chart, 'chart_status'] == 'ON':
        par_info1 = info['parameters'][
            info['parameters']['parameter'].isin(chart_dfs_mlt[chart].Parameter.unique())].drop(
            columns=["code", "parameter_ave"])
        par_info2 = info['parameters_ave'][
            info['parameters_ave']['parameter_ave'].isin(chart_dfs_mlt[chart].Parameter.unique())].rename(
            columns={"parameter_ave": "parameter"})
        par_info_all = (par_info1.append(par_info2)).query('selected_chart_' + str(chart) + ' == 1')

        # Convert colour id to rgb string
        par_info_all['colour'].replace(info['colours']['rgba_str'].to_dict(), inplace=True)
        par_info_all['fill'].replace(info['colours']['rgba_str'].to_dict(), inplace=True)

        # Set defaults for NAs
        par_info_all['colour'].fillna(info['colours'].query("theme == 'dark'")['rgba_str'].to_list()[0], inplace=True)
        par_info_all['fill'].fillna(info['colours'].query("theme == 'dark'")['rgba_str'].to_list()[0], inplace=True)
        par_info_all['shape'].fillna(1, inplace=True)
        par_info_all['line_type'].fillna("solid", inplace=True)
        par_info_all['show_in_legend'].fillna(True, inplace=True)

        par_info_all.loc[par_info_all['ribbon'] == True, 'fill'] = par_info_all.loc[par_info_all['ribbon'] == True, 'fill'].str.replace(",1\)", ",0.25)")

        plot_pars.append(par_info_all)
    else:
        plot_pars.append(pd.DataFrame())

del chart, par_info1, par_info2, par_info_all

# Export data to temp files

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

temp_folder = "Temp"
data_folder = temp_folder + "/Data"
data_types = ["info", "chart_dfs_mlt", "plot_pars"]

if not os.path.exists(temp_folder):
    os.mkdir(temp_folder)
else:
    delete_folder_contents(temp_folder)

os.mkdir(data_folder)
for data_type in data_types:
    os.mkdir(data_folder + "/" + data_type)

for A in info:
    info[A].to_csv(data_folder + "/info/info_" + str(A) + ".csv", encoding='utf-8')
for i, A in enumerate(chart_dfs_mlt):
    A.to_csv(data_folder + "/chart_dfs_mlt/chart_dfs_mlt_" + str(i) + ".csv", encoding='utf-8', index=False)
for i, A in enumerate(plot_pars):
    A.to_csv(data_folder + "/plot_pars/plot_pars_" + str(i) + ".csv", encoding='utf-8')
