import copy
import os
from typing import List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Input, Output, State

from batch_calculate import compute_security_correlations_and_plot
from config import DATA_DIR, FRED_DIR, start_years
from scripts.calculate_correlations import get_correlation_for_series
from scripts.correlation_constants import Security, SharedMemoryCache
from scripts.file_reading_funcs import load_saved_securities, read_series_data, original_get_validated_security_data, \
    fit_data_to_time_range
from scripts.plotting_functions import CorrelationPlotter, save_plot


def get_all_fred_api_series_ids() -> List[str]:
    with open(FRED_DIR / 'FRED_all_series.txt', 'r') as f:
        fred_api_symbols = [symbol.strip() for symbol in f.readlines()]

    return fred_api_symbols


def get_all_fredmd_series_ids() -> List[str]:
    fred_md_metadata = pd.read_csv(FRED_DIR / 'fred_md_metadata.csv')

    return fred_md_metadata[fred_md_metadata['fred_md_id'].notna()]['fred_md_id'].tolist()


class SecurityDashboard:
    external_scripts = [
        # 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML',
        # 'ui/custom_script.js'
    ]
    external_stylesheets = [
        {
            'href': 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600&display=swap',
            'rel': 'stylesheet',
        },
        dbc.themes.BOOTSTRAP
    ]

    LOAD_PLOT_BUTTON_ID = 'load-plot-button'

    SECURITIES_INPUT_ID = 'security_input'
    SECURITIES_DROPDOWN_ID = 'security-dropdown'

    DROPDOWN_RADIO_ID = 'dropdown_radio'

    ADD_TRACE_ID = 'add_trace'

    START_DATE_ID = 'start_date_dropdown'
    NUM_TRACES_ID = 'num_traces_id'

    SOURCE_ETF_ID = 'source_etf'
    SOURCE_STOCK_ID = 'source_stock'
    SOURCE_INDEX_ID = 'source_index'

    DETREND_SWITCH_ID = 'detrend-switch'
    MONTHLY_SWITCH_ID = 'monthly-switch'
    OTC_FILTER_ID = 'otc-filter'

    # Metadata Filters
    SECTOR_FILTER_ID = 'sector-filter'
    INDUSTRY_GROUP_FILTER_ID = 'industry-group-filter'
    INDUSTRY_FILTER_ID = 'industry-filter'
    COUNTRY_FILTER_ID = 'country-filter'
    STATE_FILTER_ID = 'state-filter'
    MARKET_CAP_FILTER_ID = 'market-cap-filter'

    PLOT_ID = 'security_plot'
    LATEX_ID = 'latex_equation'

    SECURITIES_SOURCE = 'SECURITIES'
    FREDMD_SOURCE = 'FREDMD'
    FREDAPI_SOURCE = 'FREDAPI'
    FREDAPIOG_SOURCE = 'FREDAPIOG'

    def __init__(self, data_dir):
        self.DEBUG: bool = True
        self.data_dir = data_dir
        self.cache = SharedMemoryCache()
        self.plotter = CorrelationPlotter()

        # Tracks which have already been calculated
        self.all_available_securities: List[str] = self.get_all_available_securities()

        self.available_securities: List[str] = self.get_available_securities()  # Doesn't include FRED series

        self.fredmd_metrics: List[str] = get_all_fredmd_series_ids()
        self.fred_api_metrics: List[str] = get_all_fred_api_series_ids()
        self.fred_api_unrevised_metrics: List[str] = get_all_fred_api_series_ids()

        if not self.available_securities:  # If there is nothing saved to disk
            compute_security_correlations_and_plot(cache=self.cache, symbol_list=['GME'])
        self.available_start_dates: List[str] = start_years

        self.dropdown_source = self.SECURITIES_SOURCE

        self.main_security: Security = load_saved_securities('GME', self.dropdown_source)

        self.input_symbol: str = self.main_security.symbol
        self.dropdown_symbol: str = self.main_security.symbol
        self.dropdown_options: List[str] = self.available_securities
        self.latex_equation: str = ''

        self.add_trace = []

        self.etf: bool = True
        self.stock: bool = True
        self.index: bool = True

        self.start_date = '2023'
        self.num_traces = 2

        self.show_detrended: list = []
        self.monthly_resample: list = []
        self.otc_filter: list = []

        self.displayed_positively_correlated: List[Security] = []
        self.displayed_negatively_correlated: List[Security] = []

        self.sectors: List[str] = self.main_security.get_unique_values('sector', self.start_date)
        self.industry_groups = self.main_security.get_unique_values('industry_group', self.start_date)
        self.industries = self.main_security.get_unique_values('industry', self.start_date)
        self.countries = self.main_security.get_unique_values('country', self.start_date)
        self.states = self.main_security.get_unique_values('state', self.start_date)
        self.market_caps = self.main_security.get_unique_values('market_cap', self.start_date)

        self.plot = self.load_initial_plot()  # Load initial plot
        self.detrended_plot = None
        self.monthly_plot = None
        self.app = dash.Dash(__name__, external_scripts=self.external_scripts,
                             external_stylesheets=self.external_stylesheets, assets_folder='ui/assets')
        self.app.scripts.config.serve_locally = True

        self.setup_layout()
        self.setup_callbacks()

    def load_initial_plot(self):
        fig = self.plotter.plot_security_correlations(
            main_security=self.main_security,
            start_date=self.start_date,
            num_traces=self.num_traces,
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
        return [file.split('.')[0] for file in os.listdir(self.data_dir / 'Graphs/pickled_securities_objects/') if
                file.endswith('.pkl') and not (file.endswith('_fred.pkl') or file.endswith('_fredapi.pkl') or
                                               file.endswith('_fredapi_og.pkl'))]

    def get_all_available_securities(self) -> List[str]:
        return [file.split('.')[0] for file in os.listdir(self.data_dir / 'Graphs/pickled_securities_objects/') if
                file.endswith('.pkl')]

    def setup_layout(self):
        main_security = self.main_security

        sources_div_style = {
            'display': 'flex',
            'background-color': '#003364',
            'color': 'white',
            'border': 'none',
            'padding': '0px',
            'font-size': '16px',
            'cursor': 'pointer',
        }

        sources_button_style = {
            'display': 'flex',
            'background-color': '#003364',
            'color': 'white',
            'border': 'none',
            'padding': '10px 20px',
            'font-size': '16px',
            'cursor': 'pointer',
        }

        item_style = {
            'padding': '0 10px',
            'margin': '0 0.5em',
        }  # Adjust the value to control the horizontal spacing

        switch_style = {
            'padding': '0',
            'margin': '0',
        }  # Adjust the value to control the horizontal spacing

        multi_dropdown_style = {
            'backgroundColor': '#171717',
            'color': '#fff',
            'border': 'none',
            'borderRadius': '5px',  # add border radius
            'padding': '0.2em',  # add padding
            'outline': 'none',
        }

        multi_dropdown_div_style = {
            'margin': '0.3em 1em'
        }

        button_style = {
            'background-color': '#002A50',  # Change the background color
            'color': 'white',  # Change the text color
            'border': 'none',  # Remove the border
            'outline': 'none',  # Remove the outline
            'padding': '0.5em 1em',  # Add padding
            'font-size': '16px',  # Change the font size
            'cursor': 'pointer',  # Change cursor to indicate interactivity
            'margin': '0'
        }

        dropdown_div_style = {'margin': '0.5em 2rem 0.5rem 0.1em'}

        div_style_tri_switch = {'display': 'flex', 'justifyContent': 'flex-start',
                                'alignItems': 'center', 'margin': '0.5em 4em'}
        div_style_input = {'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center',
                           'margin': '0.5em 0.1em'}
        div_style_switch = {
            'display': 'flex',
            'flexDirection': 'column',  # Set to 'column' for vertical alignment
            'justifyContent': 'flex-start',  # Align items vertically to the top
            'alignItems': 'center',
            'margin': '0.5em 0.1em'
        }

        dropdown_container_style = {
            'width': '11rem',
            'margin': '0 1em 0 0'
        }

        self.app.layout = html.Div([

            html.Div([
                html.Div([
                    html.Div([
                        html.Div([
                            dbc.Input(id=self.SECURITIES_INPUT_ID, type='text', placeholder='Enter new...',
                                      debounce=True,
                                      n_submit=0,
                                      style={
                                          'width': '11em',
                                      }),
                        ], style=dropdown_container_style),
                        html.Div([
                            html.Label('Add trace', style={'fontSize': '0.8em', 'padding': '0.1em'}),
                            dcc.Checklist(
                                id=self.ADD_TRACE_ID,
                                options=[{'label': '', 'value': 'add_trace'}],
                                value=self.add_trace,
                                inline=True,
                                className='custom-switch',
                                style=switch_style,  # Apply item_style to the element
                                labelStyle={'display': 'flex', 'alignItems': 'center'},  # vertically align the label
                            ),
                        ], style=div_style_switch),
                    ], style=div_style_input),
                    html.Div([
                        html.Div([
                            dcc.Dropdown(
                                id=self.SECURITIES_DROPDOWN_ID,
                                options=[{'label': security, 'value': security} for security in
                                         self.available_securities],
                                value=main_security.symbol,  # Use the random security here
                                style={'width': '11em'},
                            ),
                        ], style=dropdown_container_style),
                        #  Changes dropdown options from being regular stocks to being fred-md series
                        html.Div([
                            dcc.RadioItems(
                                id=self.DROPDOWN_RADIO_ID,
                                options=[
                                    {'label': ' Securities', 'value': self.SECURITIES_SOURCE},
                                    {'label': ' FRED-MD', 'value': self.FREDMD_SOURCE},
                                    {'label': ' FRED API', 'value': self.FREDAPI_SOURCE},
                                    {'label': ' FRED API Unrevised', 'value': self.FREDAPIOG_SOURCE},
                                ],
                                value=self.SECURITIES_SOURCE,  # default value
                                labelStyle={'display': 'block', 'margin': '0 0.2em'},
                                style={'fontSize': '0.8em', 'padding': '0.1em'}
                            )
                        ], style=div_style_switch)
                    ], style=div_style_input)

                ], style=dropdown_div_style),

                html.Div([
                    # Input for the start date
                    dcc.Dropdown(
                        id=self.START_DATE_ID,
                        options=[{'label': start_date, 'value': start_date} for
                                 start_date in self.available_start_dates],
                        value=self.start_date,
                        style={
                            'width': '8rem',
                        }
                    ),
                ], style=dropdown_div_style),

                # Input for how many traces to display
                dcc.Input(  # Add this input field for num_traces
                    id=self.NUM_TRACES_ID,
                    type='number',
                    value=self.num_traces,  # Default value
                    style={
                        'width': '4rem',
                    },
                ),

                html.Div([
                    dcc.Checklist(
                        id=self.OTC_FILTER_ID,
                        options=[{'label': '', 'value': 'exclude_otc'}],
                        value=self.otc_filter,
                        inline=True,
                        className='custom-switch',
                        style=item_style,  # Apply item_style to the element
                        labelStyle={'display': 'flex', 'alignItems': 'center'},  # vertically align the label
                    ),
                    html.Label('Exclude OTC'),
                    dcc.Checklist(
                        id=self.DETREND_SWITCH_ID,
                        options=[{'label': '', 'value': 'detrend'}],
                        value=self.show_detrended,
                        inline=True,
                        className='custom-switch',
                        style=item_style,
                        labelStyle={'display': 'flex', 'alignItems': 'center'},  # vertically align the label
                    ),
                    html.Label('Detrend'),
                    dcc.Checklist(
                        id=self.MONTHLY_SWITCH_ID,
                        options=[{'label': '', 'value': 'monthly'}],
                        value=self.monthly_resample,
                        inline=True,
                        className='custom-switch',
                        style=item_style,
                        labelStyle={'display': 'flex', 'alignItems': 'center'},  # vertically align the label
                    ),
                    html.Label('Monthly Resample'),
                ], style=div_style_tri_switch),
            ], style=div_style_tri_switch,
            ),

            # Checklist to include ETFs, Stocks, and/or Indices
            html.Div([
                html.Button('ETF', id=self.SOURCE_ETF_ID, n_clicks=1, style=sources_button_style),
                html.Button('Stock', id=self.SOURCE_STOCK_ID, n_clicks=1, style=sources_button_style),
                html.Button('Index', id=self.SOURCE_INDEX_ID, n_clicks=1, style=sources_button_style),
            ], style=sources_div_style),

            html.Button(  # Button for toggling filters
                "Toggle Stock Filters",
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
                            options=[{'label': sector, 'value': sector} for sector in self.sectors],
                            value=self.sectors,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    # Add Industry Group Filter
                    html.Div([
                        html.Label('Industry Group Filter'),
                        dcc.Dropdown(
                            id=self.INDUSTRY_GROUP_FILTER_ID,
                            options=[{'label': group, 'value': group} for group in self.industry_groups],
                            value=self.industry_groups,
                            multi=True,  # allow multiple selection
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    html.Div([
                        html.Label('Industry Filter'),
                        dcc.Dropdown(
                            id=self.INDUSTRY_FILTER_ID,
                            options=[{'label': industry, 'value': industry} for industry in self.industries],
                            value=self.industries,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    html.Div([
                        html.Label('Country Filter'),
                        dcc.Dropdown(
                            id=self.COUNTRY_FILTER_ID,
                            options=[{'label': country, 'value': country} for country in self.countries],
                            value=self.countries,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    html.Div([
                        html.Label('State Filter'),
                        dcc.Dropdown(
                            id=self.STATE_FILTER_ID,
                            options=[{'label': state, 'value': state} for state in self.states],
                            value=self.states,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    html.Div([
                        html.Label('Market Cap Filter'),
                        dcc.Dropdown(
                            id=self.MARKET_CAP_FILTER_ID,
                            options=[{'label': market_cap, 'value': market_cap} for market_cap in
                                     self.market_caps],
                            value=self.market_caps,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                ],
                id="collapse",
            ),

            # Button to load the plot
            html.Button(
                'Reload',
                id=self.LOAD_PLOT_BUTTON_ID,
                style=button_style,
            ),

            html.Div([
                dcc.Loading(
                    id="loading",
                    children=[dcc.Graph(
                        id=self.PLOT_ID,
                        figure=self.plot,
                        style={'height': '60vh'},  # adjust this value depending on screen's resolution, 70 for 1440p
                        responsive=True,
                    )],
                    type="circle",
                ),
                dcc.Markdown(
                    id=self.LATEX_ID,
                    children='',
                    style={
                        'position': 'absolute',
                        'bottom': '9.5em',
                        'right': '4.5em',
                        'backgroundColor': 'transparent',  # Make background transparent
                        'padding': '5px',
                        'borderRadius': '5px'
                    },
                    mathjax=True
                )
            ], style={'display': 'flex', 'flexDirection': 'column', 'height': '100%'}),

            dcc.Interval(
                id='initial-load-interval',
                interval=100,  # in milliseconds
                max_intervals=1,  # stop after the first interval
            ),

        ], style={
            'font-family': 'Open Sans, sans-serif',
            'max-height': '100vh',
            'height': '100vh',
            'backgroundColor': '#1e1e2a',
            'color': '#e0e0e0',
            'display': 'flex',
            'flexDirection': 'column',
        })

    @staticmethod
    def toggle_collapse(n, is_open):
        if n is None:
            return is_open
        return not is_open

    # Switch the dropdown values between Securities and FRED macroeconomic indicators
    def setup_callbacks(self):

        @self.app.callback(
            [
                Output(self.SOURCE_ETF_ID, 'style'),
                Output(self.SOURCE_STOCK_ID, 'style'),
                Output(self.SOURCE_INDEX_ID, 'style'),
            ],
            [
                Input(self.SOURCE_ETF_ID, 'n_clicks'),
                Input(self.SOURCE_STOCK_ID, 'n_clicks'),
                Input(self.SOURCE_INDEX_ID, 'n_clicks'),
            ],
        )
        def update_button_styles(etf_clicks, stock_clicks, index_clicks):  # Makes STOCK ETF INDEX buttons change color
            selected_style = {'flex': 1, 'background-color': '#00498B', 'color': 'white'}
            not_selected_style = {'flex': 1, 'background-color': '#1e1e2a', 'color': 'white'}

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
            [
                Output(self.PLOT_ID, 'figure'),
                Output(self.SECURITIES_INPUT_ID, 'value'),
                Output(self.SECURITIES_DROPDOWN_ID, 'value'),
                Output(self.SECURITIES_DROPDOWN_ID, 'options'),
                Output(self.LATEX_ID, 'children'),

                Output(self.SOURCE_ETF_ID, 'n_clicks'),
                Output(self.SOURCE_STOCK_ID, 'n_clicks'),
                Output(self.SOURCE_INDEX_ID, 'n_clicks'),

                Output(self.SECTOR_FILTER_ID, 'options'),
                Output(self.INDUSTRY_GROUP_FILTER_ID, 'options'),
                Output(self.INDUSTRY_FILTER_ID, 'options'),
                Output(self.COUNTRY_FILTER_ID, 'options'),
                Output(self.STATE_FILTER_ID, 'options'),
                Output(self.MARKET_CAP_FILTER_ID, 'options'),

                Output(self.SECTOR_FILTER_ID, 'value'),
                Output(self.INDUSTRY_GROUP_FILTER_ID, 'value'),
                Output(self.INDUSTRY_FILTER_ID, 'value'),
                Output(self.COUNTRY_FILTER_ID, 'value'),
                Output(self.STATE_FILTER_ID, 'value'),
                Output(self.MARKET_CAP_FILTER_ID, 'value'),
            ],
            [
                Input(self.LOAD_PLOT_BUTTON_ID, 'n_clicks'),

                Input(self.SECURITIES_INPUT_ID, 'n_submit'),
                Input(self.ADD_TRACE_ID, 'value'),
                State(self.SECURITIES_INPUT_ID, 'value'),

                Input(self.SECURITIES_DROPDOWN_ID, 'value'),
                Input(self.DROPDOWN_RADIO_ID, 'value'),  #

                Input(self.START_DATE_ID, 'value'),
                Input(self.NUM_TRACES_ID, 'value'),

                Input(self.SOURCE_ETF_ID, 'n_clicks'),
                Input(self.SOURCE_STOCK_ID, 'n_clicks'),
                Input(self.SOURCE_INDEX_ID, 'n_clicks'),

                Input(self.DETREND_SWITCH_ID, 'value'),
                Input(self.MONTHLY_SWITCH_ID, 'value'),
                Input(self.OTC_FILTER_ID, 'value'),

                Input(self.SECTOR_FILTER_ID, 'value'),
                Input(self.INDUSTRY_GROUP_FILTER_ID, 'value'),
                Input(self.INDUSTRY_FILTER_ID, 'value'),
                Input(self.COUNTRY_FILTER_ID, 'value'),
                Input(self.STATE_FILTER_ID, 'value'),
                Input(self.MARKET_CAP_FILTER_ID, 'value'),
            ],
        )
        def update_graph(n_clicks: int,
                         n_submit: int,
                         add_trace=None,
                         input_symbol: Optional[str] = self.input_symbol,
                         dropdown_symbol: Optional[str] = self.dropdown_symbol,
                         dropdown_source=None,
                         start_date: str = self.start_date, num_traces: int = self.num_traces,
                         etf_clicks: int = self.etf, stock_clicks: int = self.stock, index_clicks: int = self.index,
                         detrend_plot=None,
                         monthly=None,
                         otc_filter=None,
                         selected_sectors=None,
                         selected_industry_groups=None,
                         selected_industries=None,
                         selected_countries=None,
                         selected_states=None,
                         selected_market_caps=None):
            if selected_market_caps is None:
                selected_market_caps = self.market_caps
            if selected_states is None:
                selected_states = self.states
            if selected_countries is None:
                selected_countries = self.countries
            if selected_industries is None:
                selected_industries = self.industries
            if selected_industry_groups is None:
                selected_industry_groups = self.industry_groups
            if selected_sectors is None:
                selected_sectors = self.sectors
            if otc_filter is None:
                otc_filter = self.otc_filter
            if monthly is None:
                monthly = self.monthly_resample
            if detrend_plot is None:
                detrend_plot = self.show_detrended
            if dropdown_source is None:
                dropdown_source = self.dropdown_source
            if add_trace is None:
                add_trace = self.add_trace
            print(n_submit, '\n')

            ctx = dash.callback_context

            if self.DEBUG:
                check_changes(dropdown_symbol, dropdown_source, add_trace, start_date, num_traces, etf_clicks,
                          stock_clicks, index_clicks, detrend_plot, monthly, otc_filter)

            self.input_symbol = input_symbol
            self.dropdown_symbol = dropdown_symbol

            self.dropdown_source = dropdown_source  #

            self.start_date = start_date
            self.num_traces = num_traces

            self.etf = etf_clicks % 2 == 1
            self.stock = stock_clicks % 2 == 1
            self.index = index_clicks % 2 == 1

            self.show_detrended = detrend_plot  #
            self.monthly_resample = monthly  #

            self.otc_filter = otc_filter  #

            if ctx.triggered_id == self.DROPDOWN_RADIO_ID:
                print('dropdown triggered')
                if self.dropdown_source == self.SECURITIES_SOURCE:
                    self.dropdown_options = [{'label': security, 'value': security} for security in
                                             self.available_securities]
                elif self.dropdown_source == self.FREDMD_SOURCE:
                    self.dropdown_options = [{'label': security, 'value': security} for security in
                                             self.fredmd_metrics]
                elif self.dropdown_source == self.FREDAPI_SOURCE:
                    self.dropdown_options = [{'label': security, 'value': security} for security in
                                             self.fred_api_metrics]
                elif self.dropdown_source == self.FREDAPIOG_SOURCE:
                    self.dropdown_options = [{'label': security, 'value': security} for security in
                                             self.fred_api_unrevised_metrics]

                self.etf = True
                self.stock = True
                self.index = True

                return self.plot, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                    [{'label': sector, 'value': sector} for sector in self.sectors], \
                    [{'label': group, 'value': group} for group in self.industry_groups], \
                    [{'label': industry, 'value': industry} for industry in self.industries], \
                    [{'label': country, 'value': country} for country in self.countries], \
                    [{'label': state, 'value': state} for state in self.states], \
                    [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                    self.sectors, self.industry_groups, self.industries, \
                    self.countries, self.states, self.market_caps

            # Skip the update if no relevant trigger has occurred
            if not ctx.triggered or (
                    n_clicks is None
                    and (
                            ctx.triggered_id != self.SECURITIES_DROPDOWN_ID
                            and ctx.triggered_id != self.SECURITIES_INPUT_ID
                            and ctx.triggered_id != self.START_DATE_ID
                            and ctx.triggered_id != self.NUM_TRACES_ID

                            and ctx.triggered_id != self.SOURCE_ETF_ID
                            and ctx.triggered_id != self.SOURCE_STOCK_ID
                            and ctx.triggered_id != self.SOURCE_INDEX_ID

                            and ctx.triggered_id != self.DETREND_SWITCH_ID
                            and ctx.triggered_id != self.MONTHLY_SWITCH_ID
                            and ctx.triggered_id != self.OTC_FILTER_ID

                            and ctx.triggered_id != self.SECTOR_FILTER_ID
                            and ctx.triggered_id != self.INDUSTRY_GROUP_FILTER_ID
                            and ctx.triggered_id != self.INDUSTRY_FILTER_ID
                            and ctx.triggered_id != self.COUNTRY_FILTER_ID
                            and ctx.triggered_id != self.STATE_FILTER_ID
                            and ctx.triggered_id != self.MARKET_CAP_FILTER_ID
                    )
                    and ctx.triggered_id != 'initial-load-interval.n_intervals'
            ):
                # Return the same state that it was already in
                return self.plot, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                       [{'label': sector, 'value': sector} for sector in self.sectors], \
                       [{'label': group, 'value': group} for group in self.industry_groups], \
                       [{'label': industry, 'value': industry} for industry in self.industries], \
                       [{'label': country, 'value': country} for country in self.countries], \
                       [{'label': state, 'value': state} for state in self.states], \
                       [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                       self.sectors, self.industry_groups, self.industries, \
                       self.countries, self.states, self.market_caps

            # Is the current plot simply being modified or should a whole new plot be loaded
            loading_new_plot = False if dropdown_symbol == self.main_security.symbol else True

            # Does plot need to be computed from scratch
            recompute_plot = False
            if (dropdown_source == self.FREDMD_SOURCE and f"{dropdown_symbol}_fred" not in
                self.all_available_securities) or \
                    (dropdown_source == self.FREDAPI_SOURCE and f"{dropdown_symbol}_fredapi" not in
                     self.all_available_securities) or \
                    (dropdown_source == self.FREDAPIOG_SOURCE and f"{dropdown_symbol}_fredapi_og" not in
                     self.all_available_securities):
                print(dropdown_source, dropdown_symbol, self.all_available_securities)
                recompute_plot = True

            if input_symbol or (n_clicks is not None and ctx.triggered_id == self.LOAD_PLOT_BUTTON_ID) \
                    or len(self.main_security.positive_correlations[start_date]) == 0:  # Can remove and use ctx id
                print(dropdown_source, dropdown_symbol, self.all_available_securities, "n_clicks: ", n_clicks)
                recompute_plot = True

            # New dropdown security's pkl file exists, but selected year is not yet created
            security_exists_but_year_doesnt = False
            if not recompute_plot and loading_new_plot and dropdown_symbol in self.all_available_securities:
                test_security = load_saved_securities(dropdown_symbol, self.dropdown_source)
                if len(test_security.positive_correlations[self.start_date]) == 0:
                    security_exists_but_year_doesnt = True

                    print(len(test_security.positive_correlations[start_date]))
                    for key, value in test_security.positive_correlations.items():
                        print(key, value[:2])

            if input_symbol and add_trace:  # Keeping plot, adding trace to it
                plot = self.plot
                security = Security(input_symbol)
                name = security.name
                name = CorrelationPlotter.wrap_text(name, 50)
                trace_series = read_series_data(security.symbol, 'yahoo')

                trace_series = fit_data_to_time_range(trace_series, start_date)
                trace_series = CorrelationPlotter.normalize_data(trace_series)

                if self.monthly_resample:
                    trace_series = trace_series.resample('MS').first()

                if self.show_detrended:
                    trace_series = trace_series.diff().dropna()

                trace_series_detrended = original_get_validated_security_data(input_symbol, self.start_date,
                                                                              '2023-06-02', 'yahoo', False, False)

                correlation = get_correlation_for_series(self.main_security.series_data_detrended[self.start_date],
                                                         trace_series_detrended)

                plot.add_trace(go.Scatter(x=trace_series.index, y=trace_series, mode='lines',
                                          name=f'{correlation:.3}  {input_symbol} - {name}'), row=1, col=1)
                plot.add_trace(go.Scatter(x=trace_series.index, y=trace_series, mode='lines',
                                          name=f'{correlation:.3}  {input_symbol} - {name}'), row=2, col=1)
                self.plot = plot

                save_plot(input_symbol, plot)

                return self.plot, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                    [{'label': sector, 'value': sector} for sector in self.sectors], \
                    [{'label': group, 'value': group} for group in self.industry_groups], \
                    [{'label': industry, 'value': industry} for industry in self.industries], \
                    [{'label': country, 'value': country} for country in self.countries], \
                    [{'label': state, 'value': state} for state in self.states], \
                    [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                    self.sectors, self.industry_groups, self.industries, \
                    self.countries, self.states, self.market_caps

            if ctx.triggered_id == self.DETREND_SWITCH_ID or ctx.triggered_id == self.MONTHLY_SWITCH_ID:
                fig = copy.deepcopy(self.plot)  # Keeping plot, detrending or resampling
                if monthly and detrend_plot:
                    for trace in fig.data:
                        y_series = pd.Series(trace.y)
                        detrended_y = y_series.diff().dropna().values

                        # Adjust the x-values to match the detrended y-values
                        trace.x = trace.x[1:]  # Drop the first x-value

                        # Update the y-data of the trace
                        trace.y = detrended_y
                    fig.update_traces()

                    for trace in fig.data:
                        x = pd.to_datetime(trace.x)
                        y = pd.Series(trace.y, index=x)

                        # Resample the y-data
                        resampled_y = y.resample('MS').first()

                        # Update the x and y data of the trace
                        trace.x = resampled_y.index
                        trace.y = resampled_y.values
                    fig.update_traces()

                    return fig, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                        [{'label': sector, 'value': sector} for sector in self.sectors], \
                        [{'label': group, 'value': group} for group in self.industry_groups], \
                        [{'label': industry, 'value': industry} for industry in self.industries], \
                        [{'label': country, 'value': country} for country in self.countries], \
                        [{'label': state, 'value': state} for state in self.states], \
                        [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                        self.sectors, self.industry_groups, self.industries, \
                        self.countries, self.states, self.market_caps

                elif detrend_plot:
                    for trace in fig.data:
                        y_series = pd.Series(trace.y)
                        detrended_y = y_series.diff().dropna().values

                        # Adjust the x-values to match the detrended y-values
                        trace.x = trace.x[1:]  # Drop the first x-value

                        # Update the y-data of the trace
                        trace.y = detrended_y
                    fig.update_traces()

                    return fig, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                        [{'label': sector, 'value': sector} for sector in self.sectors], \
                        [{'label': group, 'value': group} for group in self.industry_groups], \
                        [{'label': industry, 'value': industry} for industry in self.industries], \
                        [{'label': country, 'value': country} for country in self.countries], \
                        [{'label': state, 'value': state} for state in self.states], \
                        [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                        self.sectors, self.industry_groups, self.industries, \
                        self.countries, self.states, self.market_caps

                elif monthly:
                    # print("Truthy")
                    for trace in fig.data:
                        x = pd.to_datetime(trace.x)
                        y = pd.Series(trace.y, index=x)

                        # Resample the y-data
                        resampled_y = y.resample('MS').first()

                        # Update the x and y data of the trace
                        trace.x = resampled_y.index
                        trace.y = resampled_y.values
                    fig.update_traces()

                    return fig, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                        [{'label': sector, 'value': sector} for sector in self.sectors], \
                        [{'label': group, 'value': group} for group in self.industry_groups], \
                        [{'label': industry, 'value': industry} for industry in self.industries], \
                        [{'label': country, 'value': country} for country in self.countries], \
                        [{'label': state, 'value': state} for state in self.states], \
                        [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                        self.sectors, self.industry_groups, self.industries, \
                        self.countries, self.states, self.market_caps
                else:
                    return fig, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                           [{'label': sector, 'value': sector} for sector in self.sectors], \
                           [{'label': group, 'value': group} for group in self.industry_groups], \
                           [{'label': industry, 'value': industry} for industry in self.industries], \
                           [{'label': country, 'value': country} for country in self.countries], \
                           [{'label': state, 'value': state} for state in self.states], \
                           [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                           self.sectors, self.industry_groups, self.industries, \
                           self.countries, self.states, self.market_caps

            if recompute_plot or security_exists_but_year_doesnt:
                print('Load', recompute_plot, security_exists_but_year_doesnt)
                # 4 Cases where we recompute: 1. Pressing "Load and Plot" with no other buttons to recalculate a plot
                # 2. Manually input a symbol to plot 3. Selecting FRED plot from dropdown that hasn't been calculated
                # 4. Selecting a year that hasn't been calculated yet
                param_symbol = input_symbol if input_symbol else dropdown_symbol

                fig_list = compute_security_correlations_and_plot(
                    cache=self.cache,
                    old_security=self.main_security,

                    symbol_list=[param_symbol],
                    fred_source=self.dropdown_source,
                    start_date=start_date,
                    end_date='2023-06-02',
                    num_traces=num_traces,

                    source='yahoo',
                    dl_data=False,
                    display_plot=True,
                    use_ch=False,
                    use_multiprocessing=False,

                    etf=True,
                    stock=True,
                    index=True,

                    show_detrended=self.show_detrended,
                    monthly_resample=self.monthly_resample,
                    otc_filter=self.otc_filter,
                )
                self.main_security = load_saved_securities(param_symbol, self.dropdown_source)

                print(len(self.main_security.positive_correlations[start_date]))
                for key, value in self.main_security.positive_correlations.items():
                    print(key, value[:2])

                # Once self.main_security is updated, then we can call update_filter_options
                update_filter_options()
                if dropdown_source == self.SECURITIES_SOURCE and param_symbol not in self.available_securities:
                    self.available_securities.append(param_symbol)
                    self.all_available_securities.append(param_symbol)
                    self.dropdown_options = self.available_securities
                elif dropdown_source == self.FREDMD_SOURCE and param_symbol not in self.fredmd_metrics:
                    self.all_available_securities.append(f'{param_symbol}_fred')
                    self.dropdown_options = self.fredmd_metrics
                elif dropdown_source == self.FREDAPI_SOURCE and param_symbol not in self.fred_api_metrics:
                    self.all_available_securities.append(f'{param_symbol}_fredapi')
                    self.dropdown_options = self.fred_api_metrics
                elif dropdown_source == self.FREDAPIOG_SOURCE and param_symbol not in self.fred_api_unrevised_metrics:
                    self.all_available_securities.append(f'{param_symbol}_fredapi_og')
                    self.dropdown_options = self.fred_api_unrevised_metrics

                self.dropdown_symbol = param_symbol
                self.plot = fig_list[0]

                self.etf = True
                self.stock = True
                self.index = True

                if dropdown_source == self.FREDMD_SOURCE or dropdown_source == self.FREDAPI_SOURCE or \
                        dropdown_source == self.FREDAPIOG_SOURCE:
                    self.latex_equation = self.main_security.latex_equation
                else:
                    self.latex_equation = ''

                # Return newly calculated correlation and its plot
                return self.plot, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                    [{'label': sector, 'value': sector} for sector in self.sectors], \
                    [{'label': group, 'value': group} for group in self.industry_groups], \
                    [{'label': industry, 'value': industry} for industry in self.industries], \
                    [{'label': country, 'value': country} for country in self.countries], \
                    [{'label': state, 'value': state} for state in self.states], \
                    [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                    self.sectors, self.industry_groups, self.industries, \
                    self.countries, self.states, self.market_caps

            print(f'{dropdown_symbol} != {self.main_security.symbol} is {loading_new_plot}')
            self.main_security = load_saved_securities(dropdown_symbol, self.dropdown_source)

            if loading_new_plot:
                print('Loading new plot, dropdown:', dropdown_symbol, 'self.main.symbol: ',
                      self.main_security.symbol)
                # If loading a security from disk, make filter options and values set to the new security's options
                update_filter_options()
                fig = self.plotter.plot_security_correlations(
                    main_security=self.main_security,
                    start_date=self.start_date,
                    num_traces=self.num_traces,
                    display_plot=False,

                    etf=self.etf,
                    stock=self.stock,
                    index=self.index,

                    show_detrended=self.show_detrended,
                    monthly=self.monthly_resample,
                    otc_filter=self.otc_filter,
                )

                self.plot = fig

                self.etf = True
                self.stock = True
                self.index = True

                if dropdown_source == self.FREDMD_SOURCE or dropdown_source == self.FREDAPI_SOURCE or \
                        dropdown_source == self.FREDAPIOG_SOURCE:
                    self.latex_equation = self.main_security.latex_equation
                else:
                    self.latex_equation = ''

                # Return the fig to be displayed, tha blank value for the input box, and the value for the dropdown
                return self.plot, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, 1, 1, 1, \
                    [{'label': sector, 'value': sector} for sector in self.sectors], \
                    [{'label': group, 'value': group} for group in self.industry_groups], \
                    [{'label': industry, 'value': industry} for industry in self.industries], \
                    [{'label': country, 'value': country} for country in self.countries], \
                    [{'label': state, 'value': state} for state in self.states], \
                    [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                    self.sectors, self.industry_groups, self.industries, \
                    self.countries, self.states, self.market_caps

            else:  # Modifying current plot, Not loading a new plot
                print('Keeping current plot, dropdown:', dropdown_symbol, 'self.main.symbol:',
                      self.main_security.symbol)
                # Create a list of correlations to be displayed based on selected options
                filter_displayed_correlations(self.start_date, self.num_traces, self.etf, self.stock, self.index,
                                              selected_sectors, selected_industry_groups, self.industries,
                                              selected_countries, selected_states, selected_market_caps,
                                              self.otc_filter, ctx)
                # Update the filter options based on new num_traces
                if ctx.triggered_id == self.NUM_TRACES_ID or ctx.triggered_id == self.SOURCE_ETF_ID \
                        or ctx.triggered_id == self.SOURCE_STOCK_ID or ctx.triggered_id == self.SOURCE_INDEX_ID \
                        or ctx.triggered_id == self.START_DATE_ID:
                    print("UPDATING FILTER OPTIONS")
                    update_filter_options()
                    selected_sectors = self.sectors
                    selected_industry_groups = self.industry_groups
                    selected_industries = self.industries
                    selected_countries = self.countries
                    selected_states = self.states
                    selected_market_caps = self.market_caps

                # Modify current plot
                fig = self.plotter.plot_security_correlations(
                    main_security=self.main_security,
                    start_date=start_date,
                    num_traces=num_traces,
                    display_plot=False,

                    etf=self.etf,
                    stock=self.stock,
                    index=self.index,

                    show_detrended=self.show_detrended,
                    monthly=self.monthly_resample,
                    otc_filter=self.otc_filter,

                    sector=selected_sectors,
                    industry_group=selected_industry_groups,
                    industry=selected_industries,
                    country=selected_countries,
                    state=selected_states,
                    market_cap=selected_market_caps,

                    displayed_positive_correlations=self.displayed_positively_correlated,
                    displayed_negative_correlations=self.displayed_negatively_correlated,
                )

                self.plot = fig

                # Return the fig to be displayed, tha blank value for the input box, and the value for the dropdown
                return self.plot, '', self.dropdown_symbol, self.dropdown_options, self.latex_equation, \
                    etf_clicks, stock_clicks, index_clicks, \
                    [{'label': sector, 'value': sector} for sector in self.sectors], \
                    [{'label': group, 'value': group} for group in self.industry_groups], \
                    [{'label': industry, 'value': industry} for industry in self.industries], \
                    [{'label': country, 'value': country} for country in self.countries], \
                    [{'label': state, 'value': state} for state in self.states], \
                    [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                    selected_sectors, selected_industry_groups, selected_industries, \
                    selected_countries, selected_states, selected_market_caps

        def update_filter_options():
            self.sectors = self.main_security.get_unique_values('sector', self.start_date)

            print("\nSectors: \n", self.sectors)
            for security in self.displayed_positively_correlated:
                print(f'Symbol: {security.symbol}, Source: {security.source}, Sector: {security.sector}')

            print("Options for sector dropdown:\n", [{'label': sector, 'value': sector} for sector in self.sectors])

            self.industry_groups = self.main_security.get_unique_values('industry_group', self.start_date)
            self.industries = self.main_security.get_unique_values('industry', self.start_date)
            self.countries = self.main_security.get_unique_values('country', self.start_date)
            self.states = self.main_security.get_unique_values('state', self.start_date)
            self.market_caps = self.main_security.get_unique_values('market_cap', self.start_date)

        def filter_displayed_correlations(start_date, num_traces: int,
                                          etf: bool, stock: bool,
                                          index: bool, sector: List[str],
                                          industry_group: List[str], industry: List[str],
                                          country: List[str], state: List[str],
                                          market_cap: List[str], otc_filter: bool, ctx):
            """Updates the displayed correlation sets"""

            args_dict = locals().copy()
            args_dict.pop('self')  # Remove 'self' from the dictionary

            with open('ui/debug_file.txt', 'a') as f:
                f.write('\n')

            with open('ui/debug_file2.txt', 'a') as f:
                for key, value in args_dict.items():
                    f.write(f'{key}: {value}\n')

            self.displayed_positively_correlated.clear()
            self.displayed_negatively_correlated.clear()

            correlation_list = [self.main_security.positive_correlations, self.main_security.negative_correlations]
            displayed_correlation_list = [self.displayed_positively_correlated, self.displayed_negatively_correlated]

            for correlation_set, displayed_set in zip(correlation_list, displayed_correlation_list):
                added_count = 0
                for security in correlation_set[start_date]:
                    if added_count >= num_traces:
                        break

                    if security.source == 'etf' and not etf:
                        continue
                    elif security.source == 'stock' and not stock:
                        continue
                    elif security.source == 'index' and not index:
                        continue

                    if security.source == 'stock' and ctx.triggered_id != self.SOURCE_STOCK_ID and ctx.triggered_id != \
                            self.SOURCE_ETF_ID and ctx.triggered_id != self.SOURCE_INDEX_ID \
                            and ctx.triggered_id != self.START_DATE_ID and ctx.triggered_id != \
                            self.SECURITIES_DROPDOWN_ID \
                            and ctx.triggered_id != self.NUM_TRACES_ID:
                        if sector is not None and security.sector not in sector:
                            continue
                        if industry_group is not None and security.industry_group not in industry_group:
                            continue
                        if industry is not None and security.industry not in industry:
                            continue
                        if country is not None and security.country not in country:
                            continue
                        if state is not None and security.state not in state:
                            continue
                        if market_cap is not None and security.market_cap not in market_cap:
                            continue

                        if otc_filter and 'OTC ' in security.market:  # If otc_filter and market contains 'OTC ' skip
                            continue

                    displayed_set.append(security)
                    print(security)

                    added_count += 1

        def check_changes(dropdown_symbol, dropdown_source, add_trace, start_date, num_traces, etf_clicks,
                          stock_clicks, index_clicks, detrend_plot, monthly, otc_filter):
            comparisons = [
                ('dropdown_symbol', self.dropdown_symbol, dropdown_symbol),
                ('dropdown_source', self.dropdown_source, dropdown_source),
                ('add_trace', self.add_trace, add_trace),
                ('start_date', self.start_date, start_date),
                ('num_traces', self.num_traces, num_traces),
                ('etf', self.etf, etf_clicks % 2 == 1),
                ('stock', self.stock, stock_clicks % 2 == 1),
                ('index', self.index, index_clicks % 2 == 1),
                ('show_detrended', self.show_detrended, detrend_plot),
                ('monthly_resample', self.monthly_resample, monthly),
                ('otc_filter', self.otc_filter, otc_filter)
            ]

            no_changes_have_been_made = True

            for name, self_val, val in comparisons:
                if self_val != val:
                    print(f"self.{name}: {self_val} != {name}: {val}")
                    no_changes_have_been_made = False

            return no_changes_have_been_made

    def run(self):
        self.app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


if __name__ == '__main__':
    dashboard = SecurityDashboard(DATA_DIR)
    dashboard.run()
