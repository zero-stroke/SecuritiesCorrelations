import dash
from dash import html
from dash.dependencies import Input, Output, State

app = dash.Dash(__name__)

selected_style = {
    'flex': 1,
    'background-color': '#00498B',
    'color': 'white',
    'border': 'none',
    'font-size': '16px',
    'cursor': 'pointer',
    'outline': 'none',
}

app.layout = html.Div([
    html.Div([
        html.Button('ETF', id='etf-button', n_clicks=1, style=selected_style),
        html.Button('Stock', id='stock-button', n_clicks=1, style=selected_style),
        html.Button('Index', id='index-button', n_clicks=0, style=selected_style),
    ], style={
        'display': 'flex',
    }),
])


@app.callback(
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
    new_selected_style = {'flex': 1, 'background-color': '#00498B', 'color': 'white'}
    not_selected_style = {'flex': 1, 'background-color': '#6B6B6B', 'color': 'white'}

    etf_style = new_selected_style if etf_clicks % 2 == 1 else not_selected_style
    stock_style = new_selected_style if stock_clicks % 2 == 1 else not_selected_style
    index_style = new_selected_style if index_clicks % 2 == 1 else not_selected_style

    return etf_style, stock_style, index_style


if __name__ == '__main__':
    app.run_server(debug=True)
