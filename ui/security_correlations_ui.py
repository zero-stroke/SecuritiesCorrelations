import os
from random import choice
from typing import List, Optional, Set

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State

from config import DATA_DIR
from config import PROJECT_ROOT
from main import compute_security_correlations_and_plot
from scripts.correlation_constants import Security, SharedMemoryCache
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

    LOAD_PLOT_BUTTON_ID = 'load-plot-button'

    SECURITIES_DROPDOWN_ID = 'security-dropdown'
    FRED_SWITCH_ID = 'fred_switch'
    SECURITIES_INPUT_ID = 'security_dropdown'

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

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.cache = SharedMemoryCache()
        self.available_securities: Set[str] = self.get_available_securities()
        if not self.available_securities:
            compute_security_correlations_and_plot(cache=self.cache, symbol_list=['GME'])
        self.fred_series: List[str] = self.get_all_fred_series()
        self.available_start_dates = ['2010', '2018', '2021', '2022', '2023']
        self.main_security: Security = load_saved_securities('GME')

        self.input_symbol = self.main_security.symbol
        self.dropdown_symbol = self.main_security.symbol

        self.use_fred = []

        self.etf: bool = True
        self.stock: bool = True
        self.index: bool = True

        self.start_date = '2023'
        self.num_traces = 2

        self.show_detrended = []
        self.monthly_resample = []
        self.otc_filter = []

        self.displayed_positive_correlations: Set[Security] = set()
        self.displayed_negative_correlations: Set[Security] = set()

        self.sectors = self.main_security.get_unique_values('sector', self.start_date, self.num_traces)
        self.industry_groups = self.main_security.get_unique_values('industry_group', self.start_date, self.num_traces)
        self.industries = self.main_security.get_unique_values('industry', self.start_date, self.num_traces)
        self.countries = self.main_security.get_unique_values('country', self.start_date, self.num_traces)
        self.states = self.main_security.get_unique_values('state', self.start_date, self.num_traces)
        self.market_caps = self.main_security.get_unique_values('market_cap', self.start_date, self.num_traces)

        self.initial_plot = self.load_initial_plot()  # Load initial plot
        self.app = dash.Dash(__name__, external_scripts=[PROJECT_ROOT / 'ui/custom_script.js'],
                             external_stylesheets=self.external_stylesheets, assets_folder='assets')
        self.app.scripts.config.serve_locally = True

        self.setup_layout()
        self.setup_callbacks()

    def pick_random_security(self):
        random_security = None
        while random_security is not Security:
            random_security = load_saved_securities(choice(list(self.available_securities)))
            print(random_security)
        return random_security

    def load_initial_plot(self):
        # if not self.available_securities:
        #     return 'No plots initialized'
        start_date = self.start_date
        num_traces = self.num_traces

        etf = True
        stock = True
        index = True

        show_detrended = False
        monthly_resample = False
        otc_filter = False

        security = self.main_security
        plotter = CorrelationPlotter()

        fig = plotter.plot_security_correlations(
            main_security=security,
            start_date=start_date,
            num_traces=num_traces,
            display_plot=False,

            etf=etf,
            stock=stock,
            index=index,

            show_detrended=show_detrended,
            monthly=monthly_resample,
            otc_filter=otc_filter,
        )

        return fig

    def get_available_securities(self) -> Set[str]:
        return {file.split('.')[0] for file in os.listdir(self.data_dir / 'Graphs/pickled_securities_objects/') if
                file.endswith('.pkl')}

    def get_all_fred_series(self) -> List[str]:
        with open(self.data_dir / 'FRED/FRED_original_series.txt', 'r') as file:
            base_series_ids = [line.strip() for line in file]

        return base_series_ids

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

        dropdown_div_style = {'margin': '0.5em 3rem'}

        div_style = {'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center', 'margin': '0.5em 4em'}
        div_style2 = {'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center',
                      'margin': '0.5em 0.1em'}

        self.app.layout = html.Div([

            html.Div([
                html.Div([
                    dbc.Input(id=self.SECURITIES_INPUT_ID, type='text', placeholder='Enter new...', debounce=True,
                              n_submit=0,
                              style={
                                  'width': '9rem',
                              }),
                    html.Div([
                        dcc.Dropdown(
                            id=self.SECURITIES_DROPDOWN_ID,
                            options=[{'label': security, 'value': security} for security in self.available_securities],
                            value=main_security.symbol,  # Use the random security here
                            style={
                                'width': '9rem',
                            },
                        ),
                        #  Dropdown selection for which Security to display
                        dcc.Checklist(
                            id=self.FRED_SWITCH_ID,
                            options=[{'label': '', 'value': 'use_fred'}],
                            value=self.use_fred,
                            inline=True,
                            className='custom-switch',
                            style=item_style,  # Apply item_style to the element
                            labelStyle={'display': 'flex', 'alignItems': 'center'},  # vertically align the label
                        ),
                        html.Label('FRED'),
                    ], style=div_style2)

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
                ], style=div_style),
            ], style=div_style,
            ),

            # Checklist to include ETFs, Stocks, and/or Indices
            html.Div([
                html.Button('ETF', id=self.SOURCE_ETF_ID, n_clicks=1, style=sources_button_style),
                html.Button('Stock', id=self.SOURCE_STOCK_ID, n_clicks=1, style=sources_button_style),
                html.Button('Index', id=self.SOURCE_INDEX_ID, n_clicks=1, style=sources_button_style),
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
                'Load and Plot',
                id=self.LOAD_PLOT_BUTTON_ID,
                style=button_style,
            ),

            html.Div([
                dcc.Loading(
                    id="loading",
                    children=[dcc.Graph(
                        id=self.PLOT_ID,
                        figure=self.initial_plot,
                        style={'height': '75vh'},  # adjust this value as needed
                        responsive=True,
                    )],
                    type="circle",
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
                Output(self.SECURITIES_DROPDOWN_ID, 'options'),
            ],
            [
                Input(self.FRED_SWITCH_ID, 'value'),
            ]
        )
        def update_dropdown_values(use_fred: List[str]):
            is_fred_selected = 'use_fred' in use_fred

            options = [{'label': security, 'value': security} for security in self.available_securities] if \
                not is_fred_selected else [{'label': series, 'value': series} for series in self.fred_series]

            return [options]

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
                State(self.SECURITIES_INPUT_ID, 'value'),

                Input(self.SECURITIES_DROPDOWN_ID, 'value'),

                State(self.FRED_SWITCH_ID, 'value'),

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
                         input_symbol: Optional[str] = self.input_symbol,
                         dropdown_symbol: Optional[str] = self.dropdown_symbol,
                         use_fred=None,
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
            if use_fred is None:
                use_fred = self.use_fred
            print('\n')

            if self.dropdown_symbol != dropdown_symbol:
                print(f"self.dropdown_symbol: {self.dropdown_symbol} != dropdown_symbol: {dropdown_symbol}")

            if self.use_fred != use_fred:
                print(f"self.use_fred: {self.use_fred} != use_fred: {use_fred}")

            if start_date != self.start_date:
                print(f"start_date: {start_date} != self.start_date: {self.start_date}")

            if num_traces != self.num_traces:
                print(f"num_traces: {num_traces} != self.num_traces: {self.num_traces}")

            if (etf_clicks % 2 == 1) != self.etf:
                print(f"etf_clicks: {(etf_clicks % 2 == 1)} != self.etf: {self.etf}")

            if (stock_clicks % 2 == 1) != self.stock:
                print(f"stock_clicks: {(stock_clicks % 2 == 1)} != self.stock: {self.stock}")

            if (index_clicks % 2 == 1) != self.index:
                print(f"index_clicks: {(index_clicks % 2 == 1)} != self.index: {self.index}")

            if detrend_plot != self.show_detrended:
                print(f"detrend: {detrend_plot} != self.show_detrended: {self.show_detrended}")

            if monthly != self.monthly_resample:
                print(f"monthly: {monthly} != self.monthly_resample: {self.monthly_resample}")

            if self.otc_filter != otc_filter:
                print(f"self.otc_filter: {self.otc_filter} != otc_filter: {otc_filter}")

            if self.dropdown_symbol != dropdown_symbol or self.use_fred \
                    != use_fred or start_date != self.start_date or num_traces != self.num_traces or \
                    (etf_clicks % 2 == 1) != self.etf or (stock_clicks % 2 == 1) != self.stock or \
                    (index_clicks % 2 == 1) != self.index or detrend_plot != \
                    self.show_detrended or monthly != self.monthly_resample or self.otc_filter != otc_filter:
                no_changes_have_been_made = False
            else:
                no_changes_have_been_made = True

            self.input_symbol = input_symbol
            self.dropdown_symbol = dropdown_symbol

            self.use_fred = use_fred  #

            self.start_date = start_date
            self.num_traces = num_traces

            self.etf = etf_clicks % 2 == 1
            self.stock = stock_clicks % 2 == 1
            self.index = index_clicks % 2 == 1

            ctx = dash.callback_context

            # Skip the update if no relevant trigger has occurred
            if not ctx.triggered or (
                    n_clicks is None
                    and (
                            ctx.triggered_id != self.SECURITIES_DROPDOWN_ID
                            and ctx.triggered_id != self.NUM_TRACES_ID
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
                raise dash.exceptions.PreventUpdate

            self.show_detrended = detrend_plot  #
            self.monthly_resample = monthly  #

            self.otc_filter = otc_filter  #

            # Is the current plot simply being modified or should a whole new plot be loaded
            loading_new_security = False if dropdown_symbol == self.main_security.symbol else True

            # Does plot need to be computed from scratch
            recompute_plot = False
            if input_symbol or (use_fred and dropdown_symbol not in self.available_securities) or \
                    (n_clicks is not None and no_changes_have_been_made) \
                    or len(self.main_security.positive_correlations[start_date]) == 0:
                recompute_plot = True

            # New dropdown security's pkl file exists, but selected year is not yet created
            security_exists_but_year_doesnt = False
            if not recompute_plot and loading_new_security and dropdown_symbol in self.available_securities:
                test_security = load_saved_securities(dropdown_symbol)
                if len(test_security.positive_correlations[self.start_date]) == 0:
                    security_exists_but_year_doesnt = True

            if recompute_plot or security_exists_but_year_doesnt:
                print('Load')
                print(len(self.main_security.positive_correlations[start_date]))
                for key, value in self.main_security.positive_correlations.items():
                    print(key, value[:2])
                # Five Cases where we need to recompute
                # Pressing "Load and Plot" with no other buttons to recalculate a plot
                # Manually inputting a symbol to plot
                # Selecting a FRED plot from dropdown that hasn't been loaded yet
                # Selecting a year that hasn't been calculated yet
                param_symbol = input_symbol if input_symbol else dropdown_symbol

                fig_list = compute_security_correlations_and_plot(
                    cache=self.cache,
                    old_security=self.main_security,

                    symbol_list=[param_symbol],
                    use_fred=self.use_fred,
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
                self.main_security = load_saved_securities(param_symbol)

                # Once self.main_security is updated, then we can call update_filter_options
                update_filter_options()
                if not use_fred and param_symbol not in self.available_securities:
                    self.available_securities.add(param_symbol)

                return fig_list[0], '', param_symbol, \
                       [{'label': sector, 'value': sector} for sector in self.sectors], \
                       [{'label': group, 'value': group} for group in self.industry_groups], \
                       [{'label': industry, 'value': industry} for industry in self.industries], \
                       [{'label': country, 'value': country} for country in self.countries], \
                       [{'label': state, 'value': state} for state in self.states], \
                       [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                       self.sectors, self.industry_groups, self.industries, \
                       self.countries, self.states, self.market_caps

            print(f'{dropdown_symbol} != {self.main_security.symbol} is {loading_new_security}')
            plotter = CorrelationPlotter()
            self.main_security = load_saved_securities(dropdown_symbol)

            if loading_new_security:
                print('Loading new plot, dropdown:', dropdown_symbol, 'self.main.symbol: ',
                      self.main_security.symbol)
                # If loading a new security from disk, make filter options and values set to the new security's options
                update_filter_options()
                fig = plotter.plot_security_correlations(
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

                    sector=self.sectors,
                    industry_group=self.industry_groups,
                    industry=self.industries,
                    country=self.countries,
                    state=self.states,
                    market_cap=self.market_caps,
                )

            else:  # Not loading a new security
                print('Keeping current plot, dropdown:', dropdown_symbol, 'self.main.symbol:',
                      self.main_security.symbol)
                # Update the filter options based on new num_traces
                update_displayed_correlations(self.start_date, self.num_traces, self.etf, self.stock, self.index,
                                              self.sectors, self.industry_groups, self.industries,
                                              self.countries, self.states, self.market_caps, self.otc_filter)
                update_filter_options()
                # Modify current plot
                fig = plotter.plot_security_correlations(
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
                )

            # Return the fig to be displayed, tha blank value for the input box, and the value for the dropdown
            return fig, '', dropdown_symbol, \
                   [{'label': sector, 'value': sector} for sector in self.sectors], \
                   [{'label': group, 'value': group} for group in self.industry_groups], \
                   [{'label': industry, 'value': industry} for industry in self.industries], \
                   [{'label': country, 'value': country} for country in self.countries], \
                   [{'label': state, 'value': state} for state in self.states], \
                   [{'label': market_cap, 'value': market_cap} for market_cap in self.market_caps], \
                   self.sectors, self.industry_groups, self.industries, \
                   self.countries, self.states, self.market_caps

        def get_unique_values(attribute_name: str) -> Set[str]:
            """Returns a list of a correlation_list's unique values for a given attribute"""
            unique_values = set()

            # Get values from positive_correlations
            unique_values.update(getattr(security, attribute_name) for security in
                                 self.displayed_positive_correlations if getattr(security, attribute_name))

            # Get values from negative_correlations
            unique_values.update(getattr(security, attribute_name) for security in
                                 self.displayed_negative_correlations if getattr(security, attribute_name))

            return unique_values

        def update_filter_options():
            self.sectors = get_unique_values('sector')
            self.industry_groups = get_unique_values('industry_group')
            self.industries = get_unique_values('industry')
            self.countries = get_unique_values('country')
            self.states = get_unique_values('state')
            self.market_caps = get_unique_values('market_cap')

        def update_displayed_correlations(start_date, num_traces: int,
                                          etf: bool, stock: bool,
                                          index: bool, sector: List[str],
                                          industry_group: List[str], industry: List[str],
                                          country: List[str], state: List[str],
                                          market_cap: List[str], otc_filter: bool):
            """Updates the displayed correlation sets"""
            correlation_list = [self.main_security.positive_correlations, self.main_security.negative_correlations]
            displayed_correlation_list = [self.displayed_positive_correlations, self.displayed_negative_correlations]

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

                    if security.source == 'stock':
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

                        if otc_filter and 'OTC ' in security.market:  # If otc_filter and market contains 'OTC ' in it, skip
                            continue

                    displayed_set.add(security)

                    added_count += 1

    def run(self):
        self.app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


if __name__ == '__main__':
    dashboard = SecurityDashboard(DATA_DIR)
    dashboard.run()
