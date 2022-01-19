from pathlib import Path
from datetime import datetime
from pytz import utc

io_dir = Path.home()
update = False
verbose = False

# Default config
config = {}
config['info'] = {}
config['project'] = ""
config['date_start'] = datetime(2020, 1, 1, 0, 0, 0, tzinfo=utc)
config['date_end'] = datetime(2020, 1, 1, 1, 0, 0, tzinfo=utc)
config['plot_sets'] = [] #plot_set ids list
config['plot_set_plots'] = {} # dict of plot_sets containing plots + trace names
config['selected_pars'] = [] # list of every par
config['bar_pars'] = [] # list of bar pars
config['plot_pars'] = {} # dataframe of all plot_pars info page (par + aves) CC only
config['dcc_plot_codes'] = {} # graphX:plot name code
config['dcc_plot_names'] = {} # graphX:plot name
config['dcc_trace_names'] = {} # graphX:list of trace labels
config['pdf_size_dict'] = {}
config['png_size_dict'] = {}

importer = {}
importer['files_imported'] = {} # dict of dataset: filenames
importer['selected_datasets'] = [] # list of datasets used
importer['filetypes'] = [] # list of filetypes

data = {}
data['dataset_data'] = {} # Individual data df
data['supporting_data_dict'] = {} # Supporting dataframe store
data['all_data'] = None # Master all data df

figs = {}
figs['plot_figs'] = {} # dict of plot_code:Figure
figs['dcc_plot_figs'] = {} # list of dcc Graphs

components = {}