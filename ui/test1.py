import os
from random import choice
from typing import List, Optional

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Output, State, Input

from config import DATA_DIR
from scripts.correlation_constants import Security
from scripts import load_saved_securities, read_series_data
from scripts.plotting_functions import CorrelationPlotter


class SecurityDashboard:

    PLOT_ID = 'plot_id'
    LOAD_PLOT_BUTTON_ID = 'load-plot-button'

    SECURITIES_INPUT_ID = 'security_input'
    SECURITIES_DROPDOWN_ID = 'security-dropdown'

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.available_securities: List[str] = self.get_available_securities()
        self.main_security: Optional[Security] = load_saved_securities(choice(self.available_securities),
                                                                       False)
        self.plot = self.load_initial_plot()
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], assets_folder='ui/assets')
        self.setup_layout()

    def load_initial_plot(self):
        plotter = CorrelationPlotter()

        fig = plotter.plot_security_correlations(
            main_security=self.main_security,
            start_date='2010',
            num_traces=2,
            display_plot=False,

            etf=True,
            stock=True,
            index=True,

            show_detrended=False,
            monthly=False,
            otc_filter=False,
        )

        return fig

    def get_available_securities(self) -> List[str]:
        secs = [file.split('.')[0] for file in os.listdir(self.data_dir / 'Graphs/pickled_securities_objects/') if
                file.endswith('.pkl')]
        print(secs)
        return secs

    def setup_layout(self, random_initial_load=True):

        self.app.layout = html.Div([

            html.Div(id='insert-counter', children='0', style={'display': 'none'}),


            html.Div([
                dcc.Dropdown(
                    id='security-dropdown',
                    options=[{'label': i, 'value': i} for i in self.available_securities],
                    placeholder='Pick from available',
                ),
                dbc.Input(id=self.SECURITIES_INPUT_ID, type='text', placeholder='Enter new...', debounce=True,
                          n_submit=0,
                          style={
                              'width': '9rem',
                          }),

                dcc.Graph(
                    id=self.PLOT_ID,
                    figure=self.plot,
                    style={'flexGrow': '1', 'min-height': '700px', },
                    responsive=True,
                ),
                dcc.Interval(
                    id='initial-load-interval',
                    interval=100,  # in milliseconds
                    max_intervals=1  # stop after the first interval
                ),

            ],
            )
        ],)

    def setup_callbacks(self):

        @self.app.callback(
            Output(self.PLOT_ID, 'figure'),
            [
                Input(self.SECURITIES_INPUT_ID, 'n_submit'),
                Input('insert-counter', 'children'),
                State(self.SECURITIES_INPUT_ID, 'value'),
            ],
        )
        def update_graph(n_submit, n_insert, symbol: str) -> go.Figure:
            # Check if the symbol is in available securities

            ctx = dash.callback_context

            print(ctx.triggered[0]['prop_id'])

            if ctx.triggered[0]['prop_id'] == f'{self.SECURITIES_INPUT_ID}.n_submit':
                print("Cond 1")
                return self.plot
            elif ctx.triggered[0]['prop_id'] == 'insert-counter.children':
                plot = self.plot
                security = load_saved_securities(symbol, False)
                name = security.name
                name = CorrelationPlotter.wrap_text(name, 50)
                trace_series = read_series_data(security.symbol, 'yahoo')
                plot.add_trace(go.Scatter(x=trace_series.index, y=trace_series, mode='lines',
                                          name=f'{security.correlation:.3}  {symbol} - {name}'), row=1, col=1)
                print("Cond 2")

                return plot

            if symbol in self.available_securities:

                security = load_saved_securities(symbol, False)
                plotter = CorrelationPlotter()

                # Load and plot the selected security, generates new plot based on all the parameters
                fig = plotter.plot_security_correlations(
                    main_security=security,
                )

                print('Condition 3')

                return fig
            else:
                print('Else')
                return self.plot

    def run(self):
        self.app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


# Usage
dashboard = SecurityDashboard(DATA_DIR)
dashboard.setup_callbacks()
dashboard.run()
