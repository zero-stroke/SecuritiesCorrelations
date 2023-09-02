import json
import subprocess
from typing import List

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import DATA_DIR
from scripts.correlation_constants import Security, EnhancedEncoder, SecurityMetadata
from scripts.file_reading_funcs import read_series_data, fit_data_to_time_range


class CorrelationPlotter:
    DEBUG = False
    MAIN_SERIES_COLOR = '#FFFFFF'

    def __init__(self):
        pass

    @staticmethod
    def add_traces_to_plot(fig, securities: List[Security], start_date, row: int, num_traces: int, show_detrended: bool,
                           etf: bool = False, stock: bool = True, index: bool = False, monthly: bool = False, sector:
                           List[str] = None, industry_group: List[str] = None, industry: List[str] = None,
                           country: List[str] = None, state: List[str] = None,
                           market_cap: List[str] = None, otc_filter: bool = True):
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

            if security.source == 'stock':
                if sector is not None and security.sector not in sector:
                    continue
                if industry_group is not None and security.industry_group not in industry_group:
                    continue
                if industry is not None and security.industry not in industry:
                    continue
                if country is not None and security.country not in country:
                    continue
                if state is not None and security.state not in state:
                    continue
                if market_cap is not None and security.market_cap not in market_cap:
                    continue

                if otc_filter and 'OTC ' in security.market:  # If otc_filter is True and market contains 'OTC ' in it, skip
                    continue

            symbol = security.symbol
            name = security.name
            name = CorrelationPlotter.wrap_text(name, 50)

            trace_series = read_series_data(security.symbol, 'yahoo')

            trace_series = fit_data_to_time_range(trace_series, start_date)
            trace_series = CorrelationPlotter.normalize_data(trace_series)

            if monthly:
                trace_series = trace_series.resample('MS').first()

            if show_detrended:
                trace_series = trace_series.diff().dropna()

            fig.add_trace(go.Scatter(x=trace_series.index, y=trace_series, mode='lines',
                                     name=f'{symbol} - {name}'), row=row, col=1)

            added_count += 1

    def plot_security_correlations(self, main_security: Security, start_date: str = '2010', num_traces: int = 2,
                                   display_plot: bool = False,
                                   etf: bool = False, stock: bool = True, index: bool = False,
                                   show_detrended: bool = False, monthly: bool = False, otc_filter: bool = True,
                                   sector: List[str] = None, industry_group: List[str] = None,
                                   industry: List[str] = None, country: List[str] = None, state: List[str] = None,
                                   market_cap: List[str] = None):
        """Plotting the base series against its correlated series"""
        main_security_data = read_series_data(main_security.symbol, 'yahoo')  # Prepare main series

        # Make sure the main security is normalized based on its data from the start date
        main_security_data = fit_data_to_time_range(main_security_data, start_date)
        main_security_data = CorrelationPlotter.normalize_data(main_security_data)

        if show_detrended:
            main_security_data = main_security_data.diff().dropna()

        # Set up the subplots layout
        num_rows = 2
        fig = make_subplots(rows=num_rows, cols=1)

        for i, correlations in enumerate([main_security.positive_correlations, main_security.negative_correlations],
                                         start=1):
            fig.add_trace(go.Scatter(x=main_security_data.index, y=main_security_data, mode='lines',
                                     name=main_security.symbol, line=dict(color=self.MAIN_SERIES_COLOR)), row=i, col=1)
            self.add_traces_to_plot(fig, correlations, start_date, i, num_traces, show_detrended, etf, stock, index,
                                    monthly, sector, industry_group, industry, country, state, market_cap, otc_filter,)

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

        # # Save plot (if not in debug mode)
        # if not self.DEBUG:
        #     self.save_plot(main_security.symbol, fig, start_date)

        return fig

    @staticmethod
    def save_plot(symbol: str, fig, start_date: str):
        json_file_path = DATA_DIR / f'Graphs/json_plots/{symbol}_{start_date}_plot.json'
        # Graphs/json_plots/AAPL_2010_plot.json
        json_file_path = DATA_DIR / f'Graphs/json_plots/{symbol}_plot.json'
        with open(json_file_path, 'w') as f:
            json.dump(fig.to_dict(), f, cls=EnhancedEncoder)

    @staticmethod
    def show_popup_plot(symbol: str, fig):
        html_file_path = DATA_DIR / f'Graphs/html_plots/{symbol}_plot.html'
        fig.write_html(html_file_path, full_html=True)
        subprocess.run(["cmd", "/c", "firefox2", "--kiosk", html_file_path])

    @staticmethod
    def normalize_data(series):
        """Normalize a pandas Series by scaling its values between 0 and 1."""
        return (series - series.min()) / (series.max() - series.min())

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
