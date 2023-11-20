# Attempt to add custom key listening rules

# Required imports
import os

import dash
from dash import html, dcc
from dash.dependencies import Input, Output

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Textarea(
        id='textarea-input',
        placeholder='Type something and press Ctrl + Enter...',
        style={'width': '100%', 'height': '200px'},
    ),
    dcc.Input(id='hidden-input', type='hidden', value=0),
    html.Div(id='output-div'),
    html.Script("""
        setTimeout(function(){
            var textarea = document.getElementById('textarea-input');
            textarea.addEventListener('keydown', function(event) {
                if (event.ctrlKey && event.key === 'Enter') {
                    var hiddenInput = document.getElementById('hidden-input');
                    hiddenInput.value = parseInt(hiddenInput.value) + 1;
                    hiddenInput.dispatchEvent(new Event('change'));
                }
            });
        }, 1000);  // Delay of 1 second
    """)
])

@app.callback(
    Output('output-div', 'children'),
    Input('hidden-input', 'value')
)
def update_output(value):
    if int(value) > 0:
        return f"You've pressed Ctrl + Enter {int(value)} times!"
    else:
        return "You haven't pressed Ctrl + Enter yet."


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8040)))
