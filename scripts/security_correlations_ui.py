import json
import os
from random import choice
from typing import List, Optional

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Input, Output, State

from config import DATA_DIR
from scripts.correlation_constants import Security
from scripts.file_reading_funcs import load_saved_securities
from scripts.plotting_functions import CorrelationPlotter


class SecurityDashboard:

    external_stylesheets = [
        {
            'href': 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600&display=swap',
            'rel': 'stylesheet',
        },
        dbc.themes.BOOTSTRAP
    ]

    SECURITY_DROPDOWN_ID = 'security-dropdown'
    NUM_TRACES_ID = 'num_traces_id'
    SOURCE_CHECKBOXES_ID = 'source-checkboxes'
    DETREND_SWITCH_ID = 'detrend-switch'
    MONTHLY_SWITCH_ID = 'monthly-switch'
    LOAD_PLOT_BUTTON_ID = 'load-plot-button'

    SECTOR_FILTER_ID = 'sector-filter'
    INDUSTRY_GROUP_FILTER_ID = 'industry-group-filter'
    INDUSTRY_FILTER_ID = 'industry-filter'
    COUNTRY_FILTER_ID = 'country-filter'
    STATE_FILTER_ID = 'state-filter'
    MARKET_CAP_FILTER_ID = 'market-cap-filter'
    OTC_FILTER_ID = 'otc-filter'

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.available_securities: List[str] = self.get_available_securities()
        self.initial_plot = self.load_initial_plot()  # Load initial plot
        self.current_main_security: Optional[Security] = load_saved_securities(choice(self.available_securities))
        self.app = dash.Dash(__name__, external_stylesheets=self.external_stylesheets, assets_folder='assets')
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

        security = load_saved_securities(random_security)
        self.current_main_security = security

        plotter = CorrelationPlotter()

        plotter.plot_security_correlations(
            main_security=security,
            start_date='2010-01-01',
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
        return [file.split('.')[0] for file in os.listdir(self.data_dir / 'Graphs/pickled_securities_objects/') if
                file.endswith('.pkl')]

    def setup_layout(self, random_initial_load=True):
        random_security = choice(self.available_securities) if random_initial_load else self.available_securities[0]
        all_possible_sectors = self.current_main_security.get_unique_values('sector')
        all_possible_industry_groups = self.current_main_security.get_unique_values('industry_group')
        all_possible_industries = self.current_main_security.get_unique_values('industry')
        all_possible_countries = self.current_main_security.get_unique_values('country')
        all_possible_states = self.current_main_security.get_unique_values('state')
        all_possible_market_caps = self.current_main_security.get_unique_values('market_cap')

        sources_div_style = {
            'display': 'flex',
            'background-color': '#003364',
            'color': 'white',
            'border': 'none',
            'padding': '0px',
            'font-size': '16px',
            'cursor': 'pointer',
        }

        sources_button_style={
            'display': 'flex',
            'background-color': '#003364',
            'color': 'white',
            'border': 'none',
            'padding': '10px 20px',
            'font-size': '16px',
            'cursor': 'pointer',
        }

        item_style = {'padding': '0 10px'}  # Adjust the value to control the horizontal spacing

        multi_dropdown_style = {
            'backgroundColor': '#171717',
            'color': '#fff',
            'border': '1px solid #333',
            'borderRadius': '5px',  # add border radius
            'padding': '10px',  # add padding
        }

        button_style = {
            'background-color': '#002A50',  # Change the background color
            'color': 'white',              # Change the text color
            'border': 'none',              # Remove the border
            'padding': '10px 20px',        # Add padding
            'font-size': '16px',           # Change the font size
            'cursor': 'pointer',            # Change cursor to indicate interactivity
        }

        self.app.layout = html.Div([
            # Dropdown selection for which Security to display
            dcc.Dropdown(
                id=self.SECURITY_DROPDOWN_ID,
                options=[{'label': security, 'value': security} for security in self.available_securities],
                value=random_security,  # Use the random security here
            ),
            # Input for how many traces to display
            dcc.Input(  # Add this input field for num_traces
                id=self.NUM_TRACES_ID,
                type='number',
                value=2,  # Default value
                style={'width': '42px'},
            ),

            # Checklist to include ETFs, Stocks, and/or Indices
            html.Div([
                html.Button('ETF', id='etf-button', n_clicks=1, style=sources_button_style),
                html.Button('Stock', id='stock-button', n_clicks=1, style=sources_button_style),
                html.Button('Index', id='index-button', n_clicks=0, style=sources_button_style),
            ], style=sources_div_style),

            html.Button(  # Button for toggling filters
                "Toggle Filters",
                id="collapse-button",
                className="mb-3",
                style=button_style,
            ),
            dbc.Collapse(
                [
                    # Add Sector Filter
                    html.Div([
                        html.Label('Sector Filter'),
                        dcc.Dropdown(
                            id=self.SECTOR_FILTER_ID,
                            options=[{'label': sector, 'value': sector} for sector in all_possible_sectors],
                            value=all_possible_sectors,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ]),
                    # Add Industry Group Filter
                    html.Div([
                        html.Label('Industry Group Filter'),
                        dcc.Dropdown(
                            id=self.INDUSTRY_GROUP_FILTER_ID,
                            options=[{'label': group, 'value': group} for group in all_possible_industry_groups],
                            value=all_possible_industry_groups,
                            multi=True,  # allow multiple selection
                            style=multi_dropdown_style,
                        ),
                    ]),
                    html.Div([
                        html.Label('Industry Filter'),
                        dcc.Dropdown(
                            id=self.INDUSTRY_FILTER_ID,
                            options=[{'label': industry, 'value': industry} for industry in all_possible_industries],
                            value=all_possible_industries,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ]),
                    html.Div([
                        html.Label('Country Filter'),
                        dcc.Dropdown(
                            id=self.COUNTRY_FILTER_ID,
                            options=[{'label': country, 'value': country} for country in all_possible_countries],
                            value=all_possible_countries,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ]),
                    html.Div([
                        html.Label('State Filter'),
                        dcc.Dropdown(
                            id=self.STATE_FILTER_ID,
                            options=[{'label': state, 'value': state} for state in all_possible_states],
                            value=all_possible_states,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ]),
                    html.Div([
                        html.Label('Market Cap Filter'),
                        dcc.Dropdown(
                            id=self.MARKET_CAP_FILTER_ID,
                            options=[{'label': market_cap, 'value': market_cap} for market_cap in
                                     all_possible_market_caps],
                            value=all_possible_market_caps,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ]),
                ],
                id="collapse",
            ),

            html.Div([
                dcc.Checklist(
                    id=self.OTC_FILTER_ID,
                    options=[{'label': '', 'value': 'exclude_otc'}],
                    value=[],
                    inline=True,
                    className='custom-switch',
                    style=item_style,  # Apply item_style to the element
                    labelStyle={'display': 'flex', 'alignItems': 'center'},  # vertically align the label
                ),
                html.Label('Exclude OTC'),
                dcc.Checklist(
                    id=self.DETREND_SWITCH_ID,
                    options=[{'label': '', 'value': 'detrend'}],
                    inline=True,
                    className='custom-switch',
                    style=item_style,
                    labelStyle={'display': 'flex', 'alignItems': 'center'},  # vertically align the label
                ),
                html.Label('Detrend'),
                dcc.Checklist(
                    id=self.MONTHLY_SWITCH_ID,
                    options=[{'label': '', 'value': 'monthly'}],
                    inline=True,
                    className='custom-switch',
                    style=item_style,
                    labelStyle={'display': 'flex', 'alignItems': 'center'},  # vertically align the label
                ),
                html.Label('Monthly Resample'),
            ], style={'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center', 'margin': '5px 0'}),


            # Button to load the plot
            html.Button(
                'Load and Plot',
                id=self.LOAD_PLOT_BUTTON_ID,
                style=button_style,

            ),  # Add this button
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
            'height': '100vh',
            'backgroundColor': '#1e1e2a',
            'color': '#e0e0e0',
            'display': 'flex',
            'flexDirection': 'column'
        })

    @staticmethod
    def toggle_collapse(n, is_open):
        if n is None:
            return is_open
        return not is_open

    def setup_callbacks(self):

        @self.app.callback(
            [
                Output('etf-button', 'style'),
                Output('stock-button', 'style'),
                Output('index-button', 'style'),
            ],
            [
                Input('etf-button', 'n_clicks'),
                Input('stock-button', 'n_clicks'),
                Input('index-button', 'n_clicks'),
            ],
        )
        def update_button_styles(etf_clicks, stock_clicks, index_clicks):
            selected_style = {'flex': 1, 'background-color': '#00498B', 'color': 'white'}
            not_selected_style = {'flex': 1, 'background-color': '#6B6B6B', 'color': 'white'}

            etf_style = selected_style if etf_clicks % 2 == 1 else not_selected_style
            stock_style = selected_style if stock_clicks % 2 == 1 else not_selected_style
            index_style = selected_style if index_clicks % 2 == 1 else not_selected_style

            return etf_style, stock_style, index_style

        # Collapse the filtering buttons when the "Toggle Filters" button is clicked
        @self.app.callback(
            Output("collapse", "is_open"),
            Input("collapse-button", "n_clicks"),
            State("collapse", "is_open"),
        )
        def toggle_collapse_callback(n, is_open):
            return self.toggle_collapse(n, is_open)

        # Update the graph when the "Load and Plot" button is clicked
        @self.app.callback(
            Output('security-plot', 'figure'),
            [
                Input(self.LOAD_PLOT_BUTTON_ID, 'n_clicks'),
                Input(self.SECURITY_DROPDOWN_ID, 'value'),
                State(self.NUM_TRACES_ID, 'value'),
                State('etf-button', 'n_clicks'),
                State('stock-button', 'n_clicks'),
                State('index-button', 'n_clicks'),
                State(self.DETREND_SWITCH_ID, 'value'),
                State(self.MONTHLY_SWITCH_ID, 'value'),

                State(self.SECTOR_FILTER_ID, 'value'),
                State(self.INDUSTRY_GROUP_FILTER_ID, 'value'),
                State(self.INDUSTRY_FILTER_ID, 'value'),
                State(self.COUNTRY_FILTER_ID, 'value'),
                State(self.STATE_FILTER_ID, 'value'),
                State(self.MARKET_CAP_FILTER_ID, 'value'),
                State(self.OTC_FILTER_ID, 'value'),
            ]
        )
        def update_graph(n_clicks: int, symbol: str, num_traces: int, etf_clicks, stock_clicks, index_clicks,
                         detrend: Optional[list], monthly: Optional[list], sector: List[str] = None,
                         industry_group: List[str] = None, industry: List[str] = None,
                         country: List[str] = None, state: List[str] = None,
                         market_cap: List[str] = None, otc_filter: bool = False) -> go.Figure:

            etf = etf_clicks % 2 == 1
            stock = stock_clicks % 2 == 1
            index = index_clicks % 2 == 1

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

            show_detrended = 'detrend' in detrend
            monthly_resample = 'monthly' in monthly

            security = load_saved_securities(symbol)
            plotter = CorrelationPlotter()

            # Load and plot the selected security
            plotter.plot_security_correlations(
                main_security=security,
                start_date='2010-01-01',
                num_traces=num_traces,
                display_plot=False,
                show_detrended=show_detrended,
                etf=etf,
                stock=stock,
                index=index,
                monthly=monthly_resample,
                sector=sector,
                industry_group=industry_group,
                industry=industry,
                country=country,
                state=state,
                market_cap=market_cap,
                otc_filter=otc_filter,
            )

            # Load the plot JSON from the saved file
            filepath = self.data_dir / f'Graphs/json_plots/{security.symbol}_plot.json'
            with open(filepath, 'r') as file:
                fig_data = json.load(file)
            fig = go.Figure(fig_data)

            return fig

    def run(self):
        self.app.run_server(debug=True, host='0.0.0.0', port=8080)


# Usage
dashboard = SecurityDashboard(DATA_DIR)
dashboard.run()
