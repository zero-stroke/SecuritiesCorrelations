import logging
import multiprocessing
from logging.handlers import TimedRotatingFileHandler
from typing import List
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from scripts.correlation_constants import Security, SecurityMetadata
from scripts.file_reading_funcs import get_validated_security_data, read_series_data, is_series_within_date_range, \
    fit_data_to_time_range



# Configure the logger at the module level
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Set to WARNING for production; DEBUG for development

# Create a file handler and set level to debug
fh = logging.FileHandler('correlation_calculator.log')
fh.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create a rotating file handler and set level to debug
fh = TimedRotatingFileHandler('correlation_calculator.log', when="midnight", interval=1, backupCount=7)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(fh)


def define_top_correlations(all_main_securities: List[Security]) -> List[Security]:
    num_symbols = 100
    metadata = SecurityMetadata()

    for main_security in all_main_securities:
        correlation_dict = main_security.all_correlations

        assert isinstance(correlation_dict, dict)

        sorted_symbols_desc = sorted(correlation_dict.keys(), key=correlation_dict.get, reverse=True)
        sorted_symbols_asc = sorted(correlation_dict.keys(), key=correlation_dict.get, reverse=False)

        for symbol in sorted_symbols_desc[:num_symbols]:
            correlated_security = Security(symbol, metadata)
            correlated_security.set_correlation(correlation_dict[symbol])
            main_security.positive_correlations.append(correlated_security)

        for symbol in sorted_symbols_asc[:num_symbols]:
            correlated_security = Security(symbol, metadata)
            correlated_security.set_correlation(correlation_dict[symbol])
            main_security.negative_correlations.append(correlated_security)

        main_security.all_correlations = None

    return all_main_securities


class CorrelationCalculator:
    def __init__(self):
        self.DEBUG = True

    def define_correlation_for_each_year(self, securities_list, symbols, start_date, end_date,
                                         source, dl_data, use_ch):
        all_start_dates = ['2010', '2018', '2021', '2022', '2023']
        for start_date in all_start_dates:
            self.define_correlations_for_series_list(securities_list, symbols, start_date, end_date, source, dl_data,
                                                     use_ch)

        return securities_list

    def define_correlations_for_series_list(self, all_main_securities: List['Security'],
                                            symbols: List[str],
                                            start_date: str, end_date: str, source: str, dl_data: bool, use_ch: bool,
                                            attribute_name) -> List['Security']:
        if self.DEBUG:
            symbols = ['MSFT', 'AMZN', 'SNAP', 'JPM']

        symbols = list(set(symbols))  # This DOES change the order of symbols

        max_workers = 1 if (dl_data or self.DEBUG) else (multiprocessing.cpu_count() // 4)

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(self.process_symbol, symbols, [start_date] * len(symbols), [end_date] * len(symbols),
                                   [source] * len(symbols), [dl_data] * len(symbols), [use_ch] * len(symbols))

            for symbol, security_data in results:

                if security_data is None:  # Check for None before processing
                    logger.warning(f'Skipping correlation calculation for {symbol} due to missing data.')
                    continue
                i = 0

                while i < len(all_main_securities):  # Loop to go through all the main Securities
                    main_security = all_main_securities[i]

                    if symbol == main_security.symbol:  # Skips the comparison if it is being compared to itself
                        i += 1
                        continue

                    main_security_data = read_series_data(main_security.symbol, 'yahoo')

                    if main_security_data is None:
                        logger.warning(f'{main_security.symbol} Data could not be found.')
                        all_main_securities.pop(i)
                        continue

                    main_security_data = fit_data_to_time_range(main_security_data, start_date)

                    # Check time range of security_data
                    new_start_date = main_security_data.index.min().strftime('%Y-%m-%d')

                    correlation_float = self.get_correlation_for_series(main_security_data, security_data)
                    getattr(main_security, attribute_name)[symbol] = correlation_float  # Define dicts' keys & values
                    i += 1
        return all_main_securities

    @staticmethod
    def process_symbol(symbol, start_date, end_date, source, dl_data, use_ch):
        security_data = get_validated_security_data(symbol, start_date, end_date, source, dl_data, use_ch)
        if security_data is None:
            return symbol, None
        return symbol, security_data

    def get_correlation_for_series(self, main_series_data: pd.Series, symbol_data: pd.Series) -> float:
        main_series_data = main_series_data.diff().dropna()  # Detrend

        combined_data = pd.concat([symbol_data, main_series_data], axis=1).dropna()  # Align data by date

        correlation = self.compute_correlation(combined_data.iloc[:, 0],
                                               combined_data.iloc[:, 1])  # Compute correlation
        return correlation

    @staticmethod
    def compute_correlation(series_data1: pd.Series, series_data2: pd.Series) -> float:
        return series_data1.corr(series_data2)


if __name__ == '__main__':
    manager = CorrelationCalculator()
    # Call the desired methods on the manager instance
    # manager.define_correlations_for_series_list(...)
