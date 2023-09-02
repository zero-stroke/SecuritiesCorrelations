import os

import dash
from dash import html, dcc
from dash.dependencies import Input, Output

app = dash.Dash(__name__)

available_securities = ['AAPL', 'GOOG', 'MSFT']
initial_plot = load_initial_plot()  # Load initial plot

app.layout = html.Div([
    dcc.Input(id='security-input', type='text', value=''),
    html.Div(id='security-hints'),


    dcc.Graph(
        id='security-plot',
        figure=initial_plot,
        style={'flexGrow': '1', 'min-height': '700px',},
        responsive=True,
    ),
    dcc.Interval(
        id='initial-load-interval',
        interval=100,  # in milliseconds
        max_intervals=1  # stop after the first interval
    ),

])

@app.callback(
    Output('security-hints', 'children'),
    Input('security-input', 'value')
)
def update_security_hints(input_value):
    # Filter the list of available securities based on the input value
    hints = [security for security in available_securities if input_value.upper() in security]
    # Return the hints as a list of html.Div elements
    return [html.Div(hint) for hint in hints]

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8070)))

