import subprocess

import numpy as np
import plotly.express as px

from config import DATA_DIR
from scripts import read_series_data


def show_popup_plot(symbol, fig):
    html_file_path = DATA_DIR / f'{symbol}_plot.html'
    fig.write_html(html_file_path, full_html=True)
    subprocess.run(["cmd", "/c", "firefox2", "--kiosk", html_file_path])


def plot_ticker_data(data, name):
    fig = px.line(data, x=data.index, y='Adj Close', title='Ticker Data')

    fig.update_layout(
        title_text=name,
        plot_bgcolor='#2a2a3b',  # Dark violet background
        paper_bgcolor='#1e1e2a',  # Even darker violet for the surrounding paper
        font=dict(color='#e0e0e0'),  # Light font color for contrast
        xaxis=dict(gridcolor='#4a4a5a'),  # Grid color
        yaxis=dict(gridcolor='#4a4a5a'),  # Grid color
    )

    return fig


def find_repeating_intervals(series):

    window_length = int(len(series) / (35 + np.log1p(len(series))))
    window_length = max(window_length, 3)  # Ensure window_length is at least 1

    print(f"Calculated window length: {window_length}")
    n = len(series)

    repeating_interval_list = []

    # Iterate through series
    for i in range(n - window_length + 1):
        window = series.iloc[i:i+window_length]
        if np.all(window == window.iloc[0]):
            starting_date = window.index[0]
            ending_date = window.index[-1]
            # If the interval is repeating and it's either the first repeating interval
            # or directly after the previous one, extend the interval
            if not repeating_interval_list or repeating_interval_list[-1][1] == starting_date:
                if repeating_interval_list:
                    repeating_interval_list[-1] = (repeating_interval_list[-1][0], ending_date)
                else:
                    repeating_interval_list.append((starting_date, ending_date))
            # If the interval is repeating but not directly after the previous one, start a new interval
            else:
                repeating_interval_list.append((starting_date, ending_date))

    return repeating_interval_list


if __name__ == "__main__":
    ticker = "LCID"  # Replace with your desired ticker symbol
    start_date = "2010-01-01"  # Replace with your desired start date
    end_date = "2023-06-01"  # Replace with your desired end date

    # Step 1: Download Ticker Data
    ticker_data = read_series_data(ticker, 'yahoo')

    # Step 2: Plot Ticker Data
    ticker_fig = plot_ticker_data(ticker_data, ticker)

    # Step 3: Show Popup Plot
    show_popup_plot(ticker, ticker_fig)

    return_obj = find_repeating_intervals(ticker_data)

    if isinstance(return_obj, bool):
        if return_obj:
            print("Ticker data has repeating intervals at the following indices:")
        else:
            print("Ticker data doesn't contain repeating values.")
    else:
        for interval in return_obj:
            print(f"From {interval[0]} to {interval[1]}")


