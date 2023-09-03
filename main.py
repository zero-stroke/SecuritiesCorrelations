import time
from typing import List

from config import STOCKS_DIR
from scripts.correlation_constants import SecurityMetadata, DataSource, Security
from scripts.file_reading_funcs import pickle_securities_objects, load_saved_securities
from scripts.find_correlated_symbols import CorrelationCalculator, define_top_correlations
from scripts.plotting_functions import CorrelationPlotter

DEBUG = False


def compute_security_correlations_and_plot(symbol_list: List[str],
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
    start_time = time.time()

    symbol_list = list(set(symbol_list))  # List of symbols to be converted into Securities
    metadata = SecurityMetadata()  # Initialize SecurityMetadata Singleton object
    securities_list = [Security(symbol, metadata) for symbol in symbol_list]  # Initialize Security list
    symbols = metadata.build_symbol_list(etf, stock, index)  # Build list of symbols to be used for comparisons

    calculator = CorrelationCalculator()  # Calculate all correlations for securities_list
    securities_list = calculator.define_correlation_for_each_year(securities_list, symbols, end_date,
                                                                  source, dl_data, use_ch, use_multiprocessing)

    # Take the num_traces positively and negatively correlated and assign to Security
    securities_list = define_top_correlations(securities_list)

    for security in securities_list:
        print(f'{str(security):<90}', security.positive_correlations, '\n')

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


def main():
    symbol_list = []
    while True:
        user_string = input("Enter symbol to add (or press return to finish): ")
        if user_string.lower() == '':
            break
        symbol_list.append(user_string)
    symbol_list.extend(
        ['AAPL', 'MSFT', 'TSM', 'BRK-A', 'CAT', 'CCL', 'NVDA', 'MVIS', 'ASML', 'GS', 'CLX', 'CHD', 'TSLA',
         'COST', 'TGT', 'JNJ', 'GOOG', 'AMZN', 'UNH', 'XOM', 'PG', 'TM', 'SHEL', 'META', 'CRM', 'AVGO',
         'QCOM', 'TXM', 'MA', 'SHOP', 'NOW', 'V', 'SCHW', 'TMO', 'DHR', 'TT', 'UNP', 'PYPL', 'BAC', 'WFC',
         'TD', 'NU', 'TAK', 'ZTS', 'HCA', 'HON', 'NEE', 'LIN', 'SHW', 'BHP', 'ET', 'LNG', 'E']
    )

    start_date = '2018'
    end_date = '2023-06-02'
    num_traces = 4
    source = 'yahoo'
    dl_data = False
    display_plot = True
    use_ch = False
    show_detrended = False

    start_time = time.time()

    compute_security_correlations_and_plot(
        symbol_list=symbol_list,
        start_date=start_date,
        end_date=end_date,
        num_traces=num_traces,

        source=source,
        dl_data=dl_data,
        display_plot=display_plot,
        use_ch=use_ch,
        use_multiprocessing=True,

        etf=True,
        stock=True,
        index=True,

        show_detrended=show_detrended,
        monthly_resample=False,
        otc_filter=False,
    )

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"The script took {elapsed_time:.2f} seconds to run.\n")


# Code to download symbols from the metadata and from the all_stock_symbols.txt file we scraped
def comprehensive_download_symbols(data_sources: List[DataSource]):
    metadata = SecurityMetadata()

    symbols = metadata.build_symbol_list(data_sources)

    with open(STOCKS_DIR / 'stocks_74.txt', 'r') as f:
        for line in f.readlines():
            symbols.append(line.strip())

    symbols = list(set(symbols))
    print(len(symbols))

    with open(STOCKS_DIR / 'all_stock_symbols.txt', 'w') as f:
        for symbol in symbols:
            f.write(symbol + '\n')

        # if symbol not in downloaded_symbols:
        #     download_yfin_data(symbol)


# def fred_md_main(start_date, end_date, instrument_metadata, monthly, num_traces,
#                  source='yahoo', download_csvs=False, display_plot=False, use_ch=False, detrended=True):
#     """Returns list of tickers from most to least correlated"""
#
#     fred_series_list = get_fred_md_series_list()
#
#     pkl_folder_path = DATA_DIR / 'Graphs/data_structs/'
#
#     symbols = build_symbol_list(instrument_metadata)
#
#     # Call the function, set downloading == to True to download necessary stock data from yfinance.
#     series_symbol_correlations = compute_correlations(symbols, fred_series_list, start_date, end_date, source,
#                                                       download_csvs, use_ch, detrended)
#
#     # Sort a dict of dicts
#     sorted_series_symbol_correlations = sort_series_by_correlation(series_symbol_correlations)
#
#     formatted_symbols_data = format_symbols_for_plot(sorted_series_symbol_correlations, num_traces,
#                                                      instrument_metadata)
#
#     if not DEBUG:
#         # Save dict of base series id's, and symbols that correlate with them for later use
#         with open(pkl_folder_path / 'sorted_series_symbol_correlations.pkl', 'wb') as pickle_file:
#             pickle.dump(sorted_series_symbol_correlations, pickle_file)
#
#         # Save dict of base series id's, and symbols that correlate with them for later use
#         with open(pkl_folder_path / 'formatted_symbols_data.pkl', 'wb') as pickle_file:
#             pickle.dump(formatted_symbols_data, pickle_file)
#
#     for base_series_id, symbols_and_descriptions in formatted_symbols_data.items():
#         plot_fred_md_correlations(base_series_id, symbols_and_descriptions, source, start_date,
#                                   monthly, display_plot, show_detrended=False)
#
#     return formatted_symbols_data


# def timer():
#     start_date = '2010-08-02'  # change
#     end_date = '2023-06-02'
#
#     all_base_series = {}
#     with open(FRED_DIR / 'FRED_original_series.txt', 'r') as file:
#         base_series_ids = [line.strip() for line in file]
#
#     base_series_ids = ['RPI', 'RETAILx'] if DEBUG else base_series_ids
#
#     for series_id in base_series_ids:
#         base_series = find_correlated_symbols.get_fredmd_series(series_id)  # No longer takes start_date ot detrending
#         all_base_series[series_id] = base_series
#
#     monthly = True
#     num_traces = 2
#     source = 'yahoo'
#     download_csvs = False  # download
#     display_plot = True
#     use_ch = False
#     detrended = True
#
#     start_time = time.time()
#
#     fred_md_main(
#         start_date=start_date,
#         end_date=end_date,
#         num_traces=num_traces,
#         source=source,
#         display_plot=display_plot,
#         use_ch=use_ch,
#         detrended=detrended
#     )
#
#     end_time = time.time()
#     elapsed_time = end_time - start_time
#     print(f"The script took {elapsed_time:.2f} seconds to run.\n")


# def plot_series():
#     pkl_file_path = DATA_DIR / 'Graphs/data_structs/formatted_symbols_data.pkl'
#
#     with open(pkl_file_path, 'rb') as pickle_file:
#         formatted_symbols_data = pickle.load(pickle_file)
#
#     for base_series_id, symbols_and_descriptions in formatted_symbols_data.items():
#         find_correlated_tickers.plot_correlations(base_series_id, symbols_and_descriptions, source, start_date,
#                                                   data_format, monthly, display_plot=True, show_detrended=False)


# def write_correlation_rankings():
#     num_shown = 7
#     output_file = r"C:\Users\afshin\Documents\FRED_Correlations.txt"
#     pkl_file_path = DATA_DIR / 'Graphs/data_structs/sorted_series_symbol_correlations.pkl'
#
#     with open(pkl_file_path, 'rb') as pickle_file:
#         sorted_series_symbol_correlations = pickle.load(pickle_file)
#
#     with open(output_file, 'w') as f:
#         for fred_series, correlation_dict in sorted_series_symbol_correlations.items():
#             title = find_correlated_tickers.get_fred_title(fred_series)
#             title = re.sub(r'\(.*?\)', '', title).strip()
#             f.write(f"\n{num_shown}{' Highest Correlated Series For:':<35} {fred_series:<15} {title}\n")
#
#             for i, (symbol, correlation_value) in enumerate(list(correlation_dict.items())[:num_shown]):
#                 description = find_correlated_tickers.get_symbol_description(symbol)
#                 f.write(f"{i + 1}. {symbol:<6} | {description:<40} {correlation_value:.3f}\n")

# with open('requirements/requirements.txt', 'r') as f:
#     required_packages = f.readlines()
#
# with open('requirements/requirements_old.txt', 'r') as f:
#     installed_packages = f.readlines()
#
# # Extract package names from the installed packages
# installed_package_names = {pkg.split('==')[0].lower() for pkg in installed_packages}
#
# filtered_requirements = [pkg for pkg in required_packages if pkg.split('==')[0].lower() in installed_package_names]
#
# # Write the filtered requirements to a new file
# with open('filtered_requirements.txt', 'w') as f:
#     f.writelines(filtered_requirements)

# plot_series('AAA')
#
# write_correlation_rankings()

if __name__ == '__main__':
    main()
