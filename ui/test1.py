import json
import os
from random import choice
from typing import List, Optional

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Output, State

from config import DATA_DIR
from scripts.correlation_constants import Security
from scripts.file_reading_funcs import load_saved_securities
from scripts.plotting_functions import CorrelationPlotter


class SecurityDashboard:
    SECURITIES_INPUT_ID = 'security_dropdown'

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.available_securities: List[str] = self.get_available_securities()
        self.initial_plot = self.load_initial_plot()
        self.current_main_security: Optional[Security] = load_saved_securities(choice(self.available_securities),
                                                                               '2010-01-01')
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], assets_folder='assets')
        self.setup_layout()

    def load_initial_plot(self):
        random_security = choice(self.available_securities)
        start_date = '2010-01-01'
        num_traces = 2
        show_detrended = False
        etf = True
        stock = False
        index = False
        monthly_resample = False

        security = load_saved_securities(random_security, start_date)
        self.current_main_security = security

        plotter = CorrelationPlotter()

        plotter.plot_security_correlations(
            main_security=security,
            start_date=start_date,
            num_traces=num_traces,
            display_plot=False,
            show_detrended=show_detrended,
            etf=etf,
            stock=stock,
            index=index,
            monthly=monthly_resample
        )

        filepath = self.data_dir / f'Graphs/json_plots/{security.symbol}_plot.json'
        with open(filepath, 'r') as file:
            fig_data = json.load(file)
        return go.Figure(fig_data)

    def get_available_securities(self) -> List[str]:
        secs = [file.split('.')[0] for file in os.listdir(self.data_dir / 'Graphs/pickled_securities_objects/') if
                file.endswith('.pkl')]
        print(secs)
        return secs

    def setup_layout(self, random_initial_load=True):

        self.app.layout = html.Div([

            html.Div([
                dcc.Dropdown(
                    id='security-dropdown',
                    options=[{'label': i, 'value': i} for i in self.available_securities],
                    placeholder='Pick from available',
                ),
                dbc.Input(id=self.SECURITIES_INPUT_ID, type='text', placeholder='Enter custom', debounce=True),
            ], style={'width': '50%', 'display': 'inline-block'}),

            dcc.Graph(
                id='security-plot',
                figure=self.initial_plot,
                style={'flexGrow': '1', 'min-height': '700px',},
                responsive=True,
            ),
            dcc.Interval(
                id='initial-load-interval',
                interval=100,  # in milliseconds
                max_intervals=1  # stop after the first interval
            ),

        ], )

    def setup_callbacks(self):

        @self.app.callback(
            Output('security-plot', 'figure'),
            [
                State('security-dropdown', 'value'),

            ])
        def update_graph(symbol: str) -> go.Figure:
            # Check if the symbol is in available securities
            if symbol in self.available_securities:

                security = load_saved_securities(symbol, '2010')
                plotter = CorrelationPlotter()

                # Load and plot the selected security, generates new plot based on all the parameters
                fig = plotter.plot_security_correlations(
                    main_security=security,
                )

                return fig
            else:
                print("Missing symbol")


    def run(self):
        self.app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8050)))


# Usage
dashboard = SecurityDashboard(DATA_DIR)
dashboard.setup_callbacks()
dashboard.run()
