import time

import pandas as pd
from functools import lru_cache, wraps
import threading
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from config import STOCKS_DIR

# Setting up the logger
from scripts.correlation_constants import SecurityMetadata

log_format = '%(asctime)s - %(message)s'
date_format = '%H:%M:%S'

logging.basicConfig(filename='cache_info.log', level=logging.INFO,
                    format=log_format, datefmt=date_format, filemode='w')


# Shared cache lock
cache_lock = threading.Lock()


# Cache info decorator
def cache_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        logging.info(f"Function {func.__name__} called with args {args}."
                     f" Cache info: {func.cache_info()}")
        return result

    return wrapper


@cache_info
@lru_cache(maxsize=None)
def read_series_data(symbol: str, source: str):
    with cache_lock:
        if source == 'yahoo':
            file_path = STOCKS_DIR / f'yahoo_daily/parquets/{symbol}.parquet'
            try:
                series = pd.read_parquet(file_path)
            except FileNotFoundError:
                logging.warning(f'{file_path} does not exist')
                return None

            try:
                return series['Adj Close']
            except KeyError:
                return None

        return None


def main_test(symbols, source='yahoo'):
    with ThreadPoolExecutor() as executor:
        results_list = list(executor.map(read_series_data, symbols, [source] * len(symbols)))
    return results_list


metadata = SecurityMetadata()  # Initialize SecurityMetadata Singleton object

# Build list of symbols to be used for comparisons
symbols = metadata.build_symbol_list(False, True, False)

if __name__ == '__main__':
    # First execution
    start_time_1 = time.time()

    main_test(symbols)

    duration_1 = time.time() - start_time_1
    print(f"\nFirst run took {duration_1:.2f} seconds.")

    # Second execution
    start_time_2 = time.time()

    main_test(symbols)

    duration_2 = time.time() - start_time_2
    print(f"\nSecond run took {duration_2:.2f} seconds.")

    start_time_3 = time.time()

    main_test(symbols)

    duration_3 = time.time() - start_time_3
    print(f"\nThird run took {duration_3:.2f} seconds.")


