import json
from collections import defaultdict

import dash
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output

from config import FRED_DIR, DATA_DIR
from scripts.file_reading_funcs import load_saved_securities, get_fredmd_series
from scripts.plotting_functions import CorrelationPlotter

# DEFINED CONSTANTS
#####################################################################################

dict_file_path = FRED_DIR / 'sorted_series_correlated_symbols.json'
DEBUG = False
start_date = '2010-08-02'

all_base_series = {}

if DEBUG:
    base_series_ids = ['RPI',
                       'RETAILx']
else:
    with open(FRED_DIR / 'FRED_original_series.txt', 'r') as file:
        base_series_ids = [line.strip() for line in file]

for series_id in base_series_ids:
    base_series = get_fredmd_series(series_id)
    all_base_series[series_id] = base_series

# FUNCTIONS
######################################################################################################################

misc_subgroups = [
    "U.S. Employment and Training Administration",
    "U.S. Energy Information Administration",
    "University of Michigan",
    "Moody's",
    "Chicago Board Options Exchange"
]

external_stylesheets = [
    {
        'href': 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600&display=swap',
        'rel': 'stylesheet',
    },
]


class AppRunner:
    def __init__(self, layout):
        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
        self.app.layout = layout

    def run(self):
        self.app.run_server(debug=True, host='0.0.0.0', port=8080)


class CallbackHandler:
    def __init__(self, app, sorted_series_ids):
        self.app = app
        self.sorted_series_ids = sorted_series_ids
        self.register_callbacks()

    def register_callbacks(self):
        @self.app.callback(
            Output('display-graph', 'figure'),
            [Input(series_id, 'n_clicks') for series_id in self.sorted_series_ids] +
            [Input('detrended-switch', 'value'), Input('monthly-switch', 'value')]
        )
        def update_graph(*args):
            # Extract button values and switch values from the callback arguments
            btn_values = args[:-2]
            detrended_values, monthly_values = args[-2:]

            # Check if the graph should be detrended based on the switch value
            detrended = 'detrended' in detrended_values
            # Check if the graph should be displayed in monthly format based on the switch value
            monthly = 'monthly' in monthly_values

            # Get the context to determine which button was clicked
            ctx = dash.callback_context
            if not ctx.triggered:
                # If no button was clicked, load the default graph
                button_id = sorted_series_ids[0]  # Default series_id
                default_file_path = DATA_DIR / f'Graphs/{button_id}_correlations.json'
                if default_file_path.exists():
                    # Load the default graph from the saved JSON file
                    with open(default_file_path, 'r') as f:
                        fig_dict = json.load(f)
                        fig = go.Figure(fig_dict)
                        fig.update_layout(autosize=True, margin=dict(t=40, b=40, l=40, r=10))  # Adjusted top margin
                        return fig
                else:
                    # Return an empty figure if the default graph file doesn't exist
                    return go.Figure()
            else:
                num_traces = 2
                plotter = CorrelationPlotter()
                # If a button was clicked, get its ID
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                # Load the saved security from the pickle file
                security = load_saved_securities(button_id)
                # Generate the graph
                fig = plotter.plot_security_correlations(
                    security.symbol,
                    start_date='2010-08-02',
                    num_traces=num_traces,
                    display_plot=False,
                    show_detrended=detrended,
                    monthly=monthly
                )
                fig.update_layout(autosize=True, margin=dict(t=40, b=40, l=40, r=10))  # Adjusted top margin
                return fig


class ButtonGenerator:
    def __init__(self, sorted_series_ids, misc_subgroups):
        self.sorted_series_ids = sorted_series_ids
        self.misc_subgroups = misc_subgroups
        self.button_groups = defaultdict(lambda: defaultdict(list))

    def generate_buttons(self):
        for series_id in self.sorted_series_ids:
            source_title = get_fred_source_title(series_id)
            button = html.Button(series_id, id=series_id, n_clicks=(1 if series_id == self.sorted_series_ids[0] else 0))

            if source_title in self.misc_subgroups:
                self.button_groups['Misc'][source_title].append(button)
            else:
                self.button_groups[source_title]['main'].append(button)

        return self.button_groups


class LayoutCreator:
    def __init__(self, button_groups, sorted_series_ids, misc_subgroups):
        self.button_groups = button_groups
        self.sorted_series_ids = sorted_series_ids
        self.misc_subgroups = misc_subgroups

    def create_layout(self):
        grouped_buttons = self._group_buttons()

        layout = html.Div([
            html.H1("Securities Correlated with FRED Macro Data",
                    style={'textAlign': 'center', 'color': '#e0e0e0', 'padding': '10px'}),
            html.Div(grouped_buttons, style={
                'display': 'flex',
                'flexDirection': 'row',
                'flexWrap': 'nowrap',
                'justifyContent': 'flex-start',
                'overflowX': 'auto',
                'marginBottom': '10px',
                'flexShrink': '0'
            }),
            self._create_switches(),
            dcc.Graph(
                id='display-graph',
                style={'flexGrow': '1'}
            )
        ], style={
            'font-family': 'Open Sans, sans-serif',
            'height': '100vh',
            'backgroundColor': '#1e1e2a',
            'color': '#e0e0e0',
            'display': 'flex',
            'flexDirection': 'column'
        })

        return layout

    def _group_buttons(self):
        # Create a button for each series ID. Auto-load the first button by setting its n_clicks to 1.
        buttons = [html.Button(series_id, id=series_id, n_clicks=(1 if series_id == sorted_series_ids[0] else 0))
                   for series_id in sorted_series_ids]

        # Create a dictionary to group buttons by their title
        button_groups = defaultdict(lambda: defaultdict(list))

        misc_subgroups = [
            "U.S. Employment and Training Administration",
            "U.S. Energy Information Administration",
            "University of Michigan",
            "Moody's",
            "Chicago Board Options Exchange"
        ]

        for series_id in sorted_series_ids:
            source_title = get_fred_source_title(series_id)
            button = html.Button(series_id, id=series_id, n_clicks=(1 if series_id == sorted_series_ids[0] else 0))

            # Check if the title belongs to a 'Misc' subgroup
            if source_title in misc_subgroups:
                print("Misc: ", source_title, button)
                button_groups['Misc'][source_title].append(button)
            else:
                button_groups[source_title]['main'].append(button)  # Use 'main' as a default key for non-Misc groups
                print("Main: ", source_title, button)

        # Create a list of Divs for each group of buttons
        grouped_buttons = []
        for title, buttons_dict in button_groups.items():
            if title == 'Misc':
                misc_divs = [
                    html.H4('Misc', style={'textAlign': 'center', 'marginBottom': '20px'})]  # Label for Misc section
                for subgroup_title, subgroup_buttons in buttons_dict.items():
                    misc_divs.append(html.Div([
                        html.H6(subgroup_title, style={'textAlign': 'center', 'margin': '6px'}),
                        html.Div(subgroup_buttons, style={
                            'display': 'flex',
                            'flexDirection': 'row',
                            'flexWrap': 'wrap',
                            'justifyContent': 'center',
                            'gap': '1px',
                            'margin': '1px',  # Adjust margin value
                            'padding': '1px'  # Adjust padding value
                        })
                    ]))
                grouped_buttons.append(html.Div(misc_divs, style={'marginRight': '20px'}))
            else:
                grouped_buttons.append(html.Div([
                    html.H4(title, style={'textAlign': 'center'}),
                    html.Div(buttons_dict['main'], style={  # Extract the 'main' key here
                        'display': 'flex',
                        'flexDirection': 'row',
                        'flexWrap': 'wrap',
                        'justifyContent': 'center',
                        'gap': '10px',
                        'margin': '5px',  # Adjust margin value
                        'padding': '5px'  # Adjust padding value
                    })
                ], style={'marginRight': '20px'}))

    def _create_switches(self):
        return html.Div([
            dcc.Checklist(
                id='detrended-switch',
                options=[{'label': 'Detrended', 'value': 'detrended'}],
                value=[],
                inline=True
            ),
            dcc.Checklist(
                id='monthly-switch',
                options=[{'label': 'Monthly', 'value': 'monthly'}],
                value=[],
                inline=True
            )
        ], style={'display': 'flex', 'justifyContent': 'center', 'margin': '10px'})


if __name__ == '__main__':
    button_generator = ButtonGenerator(sorted_series_ids, misc_subgroups)
    button_groups = button_generator.generate_buttons()

    layout_creator = LayoutCreator(button_groups, sorted_series_ids, misc_subgroups)
    app_layout = layout_creator.create_layout()

    app_runner = AppRunner(app_layout)
    callback_handler = CallbackHandler(app_runner.app, sorted_series_ids)  # Instantiate the CallbackHandler

    app_runner.run()
