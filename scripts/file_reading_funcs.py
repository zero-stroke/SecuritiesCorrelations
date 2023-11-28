import logging
import pickle
import threading
import traceback
from functools import lru_cache
from functools import wraps
from typing import List, Set

import financedatabase as fd
import numpy as np
import pandas as pd
import yfinance as yf
from finagg import fred

from config import STOCKS_DIR, FRED_DIR, DATA_DIR, FRED_KEY
from scripts.clickhouse_functions import get_data_from_ch_stock_data
from scripts.correlation_constants import Security, logger, FredmdSeries, FredapiSeries, \
    etf_metadata, index_metadata, stock_metadata, observation_end

# Configure the logger at the module level
log_format = '%(asctime)s - %(message)s'
date_format = '%H:%M:%S'

logging.basicConfig(filename='cache_info.log', level=logging.INFO,
                    format=log_format, datefmt=date_format, filemode='a')

# def initialize_shared_objects():  # Related to caching while using multiprocessing
#     global shared_cache, cache_lock
#     manager = Manager()
#     shared_cache = manager.dict()
#     cache_lock = manager.Lock()


cache_lock = threading.Lock()
shared_cache = {}


def cache_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        logging.info(f"Function {func.__name__}, Args {args}."
                     f" {func.cache_info()}")
        return result

    return wrapper


@lru_cache(maxsize=None)
def read_series_data(symbol: str, source: str) -> pd.Series | None:
    """Looks for a symbol in yahoo_daily directory and returns its 'Adj Close' column."""
    with cache_lock:
        try:
            if source == 'yahoo':
                file_path = STOCKS_DIR / f'yahoo_daily/parquets/{symbol}.parquet'
                series = pd.read_parquet(file_path)
                return series['Adj Close']
            elif source == 'alpaca':
                print("Alpaca coming soon")
            else:
                raise ValueError("Unknown source")
        except FileNotFoundError as e:
            raise ValueError(f"File not found{e}")
            # df: pd.DataFrame = fred.api.series.observations.get_first_observations(
            #     symbol, observation_start="1980-02-27", observation_end=observation_end, api_key=FRED_KEY,
            # )
            # df: pd.DataFrame = df.rename(columns={'date': 'Date'})
            # df = df.rename(columns={'value': symbol})
            # df['Date'] = pd.to_datetime(df['Date'])
            # trace_series: pd.Series = df.set_index('Date')[symbol]
            # return trace_series


# @cache_info
@lru_cache(maxsize=None)
def original_get_validated_security_data(symbol: str, start_date: str, end_date: str, source: str, dl_data: bool,
                                         use_ch: bool) -> pd.DataFrame:
    """Get security data from file, make sure it's within range and continuous"""
    if dl_data:
        security_data = download_yfin_data(symbol)
    elif use_ch:
        security_data = get_data_from_ch_stock_data(symbol, start_date)
    else:
        security_data = read_series_data(symbol, source)

    # ## The below code is necessary if you have a lot of files that contain "jumk" data, that need to be filtered out.
    # # Data validation steps, most do not need to be used on every run
    # # DELETES SERIES FROM METADATA FILE
    # if series_is_empty(security_data, symbol):
    #     raise AttributeError(f"{symbol:<6} is empty. Skipping...")
    #
    # # Takes up a lot of time
    # if is_series_repeating(security_data, symbol):
    #     raise AttributeError(f"{symbol:<6} isn't continuous. Skipping...")
    #
    # if not is_series_continuous(security_data, symbol):
    #     raise AttributeError(f"{symbol:<6} isn't continuous. Skipping...")

    # Only one that is necessary during all runs
    if not is_series_within_date_range(security_data, start_date, end_date):
        # logger.warning(f"{symbol:<6} hasn't been on the market for the required duration. Skipping...")
        raise AttributeError(f"{symbol:<6} hasn't been on the market for the required duration. Skipping...")

    # Detrend
    security_data = security_data.diff().dropna()
    security_data = security_data[security_data.index.year >= int(start_date[:4])]
    security_data = security_data.to_frame(name='symbol')

    return security_data


def series_is_empty(series, symbol) -> bool:
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


def pickle_securities_objects(security: Security | FredapiSeries | FredmdSeries, source: str):
    """Pickles a security object to re-use the calculations"""
    symbol = security.symbol

    file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}.pkl'
    if source == 'FREDMD':
        file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}_fred.pkl'
    elif source == 'FREDAPI':
        file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}_fredapi.pkl'
    elif source == 'FREDAPIOG':
        file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}_fredapi_og.pkl'
    # Save dict of base security id's, and symbols that correlate with them for later use
    with open(file_path, 'wb') as pickle_file:
        pickle.dump(security, pickle_file)


def load_saved_securities(symbol: str, source: str) -> Security | FredapiSeries | FredmdSeries:
    """Loads and returns saved security objects from pickle files."""
    if source == 'SECURITIES':
        file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}.pkl'
    elif source == 'FREDMD':
        file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}_fred.pkl'
    elif source == 'FREDAPI':
        file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}_fredapi.pkl'
    elif source == 'FREDAPIOG':
        file_path = DATA_DIR / f'Graphs/pickled_securities_objects/{symbol}_fredapi_og.pkl'
    else:
        raise ValueError(f"Unrecognized source: {source}")

    if file_path.exists():
        with open(file_path, 'rb') as pickle_file:
            security = pickle.load(pickle_file)
        return security
    else:
        print(f"No saved data found for symbol: {symbol}")


def get_fred_md_series_list() -> Set[FredmdSeries]:
    """Create list of FredSeries objects from fred_md_metadata csv"""
    fred_md_metadata = pd.read_csv(FRED_DIR / 'fred_md_metadata.csv')

    # Filter rows where 'fred_md_id' is not null and not empty
    valid_rows = fred_md_metadata[pd.notnull(fred_md_metadata['fred_md_id']) & (fred_md_metadata['fred_md_id'] != '')]

    # Create a list of FredSeries objects using the 'fred_md_id' from the valid rows
    fred_series_list = {FredmdSeries(row['fred_md_id']) for _, row in valid_rows.iterrows()}

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
    # Makes sure series_data starts at the start date, or its earliest datapoint
    start_datetime = pd.to_datetime(start_date)
    start_datetime = max(start_datetime, series_data.index.min())
    series_data = series_data.loc[start_datetime:]
    return series_data


def initialize_fin_db_stock_metadata():
    equities = fd.Equities()
    df = equities.select()
    df.to_csv(STOCKS_DIR / 'FinDB/fin_db_stock_data.csv')


def delete_symbol_from_metadata(symbol: str):
    """For when cleaning out the metadata files to remove junk data."""
    with open(STOCKS_DIR / 'all_stock_symbols.txt', 'r') as file:
        all_symbols = file.read().splitlines()

    if symbol in stock_metadata.index:
        stock_metadata_new = stock_metadata.drop(symbol)

        stock_metadata_new.to_csv(STOCKS_DIR / 'FinDB/updated_fin_db_stock_data.csv')
    if symbol in all_symbols:
        # Remove lines that match the string
        lines = [line for line in all_symbols if line != symbol]

        # Write the modified lines back to the file
        with open(STOCKS_DIR / 'all_stock_symbols.txt', 'w') as file:
            for line in lines:
                file.write(line + '\n')

    # Check if the string exists in the 'symbol' column
    elif symbol in etf_metadata.index:
        etf_metadata_new = etf_metadata.drop(symbol)
        etf_metadata_new.to_csv(STOCKS_DIR / 'FinDB/updated_fin_db_etf_data.csv')

    elif symbol in index_metadata.index:
        index_metadata_new = index_metadata.drop(symbol)
        index_metadata_new.to_csv(STOCKS_DIR / 'FinDB/updated_fin_db_indices_data.csv')


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


def download_findb_data():  # Test if this works properly later
    indices = fd.Indices()
    indices.select().to_csv(STOCKS_DIR / 'FinDB/fin_db_indices2.csv')


def build_symbol_list(etf: bool = False, stock: bool = True, index: bool = False) -> List[str]:
    """Build list of symbols from the given data sources."""
    symbols = []

    if etf:
        etf_metadata_filtered = etf_metadata[etf_metadata['market'].notna() &
                                             etf_metadata['exchange'].notna() &
                                             etf_metadata['family'].notna()]
        symbols.extend(etf_metadata_filtered.index.tolist())

    if stock:

        # Use a txt file with all stock symbols
        stock_composite_list = []
        with open(STOCKS_DIR / 'all_stock_symbols.txt', 'r') as f:
            for line in f.readlines():
                stock_composite_list.append(line.strip())

        # # Use only data from the metadata csv
        # stock_metadata_filtered = \
        #     self.stock_metadata[~self.stock_metadata['market_cap'].isin(['Nano Cap', 'Micro Cap']) &
        #                         self.stock_metadata['market_cap'].notna()]

        symbols.extend(stock_composite_list)

    if index:
        index_metadata_filtered = index_metadata[index_metadata['name'].notna()]
        symbols.extend(index_metadata_filtered.index.tolist())

    return symbols


def get_all_fred_api_series_ids() -> List[str]:
    with open(FRED_DIR / 'FRED_all_series.txt', 'r') as f:
        fred_api_symbols = [symbol.strip() for symbol in f.readlines()]

    return fred_api_symbols


def get_all_fredmd_series_ids() -> List[str]:
    fred_md_metadata = pd.read_csv(FRED_DIR / 'fred_md_metadata.csv')

    return fred_md_metadata[fred_md_metadata['fred_md_id'].notna()]['fred_md_id'].tolist()
