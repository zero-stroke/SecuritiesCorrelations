import json
# Configure the logger at the module level
import logging
import time
from datetime import datetime
from multiprocessing import Manager
from typing import List, Dict, Optional, Iterable
from finagg import fred

import pandas as pd
from requests import HTTPError
from unicodedata import normalize

from config import STOCKS_DIR, FRED_DIR, securities_metadata, FRED_KEY, start_years

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Set to WARNING for production; DEBUG for development


class FredSeriesBase:
    def __init__(self, _id, id_type):
        self.symbol = _id
        fred_metadata = pd.read_csv(FRED_DIR / 'fred_md_metadata.csv')
        try:
            row = fred_metadata[fred_metadata[id_type] == _id].iloc[0]
        except IndexError:
            raise IndexError(f'{_id} does not exist.')

        self.fred_md_id = row['fred_md_id']
        self.api_id = row['api_id']
        self.name = row['title']
        self.source_title = row['source_title']
        self.source_link = row['source_link']
        self.release_title = row['release_title']
        self.release_link = row['release_link']
        self.tcode = row['tcode']
        self.frequency = row['frequency']
        self.latex_equation = self.get_latex_equation()
        self.series_data: pd.Series = {}
        self.series_data_detrended: pd.DataFrame = {}
        self.positive_correlations, self.negative_correlations, self.all_correlations = self.initialize_correlations()

    def initialize_correlations(self):
        return (
            {start_date: [] for start_date in start_years},
            {start_date: [] for start_date in start_years},
            {start_date: {} for start_date in start_years}
        )

    def get_latex_equation(self):
        latex_eq_dict = {
            1: r"No transformation",
            2: r"$\Delta x_t$",
            3: r"$\Delta^2 x_t$",
            4: r"$\log(x_t)$",
            5: r"$\Delta \log(x_t)$",
            6: r"$\Delta^2 \log(x_t)$",
            7: r"$\Delta (x_t/x_{t−1} - 1.0)$"
        }
        return latex_eq_dict.get(self.tcode, "Unknown transformation code")

    def get_unique_values(self, attribute_name: str, start_date) -> List[str]:
        unique_values = set()
        unique_values.update(getattr(security, attribute_name) for security in
                             self.positive_correlations[start_date] if getattr(security, attribute_name))
        unique_values.update(getattr(security, attribute_name) for security in
                             self.negative_correlations[start_date] if getattr(security, attribute_name))
        return list(unique_values)

    def __str__(self):
        return f"Symbol: {self.symbol}, Name: {self.name}, Source: {self.source_title}"

    def __repr__(self):
        return (
                "FredSeries(fred_md_id=" + f"{self.fred_md_id}\n"
                + "api_id=" + f"{self.api_id}\n"
                + "title=" + f"{self.name}\n"
                + "source_title=" + f"{self.source_title}\n"
                + "tcode=" + f"{self.tcode}\n"
                + f"frequency={self.frequency})"
        )

    def __hash__(self):  # Make the instance hashable using its symbol attribute
        return hash(self.symbol)

    def __eq__(self, other) -> bool:
        if isinstance(other, Security):
            return self.symbol == other.symbol
        return False

    def to_dict(self):
        return self.__dict__


class FredapiSeries(FredSeriesBase):
    def __init__(self, api_id, revised):
        super().__init__(api_id, 'api_id')
        if not revised:
            self.name = self.name + ' (UNREVISED)'
        self.set_fred_series(revised)

    def set_fred_series(self, revised):
        """For getting a series from the FRED API"""
        if revised:
            while True:
                try:
                    df = fred.api.series.observations.get_first_observations(
                        self.symbol,
                        observation_start="1980-02-27",
                        observation_end="2023-06-29",
                        api_key=FRED_KEY,
                    )
                    break
                except HTTPError as err:
                    if '429' in str(err):  # Too Many Requests error
                        time.sleep(5)  # Sleep for 5 seconds before trying again
                    else:  # For any other HTTP error, just raise the error to be handled in the main loop
                        raise
        else:
            while True:
                try:
                    df = fred.api.series.observations.get(
                        self.symbol,
                        observation_start="1980-02-27",
                        observation_end="2023-06-29",
                        api_key=FRED_KEY,
                    )
                    break
                except HTTPError as err:
                    if '429' in str(err):
                        time.sleep(5)
                    else:
                        raise

        # Rename the 'date' column to 'Date'
        df = df.rename(columns={'date': 'Date'})
        df = df.rename(columns={'value': self.symbol})

        # Convert the 'Date' column to datetime
        df['Date'] = pd.to_datetime(df['Date'])

        # Set the 'Date' column as the index
        df = df.set_index('Date')[self.symbol]

        for year in start_years:
            self.series_data[year] = df[df.index.year >= int(year)]
            detrended_series = self.series_data[year].diff().dropna()
            self.series_data_detrended[year] = detrended_series.to_frame(name='main')


class FredmdSeries(FredSeriesBase):
    def __init__(self, fred_md_id):
        super().__init__(fred_md_id, 'fred_md_id')
        self.set_fred_series()

    def set_fred_series(self):
        """For getting a series from the FRED-MD dataset"""
        md_data = pd.read_csv(FRED_DIR / 'FRED_MD/MD_2023-08-02.csv')
        md_data = md_data.rename(columns={'sasdate': 'Date'})

        md_data['Date'] = pd.to_datetime(md_data['Date'])

        # Extract the 'series_id' column for correlation
        md_data = md_data.set_index('Date')[self.fred_md_id]

        for year in start_years:
            self.series_data[year] = md_data[md_data.index.year >= int(year)]
            detrended_series = self.series_data[year].diff().dropna()
            self.series_data_detrended[year] = detrended_series.to_frame(name='main')


class SharedMemoryCache:
    def __init__(self):
        manager = Manager()
        self.data_dict = manager.dict()
        self.hits = manager.Value('i', 0)  # Create a shared integer with initial value 0
        self.misses = manager.Value('i', 0)  # Create a shared integer with initial value 0

    def set(self, symbol, data):
        self.data_dict[symbol] = data

    def get(self, symbol):
        data = self.data_dict.get(symbol, None)
        if data is not None:
            self.hits.value += 1
        else:
            self.misses.value += 1
        return data

    def get_hits(self):
        return self.hits.value

    def get_misses(self):
        return self.misses.value


class Security:
    def __init__(self, symbol: str):
        self.symbol: str = symbol
        self.name: Optional[str] = None
        self.summary: Optional[str] = None
        self.sector: Optional[str] = None
        self.industry_group: Optional[str] = None
        self.industry: Optional[str] = None
        self.market: Optional[str] = None
        self.country: Optional[str] = None
        self.state: Optional[str] = None
        self.city: Optional[str] = None
        self.website: Optional[str] = None
        self.market_cap: Optional[str] = None
        self.source: Optional[str] = ''
        self.correlation: Optional[float] = None
        self.series_data: Optional[Dict[str, pd.Series]] = {}
        self.series_data_detrended: Optional[Dict[str, pd.DataFrame]] = {}

        self.positive_correlations: Dict[str, List[Security]] = \
            {start_date: [] for start_date in ['2010', '2018', '2021', '2022', '2023']}
        self.negative_correlations: Dict[str, List[Security]] = \
            {start_date: [] for start_date in ['2010', '2018', '2021', '2022', '2023']}

        self.all_correlations: Dict[str, Optional[Dict[str, float]]] = \
            {start_date: {} for start_date in ['2010', '2018', '2021', '2022', '2023']}

        self.get_symbol_name_and_type()  # Set the name and type during initialization

    def set_series_data(self):
        """Reads data from file and sets it to 'series_data' dictionary with years as keys."""
        file_path = STOCKS_DIR / f'yahoo_daily/parquets/{self.symbol}.parquet'
        try:
            full_series = pd.read_parquet(file_path)['Adj Close']
        except FileNotFoundError:
            logger.warning(f'{file_path} does not exist')
            return None

        # Filter series for each start year and store in series_data dictionary
        for year in start_years:
            self.series_data[year] = full_series[full_series.index.year >= int(year)]
            detrended_series = self.series_data[year].diff().dropna()
            self.series_data_detrended[year] = detrended_series.to_frame(name='main')

    def set_correlation(self, value: float) -> None:
        self.correlation = value

    def set_properties_from_metadata(self, metadata: pd.Series, source_type: str) -> None:
        def set_property(name_of_attribute: str, default_val: str = 'Missing') -> None:
            # If name is 'one', 'two', or 'RH', set the attribute to 'Missing' and return
            if self.name in ('one', 'two', 'RH'):
                setattr(self, name_of_attribute, default_val)
                return

            # Otherwise, get the value of the attribute from the metadata
            raw_value = metadata.get(name_of_attribute, '')
            # Normalize the value in cases of non-standard values
            normalized_value = normalize('NFKD', str(raw_value)).encode('ascii', 'ignore').decode() or None
            setattr(self, name_of_attribute, normalized_value or default_val)

        # Safely set the name attribute
        self.name = normalize('NFKD', str(metadata.get('name', ''))).encode('ascii', 'ignore').decode()

        # Use the loop to set the attributes
        for attribute_name in ['summary', 'sector', 'industry_group', 'industry', 'market', 'country', 'state', 'city',
                               'website']:
            set_property(attribute_name)

        # Set market_cap and source attributes
        self.market_cap = \
            normalize('NFKD', str(metadata.get('market_cap', ''))).encode('ascii', 'ignore').decode() or None
        self.source = source_type

    def get_symbol_name_and_type(self) -> None:
        etf_metadata, stock_metadata, index_metadata = securities_metadata

        # Check for Stock metadata
        if stock_metadata is not None and self.symbol in stock_metadata.index:
            stock_data = stock_metadata.loc[self.symbol]
            self.set_properties_from_metadata(stock_data, 'stock')

        # Check for ETF metadata
        if etf_metadata is not None and self.symbol in etf_metadata.index:
            etf_data = etf_metadata.loc[self.symbol]
            self.set_properties_from_metadata(etf_data, 'etf')

        # Check for Index metadata
        if index_metadata is not None and self.symbol in index_metadata.index:
            index_data = index_metadata.loc[self.symbol]
            self.set_properties_from_metadata(index_data, 'index')

    def get_unique_values(self, attribute_name: str, start_date) -> List[str]:
        """Returns a list of a correlation_list's unique values for a given attribute"""
        unique_values = set()

        # Get values from positive_correlations
        unique_values.update(getattr(security, attribute_name) for security in
                             self.positive_correlations[start_date] if getattr(security, attribute_name))

        # Get values from negative_correlations
        unique_values.update(getattr(security, attribute_name) for security in
                             self.negative_correlations[start_date] if getattr(security, attribute_name))

        return list(unique_values)

    def __hash__(self) -> int:
        # Make the instance hashable using its symbol attribute
        return hash(self.symbol)

    def __eq__(self, other) -> bool:
        if isinstance(other, Security):
            return self.symbol == other.symbol
        return False

    def __str__(self) -> str:
        return f"Symbol: {self.symbol}, Name: {self.name}, Source: {self.source}, Sector: {self.sector} \n"

    def __repr__(self) -> str:
        return f"Symbol: {self.symbol}, Name: {self.name}, Source: {self.source}, Sector: {self.sector}," \
               f" Industry_group: {self.industry_group}, Industry: {self.industry}, Market: {self.market}, Country: " \
               f"{self.country}, State: {self.state}, City: {self.city}, Website: {self.website}, Market Cap: " \
               f"{self.market_cap}'\n"


class EnhancedEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'tolist'):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(EnhancedEncoder, self).default(obj)


class EnhancedEncoder2(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Iterable) and not isinstance(obj, str):
            return list(obj)
        return super(EnhancedEncoder2, self).default(obj)


SERIES_DICT = {
    "CMRMTSPL": "CMRMTSPLx",
    "RSAFS": "RETAILx",
    "JTSJOL": "HWI",
    "ICNSA": "CLAIMSx",
    "DGORDER": "AMDMNOx",
    "ANDENO": "ANDENOx",
    "AMDMUO": "AMDMUOx",
    "BUSINV": "BUSINVx",
    "ISRATIO": "ISRATIOx",
    "CPF3M": "CP3Mx",
    "TWEXAFEGSMTH": "TWEXAFEGSMTHx",
    "EXSZUS": "EXSZUSx",
    "EXJPUS": "EXJPUSx",
    "EXUSUK": "EXUSUKx",
    "EXCAUS": "EXCAUSx",
    "MCOILWTICO": "OILPRICEx",
    "UMCSENT": "UMCSENTx",
    "VIXCLS": "VIXCLSx",
    "UNEMPLOY": "HWIURATIO",
    "NONREVSL": "CONSPI",
    "FEDFUNDS": "COMPAPFFx",
    "VIXCLSx": "VIXCLSx"
}
