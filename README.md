# TimeSeriesProcessor

This `TimeSeriesProcessor` set of scripts can be used to process time series data into standardised formatting with interactive chart plotting and options for csv, pdf, png and html export.

## Setup

### Installation and prerequisites

Install Python v3 (this has been tested with v3.7.3).

- E.g. To use an Anaconda distribution of Python download `Anaconda3-2019.07-Windows-x86_64.exe` from https://repo.anaconda.com/archive/

Install the python modules listed in the `requirements.txt` file.

- E.g. Open `Anaconda Prompt` ▶ Navigate to folder containing `requirements.txt` file `pip install --user -r requirements.txt`

#### File structure

Create a `TimeSeriesProcessor` folder to store the general scripts for processing.

Inside this folder download save the following files in this structure:

<code>
  📦TimeSeriesProcessor<br>
  ┣ 📂assets<br>
    ┃ ┗ 📜header_image.png<br>
    ┣ 📂Scripts<br>
    ┃ ┣ 📜Callbacks.py<br>
    ┃ ┣ 📜config.py<br>
    ┃ ┣ 📜CreateCharts.py<br>
    ┃ ┣ 📜Functions.py<br>
    ┃ ┣ 📜Layout.py<br>
    ┃ ┗ 📜ProcessData_resampler.py<br>
    ┣ 📜app.py<br>
    ┣ 📜requirements.txt<br>
    ┗ 📜TimeSeriesProcessor_example.code-workspace <i>[Optional]</i>
</code>

### Optional: VSCode setup

For regular use or multiple instances, it is easier to run the scripts using VSCode. Install this either from `Anaconda Navigator` or  https://code.visualstudio.com/download.








