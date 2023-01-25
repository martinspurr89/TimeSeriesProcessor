# TimeSeriesProcessor

This `TimeSeriesProcessor` set of scripts can be used to process time series data from multiple sources into a standardised formatting with interactive chart plotting and options for csv, pdf, png and html export.

## Interactive chart plotting & export
### Chart plotting from multiple datasets
Available chart types:
- Line plots
![Line plots](docs/images/lines.png?raw=true "Line plots")
- Average line with ribbon plots
![Ribbon plots](docs/images/ribbon.png?raw=true "Ribbon plots")
With ribbon showing error around average line.
- Point (+ line) plots
![Point+line plots](docs/images/points.png?raw=true "Point+line plots")
With support for error bars around average points.
- Horizontal bar plots
![Horizontal bar plots](docs/images/horiz_bar.png?raw=true "Horizontal bar plots")
To display binary ON/OFF status of a parameter.

### Interactive chart control
#### DateTime Timeframe selection
- Chart Range selector

	<img src="docs/images/DT_selector.png?raw=true" alt="DateTime selector" width="300">

	- Select pre-defined timeframes from Information file (see below).
- Slider

	![DateTime slider](docs/images/slider.png?raw=true "DateTime slider")

	- Drag handles to adjust timeframe between data extents.

- Absolute DateTime input

	![DateTime input](docs/images/DT_input.png?raw=true "DateTime input")

	- Click on start and end Date and Time to select absolute values.

#### Plot selection
- Pre-set plot selector

	<img src="docs/images/plot-set_select.png?raw=true" alt="Plot selector" width="150">

	- Select pre-defined plot sets from Information file (see below).

- Custom plot and trace selector

	<img src="docs/images/plot_select.png?raw=true" alt="Plot selector" width="500">

	- Select plots and traces to be displayed.

#### Time series resampling

<img src="docs/images/resample.png?raw=true" alt="Resample" width="350">

- Resampling selector

	- Creates a time-resampled subset of the data (average within each resampling period) for rapid plotting or downstream analysis.
	- Assumes time series data is recorded no more frequent than 1 record per minute.
	- Select from:
		- Low (up to 700 records per series)
		- High (up to 2800 records per series)
		- None (no resampling - returns and plots raw data)
		- Set (enables input of defined resampling factor in minutes)

#### Plot display settings

<img src="docs/images/display.png?raw=true" alt="Display settings" width="200">

- Plot height: Set % vertical height a plot takes up, so with 20% 5 plots are shown per 100% screen height.
- Font size: for displayed plots.

#### Export options

<img src="docs/images/export.png?raw=true" alt="Export" width="400">

- All outputs are saved to an Output folder within each Project folder.
- CSV: A csv file for the displayed traces at the set resampling resolution is created.
- HTML: An offline html file of the displayed plots at the set resampling resolution is created.
- PDF: A pdf file at the set width (w) and height (h) is created of the displayed plots at the set resampling resolution.
- PNG: A png file at the set width (w), height (h) and image resolution (dpi) is created of the displayed plots at the set resampling resolution.

#### Plot loading

<img src="docs/images/submit.png?raw=true" alt="Submit" width="300">

- Submit: Displays selected plots/traces below the controls in an interactive plotly chart at the set resampling resolution.
- Export: Exports the selected outputs to the Output folder.

# Setup

## TimeSeriesProcessor file structure

Create a `TimeSeriesProcessor` folder to store the general scripts for processing.

Inside this folder download save the following files in this structure:

<pre><code>📦TimeSeriesProcessor
┣ 📂assets
┃ ┗ 📜header_image.png
┣ 📂Scripts
┃ ┣ 📜Callbacks.py
┃ ┣ 📜config.py
┃ ┣ 📜CreateCharts.py
┃ ┣ 📜Functions.py
┃ ┣ 📜Layout.py
┃ ┗ 📜ProcessData_resampler.py
┣ 📂<i>Example
┃ ┣ 📂Example_project
┃ ┃ ┣ 📂Scripts
┃ ┃ ┃ ┗ 📜CustomDataImports.py
┃ ┃ ┗ 📜Info2.xlsx
┃ ┣ 📂Example_Sample_data
┃ ┃ ┗ 📜Sample_log_data.csv
┃ ┗ 📂Example_TS_data
┃   ┗ 📜Timeseries_data.cs</i>
┣ 📜app.py
┣ 📜<i>requirements.txt</i>
┗ 📜<i>TimeSeriesProcessor.code-workspace</i>

<i>[Items in italics optional for normal running of the script]</i></code></pre>

## Software installation and prerequisites

Install Python v3 (this has been tested with v3.7.3).

- E.g. To use an Anaconda distribution of Python download `Anaconda3-2019.07-Windows-x86_64.exe` from https://repo.anaconda.com/archive/

Install the python modules listed in the `requirements.txt` file.

- E.g. If using Anaconda, open `Anaconda Prompt` ▶ Navigate to the folder containing the `requirements.txt` file (using `cd` and `dir`) ▶ Install the required packages using pip: `pip install --user -r requirements.txt`

# Create a Project

## Project Folder

Each experiment to be processed should be assigned a new Project folder (note this can be in any location and does not need to be within the script folder). As with the `Example_project` below, each Project folder should contain the following files:

<pre><code>📂Example_project
┣ 📂Scripts
┃ ┗ 📜CustomDataImports.py
┗ 📜Info2.xlsx</code></pre>

The `Info2.xlsx` and `CustomDataImports.py` files should be adapted from the `Example_project` provided. See below for more details.

During the script running an `Output` folder will be created in the project folder for all exported files and a file containing all data resampled to 15 minute intervals `all_data_15Min.csv` file.

## Data

Data files to be imported by the script should also be stored within their own dataset folder - one folder per dataset type/source (in case different import settings are needed) - the path of these will also be supplied to the script.

By default the script supports two dataset types with specific formatting:
- `TimeSeries` data
- `SampleLog` data
 Further dataset formats can be included by modifying `CustomDataImports.py` as below.

 ### TimeSeries data

 Example time series data is stored in the Example folder.

<pre><code>📦Example_TS_data
 ┣ 📜Timeseries_data_01_01_2023.csv
 ┣ 📜Timeseries_data_02_01_2023.csv
 ┣ 📜Timeseries_data_03_01_2023.csv
 ...</code></pre>

 To use the default import settings, all `TimeSeries` data should be modified to the format:

 | Date       | Time     | parameter_code_1 | parameter_code_2 | ... |
| ---------- | -------- | ----------------- | -----------------  | ----------------- |
| dd/mm/yyyy | hh:mm:ss | #         | #         | ...          |

With the columns:
- `Date`: in dd/mm/yyyy format
- `Time`: in hh:mm:ss format
- Additional columns for each parameter with a header name `code` to be provided in the Information file (see below).
	- Parameter columns should data in either:
		- numeric data for line/point/ribbon plotting
		- binary 0/1 for horizontal bar plotting.

### SampleLog data

 Example sample log data is stored in the Example folder.

<pre><code>📂Example_Sample_data
┗ 📜Sample_log_data.csv</code></pre>

 To use the default import settings, all `SampleLog` data should be modified to the format:

 | DateTime         | Type  | Vial | R1 | R2  | R3  | Location |
| ---------------- | ----- | ---- | -- | --- | --- | -------- |
| dd/mm/yyyy hh:mm | parameter  | 1    | #  | [#] | [#] | A        |
| dd/mm/yyyy hh:mm | parameter  | 2    | #  | [#] | [#] | A        |
| dd/mm/yyyy hh:mm | parameter  | 1    | #  | [#] | [#] | B        |
| dd/mm/yyyy hh:mm | parameter  | 2    | #  | [#] | [#] | B        |
| dd/mm/yyyy hh:mm | parameter  | 1    | #  | [#] | [#] | C        |
| dd/mm/yyyy hh:mm | parameter  | 2    | #  | [#] | [#] | C        |
|...|

This format is flexible to allow unlimited number of parameters (analyses) and replicate measurements. Each row represents an analysis test.
- Within each row the following data fields:
- `DateTime`: When sample was taken. Enter in required format. N.B. by default times should be entered in 'Europe/London' (GMT/BST) timezone and this will be converted to UTC by the script later.
	- Default import can be modified by altering `CustomDataImports.py` file as below.
- `Type`: Enter a parameter name which will be converted to a parameter_code for use in the Information file.
- `Vial`: To allow for replicate measurements of the same sample, enter an integer incrementing from 1 per replicate (e.g. 3 rows with vial 1, 2 and 3 for triplicate measurements).
- `R1`: Read value. Enter numeric data for the analysis result in units to be plotted.
- `R2`, `R3`: Optional. Additional read values where multiple readings of the same analysis vial may have been taken (E.g. for inconsistent measuring devices). Enter numeric data which will be averaged across `R1`, `R2` and `R3`.
- `Location`: Sampling location (E.g. reactor ID or treatment reference) to form part of parameter_code generated.
	
Parameter codes will be generated for unique DateTime values in the format: `Location`\_`Type`\_`Vial`. These `parameter codes` should be referenced in the Information file.

Behind the scenes a wide-format data table will be automatically generated from this data in the format:

| DateTime         | A_parameter_1 | A_parameter_2 | B_parameter_1 | B_parameter_2 | C_parameter_1 | C_parameter_2 |
| ---------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- |
| dd/mm/yyyy hh:mm | #             | #             | #             | #             | #             | #             |
|...|

This table format is accessible from the `all_data...` and `CSV` export options.

# Define a Project

## Information File

Each project has an information file (`Info2.xlsx`) with Excel worksheets detailing various input specifications.

### The `setup` worksheet

On this sheet enter project details:
- `project`: Select a name to be displayed on interactive plotting pages.
- `date_start_utc`: Enter datetime in required format.
- `date_end_utc`: Enter datetime in required format.
- `default_font_size`: default `12` (alter if needed).
- `default_html_height`: default `20`. This is the % vertical height a plot takes up, so with 20% set 5 plots are shown per 100% screen height.

| id                  | value               |
| ------------------- | ------------------- |
| project             | Project name        |
| date_start_utc      | dd/mm/yyyy hh:mm:ss |
| date_end_utc        | dd/mm/yyyy hh:mm:ss |
| default_font_size   | 12                  |
| default_html_height | 20                  |

### The `datasets` worksheet

On this sheet enter details of each dataset folder to be imported.
- `dataset`: ID of dataset. With default settings this must be `TimeSeries` or `SampleLog`.
- `folder`: default `1` (increment for each additional folder containing data of the same dataset type). E.g. if there are multiple folders (2023, 2022, etc) containing data for several years these would need their own rows.
- `data_folder_path`: Enter the full path to folders containing dataset data files. Must use `/` slashes.
- `supp_data_filepath`: Optional - leave blank if unused. Path to a file containing supporting data for datasets which need this imported first rather than with every data file. E.g. File may contain a parameter dictionary or data file timestamp information.
- `file_pat`: Enter the file pattern suffix to identify the data files.
- `skiprows`: default `0` (alter if first X rows from each data file are to be ignored).

E.g.

| dataset    | folder | data_folder_path            | supp_data_filepath | file_pat | skiprows |
| ---------- | ------ | --------------------------- | ------------------ | -------- | -------- |
| TimeSeries | 1      | C:/Users/username/Data/Example_TS_data/     |                    | .csv     | 0        |
| SampleLog  | 1      | C:/Users/username/Data/Example_Sample_data/ |                    | .csv     | 0        |
|...|

### The `charts` worksheet

A chart is defined as the page on which selected plots will be placed with a common timeframe.

Enter details of pre-defined charts to be created by the script (available for selection in interactive mode).
- `order`: Increment chart ID from 0.
- `chart`: Short name for use in filenames of exported data/plots.
- `chart_label`: Name for display and selection.
- `chart_range_window`: Optional date range window for data selection in days. Can be used with either `chart_range_start` or `chart_range_end` or neither. If start is provided data will be selected from start datetime to start + X days. If end is provided data will be selected from end - X days to end datetime. If neither start or end are provided the script will select data in reference to the last data point (e.g. Last X days).
- `chart_range_start`: Optional. Enter datetime in required format.
- `chart_range_end`: Optional. Enter datetime in required format.
N.B. if no window, start or end are provided all data will be selected.
- `plot_set`: ID of plot_set to be used on each chart by default as defined on `plots` worksheet below.
- `auto_html`, `auto_pdf`, `auto_png`: ON/OFF. Whether script should automatically export html/pdf/png to Output folder when running. Default `OFF` for all.
- `pdf_size`, `png_size`: Default page_size ID for pdf/png export (as defined on `page_sizes` worksheet).

E.g.

| order | chart   | chart_label  | chart_range_window | chart_range_start   | chart_range_end     | plot_set | auto_html | auto_pdf | auto_png | pdf_size | png_size |
| ----- | ------- | ------------ | ------------------ | ------------------- | ------------------- | -------- | --------- | -------- | -------- | -------- | -------- |
| 0     | last10d | Last 10 days | 10                 |                     |                     | 1        | OFF       | OFF      | OFF      | 0        | 1        |
| 1     | expt    | Experiment 1 |                    | 05/01/2022 09:00:00 | 10/01/2023 17:00:00 | 1        | OFF       | OFF      | OFF      | 0        | 1        |
| 2     | all     | All Data     |                    |                     |                     | 1        | OFF       | OFF      | OFF      | 0        | 1        |
|...|

### The `plots` worksheet

Plots are defined as singular graphs which may be combined on a chart page.

Plot sets are collections of plots which can be set as default display for specified charts on the `charts` worksheet.

Enter details of plots to be created by the script.
- `plot`: ID of plot used in `parameters` and `parameters_ave` worksheets.
- `ylab`: Label for plot y-axis. Use \<br> for line breaks.
- `ymin`, `ymax`: Optional. Minimum/maximum y range.
- `height`: Height of plot relative to other plots on page. Default `10`.
- `log`: Default `FALSE`. Whether to display as log y axis.
- `selected_plot_set_X`: Enter a unique number representing the order (1 at top) to include the plot in the plot set or leave blank to omit plot. Add additional plot set columns with the same naming scheme as needed.

| plot  | ylab                    | ymin | ymax |  height | log   | selected_plot_set_0 | selected_plot_set_1 |
| ----- | ----------------------- | ---- | ---- | ------- | ----- | ------------------- | ------------------- |
| V_AVE | Average Voltage\<br>(mV) | 0    |      | 10      | FALSE | 1                   |                     |
| V_A   | Voltage\<br>(mV) A       | 0    |      | 10      | FALSE |                     | 1                   |
| V_B   | Voltage\<br>(mV) B       | 0    |      | 10      | FALSE |                     | 2                   |
|...|

### The `parameters` worksheet

Parameters represent individual series which are plotted within a plot.

Enter details of parameters to be plotted and whether to include as a line, ribbon, point or horizontal bar plot.
- `dataset`: Enter dataset ID from `datasets` worksheet the parameter is imported from.
- `code`: The parameter name code (e.g. column header or ID) in the imported data file.
- `parameter`: Unique parameter name to be used in the script processing (can be same as `code` or renamed to avoid conflicts across different datasets).
- `parameter_ave`: If a new parameter is to be generated from the average of multiple parameters (e.g. replicates), enter a new average parameter name and include this in the `parameter_ave` field on the row of each parameter to be averaged - see `A1_V` and `B1_V` rows below. Details for this parameter will be defined on the `parameters_ave` worksheet. If no average is required, repeat the `parameter` name here - see `TEMP_SP` row below.
- `parameter_lab`: Enter label for parameter to appear in plot legends.
- `plot`: Enter plot ID from `plots` worksheet to display the parameter.
- `line`: Enter shape of line to display line plots E.g. `linear` or `hv` (horizontal-then-vertical) (see other types here: https://plotly.com/python/reference/scatter/#scatter-line-shape). If no line is to be plotted for this parameter leave blank.
- `ribbon`: Enter TRUE to plot a ribbon displaying error around an (averaged parameter) line. Enter FALSE or leave blank to prevent ribbon.
- `bar`: Enter TRUE to plot a horizontal bar displaying ON/OFF status for a parameter. Requires data in `0`/`1` (OFF/ON) binary format. Enter FALSE or leave blank to prevent bar.
- `point`: Enter TRUE to plot points for this parameter. Enter FALSE or leave blank to prevent points.
- `colour`, `fill`: Enter ID of colour from `colours` worksheet. Colours correspond to lines and point outlines, fills correspond to ribbons, point fills and bars.
- `shape`: Enter shape name for points to be plotted (when `point` is TRUE). E.g. `circle` (see other types here: https://plotly.com/python/marker-style/#custom-marker-symbols)
- `dash`: Enter dash style for lines (when `line` is not blank). E.g. `solid` (see other styles here: https://plotly.com/python/reference/scatter/#scatter-line-dash)
- `bar_order`: Enter unique (per plot) integer starting from `1` to define order of bars (highest number is top of plot).
- `show_in_legend`: Enter TRUE to show parameter name label in the legend. Enter FALSE or leave blank to prevent showing in the legend.
- `selected_plot_set_X`: Enter plot set ID from `plots` worksheet. Add additional plot set columns with the same naming scheme as needed.

| dataset    | code                  | parameter       | parameter_ave   | parameter_lab     | plot   | line   | ribbon | bar   | point | colour | fill | shape | dash  | bar_order | show_in_legend | selected_plot_set_0 | selected_plot_set_1 |
| ---------- | --------------------- | --------------- | --------------- | ----------------- | ------ | ------ | ------ | ----- | ----- | ------ | ---- | ----- | ----- | --------- | -------------- | ------------------- | ------------------- |
| TimeSeries | Reactor_A_Stage_1     | A1_V            | 1_V_ave         | Reactor A Stage 1 | V_A    | linear | FALSE  | FALSE | FALSE | 1      | 1    |       | solid |           | TRUE           | 1                   | 1                   |
| TimeSeries | Reactor_B_Stage_1     | B1_V            | 1_V_ave         | Reactor B Stage 1 | V_B    | linear | FALSE  | FALSE | FALSE | 2      | 2    |       | solid |           | TRUE           | 1                   | 1                   |
| SampleLog  | sCOD                  | A_sCOD_1        | A_sCOD_ave      | A sCOD 1          | COD    |        |        |       |       |        |      |       |       |           |                | 0                   | 0                   |
| SampleLog  | sCOD                  | A_sCOD_2        | A_sCOD_ave      | A sCOD 2          | COD    |        |        |       |       |        |      |       |       |           |                | 0                   | 0                   |
| TimeSeries | Temperature_Set_Point | TEMP_SP         | TEMP_SP         | Temp Set Point    | TEMP   | hv     | FALSE  | FALSE | FALSE | 19     | 19   |       | solid |           | TRUE           | 1                   | 1                   |
| TimeSeries | Heater_A_Status       | HEATER_A_STATUS | HEATER_A_STATUS | Heater A Enabled  | EVENTS |        | FALSE  | TRUE  | FALSE | 1      | 1    |       | solid | 1         | TRUE           | 1                   | 1                   |
| ... |

### The `parameters_ave` worksheet

This worksheet defines configurations for any new `parameter_ave` names defined on the `parameters` worksheet for averaged parameters generated by the script.

The format of the fields in this worksheet is very similar to the `parameters` worksheet.

- `parameter_ave`: Enter names indicated on the `parameters` worksheet where the `parameter` value and `parameters_ave` fields are not the same. Multiple `parameter` values should share a `parameter_ave` to be averaged. E.g. `1_V_ave` and `A_sCOD_ave` above and below.

| dataset    | parameter_ave | parameter_lab | plot  | line   | ribbon | bar   | point | colour | fill | shape  | dash  | bar_order | show_in_legend | selected_plot_set_0 | selected_plot_set_1 |
| ---------- | ------------- | ------------- | ----- | ------ | ------ | ----- | ----- | ------ | ---- | ------ | ----- | --------- | -------------- | ------------------- | ------------------- |
| TimeSeries | 1_V_ave       | Stage 1 (ave) | V_AVE | linear | TRUE   | FALSE | FALSE | 0      | 0    |        | solid |           | TRUE           | 1                   | 0                   |
| SampleLog  | A_sCOD_ave    | A sCOD        | COD   | linear | FALSE  | FALSE | TRUE  | 21     | 21   | circle | solid |           | TRUE           | 1                   | 1                   |
|...|

### The `colours` worksheet

Enter the details for a colour set to be used for plotting parameters.
- `order`: Colour ID used in `parameters` and `parameters_ave` worksheets.
- `colour`, `theme`: Name for reference only.
- `r`, `g`, `b`: Enter the Decimal RGB code (see: https://www.rapidtables.com/web/color/RGB_Color.html).

| order | colour | theme | r   | g   | b  |
| ----- | ------ | ----- | --- | --- | -- |
| 0     | red    | mid   | 214 | 39  | 40 |
| 1     | orange | mid   | 255 | 127 | 14 |
| 2     | yellow | mid   | 188 | 189 | 34 |
|...|

### The `page_sizes` worksheet

Page sizes to be used in default exports can be defined here.
- `order`: Page size ID used in `charts` worksheet.
- `type`: `pdf` or `png`.
- `size_name`: Reference name for display.
- `width`, `height`: Size in pixels.
- `png_dpi`: Resolution of `png` export.

| order | type | size_name | width | height | png_dpi |
| ----- | ---- | --------- | ----- | ------ | ------- |
| 0     | pdf  | A4        | 794   | 1123   |         |
| 1     | png  | PPT       | 1280  | 720    | 300     |
| 2     | png  | A4        | 794   | 1123   | 300     |
|...|

# Running the script

## From the command line

### Get all data

To run the scripts using the command line (or Anaconda Prompt if using Anaconda), navigate to the scripts folder containing `app.py`.

To collect all data from the datasets described in the Information file use:

``` python
python app.py --io_dir "path/to/project_folder" --port "8051"
```

Provide the following arguments after the `app.py` name:
- `--io_dir`: The path to the project folder containing `Info2.xlsx`.
- `--port`: Enter a port to use (E.g. starting from 8051). Using different ports for different projects allows the script and interactive charting to be run simultaneously.

This will import the data and launch the interactive charting webpage. Please note that for large datasets the script can take considerable time to run through all the processes (E.g. 45 minutes to run for a 2 year × 1 minute dataset).

Outputs from the processing will be stored in the Output folder created within the project folder.

### Update mode

To use a previous output of the script for interactive charting and prevent reimporting the data again add the `--update` argument.

``` python
python app.py --io_dir "path/to/project_folder" --port "8051" --update
```

This is a much faster way to access interactive charting if no update to the data is needed. It requires the files created within the Output folder within the project folder.

## Optional: VS Code setup

### Setup VS Code

It is easier to run the scripts using the VS Code editor for regular use, troubleshooting or running multiple instances. Install this either from `Anaconda Navigator` (if using Anaconda) or at https://code.visualstudio.com/download.

Launch VS Code (from inside `Anaconda Navigator` if using Anaconda).

Open the workspace file from: File ▶ Open Workspace from File ▶ Select `TimeSeriesProcessor_WS.code-workspace`.

Within VS Code, open the `TimeSeriesProcessor_WS.code-workspace` file from the `Explorer` left hand menu.

Modify the file so that the highlighted items below have the correct paths for the `pythonPath`, `condaPath` and for each project amend the `Name`, `io-dir` (directory folder for input/ouput to the script). The `port` value can also be changed - useful to have a different port for each project so multiple instances of the script can be run simultaneously.

This can be used to provide a `Get_all` and `Update` script for each project.

<pre><code>{	
	"folders": [
		{
			"path": "."
		}
	],
	"launch": {
		"version": "0.2.0",
		"python.pythonPath": "<b>C:/Users/username/Anaconda3/python.exe</b>"🔴,
		"python.condaPath": "<b>C:/Users/username/Anaconda3/Scripts/conda.exe</b>"🟠,
		"configurations": [

			{
				"name": "Get_all-Example",
				"type": "python",
				"request": "launch",
				"program": "${file}",
				"console": "integratedTerminal",
				"args": ["--io_dir", "Example/Example_project", "--port", "8050"]
			},
            {
				"name": "Get_all-<b>PROJECT</b>"🟢,
				"type": "python",
				"request": "launch",
				"program": "${file}",
				"console": "integratedTerminal",
				"args": ["--io_dir", "<b>C:/Users/username/PROJECTS/PROJECT</b>"🔵, "--port", "<b>8051</b>"🟣]
			},
            {
				"name": "Update-<b>PROJECT</b>"🟢,
				"type": "python",
				"request": "launch",
				"program": "${file}",
				"console": "integratedTerminal",
				"args": ["--io_dir", "<b>C:/Users/username/PROJECTS/PROJECT</b>"🔵, "--port", "<b>8051</b>"🟣, "--update"]
			},
		]
	}
}</code></pre>

### Run with VS Code

To run the scripts using VS Code, open the `app.py` file.

<img src="docs/images/vscode.png?raw=true" alt="Export" width="500">

Then select the `Run and Debug` menu from the left hand pane. Select the required run parameters from the dropdown list (e.g. `Get_all-Example`). Press the green `play` button to run the script.

To run without debugging enabled (faster but won't catch errors) use Run -> `Run Without Debugging` with the required run parameters selected from the dropdown.

The script running can be monitored from the Terminal window within VS Code.





