import os
import pickle
import bz2

from pytz import timezone, utc
from datetime import datetime, timedelta
from threading import Timer
import dash_bootstrap_components as dbc
from dash_extensions.enrich import Output, Dash, Trigger, FileSystemCache

import Scripts.config as config
import Scripts.ProcessData_resampler as ProcessData
import Scripts.CreateCharts as CreateCharts
import Scripts.Functions as func
import Scripts.Layout as Layout
from Scripts.Callbacks  import register_callbacks


def getConfigData():
    dfile_path = config.io_dir / "Output" / 'all_data.pbz2'
    pfile_path = config.io_dir / "Output" / 'sub_config2.pbz2'
    if os.path.exists(dfile_path) and os.path.exists(pfile_path) and config.update:
        print("Importing processed data...")
        with bz2.open(dfile_path, 'rb') as pfile:
            config.data['all_data'] = pickle.load(pfile)
        print("Importing config...")
        with bz2.open(pfile_path, 'rb') as pfile:
            items = pickle.load(pfile)
        for key in list(items[0].keys()):
            config.config[key] = items[0][key]
        for key in list(items[1].keys()):
            config.figs[key] = items[1][key]
    else:
        if config.update:
            print("No processed all_data.pbz2 or sub_config2.pbz2 files exist")
        CreateCharts.main()
        config.update = True
        getConfigData()

begin = datetime.now(timezone('UTC')).replace(microsecond=0)
print("Starting processing at: " + str(begin))

ProcessData.processArguments()
getConfigData()
print("Config imported!")

external_stylesheets = [dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]#, 'https://codepen.io/chriddyp/pen/bWLwgP.css']
#app = JupyterDash('__name__')
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions = True)
#app.scripts.config.serve_locally = True

##APP##
config.components = Layout.prepare_layout() # Prepare layout
app.layout = Layout.serve_layout
register_callbacks(app) # Add callbacks

# Create a server side resource.
config.fsc = FileSystemCache("cache_dir")
config.fsc.set("submit_progress", None)
config.fsc.set("export_progress", None)

finish = datetime.now(timezone('UTC')).replace(microsecond=0)
print("App ready at: " + str(finish) + " (" + str(finish - begin) + ")")

if __name__ == '__main__':
    Timer(1, func.open_browser).start()
    app.run_server(port=8050, debug=True, use_reloader=False)

####
