# TimeSeriesProcessor

This `TimeSeriesProcessor` set of scripts can be used to process time series data into standardised formatting with interactive chart plotting and options for csv, pdf, png and html export.

# Installation and prerequisites

Install Python v3 (this has been tested with v3.7.3).

- E.g. To use an Anaconda distribution of Python download `Anaconda3-2019.07-Windows-x86_64.exe` from https://repo.anaconda.com/archive/

Install the python modules listed in the `requirements.txt` file.

- E.g. Open Anaconda Navigator --> In Command Prompt use `python -m pip install --user -r /path/to/requirements.txt`

# Setup

Create a `TimeSeriesProcessor` folder to store the general scripts for processing.

Inside this folder save the following files in this structure:

```
📦TimeSeriesProcessor
 ┣ 📂assets
 ┃ ┗ 📜header_image.png
 ┣ 📂Scripts
 ┃ ┣ 📜Callbacks.py
 ┃ ┣ 📜config.py
 ┃ ┣ 📜CreateCharts.py
 ┃ ┣ 📜Functions.py
 ┃ ┣ 📜Layout.py
 ┃ ┗ 📜ProcessData_resampler.py
 ┗ 📜app.py
```






