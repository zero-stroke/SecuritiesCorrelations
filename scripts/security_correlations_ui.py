from random import choice
from typing import List, Optional

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import os
import json

from config import DATA_DIR
from main import load_securities_correlations_and_plot


class SecurityDashboard:

    external_stylesheets = [
        {
            'href': 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600&display=swap',
            'rel': 'stylesheet',
        },
    ]

    SECURITY_DROPDOWN_ID = 'security-dropdown'
    NUM_TRACES_ID = 'num_traces_id'
    SOURCE_CHECKBOXES_ID = 'source-checkboxes'
    DETREND_SWITCH_ID = 'detrend-switch'
    MONTHLY_SWITCH_ID = 'monthly-switch'
    LOAD_PLOT_BUTTON_ID = 'load-plot-button'

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.available_securities = self.get_available_securities()
        self.initial_plot = self.load_initial_plot()  # Load initial plot
        self.app = dash.Dash(__name__, external_stylesheets=self.external_stylesheets)
        self.setup_layout()
        self.setup_callbacks()

    def load_initial_plot(self):
        random_security = choice(self.available_securities)
        num_traces = 2
        show_detrended = False
        etf = True
        stock = False
        index = False
        monthly_resample = False

        load_securities_correlations_and_plot(
            symbol=random_security,
            start_date='2010-01-01',
            num_traces=num_traces,
            display_plot=False,
            show_detrended=show_detrended,
            etf=etf,
            stock=stock,
            index=index,
            monthly=monthly_resample
        )

        with open(self.data_dir / f'Graphs/json_plots/{random_security}_plot.json', 'r') as file:
            fig_data = json.load(file)
        return go.Figure(fig_data)

    def get_available_securities(self) -> List[str]:
        return [file.split('_')[0] for file in os.listdir(self.data_dir / 'Graphs/json_plots/') if
                file.endswith('.json')]

    def setup_layout(self, random_initial_load=True):
        random_security = choice(self.available_securities) if random_initial_load else self.available_securities[0]
        self.app.layout = html.Div([
            # Dropdown selection for which Security to display
            dcc.Dropdown(
                id=self.SECURITY_DROPDOWN_ID,
                options=[{'label': security, 'value': security} for security in self.available_securities],
                value=random_security  # Use the random security here
            ),
            # Input for how many traces to display
            dcc.Input(  # Add this input field for num_traces
                id=self.NUM_TRACES_ID,
                type='number',
                value=2,  # Default value
                style={'width': '42px'},
            ),
            # Checklist to include ETFs, Stocks, and/or Indices
            dcc.Checklist(
                id=self.SOURCE_CHECKBOXES_ID,
                options=[
                    {'label': 'ETF', 'value': 'etf'},
                    {'label': 'Stock', 'value': 'stock'},
                    {'label': 'Index', 'value': 'index'}
                ],
                value=['stock'],   # default value
                inline=True
            ),
            html.Div([
                dcc.Checklist(
                    id=self.DETREND_SWITCH_ID,
                    options=[{'label': 'Detrend', 'value': 'detrend'}],
                    inline=True
                ),
                dcc.Checklist(
                    id=self.MONTHLY_SWITCH_ID,
                    options=[{'label': 'Monthly Resample', 'value': 'monthly'}],
                    inline=True
                )
            ]),
            # Button to load the plot
            html.Button('Load and Plot', id=self.LOAD_PLOT_BUTTON_ID),  # Add this button
            dcc.Graph(
                id='security-plot',
                figure=self.initial_plot,  # Use the preloaded figure
                style={'flexGrow': '1'}
            ),
            dcc.Interval(
                id='initial-load-interval',
                interval=100,  # in milliseconds
                max_intervals=1  # stop after the first interval
            ),
        ], style={
            'font-family': 'Open Sans, sans-serif',
            'height': '80vh',
            'backgroundColor': '#1e1e2a',
            'color': '#e0e0e0',
            'display': 'flex',
            'flexDirection': 'column'
        })

    def setup_callbacks(self):
        @self.app.callback(
            Output('security-plot', 'figure'),
            [
                Input(self.LOAD_PLOT_BUTTON_ID, 'n_clicks'),
                Input(self.SECURITY_DROPDOWN_ID, 'value'),
                State(self.NUM_TRACES_ID, 'value'),
                State(self.SOURCE_CHECKBOXES_ID, 'value'),
                State(self.DETREND_SWITCH_ID, 'value'),
                State(self.MONTHLY_SWITCH_ID, 'value')
            ]
        )
        def update_graph(n_clicks: int, security: str, num_traces: int, sources: list,
                         detrend: Optional[list], monthly: Optional[list]) -> go.Figure:
            ctx = dash.callback_context

            # Skip the update if no relevant trigger has occurred
            if not ctx.triggered or (
                    n_clicks is None
                    and ctx.triggered_id != self.SECURITY_DROPDOWN_ID
                    and ctx.triggered_id != 'initial-load-interval.n_intervals'
            ):
                raise dash.exceptions.PreventUpdate

            # Add default values if None
            detrend = detrend or []
            monthly = monthly or []

            etf = 'etf' in sources
            stock = 'stock' in sources
            index = 'index' in sources
            show_detrended = 'detrend' in detrend
            monthly_resample = 'monthly' in monthly

            # Load and plot the selected security
            load_securities_correlations_and_plot(
                symbol=security,
                start_date='2010-01-01',
                num_traces=num_traces,
                display_plot=False,
                show_detrended=show_detrended,
                etf=etf,
                stock=stock,
                index=index,
                monthly=monthly_resample
            )

            # Load the plot JSON from the saved file
            with open(self.data_dir / f'Graphs/json_plots/{security}_plot.json', 'r') as file:
                fig_data = json.load(file)
            fig = go.Figure(fig_data)

            return fig

    def run(self):
        self.app.run_server(debug=True, host='0.0.0.0', port=8080)


# Usage
dashboard = SecurityDashboard(DATA_DIR)
dashboard.run()

