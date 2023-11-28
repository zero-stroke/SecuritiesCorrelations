import time
from typing import List

from scripts.correlation_constants import Security, SharedMemoryCache, FredmdSeries, FredapiSeries, start_years
from scripts.file_reading_funcs import pickle_securities_objects, get_fred_md_series_list, build_symbol_list
from scripts.calculate_correlations import CorrelationCalculator, define_top_correlations
from scripts.plotting_functions import CorrelationPlotter

DEBUG = False


def compute_security_correlations_and_plot(cache: SharedMemoryCache, old_security: Security = None,
                                           symbol_list: List[str] = None, fred_source: str = 'SECURITIES',
                                           start_date: str = '2023', end_date: str = '2023-06-02',
                                           num_traces: int = 2,
                                           source: str = 'yahoo', dl_data: bool = False,
                                           display_plot: bool = False, use_ch: bool = False,
                                           use_multiprocessing: bool = False,
                                           etf: bool = True, stock: bool = True, index: bool = True,
                                           show_detrended: bool = False, monthly_resample: bool = False,
                                           otc_filter: bool = True,
                                           sector: List[str] = None, industry_group: List[str] = None,
                                           industry: List[str] = None, country: List[str] = None,
                                           state: List[str] = None, market_cap: List[str] = None, debug=False):
    """Returns list of tickers from most to least correlated"""
    if fred_source == 'SECURITIES' or fred_source == 'yahoo':
        securities_list = make_securities_set(symbol_list)
    elif len(symbol_list) < 3:
        if fred_source == 'FREDMD':
            securities_list = {FredmdSeries(symbol_list[0])}
        elif fred_source == 'FREDAPI':
            securities_list = {FredapiSeries(symbol_list[0], revised=True)}
        elif fred_source == 'FREDAPIOG':
            securities_list = {FredapiSeries(symbol_list[0], revised=False)}
        else:
            raise ValueError('Unknown fred_source')
    else:
        securities_list = get_fred_md_series_list()

    for security in securities_list:
        assert next(iter(security.series_data_detrended.items())), f"Invalid symbol, no data for {security.symbol}."
    start_time = time.time()

    # Build list of symbols to be used for comparisons
    symbols = build_symbol_list(etf, stock, index)

    # MAIN CALCULATION
    calculator = CorrelationCalculator(symbols, cache, debug=debug)  # Calculate all correlations for securities_list

    if use_multiprocessing:
        securities_list = calculator.define_correlation_for_each_year(securities_list, end_date,
                                                                      source, dl_data, use_ch, use_multiprocessing)
    else:
        securities_list = calculator.define_correlations_for_series_list(securities_list, start_date, end_date,
                                                                         source, dl_data, use_ch)
        with open('scripts/temp_file.txt', 'a') as f:
            f.write(f'{securities_list, start_date, end_date, source, dl_data, use_ch}')

    # Take the 100 most positively and negatively correlated and assign to Security
    securities_list = define_top_correlations(securities_list)

    # for security in securities_list:
    #     print(f'{str(security):<90}', security.positive_correlations, '\n')
    #     print(f'{str(security):<90}', security.negative_correlations, '\n')

    if True:  # Pickle securities list to use later for configuring plots
        for security in securities_list:
            # If the old security is the same as the new security, add to the correlation cache list
            if old_security is not None and type(old_security) == type(security) and \
                    security.symbol == old_security.symbol:
                for year in start_years:
                    if len(security.positive_correlations[year]) == 0 and \
                            len(old_security.positive_correlations[year]) != 0:
                        security.positive_correlations[year] = old_security.positive_correlations[year]
                        security.negative_correlations[year] = old_security.negative_correlations[year]
            pickle_securities_objects(security, fred_source)

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


def make_securities_set(symbol_list):
    symbol_list = set(symbol_list)  # List of symbols to be converted into Securities
    securities_list = {Security(symbol) for symbol in symbol_list}  # Initialize Security list

    # Populate series_data for each security
    for security in securities_list:
        security.set_series_data()

    # Filter out securities with None series_data
    filtered_securities_set = {security for security in securities_list if security.series_data is not None}

    return filtered_securities_set


def main():
    cache = SharedMemoryCache()

    start_date = '2023'
    end_date = '2023-06-02'
    num_traces = 4
    source = 'yahoo'
    dl_data = False
    display_plot = True
    use_ch = False
    show_detrended = False

    fig_list = compute_security_correlations_and_plot(
        cache=cache,

        symbol_list=['RPI'],
        fred_source='FREDAPIOG',
        start_date=start_date,
        end_date=end_date,
        num_traces=num_traces,

        source=source,
        dl_data=dl_data,
        display_plot=display_plot,
        use_ch=use_ch,
        use_multiprocessing=False,

        etf=False,
        stock=True,
        index=False,

        show_detrended=show_detrended,
        monthly_resample=False,
        otc_filter=False,
    )


if __name__ == '__main__':
    main()
