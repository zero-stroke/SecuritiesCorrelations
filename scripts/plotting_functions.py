import subprocess
import json
from itertools import islice
from typing import List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import DATA_DIR
from scripts.correlation_constants import Security, EnhancedEncoder, SecurityMetadata
from scripts.file_reading_funcs import read_series_data


class CorrelationPlotter:
    DEBUG = False
    MAIN_SERIES_COLOR = '#FFFFFF'

    def __init__(self):
        pass

    @staticmethod
    def add_traces_to_plot(fig, securities: List[Security], row: int, num_traces: int, show_detrended: bool,
                           etf: bool = False, stock: bool = True, index: bool = False, monthly: bool = False):
        """Adds num_traces # of traces of securities to plotly fig. Flags for displaying detrended and monthly data."""
        added_count = 0
        for security in securities:
            if added_count >= num_traces:
                break

            if security.source == 'etf' and not etf:
                continue
            elif security.source == 'stock' and not stock:
                continue
            elif security.source == 'index' and not index:
                continue

            symbol = security.symbol
            name = security.name
            trace_series = read_series_data(security.symbol, 'yahoo')

            trace_series = CorrelationPlotter.normalize(trace_series)

            if monthly:
                trace_series = trace_series.resample('MS').first()

            if show_detrended:
                trace_series = trace_series.diff().dropna()

            fig.add_trace(go.Scatter(x=trace_series.index, y=trace_series, mode='lines',
                                     name=f'{symbol} - {name}'), row=row, col=1)

            added_count += 1

    def plot_security_correlations(self, main_security: Security, start_date: str, num_traces: int, display_plot: bool,
                                   show_detrended: bool, etf: bool = False, stock: bool = True, index: bool = False,
                                   monthly: bool = False):
        """Plotting the base series against its correlated series"""

        # Prepare the base series
        main_security_data = read_series_data(main_security.symbol, 'yahoo')

        # Make sure the main security is normalized based on its data from the start date
        start_datetime = pd.to_datetime(start_date)
        start_datetime = max(start_datetime, main_security_data.index.min())
        main_security_data = main_security_data.loc[start_datetime:]
        main_security_data = self.normalize(main_security_data)
        if show_detrended:
            main_security_data = main_security_data.diff().dropna()

        # Set up the subplots layout
        num_rows = 2
        fig = make_subplots(rows=num_rows, cols=1)

        fig.add_trace(go.Scatter(x=main_security_data.index, y=main_security_data, mode='lines',
                                 name=main_security.symbol, line=dict(color=self.MAIN_SERIES_COLOR)), row=1, col=1)
        self.add_traces_to_plot(fig, main_security.positive_correlations, 1, num_traces, show_detrended,
                                etf, stock, index, monthly)

        fig.add_trace(go.Scatter(x=main_security_data.index, y=main_security_data, mode='lines',
                                 name=main_security.symbol, line=dict(color=self.MAIN_SERIES_COLOR)), row=2, col=1)
        self.add_traces_to_plot(fig, main_security.negative_correlations, 2, num_traces, show_detrended, monthly)

        # Aesthetic configurations
        fig.update_layout(
            title_text=main_security.name,
            plot_bgcolor='#2a2a3b',  # Dark violet background
            paper_bgcolor='#1e1e2a',  # Even darker violet for the surrounding paper
            font=dict(color='#e0e0e0'),  # Light font color for contrast
            xaxis=dict(gridcolor='#4a4a5a'),  # Grid color
            yaxis=dict(gridcolor='#4a4a5a'),  # Grid color
        )

        # Set x-axis range for all subplots
        for row in range(1, num_rows + 1):
            fig['layout'][f'xaxis{row}'].update(range=[start_date, main_security_data.index[-1]])

        # Handle display
        if display_plot:
            self.show_popup_plot(main_security.symbol, fig)

        # Save plot (if not in debug mode)
        if not self.DEBUG:
            self.save_plot(main_security.symbol, fig)

    @staticmethod
    def save_plot(symbol: str, fig):
        json_file_path = DATA_DIR / f'Graphs/json_plots/{symbol}_plot.json'
        with open(json_file_path, 'w') as f:
            json.dump(fig.to_dict(), f, cls=EnhancedEncoder)

    @staticmethod
    def show_popup_plot(symbol: str, fig):
        html_file_path = DATA_DIR / f'Graphs/html_plots/{symbol}_plot.html'
        fig.write_html(html_file_path, full_html=True)
        subprocess.run(["cmd", "/c", "firefox2", "--kiosk", html_file_path])

    @staticmethod
    def normalize(series):
        """Normalize a pandas Series by scaling its values between 0 and 1."""
        return (series - series.min()) / (series.max() - series.min())


if __name__ == '__main__':
    # Assuming you have some dummy data or test data
    metadata = SecurityMetadata()
    mock_security = Security('TSLA', metadata)
    mock_start_date = "2021-01-01"

    plotter = CorrelationPlotter()
    plotter.plot_security_correlations(mock_security, mock_start_date, num_traces=5, display_plot=True,
                                       show_detrended=False)

#
# def plot_fred_md_correlations(base_series_obj, symbols_and_descriptions, source, start_date, data_format,
#                               monthly, display_plot, show_detrended):
#     """Plotting the base series against its correlated series"""
#
#     # Retrieve the series data directly from the FredSeries object.
#     base_series = base_series_obj.series_data
#
#     if monthly:
#         base_series = base_series.resample('MS').first()
#
#     if show_detrended:
#         base_series = base_series.diff().dropna()
#
#     num_rows = len(symbols_and_descriptions)
#
#     fig = make_subplots(rows=num_rows, cols=1)
#     base_series = normalize(base_series)
#
#     for i, (symbols, symbol_descriptions) in enumerate(symbols_and_descriptions.items(), start=1):
#         fig.add_trace(go.Scatter(x=base_series.index, y=base_series, mode='lines', name=base_series_obj.fred_md_id),
#                       row=i, col=1)
#         add_traces_to_plot(fig, symbols, symbol_descriptions, source, i, data_format, monthly, show_detrended)
#
#     # Get the title directly from the FredSeries object.
#     title = base_series_obj.name
#
#     fig.update_layout(
#         title_text=title,
#         plot_bgcolor='#2a2a3b',  # Dark violet background
#         paper_bgcolor='#1e1e2a',  # Even darker violet for the surrounding paper
#         font=dict(color='#e0e0e0'),  # Light font color for contrast
#         xaxis=dict(gridcolor='#4a4a5a'),  # Grid color
#         yaxis=dict(gridcolor='#4a4a5a'),  # Grid color
#     )
#
#     # Loop through each x-axis and set the range
#     for i in range(1, num_rows + 1):
#         fig['layout'][f'xaxis{i}'].update(range=[start_date, base_series.index[-1]])
#
#     if display_plot:
#         # Write the plot as html for immediate display.
#         html_file_path = DATA_DIR / f'Graphs/{base_series_obj.symbol}_correlations.html'
#         fig.write_html(html_file_path, full_html=True)
#         subprocess.run(["cmd", "/c", "firefox2", "--kiosk", html_file_path])
#
#     if not DEBUG:
#         # Write the plot as a json file to be displayed using plotly dash.
#         json_file_path = DATA_DIR / f'Graphs/{base_series_obj.symbol}_correlations.json'
#         with open(json_file_path, 'w') as f:
#             json.dump(fig.to_dict(), f, cls=EnhancedEncoder)
#
#     return fig
