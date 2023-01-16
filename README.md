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


## Optional: VS Code setup

For regular use, troubleshooting or running multiple instances, it is easier to run the scripts using the VS Code editor. Install this either from `Anaconda Navigator` (if using Anaconda) or at https://code.visualstudio.com/download.

Launch VS Code (from `Anaconda Navigator` if using Anaconda).
File ▶ Open Workspace from File ▶ Select the `TimeSeriesProcessor.code-workspace` file.

Within VS Code, open the `TimeSeriesProcessor.code-workspace` file from the `Explorer` left hand menu.

<pre lang="python"><code>
{	
	"folders": [
		{
			"path": "."
		}
	],
	"launch": {
		"version": "0.2.0",
		"python.pythonPath": "C:/Program Files/Python37/python.exe",
		"python.condaPath": "C:/Anaconda3/Scripts/conda.exe",
		"configurations": [

			{
				"name": "Get_all-PROJECT",
				"type": "python",
				"request": "launch",
				"program": "${file}",
				"console": "integratedTerminal",
				"pythonPath": "C:/Program Files/Python37/python.exe",
				"args": ["--io_dir", "C:/Users/username/PROJECTS/PROJECT", "--port", "8052"]
			},
            {
				"name": "Update-PROJECT",
				"type": "python",
				"request": "launch",
				"program": "${file}",
				"console": "integratedTerminal",
				"pythonPath": "C:/Program Files/Python37/python.exe",
				"args": ["--io_dir", "C:/Users/username/PROJECTS/PROJECT", "--port", "8052", "--update"]
			},
		]
	}
}
</code></pre>



## Example Project

Project structure

<code>📂Example_project<br>
┣ 📂Scripts<br>
┃ ┗ 📜CustomDataImports.py<br>
┗ 📜Info2.xlsx<br></code>

Data files

<code>📂Example_Sample_data<br>
┗ 📜Sample_log_data.csv<br>

📂Example_TS_data<br>
┗ 📜Timeseries_data.cs<br></code>





