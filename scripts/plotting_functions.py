import json
import subprocess
from typing import List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import DATA_DIR
from scripts.correlation_constants import Security, EnhancedEncoder, FredmdSeries, FredapiSeries, \
    FredSeriesBase
from scripts.file_reading_funcs import read_series_data, fit_data_to_time_range


def set_comment_text(main_security: FredmdSeries | FredapiSeries | Security) -> str:
    if isinstance(main_security, FredapiSeries) or isinstance(main_security, FredmdSeries):
        # Remove "http://www." prefix from source_link and release_link
        source_link_cleaned = main_security.source_link.replace("http://www.", "")
        source_link_cleaned = source_link_cleaned.replace("https://www.", "")

        release_link_cleaned = main_security.release_link

        if type(main_security.release_link) == str:
            release_link_cleaned = release_link_cleaned.replace("http://www.", "")
            release_link_cleaned = release_link_cleaned.replace("https://www.", "")

        comment_text = f'Source: {main_security.source_title},    {source_link_cleaned},    ' \
                       f'Release: {main_security.release_title},    {release_link_cleaned},    ' \
                       f'Transformation Method: '
    else:
        if main_security.source == 'stock':
            comment_text = f"Sector: {main_security.sector},    Industry Group: {main_security.industry_group},    " \
                           f"Industry: {main_security.industry},     Country: {main_security.country},    " \
                           f"State: {main_security.state},    Market: {main_security.market}"
        else:
            return ''

    return comment_text


DEBUG = False
MAIN_SERIES_COLOR = '#FFFFFF'


class CorrelationPlotter:

    def __init__(self): \
            pass

    @staticmethod
    def add_traces_to_plot_ui(fig, securities: List[Security], start_date, row: int, show_detrended: bool,
                              monthly: bool = False):
        """Adds num_traces # of traces of securities to plotly fig. Flags for displaying detrended and monthly data."""
        for security in securities:
            symbol = security.symbol
            name = security.name
            name = CorrelationPlotter.wrap_text(name, 50)

            trace_series = read_series_data(security.symbol, 'yahoo')

            trace_series = fit_data_to_time_range(trace_series, start_date)
            trace_series = normalize_data(trace_series)

            if monthly:
                trace_series = trace_series.resample('MS').first()

            if show_detrended:
                trace_series = trace_series.diff().dropna()

            fig.add_trace(go.Scatter(x=trace_series.index, y=trace_series, mode='lines',
                                     name=f'{security.correlation:.3}  {symbol} - {name}'), row=row, col=1)

    @staticmethod
    def add_traces_to_plot(fig, securities: List[Security], start_date, row: int, num_traces: int, show_detrended: bool,
                           monthly: bool = False):
        """Adds num_traces # of traces of securities to plotly fig. Flags for displaying detrended and monthly data."""
        added_count = 0
        for security in securities:
            if added_count >= num_traces:
                break

            symbol = security.symbol
            name = security.name
            name = CorrelationPlotter.wrap_text(name, 50)

            trace_series = read_series_data(security.symbol, 'yahoo')

            trace_series = fit_data_to_time_range(trace_series, start_date)
            trace_series = normalize_data(trace_series)

            if monthly:
                trace_series = trace_series.resample('MS').first()

            if show_detrended:
                trace_series = trace_series.diff().dropna()

            fig.add_trace(go.Scatter(x=trace_series.index, y=trace_series, mode='lines',
                                     name=f'{security.correlation:.3}  {symbol} - {name}'), row=row, col=1)

            added_count += 1

    def plot_security_correlations(self, main_security: Security | FredSeriesBase, start_date: str = '2010',
                                   num_traces: int = 2, display_plot: bool = False,
                                   etf: bool = False, stock: bool = True, index: bool = False,
                                   show_detrended: bool = False, monthly: bool = False, otc_filter: bool = True,
                                   sector: List[str] = None, industry_group: List[str] = None,
                                   industry: List[str] = None, country: List[str] = None, state: List[str] = None,
                                   market_cap: List[str] = None, displayed_positive_correlations=None,
                                   displayed_negative_correlations=None,
                                   num_rows: int = 2):
        """Plotting the base series against its correlated series"""

        args_dict = locals().copy()
        args_dict.pop('self')  # Remove 'self' from the dictionary

        with open('debug_file.txt', 'a') as f:
            f.write('\n')

        # Write the arguments to a file for debugging
        with open('debug_file.txt', 'a') as f:
            for key, value in args_dict.items():
                f.write(f'{key}: {value}\n')

        start_year = start_date[:4]
        main_security_data: pd.Series = main_security.series_data[start_year]

        # Make sure the securities_main security is normalized based on its data from the start date
        main_security_data = normalize_data(main_security_data)
        if monthly:
            main_security_data = main_security_data.resample('MS').first()

        if show_detrended:
            main_security_data = main_security_data.diff().dropna()

        # Set up the subplots layout
        fig = make_subplots(rows=num_rows, cols=1)

        if displayed_positive_correlations is not None and num_rows > 1:
            for i, correlations in enumerate([displayed_positive_correlations, displayed_negative_correlations],
                                             start=1):  # Only loops twice
                fig.add_trace(go.Scatter(x=main_security_data.index, y=main_security_data, mode='lines',
                                         name=main_security.symbol, line=dict(color=MAIN_SERIES_COLOR)), row=i, col=1)
                self.add_traces_to_plot_ui(fig, correlations, start_date, i, show_detrended, monthly)
        elif num_rows > 1:
            for i, correlations in enumerate([main_security.positive_correlations[start_date],
                                              main_security.negative_correlations[start_date]], start=1):
                fig.add_trace(go.Scatter(x=main_security_data.index, y=main_security_data, mode='lines',
                                         name=main_security.symbol, line=dict(color=MAIN_SERIES_COLOR)), row=i, col=1)
                self.add_traces_to_plot(fig, correlations, start_date, i, num_traces, show_detrended, monthly)
        else:
            fig.add_trace(go.Scatter(x=main_security_data.index, y=main_security_data, mode='lines',
                                     name=main_security.symbol, line=dict(color=MAIN_SERIES_COLOR)), row=1, col=1)

        comment_text = set_comment_text(main_security)

        # Aesthetic configurations
        fig.update_layout(
            title_text=main_security.name,
            plot_bgcolor='#2a2a3b',  # Dark violet background
            paper_bgcolor='#1e1e2a',  # Even darker violet for the surrounding paper
            font=dict(color='#e0e0e0'),  # Light font color for contrast
            xaxis=dict(gridcolor='#4a4a5a'),  # Grid color
            yaxis=dict(gridcolor='#4a4a5a'),  # Grid color
        )

        if num_rows > 1:
            fig.add_annotation(
                text='Inverse Correlations',  # Title of second row
                showarrow=False,
                xref="paper", yref="paper",
                x=0, y=0.47,
                font=dict(size=16),
            )

        fig.add_annotation(
            text=comment_text,
            showarrow=False,
            xref="paper", yref="paper",
            x=0, y=-0.1,
            font=dict(size=12),
        )

        # Set x-axis range for all subplots
        for row in range(1, num_rows + 1):
            fig['layout'][f'xaxis{row}'].update(range=[start_date, main_security_data.index[-1]])

        # Handle display
        if display_plot:
            show_popup_plot(main_security.symbol, fig)

        # Save plot (if not in debug mode)
        # if not DEBUG:
        #     save_plot(main_security.symbol, fig)

        return fig

    @staticmethod
    def wrap_text(name, max_length=50):
        if name is not None and len(name) > max_length:
            # Find a suitable break point (e.g., a space) and insert a line break
            break_point = name.rfind(' ', 0, max_length)
            if break_point > 0:
                name = name[:break_point] + '<br>' + name[break_point + 1:]
            else:  # If no suitable break point found, force a break at the max length
                name = name[:max_length] + '<br>' + name[max_length:]
        elif name is not None:
            padding = '&nbsp;' * (max_length - len(name))
            name = name + padding
        return name


def show_popup_plot(symbol: str, fig):
    html_file_path = DATA_DIR / f'Graphs/html_plots/{symbol}_plot.html'
    fig.write_html(html_file_path, full_html=True)
    subprocess.run(["cmd", "/c", "firefox2", "--kiosk", html_file_path])


def normalize_data(series: pd.Series):
    """Normalize a pandas Series by scaling its values between 0 and 1."""
    return (series - series.min()) / (series.max() - series.min())


def save_plot(symbol: str, fig):
    # Graphs/json_plots/AAPL_2010_plot.json
    json_file_path = DATA_DIR / f'Graphs/json_plots/{symbol}_plot.json'
    with open(json_file_path, 'w') as f:
        json.dump(fig.to_dict(), f, cls=EnhancedEncoder)


if __name__ == '__main__':
    pass

