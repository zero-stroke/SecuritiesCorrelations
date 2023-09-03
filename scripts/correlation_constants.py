import json
import os
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

import numpy
import pandas as pd
from unicodedata import normalize

from config import STOCKS_DIR, FRED_DIR


class DataSource(Enum):
    ETF = "etf"
    STOCK = "stock"
    INDEX = "index"


class SecurityMetadata:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecurityMetadata, cls).__new__(cls)
            # Load ETF, Stock, and Index data
            cls._instance.etf_metadata = \
                pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_etf_data.csv', index_col='symbol')
            cls._instance.stock_metadata =\
                pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_stock_data.csv', index_col='symbol')
            cls._instance.index_metadata = \
                pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_indices_data.csv', index_col='symbol')
        return cls._instance

    def build_symbol_list(self, etf: bool = False, stock: bool = True, index: bool = False) -> List[str]:
        """Build list of symbols from the given data sources."""
        symbols = []

        if etf and self.etf_metadata is not None:
            etf_metadata_filtered = self.etf_metadata[self.etf_metadata['market'].notna() &
                                                      self.etf_metadata['exchange'].notna() &
                                                      self.etf_metadata['family'].notna()]
            symbols.extend(etf_metadata_filtered.index.tolist())

        if stock and self.stock_metadata is not None:

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

        if index and self.index_metadata is not None:
            index_metadata_filtered = self.index_metadata[self.index_metadata['name'].notna()]
            symbols.extend(index_metadata_filtered.index.tolist())

        return symbols


class Security:
    def __init__(self, symbol: str, metadata: SecurityMetadata):
        self.symbol: str = symbol
        self.metadata = metadata
        self.name: Optional[str] = None  # Set it to None initially
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
        self.source: Optional[str] = ''  # Initialize to an empty string
        self.correlation: Optional[float] = None  # Initialized to None, can be updated later
        self.positive_correlations: List[Security] = []  # List of Security objects
        self.negative_correlations: List[Security] = []  # List of Security objects
        self.positive_correlations_2018: List[Security] = []  # Future use
        self.negative_correlations_2018: List[Security] = []  # Future use
        self.positive_correlations_2021: List[Security] = []  # Future use
        self.negative_correlations_2021: List[Security] = []  # Future use
        self.positive_correlations_2022: List[Security] = []  # Future use
        self.negative_correlations_2022: List[Security] = []  # Future use
        self.positive_correlations_2023: List[Security] = []  # Future use
        self.negative_correlations_2023: List[Security] = []  # Future use
        self.positive_correlations_1m: List[Security] = []  # Future use
        self.negative_correlations_1m: List[Security] = []  # Future use
        self.positive_correlations_1w: List[Security] = []  # Future use, would have to use weekly Alpaca data
        self.negative_correlations_1w: List[Security] = []  # Future use, would have to use weekly Alpaca data
        self.all_correlations: Dict[str, float] = {}  # Dictionary with string keys and float values
        self.all_correlations_2018: Dict[str, float] = {}  # Dictionary with string keys and float values
        self.all_correlations_2021: Dict[str, float] = {}  # Dictionary with string keys and float values
        self.all_correlations_2022: Dict[str, float] = {}  # Dictionary with string keys and float values
        self.all_correlations_2023: Dict[str, float] = {}  # Dictionary with string keys and float values
        self.all_correlations_1m: Dict[str, float] = {}  # Dictionary with string keys and float values
        self.all_correlations_1w: Dict[str, float] = {}  # Dictionary with string keys and float values

        self.get_symbol_name_and_type()  # Set the name and type during initialization

    def get_series_data(self) -> Optional[pd.Series]:
        """Reads data from file and sets it to 'series' attribute"""
        file_path = STOCKS_DIR / f'yahoo_daily/parquets/{self.symbol}.parquet'
        if not os.path.exists(file_path):
            print(f'{file_path} does not exist')
            return None
        series = pd.read_parquet(file_path)
        if 'Date' in series.columns:
            series['Date'] = pd.to_datetime(series['Date'])
            series = series.set_index('Date')['Adj Close']
        else:
            series.index = pd.to_datetime(series.index)
        series = series['Adj Close']

        return series

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
        # Check for ETF metadata
        if self.metadata.etf_metadata is not None and self.symbol in self.metadata.etf_metadata.index:
            etf_data = self.metadata.etf_metadata.loc[self.symbol]
            self.set_properties_from_metadata(etf_data, 'etf')

        # Check for Stock metadata
        if self.metadata.stock_metadata is not None and self.symbol in self.metadata.stock_metadata.index:
            stock_data = self.metadata.stock_metadata.loc[self.symbol]
            self.set_properties_from_metadata(stock_data, 'stock')

        # Check for Index metadata
        if self.metadata.index_metadata is not None and self.symbol in self.metadata.index_metadata.index:
            index_data = self.metadata.index_metadata.loc[self.symbol]
            self.set_properties_from_metadata(index_data, 'index')

    def get_unique_values(self, attribute_name: str) -> List[str]:
        """Returns a list of a correlation_list's unique values for a given attribute"""
        unique_values = set()

        # Get values from positive_correlations
        unique_values.update(getattr(security, attribute_name) for security in self.positive_correlations if
                             getattr(security, attribute_name))

        # Get values from negative_correlations
        unique_values.update(getattr(security, attribute_name) for security in self.negative_correlations if
                             getattr(security, attribute_name))

        return list(unique_values)

    def __hash__(self) -> int:
        # Make the instance hashable using its symbol attribute
        return hash(self.symbol)

    def __str__(self) -> str:
        return f"Symbol: {self.symbol}, Name: {self.name}, Source: {self.source}, Correlation: {self.correlation}, " \
               f"Top Correlations: {[obj.symbol for obj in self.positive_correlations[:5]]}"

    def __repr__(self) -> str:
        return f"Symbol: {self.symbol}, Name: {self.name}, Source: {self.source}, Correlation: {self.correlation}, " \
               f"Top Correlations: {[obj.symbol for obj in self.positive_correlations[:5]]}"


# Define Series class with data about each series. Needs self.update_time to be added
class FredSeries:
    def __init__(self, fred_md_id, api_id, name, tcode, frequency, source_title, source_link, release_title,
                 release_link):
        self.fred_md_id = fred_md_id
        self.symbol = fred_md_id
        self.api_id = api_id
        self.name = name
        self.source_title = source_title
        self.source_link = source_link
        self.release_title = release_title
        self.release_link = release_link
        self.tcode = tcode
        self.frequency = frequency
        self.latex_equation = self.get_latex_equation()
        self.positive_correlations: List[Security] = []  # List of Security objects
        self.negative_correlations: List[Security] = []  # List of Security objects
        self.all_correlations: Dict[str, float] = {}  # Dictionary with string keys and float values

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

    def __repr__(self):
        return (
                "FredSeries(fred_md_id=" + f"{self.fred_md_id:<17},"
                + " api_id=" + f"{self.api_id:<17}"
                + " title=" + f"{self.name:<80}"
                + " source_title=" + f"{self.source_title:<35},"
                + " tcode=" + f"{self.tcode:<4}"
                + f" frequency={self.frequency})"
        )

    def get_fredmd_series(self):
        """For getting a series from the FRED-MD dataset"""
        md_data = pd.read_csv(FRED_DIR / 'FRED_MD/MD_2023-08-02.csv')
        md_data = md_data.rename(columns={'sasdate': 'Date'})
        md_data['Date'] = pd.to_datetime(md_data['Date'])

        # Extract the 'series_id' column for correlation
        md_data = md_data.set_index('Date')[self.fred_md_id]

        return md_data

    def __hash__(self):
        # Make the instance hashable using its symbol attribute
        return hash(self.symbol)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return f"Symbol: {self.symbol}, Name: {self.name}, Source: {self.source_title}, " \
               f"Top Correlations: {[obj.symbol for obj in self.positive_correlations[:5]]}"


class EnhancedEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(EnhancedEncoder, self).default(obj)


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
