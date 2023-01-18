# TimeSeriesProcessor

This `TimeSeriesProcessor` set of scripts can be used to process time series data into standardised formatting with interactive chart plotting and options for csv, pdf, png and html export.

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

## Create a Project

Each experiment to be processed should be assigned a new Project folder (note this can be in any location and does not need to be within the script folder). As with the `Example_project` below, each Project folder should contain the following files:

<code>📂Example_project<br>
┣ 📂Scripts<br>
┃ ┗ 📜CustomDataImports.py<br>
┗ 📜Info2.xlsx<br></code>

The `Info2.xlsx` and `CustomDataImports.py` files should be adapted from the `Example_project` provided. See below for more details.

Separately, data files to be imported should be stored within a folder - one folder per dataset type/source (in case different import settings are needed) - the path of these will also be supplied to the script.

<code>📂Example_Sample_data<br>
┗ 📜Sample_log_data.csv<br>

📂Example_TS_data<br>
┗ 📜Timeseries_data.cs<br></code>

## Information File

Each project has an information file (`Info2.xlsx`) with Excel worksheets detailing various input specifications.

### The `setup` worksheet

| id                  | value                    |
| ------------------- | ------------------------ |
| project             | Example Project Jan 2023 |
| date_start_utc      | 01/01/2023 12:00:00      |
| date_end_utc        | 21/01/2023 00:00:00      |
| default_font_size   | 12                       |
| default_html_height | 20                       |

## Optional: VS Code setup

It is easier to run the scripts using the VS Code editor for regular use, troubleshooting or running multiple instances. Install this either from `Anaconda Navigator` (if using Anaconda) or at https://code.visualstudio.com/download.

Launch VS Code (from inside `Anaconda Navigator` if using Anaconda).

Open the workspace file from: File ▶ Open Workspace from File ▶ Select `TimeSeriesProcessor_WS.code-workspace`.

Within VS Code, open the `TimeSeriesProcessor_WS.code-workspace` file from the `Explorer` left hand menu.

Modify the file so that the highlighted items below have the correct paths for the `pythonPath`, `condaPath` and for each project amend the `Name`, `io-dir` (directory folder for input/ouput to the script). The `port` value can also be changed - useful to have a different port for each project so multiple instances of the script can be run simultaneously.

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





