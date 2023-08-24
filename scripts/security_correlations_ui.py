import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import os
import json

from config import DATA_DIR
from main import load_securities_correlations_and_plot


class SecurityDashboard:

    SECURITY_DROPDOWN_ID = 'security-dropdown'
    SOURCE_CHECKBOXES_ID = 'source-checkboxes'
    DETREND_SWITCH_ID = 'detrend-switch'
    MONTHLY_SWITCH_ID = 'monthly-switch'
    LOAD_PLOT_BUTTON_ID = 'load-plot-button'

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.available_securities = self.get_available_securities()
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()

    def get_available_securities(self):
        return [file.split('_')[0] for file in os.listdir(self.data_dir / 'Graphs/json_plots/') if
                file.endswith('.json')]

    def setup_layout(self):
        self.app.layout = html.Div([
            dcc.Dropdown(
                id=self.SECURITY_DROPDOWN_ID,
                options=[{'label': security, 'value': security} for security in self.available_securities],
                value=self.available_securities[0]
            ),
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
            html.Button('Load and Plot', id=self.LOAD_PLOT_BUTTON_ID),  # Add this button
            dcc.Graph(id='security-plot')
        ])

    def setup_callbacks(self):
        @self.app.callback(
            Output('security-plot', 'figure'),
            [
                Input(self.LOAD_PLOT_BUTTON_ID, 'n_clicks'),
                State(self.SECURITY_DROPDOWN_ID, 'value'),
                State(self.SOURCE_CHECKBOXES_ID, 'value'),
                State(self.DETREND_SWITCH_ID, 'value'),
                State(self.MONTHLY_SWITCH_ID, 'value')
            ]
        )
        def update_graph(n_clicks, security, sources, detrend, monthly):
            if n_clicks is None:
                raise dash.exceptions.PreventUpdate

            etf = 'etf' in sources
            stock = 'stock' in sources
            index = 'index' in sources
            show_detrended = 'detrend' in detrend
            monthly_resample = 'monthly' in monthly

            # Load and plot the selected security
            load_securities_correlations_and_plot(
                symbol=security,
                start_date='2010-01-01',
                num_traces=2,
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

