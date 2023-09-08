import logging
import traceback
from typing import List, Union
import pickle
import os
from functools import lru_cache
from functools import wraps


import numpy as np
import pandas as pd


import yfinance as yf
import financedatabase as fd
from scripts.correlation_constants import FredSeries, Security
from scripts.clickhouse_functions import get_data_from_ch_stock_data
from config import STOCKS_DIR, FRED_DIR, DATA_DIR

# Configure the logger at the module level
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Set to WARNING for production; DEBUG for development

logging.basicConfig(filename='cache_info.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')


def download_yfin_data(symbol):
    """Download historical data for a given symbol."""
    try:
        print(f"Downloading data for: {symbol}")
        df = yf.download(symbol)
        print("SAVING PARQUET to ", STOCKS_DIR / f'yahoo_daily/parquets/{symbol}.parquet')
        df.to_parquet(STOCKS_DIR / f'yahoo_daily/parquets/{symbol}.parquet')
        return df

    except Exception as e:
        print(f"EXCEPTION 1: {e}\nTraceback (most recent call last:\n{traceback.format_exc()}")
        return pd.Series()


from multiprocessing import Manager

manager = Manager()
shared_cache = manager.dict()
cache_lock = manager.Lock()


def shared_memory_cache(func):
    def wrapper(symbol, source):
        key = f"{symbol}_{source}"
        with cache_lock:
            if key in shared_cache:
                return shared_cache[key]
            result = func(symbol, source)
            shared_cache[key] = result
        return result
    return wrapper


def cache_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        logging.info(f"Function {func.__name__} called with args {args} and kwargs {kwargs}."
                     f" Cache info: {func.cache_info()}")
        return result

    return wrapper


@cache_info
@shared_memory_cache
def read_series_data(symbol: str, source: str):
    """Read data based on the source and data format."""
    if source == 'yahoo':
        file_path = STOCKS_DIR / f'yahoo_daily/parquets/{symbol}.parquet'
        try:
            series = pd.read_parquet(file_path)
        except FileNotFoundError:
            logger.warning(f'{file_path} does not exist')
            return None

        try:
            return series['Adj Close']
        except KeyError:
            return None

    return None


def get_validated_security_data(symbol: str, start_date: str, end_date: str, source: str, dl_data: bool, use_ch: bool):
    """Get security data from file, make sure its within range and continuous"""
    if dl_data:
        security_data = download_yfin_data(symbol)
    elif use_ch:
        security_data = get_data_from_ch_stock_data(symbol, start_date)
    else:
        security_data = read_series_data(symbol, source)

    if not is_series_within_date_range(security_data, start_date, end_date):
        # logger.warning(f"{symbol:<6} hasn't been on the market for the required duration. Skipping...")
        return None

    # Detrend
    security_data = security_data.diff().dropna()

    return security_data


def series_is_empty(series, symbol, file_path, dl_data=True) -> bool:
    # Check for duplicate column names and NaN only columns
    duplicate_columns = series.columns[series.columns.duplicated()].tolist()
    nan_only_columns = series.columns[series.isna().all()].tolist()
    if duplicate_columns or nan_only_columns:
        logger.warning(f"{symbol} Duplicate columns/NaN only columns. Deleting from metadata...")
        delete_symbol_from_metadata(symbol)
        with open(DATA_DIR / 'files_to_delete.txt', 'a') as f:
            f.write(f'{symbol}\n')
        return True

    # Check if the stock has data
    if series is None or series.empty or series.shape[0] == 0 or series.isna().all().all() or \
            series.dropna().nunique().nunique() == 1:
        logger.warning(f"{symbol} No data available. Deleting from metadata...")
        delete_symbol_from_metadata(symbol)
        with open(DATA_DIR / 'files_to_delete.txt', 'a') as f:
            f.write(f'{symbol}\n')
        return True

    return False


def is_series_within_date_range(series, start_date: str, end_date: str) -> bool:
    """Check if series is within date range, takes start_date format as either YYYY or YYYY-MM-DD"""
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)

    start_year = start_date.year
    start_month = start_date.month
    end_year = end_date.year
    end_month = end_date.month

    # Check if the stock has data since 'start year' and past 'end year'
    start_condition = series.index.min().year > start_year or (series.index.min().year == start_year and
                                                               series.index.min().month > start_month)
    end_condition = series.index.max().year < end_year or (series.index.max().year == end_year and
                                                           series.index.max().month < end_month)

    if start_condition or end_condition:
        return False
    return True


def is_series_within_date_range_new(series, start_date: str, end_date: str) -> bool:  # TODO
    """Check if series is within date range, takes start_date format as either YYYY or YYYY-MM-DD"""

    # Extracting year and month from the start_date and end_date
    start_year = int(start_date[:4])
    start_month = int(start_date[5:7]) if len(start_date) > 4 else 1
    end_year = int(end_date[:4])
    end_month = int(end_date[5:7]) if len(end_date) > 4 else 12

    # Check if the stock has data since 'start year' and past 'end year'
    start_condition = series.index.min().year > start_year or (series.index.min().year == start_year and
                                                               series.index.min().month > start_month)
    end_condition = series.index.max().year < end_year or (series.index.max().year == end_year and
                                                           series.index.max().month < end_month)

    if start_condition or end_condition:
        return False
    return True


def is_series_linear(series, symbol):
    window_length = int(len(series) / (35 + np.log1p(len(series))))
    window_length = max(window_length, 3)  # Ensure window_length is at least 1

    # print(f"Calculated window length: {window_length}")
    n = len(series)

    # Iterate through series
    for i in range(n - window_length + 1):
        window = series.iloc[i:i + window_length]

        # Check for constant values
        if np.all(window == window.iloc[0]):
            logger.warning(f"{symbol} has sections with {window_length} or more consecutive repeated values. "
                           f"Deleting from metadata...")
            with open(DATA_DIR / 'files_to_delete.txt', 'a') as f:
                f.write(f'{symbol}\n')
            return True

        # Check for constant slope (perfectly linear)
        differences = np.diff(window)
        if np.all(differences == differences[0]):
            logger.warning(f"{symbol} has sections with {window_length} or more consecutive linear values. "
                           f"Deleting from metadata...")
            with open(DATA_DIR / 'files_to_delete.txt', 'a') as f:
                f.write(f'{symbol}\n')
            return True

    return False


def is_series_repeating(series, symbol):
    window_length = int(len(series) / (35 + np.log1p(len(series))))
    window_length = max(window_length, 3)  # Ensure window_length is at least 3

    # print(f"Calculated window length: {window_length}")
    n = len(series)

    # Iterate through series
    for i in range(n - window_length + 1):
        window = series.iloc[i:i + window_length]
        if np.all(window == window.iloc[0]):
            logger.warning(f"{symbol} has sections with {window_length} or more consecutive repeated values. "
                           f"Deleting from metadata...")
            with open(DATA_DIR / 'files_to_delete.txt', 'a') as f:
                f.write(f'{symbol}\n')
            return True

    return False


def is_series_continuous(series, symbol: str) -> bool:
    """Check if series is continuous, allowing for up to window_size consecutive missing datapoints"""
    window_size = 10  # Define the size of the rolling window
    if series.rolling(window_size).apply(lambda x: all(np.isnan(x))).any():
        logger.warning(f"{symbol} has sections with {window_size} or more consecutive NaN values. Skipping...")
        with open(DATA_DIR / 'files_to_delete.txt', 'a') as f:
            f.write(f'{symbol}\n')
        return False
    return True


def pickle_securities_objects(security: Union[Security, FredSeries]):
    """Pickles a security object to re-use the calculations"""
    file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{security.symbol}.pkl'
    # Save dict of base security id's, and symbols that correlate with them for later use
    with open(file_path, 'wb') as pickle_file:
        pickle.dump(security, pickle_file)


def load_saved_securities(symbol: str) -> Union[Security, FredSeries]:
    """Loads and returns saved security objects from pickle files."""
    file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}.pkl'

    if file_path.exists():
        with open(file_path, 'rb') as pickle_file:
            security = pickle.load(pickle_file)
        return security
    else:
        print(f"No saved data found for symbol: {symbol}")


def get_fred_md_series_list() -> List[FredSeries]:
    """Create list of FredSeries objects from fred_md_metadata csv"""
    fred_md_metadata = pd.read_csv(FRED_DIR / 'fred_md_metadata.csv')

    # Filter rows where 'fred_md_id' is not null and not empty
    valid_rows = fred_md_metadata[pd.notnull(fred_md_metadata['fred_md_id']) & (fred_md_metadata['fred_md_id'] != '')]

    # Create a list of FredSeries objects using the 'fred_md_id' from the valid rows
    fred_series_list = [FredSeries(row['fred_md_id']) for _, row in valid_rows.iterrows()]

    return fred_series_list


def get_fred_md_series_data(series_id):
    """For getting a series from the FRED-MD dataset"""
    md_data = pd.read_csv(FRED_DIR / 'FRED_MD/MD_2023-08-02.csv')
    md_data = md_data.rename(columns={'sasdate': 'Date'})
    md_data['Date'] = pd.to_datetime(md_data['Date'])

    # Extract the 'series_id' column for correlation
    md_data = md_data.set_index('Date')[series_id]

    return md_data


def fit_data_to_time_range(series_data, start_date):
    # Makes sure the data starts at the start date, or its earliest datapoint
    start_datetime = pd.to_datetime(start_date)
    start_datetime = max(start_datetime, series_data.index.min())
    series_data = series_data.loc[start_datetime:]
    return series_data


def initialize_fin_db_stock_metadata():
    equities = fd.Equities()
    df = equities.select()
    df.to_csv(STOCKS_DIR / 'FinDB/fin_db_stock_data.csv')


def delete_symbol_from_metadata(symbol):
    # Read the CSV into a DataFrame
    etf_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_etf_data.csv', index_col='symbol')
    stock_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_stock_data.csv', index_col='symbol')
    index_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_indices_data.csv', index_col='symbol')

    with open(STOCKS_DIR / 'all_stock_symbols.txt', 'r') as file:
        all_symbols = file.read().splitlines()

    if symbol in stock_metadata.index:
        stock_metadata = stock_metadata.drop(symbol)

        stock_metadata.to_csv(STOCKS_DIR / 'FinDB/updated_fin_db_stock_data.csv')
    if symbol in all_symbols:
        # Remove lines that match the string
        lines = [line for line in all_symbols if line != symbol]

        # Write the modified lines back to the file
        with open(STOCKS_DIR / 'all_stock_symbols.txt', 'w') as file:
            for line in lines:
                file.write(line + '\n')

    # Check if the string exists in the 'symbol' column
    elif symbol in etf_metadata.index:
        etf_metadata = etf_metadata.drop(symbol)
        etf_metadata.to_csv(STOCKS_DIR / 'FinDB/updated_fin_db_etf_data.csv')

    elif symbol in index_metadata.index:
        index_metadata = index_metadata.drop(symbol)
        index_metadata.to_csv(STOCKS_DIR / 'FinDB/updated_fin_db_indices_data.csv')
