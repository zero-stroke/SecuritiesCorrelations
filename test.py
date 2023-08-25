import json

import dash
import plotly.graph_objs as go
from dash import dcc, html

from config import DATA_DIR
from main import load_securities_correlations_and_plot

# Path to the data directory
data_dir = DATA_DIR

# Security to load
security = "AAPL"  # Modify this to match a security you want to load

# Parameters
num_traces = 2
show_detrended = False
etf = True
stock = False
index = False
monthly_resample = False

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
    monthly=False
)

# Load the plot JSON from the saved file
with open(data_dir / f'Graphs/json_plots/{security}_plot.json', 'r') as file:
    fig_data = json.load(file)
fig = go.Figure(fig_data)

# Create Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div([
    dcc.Graph(
        id='security-plot',
        figure=fig  # Use the loaded figure here
    )
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
