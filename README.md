# TimeSeriesProcessor

This `TimeSeriesProcessor` set of scripts can be used to process time series data into standardised formatting with interactive chart plotting and options for csv, pdf, png and html export.

# Setup

## TimeSeriesProcessor file structure

Create a `TimeSeriesProcessor` folder to store the general scripts for processing.

Inside this folder download save the following files in this structure:

<code>📦TimeSeriesProcessor<br>
┣ 📂assets<br>
┃ ┗ 📜header_image.png<br>
┣ 📂Scripts<br>
┃ ┣ 📜Callbacks.py<br>
┃ ┣ 📜config.py<br>
┃ ┣ 📜CreateCharts.py<br>
┃ ┣ 📜Functions.py<br>
┃ ┣ 📜Layout.py<br>
┃ ┗ 📜ProcessData_resampler.py<br>
┣ 📂<i>Example<br>
┃ ┣ 📂Example_project<br>
┃ ┃ ┣ 📂Scripts<br>
┃ ┃ ┃ ┗ 📜CustomDataImports.py<br>
┃ ┃ ┗ 📜Info2.xlsx<br>
┃ ┣ 📂Example_Sample_data<br>
┃ ┃ ┗ 📜Sample_log_data.csv<br>
┃ ┗ 📂Example_TS_data<br>
┃   ┗ 📜Timeseries_data.cs</i><br></code>
┣ 📜app.py<br>
┣ 📜<i>requirements.txt</i><br>
┗ 📜<i>TimeSeriesProcessor_example.code-workspace</i><br>

<i>[Optional for normal of the running script]</i></code>

## Software installation and prerequisites

Install Python v3 (this has been tested with v3.7.3).

- E.g. To use an Anaconda distribution of Python download `Anaconda3-2019.07-Windows-x86_64.exe` from https://repo.anaconda.com/archive/

Install the python modules listed in the `requirements.txt` file.

- E.g. If using Anaconda, open `Anaconda Prompt` ▶ Navigate to the folder containing the `requirements.txt` file (using `cd` and `dir`) ▶ Install the required packages using pip: `pip install --user -r requirements.txt`


## Optional: VSCode setup

For regular use or multiple instances, it is easier to run the scripts using VSCode. Install this either from `Anaconda Navigator` or  https://code.visualstudio.com/download.



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





