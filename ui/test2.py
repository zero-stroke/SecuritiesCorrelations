import os

import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objects as go

app = dash.Dash(__name__)

available_securities = ['AAPL', 'GOOG', 'MSFT']

def load_initial_plot():
    fig = go.Figure(data=[
        go.Bar(name='SF Zoo', x=available_securities, y=[10, 11, 12]),
    ])
    return fig

initial_plot = load_initial_plot()

app.layout = html.Div([
    dcc.Input(id='security-input', type='text', value=''),
    html.Div(id='security-hints'),

    # Container for the plot and the LaTeX
    html.Div([
        dcc.Graph(
            id='security-plot',
            figure=initial_plot,
            style={'flexGrow': '1', 'min-height': '700px'},
            responsive=True,
        ),
        # LaTeX overlay
        dcc.Markdown('$Area (m^{2})$',
                     style={
                         'position': 'absolute',
                         'bottom': '0.5em',  # Adjust as needed to align with your annotation
                         'right': '1.5em',  # Adjusted from 'right' to 'left' to align with the left edge
                         'backgroundColor': 'green',  # Make background transparent
                         'padding': '5px',
                         'borderRadius': '5px'
                     },
                     mathjax=True
                     )
    ], style={'display': 'flex', 'flexDirection': 'column', 'height': '100%'}),

    dcc.Interval(
        id='initial-load-interval',
        interval=100,  # in milliseconds
        max_intervals=1  # stop after the first interval
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

@app.callback(
    Output('security-hints', 'children'),
    Input('security-input', 'value')
)
def update_security_hints(input_value):
    hints = [security for security in available_securities if input_value.upper() in security]
    return [html.Div(hint) for hint in hints]

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8070)))
