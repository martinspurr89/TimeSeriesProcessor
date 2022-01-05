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
config['refresh_hours'] = 1
config['date_start'] = datetime(2020, 1, 1, 0, 0, 0, tzinfo=utc)
config['date_end'] = datetime(2020, 1, 1, 1, 0, 0, tzinfo=utc)
config['charts'] = {}
config['chart_plot_sets'] = {}
config['plot_sets'] = []
config['files_imported'] = {}
config['supporting_data_dict'] = {}
config['selected_pars'] = []
config['bar_pars'] = []
config['selected_datasets'] = []
config['dataset_data'] = {}
config['all_data'] = None
config['bar_dfs'] = {}
config['chart_dfs'] = {}
config['par_plot_dict'] = {}
config['filetypes'] = []
config['styles'] = ['line', 'ribbon', 'bar', 'point']
config['par_style_dict'] = {}
config['chart_dfs_mlt'] = {}
config['plot_pars'] = {}
config['plot_set_figs'] = {}
config['chart_figs'] = {}
config['dcc_chart_figs'] = {}
config['dcc_plot_set_figs'] = {}
config['dcc_plot_names'] = {}
config['div_chart_figs'] = {}