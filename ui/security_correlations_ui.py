import os
from random import choice
from typing import List, Optional

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Input, Output, State

from config import DATA_DIR
from config import PROJECT_ROOT
from main import compute_security_correlations_and_plot
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

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.available_securities: List[str] = self.get_available_securities()
        self.fred_series: List[str] = self.get_all_fred_series()
        self.available_start_dates = ['2010', '2018', '2021', '2022', '2023']
        self.current_main_security: Security = load_saved_securities(choice(self.available_securities))
        self.current_start_date: str = choice(self.available_start_dates)
        self.current_num_traces: int = 2
        self.initial_plot = self.load_initial_plot()  # Load initial plot
        self.app = dash.Dash(__name__, external_scripts=[PROJECT_ROOT / 'ui/custom_script.js'],
                             external_stylesheets=self.external_stylesheets, assets_folder='assets')
        self.app.scripts.config.serve_locally = True
        self.setup_layout()
        self.setup_callbacks()

    def load_initial_plot(self):
        # if not self.available_securities:
        #     return 'No plots initialized'
        random_symbol = choice(self.available_securities)
        start_date = self.current_start_date
        num_traces = self.current_num_traces

        etf = True
        stock = True
        index = True

        show_detrended = False
        monthly_resample = False
        otc_filter = False

        security = load_saved_securities(random_symbol)
        self.current_main_security = security
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

    def get_available_securities(self) -> List[str]:
        return [file.split('.')[0] for file in os.listdir(self.data_dir / 'Graphs/pickled_securities_objects/') if
                file.endswith('.pkl')]

    def get_all_fred_series(self) -> List[str]:
        with open(self.data_dir / 'FRED/FRED_original_series.txt', 'r') as file:
            base_series_ids = [line.strip() for line in file]

        return base_series_ids

    def setup_layout(self):
        main_security = self.current_main_security
        start_date = self.current_start_date
        num_traces = self.current_num_traces

        all_sectors = main_security.get_unique_values('sector', start_date, num_traces)
        all_industry_groups = main_security.get_unique_values('industry_group', start_date, num_traces)
        all_industries = main_security.get_unique_values('industry', start_date, num_traces)
        all_countries = main_security.get_unique_values('country', start_date, num_traces)
        all_states = main_security.get_unique_values('state', start_date, num_traces)
        all_market_caps = main_security.get_unique_values('market_cap', start_date, num_traces)

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
            'margin': '1em'
        }

        button_style = {
            'background-color': '#002A50',  # Change the background color
            'color': 'white',              # Change the text color
            'border': 'none',              # Remove the border
            'outline': 'none',             # Remove the outline
            'padding': '0.5em 1em',        # Add padding
            'font-size': '16px',           # Change the font size
            'cursor': 'pointer',            # Change cursor to indicate interactivity
            'margin': '0'
        }

        dropdown_div_style = {'margin': '0.5em 3rem'}

        div_style = {'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center', 'margin': '0.5em 4em'}
        div_style2 = {'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center', 'margin': '0.5em 0.1em'}

        self.app.layout = html.Div([

            html.Div([
                html.Div([
                    dbc.Input(id=self.SECURITIES_INPUT_ID, type='text', placeholder='Enter new...', debounce=True,
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
                            options=[{'label': '', 'value': 'exclude_otc'}],
                            value=[],
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
                        value='2010',
                        style={
                            'width': '8rem',
                        }
                    ),
                ], style=dropdown_div_style),

                # Input for how many traces to display
                dcc.Input(  # Add this input field for num_traces
                    id=self.NUM_TRACES_ID,
                    type='number',
                    value=2,  # Default value
                    style={
                        'width': '4rem',
                    },
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
                ], style=div_style),
                ], style=div_style,
            ),


            # Checklist to include ETFs, Stocks, and/or Indices
            html.Div([
                html.Button('ETF', id=self.SOURCE_ETF_ID, n_clicks=0, style=sources_button_style),
                html.Button('Stock', id=self.SOURCE_STOCK_ID, n_clicks=1, style=sources_button_style),
                html.Button('Index', id=self.SOURCE_INDEX_ID, n_clicks=0, style=sources_button_style),
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
                            options=[{'label': sector, 'value': sector} for sector in all_sectors],
                            value=all_sectors,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    # Add Industry Group Filter
                    html.Div([
                        html.Label('Industry Group Filter'),
                        dcc.Dropdown(
                            id=self.INDUSTRY_GROUP_FILTER_ID,
                            options=[{'label': group, 'value': group} for group in all_industry_groups],
                            value=all_industry_groups,
                            multi=True,  # allow multiple selection
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    html.Div([
                        html.Label('Industry Filter'),
                        dcc.Dropdown(
                            id=self.INDUSTRY_FILTER_ID,
                            options=[{'label': industry, 'value': industry} for industry in all_industries],
                            value=all_industries,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    html.Div([
                        html.Label('Country Filter'),
                        dcc.Dropdown(
                            id=self.COUNTRY_FILTER_ID,
                            options=[{'label': country, 'value': country} for country in all_countries],
                            value=all_countries,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    html.Div([
                        html.Label('State Filter'),
                        dcc.Dropdown(
                            id=self.STATE_FILTER_ID,
                            options=[{'label': state, 'value': state} for state in all_states],
                            value=all_states,
                            multi=True,
                            style=multi_dropdown_style,
                        ),
                    ], style=multi_dropdown_div_style),
                    html.Div([
                        html.Label('Market Cap Filter'),
                        dcc.Dropdown(
                            id=self.MARKET_CAP_FILTER_ID,
                            options=[{'label': market_cap, 'value': market_cap} for market_cap in
                                     all_market_caps],
                            value=all_market_caps,
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
                        id='security-plot',
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

    def setup_callbacks(self):
        @self.app.callback(
            [
                Output(self.SECURITIES_DROPDOWN_ID, 'options'),
            ],
            [
                Input(self.FRED_SWITCH_ID, 'value'),
            ]
        )
        def update_dropdown_values(fred_switch_value: List[str]):
            is_fred_selected = 'exclude_otc' in fred_switch_value

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
        def update_button_styles(etf_clicks, stock_clicks, index_clicks):
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
            Output('security-plot', 'figure'),
            [
                Input(self.LOAD_PLOT_BUTTON_ID, 'n_clicks'),

                State(self.SECURITIES_INPUT_ID, 'value'),
                Input(self.SECURITIES_DROPDOWN_ID, 'value'),

                Input(self.START_DATE_ID, 'value'),
                Input(self.NUM_TRACES_ID, 'value'),

                Input(self.SOURCE_ETF_ID, 'n_clicks'),
                Input(self.SOURCE_STOCK_ID, 'n_clicks'),
                Input(self.SOURCE_INDEX_ID, 'n_clicks'),

                State(self.DETREND_SWITCH_ID, 'value'),
                State(self.MONTHLY_SWITCH_ID, 'value'),
                State(self.OTC_FILTER_ID, 'value'),

                State(self.SECTOR_FILTER_ID, 'value'),
                State(self.INDUSTRY_GROUP_FILTER_ID, 'value'),
                State(self.INDUSTRY_FILTER_ID, 'value'),
                State(self.COUNTRY_FILTER_ID, 'value'),
                State(self.STATE_FILTER_ID, 'value'),
                State(self.MARKET_CAP_FILTER_ID, 'value'),
            ]
        )
        def update_graph(n_clicks: int, input_symbol: Optional[str] = None, symbol: Optional[str] = None,
                         start_date: str = '2010', num_traces: int = 2,
                         etf_clicks: int = 1, stock_clicks: int = 1, index_clicks: int = 0,
                         detrend: Optional[list] = None, monthly: Optional[list] = None, otc_filter: bool = False,
                         sector: List[str] = None, industry_group: List[str] = None, industry: List[str] = None,
                         country: List[str] = None, state: List[str] = None, market_cap: List[str] = None) -> go.Figure:

            self.current_num_traces = num_traces
            self.current_start_date = start_date

            symbol = symbol.upper()

            etf = etf_clicks % 2 == 1
            stock = stock_clicks % 2 == 1
            index = index_clicks % 2 == 1

            ctx = dash.callback_context

            # Skip the update if no relevant trigger has occurred
            if not ctx.triggered or (
                    n_clicks is None
                    and (
                            ctx.triggered_id != self.SECURITIES_DROPDOWN_ID
                            and ctx.triggered_id != self.NUM_TRACES_ID
                            and ctx.triggered_id != self.START_DATE_ID
                            and ctx.triggered_id != self.SOURCE_ETF_ID
                            and ctx.triggered_id != self.SOURCE_STOCK_ID
                            and ctx.triggered_id != self.SOURCE_INDEX_ID
                    )
                    and ctx.triggered_id != 'initial-load-interval.n_intervals'
            ):
                raise dash.exceptions.PreventUpdate

            # Add default values if None
            detrend = detrend or []
            monthly = monthly or []

            show_detrended = 'detrend' in detrend
            monthly_resample = 'monthly' in monthly

            if input_symbol:
                # Call compute_security_correlations_and_plot if symbol is not in available securities
                fig_list = compute_security_correlations_and_plot(
                    symbol_list=[symbol],
                    start_date=start_date,
                    end_date='2023-06-02',
                    num_traces=num_traces,

                    source='yahoo',
                    dl_data=False,
                    display_plot=False,
                    use_ch=False,
                    use_multiprocessing=False,

                    etf=etf,
                    stock=stock,
                    index=index,

                    show_detrended=show_detrended,
                    monthly_resample=monthly_resample,
                    otc_filter=otc_filter,
                    sector=sector,
                    industry_group=industry_group,
                    industry=industry,
                    country=country,
                    state=state,
                    market_cap=market_cap,
                )
                self.current_main_security = load_saved_securities(symbol)
                return fig_list[0]

            self.current_main_security = load_saved_securities(symbol)
            plotter = CorrelationPlotter()

            # Load and plot the selected security, generates new plots based on all the parameters
            fig = plotter.plot_security_correlations(
                main_security=self.current_main_security,
                start_date=start_date,
                num_traces=num_traces,
                display_plot=False,

                etf=etf,
                stock=stock,
                index=index,

                show_detrended=show_detrended,
                monthly=monthly_resample,
                otc_filter=otc_filter,

                sector=sector,
                industry_group=industry_group,
                industry=industry,
                country=country,
                state=state,
                market_cap=market_cap,
            )

            return fig

    def run(self):
        self.app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


# Usage
dashboard = SecurityDashboard(DATA_DIR)
dashboard.run()
