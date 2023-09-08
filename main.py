import time
from typing import List, Union

from scripts.correlation_constants import SecurityMetadata, Security, FredSeries
from scripts.file_reading_funcs import pickle_securities_objects, get_fred_md_series_list, load_saved_securities
from scripts.find_correlated_symbols import CorrelationCalculator, define_top_correlations
from scripts.plotting_functions import CorrelationPlotter

DEBUG = False


def compute_security_correlations_and_plot(symbol_list: List[str], use_fred: bool = False,
                                           start_date: str = '2010', end_date: str = '2023',
                                           num_traces: int = 2,
                                           source: str = 'yahoo', dl_data: bool = False,
                                           display_plot: bool = False, use_ch: bool = False,
                                           use_multiprocessing: bool = False,
                                           etf: bool = True, stock: bool = True, index: bool = True,
                                           show_detrended: bool = False, monthly_resample: bool = False,
                                           otc_filter: bool = True,
                                           sector: List[str] = None, industry_group: List[str] = None,
                                           industry: List[str] = None, country: List[str] = None,
                                           state: List[str] = None, market_cap: List[str] = None):
    """Returns list of tickers from most to least correlated"""
    if not use_fred:
        securities_list = make_securities_list(symbol_list)
    else:
        securities_list = get_fred_md_series_list()

    start_time = time.time()
    metadata = SecurityMetadata()  # Initialize SecurityMetadata Singleton object

    # Build list of symbols to be used for comparisons
    symbols = metadata.build_symbol_list(etf, stock, index)

    calculator = CorrelationCalculator()  # Calculate all correlations for securities_list
    securities_list = calculator.define_correlation_for_each_year(securities_list, symbols, end_date,
                                                                  source, dl_data, use_ch, use_multiprocessing)

    # Take the num_traces positively and negatively correlated and assign to Security
    securities_list = define_top_correlations(securities_list)

    # for security in securities_list:
    #     print(f'{str(security):<90}', security.positive_correlations, '\n')
    #     print(f'{str(security):<90}', security.negative_correlations, '\n')

    if not DEBUG:  # Pickle securities list to use later for configuring plots
        for security in securities_list:
            pickle_securities_objects(security)

    plotter = CorrelationPlotter()
    fig_list = []  # List of figures from plotly
    for security in securities_list:  # Create a plot for each Security
        fig = plotter.plot_security_correlations(
            main_security=security,
            start_date=start_date,
            num_traces=num_traces,
            display_plot=display_plot,

            etf=etf,
            stock=stock,
            index=index,

            show_detrended=show_detrended,
            monthly=monthly_resample,
            otc_filter=otc_filter,

            sector=sector,
            industry_group=industry_group,
            industry=industry,
            country=country,
            state=state,
            market_cap=market_cap,
        )
        fig_list.append(fig)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"The script took {elapsed_time:.2f} seconds to run.\n")

    return fig_list


def make_securities_list(symbol_list):
    symbol_list = list(set(symbol_list))  # List of symbols to be converted into Securities
    securities_list = [Security(symbol) for symbol in symbol_list]  # Initialize Security list

    # Populate series_data for each security
    for security in securities_list:
        security.set_series_data()

    # Filter out securities with None series_data
    filtered_securities_list = [security for security in securities_list if security.series_data is not None]

    return filtered_securities_list


def main():

    start_date = '2023'
    end_date = '2023-06-02'
    num_traces = 4
    source = 'yahoo'
    dl_data = False
    display_plot = True
    use_ch = False
    show_detrended = False

    fig_list = compute_security_correlations_and_plot(
        symbol_list=['F'],
        use_fred=False,
        start_date=start_date,
        end_date=end_date,
        num_traces=num_traces,

        source=source,
        dl_data=dl_data,
        display_plot=display_plot,
        use_ch=use_ch,
        use_multiprocessing=True,

        etf=False,
        stock=True,
        index=False,

        show_detrended=show_detrended,
        monthly_resample=False,
        otc_filter=False,
    )



if __name__ == '__main__':
    main()
