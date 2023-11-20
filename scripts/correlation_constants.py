import json
import logging
import time
from datetime import datetime
from multiprocessing import Manager
from typing import List, Dict, Optional, Iterable, Callable
from finagg import fred

import pandas as pd
from requests import HTTPError
from unicodedata import normalize

from config import STOCKS_DIR, FRED_DIR, FRED_KEY

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Set to WARNING for production; DEBUG for development

etf_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_etf_data.csv', index_col='symbol')
stock_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_stock_data.csv', index_col='symbol')
index_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_indices_data.csv', index_col='symbol')
start_years = ['2010', '2017', '2018', "2019", "2020", '2021', '2022', '2023']
observation_end = "2023-06-29"

latex_eq_dict = {
    1: r"No transformation",
    2: r"$\Delta x_t$",
    3: r"$\Delta^2 x_t$",
    4: r"$\log(x_t)$",
    5: r"$\Delta \log(x_t)$",
    6: r"$\Delta^2 \log(x_t)$",
    7: r"$\Delta (x_t/x_{t−1} - 1.0)$"
}


class BaseSeries:
    def __init__(self, symbol=""):
        self.symbol = symbol
        self.name = symbol
        self.series_data: Dict[str, pd.Series] = {key: None for key in start_years}  # Dict of each year
        self.series_data_detrended: Dict[str, pd.DataFrame] = {key: None for key in start_years}
        self.positive_correlations: Dict[str, List[Security]] = {start_date: [] for start_date in start_years}
        self.negative_correlations: Dict[str, List[Security]] = {start_date: [] for start_date in start_years}
        self.all_correlations: Dict[str, Dict[str, float]] | None = {start_date: {} for start_date in start_years}

    def set_data_years(self, series: pd.Series):
        for start_year in start_years:
            # index: pd.DatetimeIndex = pd.DatetimeIndex(series.index)
            # self.series_data[start_year] = series[index.year >= int(start_year)]
            self.series_data[start_year] = series[series.index.year >= int(start_year)]

            detrended_series = self.series_data[start_year].diff().dropna()
            self.series_data_detrended[start_year] = detrended_series.to_frame(name='main')  # !! Not needed

    def get_unique_values(self, attribute_name: str, start_date) -> List[str]:
        """Returns a list of a correlation_list's unique values for a given attribute"""
        unique_values = set()  # TO BE COMBINED TO BASESERIES CLASS
        unique_values.update(getattr(security, attribute_name) for security in
                             self.positive_correlations[start_date] if getattr(security, attribute_name))
        unique_values.update(getattr(security, attribute_name) for security in
                             self.negative_correlations[start_date] if getattr(security, attribute_name))
        return list(unique_values)


class Security(BaseSeries):
    def __init__(self, symbol: str):
        super().__init__()
        self.symbol: str = symbol
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
        self.get_symbol_name_and_type()  # Set the name and type during initialization

    def set_series_data(self):
        """Reads data from file and sets it to 'series_data' dictionary with years as keys."""
        from scripts.file_reading_funcs import read_series_data
        series: pd.Series = read_series_data(self.symbol, source='yahoo')

        self.set_data_years(series)

    def set_correlation(self, value: float) -> None:
        self.correlation = value

    def set_properties_from_metadata(self, metadata: pd.Series, source_type: str) -> None:
        def set_property(name_of_attribute: str, default_val: str = 'Missing') -> None:
            # If name is 'one', 'two', or 'RH', set the attribute to 'Missing' and return
            if self.name in ('one', 'two', 'RH'):
                setattr(self, name_of_attribute, default_val)
                return
            value = metadata.get(name_of_attribute, '')  # Otherwise, get the value of the attribute from the metadata
            # Normalize the value in cases of non-standard values
            normalized_value = normalize('NFKD', str(value)).encode('ascii', 'ignore').decode() or None
            setattr(self, name_of_attribute, normalized_value or default_val)

        # Safely set the name attribute
        self.name = normalize('NFKD', str(metadata.get('name', ''))).encode('ascii', 'ignore').decode()

        for attribute_name in ['summary', 'sector', 'industry_group', 'industry', 'market', 'country', 'state', 'city',
                               'website']:  # Use the loop to set the attributes
            set_property(attribute_name)

        self.market_cap = \
            normalize('NFKD', str(metadata.get('market_cap', ''))).encode('ascii', 'ignore').decode() or None
        self.source = source_type

    def get_symbol_name_and_type(self) -> None:
        if stock_metadata is not None and self.symbol in stock_metadata.index:  # Check for Stock metadata
            stock_data = stock_metadata.loc[self.symbol]
            self.set_properties_from_metadata(stock_data, 'stock')

        if etf_metadata is not None and self.symbol in etf_metadata.index:  # Check for ETF metadata
            etf_data = etf_metadata.loc[self.symbol]
            self.set_properties_from_metadata(etf_data, 'etf')

        if index_metadata is not None and self.symbol in index_metadata.index:  # Check for Index metadata
            index_data = index_metadata.loc[self.symbol]
            self.set_properties_from_metadata(index_data, 'index')

    def __hash__(self) -> int:
        return hash(self.symbol)  # Make the instance hashable using its symbol attribute

    def __eq__(self, other) -> bool:
        if isinstance(other, Security):
            return self.symbol == other.symbol
        return False

    def __str__(self) -> str:
        return f"Symbol: {self.symbol}, Name: {self.name}, Source: {self.source}, Sector: {self.sector} \n"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        attrs = [
            f"symbol={self.symbol!r}",
            f"name={self.name!r}",
            f"sector={self.sector!r}",
            f"industry_group={self.industry_group!r}",
            f"industry={self.industry!r}",
            f"market={self.market!r}",
            f"country={self.country!r}",
            f"state={self.state!r}",
            f"city={self.city!r}",
            f"website={self.website!r}",
            f"market_cap={self.market_cap!r}",
            f"source={self.source!r}"
        ]

        series_data_summary = f"series_data_years={list(self.series_data.keys())}"

        # Calculate the positive correlations count separately
        positive_correlations_count = {year: len(corrs) for year, corrs in self.positive_correlations.items()}
        pos_corr_summary = f"positive_correlations_count={positive_correlations_count}"

        attrs_str = "\n".join(attrs + [series_data_summary, pos_corr_summary])
        return f"{class_name}(\n{attrs_str}\n)"


class FredSeriesBase(BaseSeries):
    def __init__(self, symbol, id_type):
        super().__init__()
        self.symbol = symbol
        fred_metadata: pd.DataFrame = pd.read_csv(FRED_DIR / 'fred_md_metadata.csv')
        try:
            row: pd.Series = fred_metadata[fred_metadata[id_type] == symbol].iloc[0]
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
        except IndexError:
            na_str = 'N/A'
            self.fred_md_id = symbol
            self.api_id = symbol
            self.name = symbol
            self.source_title = na_str
            self.source_link = na_str
            self.release_title = na_str
            self.release_link = na_str
            self.tcode = na_str
            self.frequency = na_str
            self.latex_equation = na_str

    def get_latex_equation(self):
        return latex_eq_dict.get(self.tcode, "Unknown transformation code")

    def __str__(self):
        return f"Symbol: {self.symbol}, Name: {self.name}, Source: {self.source_title}"

    def __repr__(self):
        series_data_repr = {key: (df.shape if df is not None else None)
                            for key, df in self.series_data.items()}
        correlations_repr = {key: f"{len(correlations)} securities (e.g. {correlations[:2]})"
                             for key, correlations in self.positive_correlations.items()}
        return (
                f"{self.__class__.__name__}\n"
                f"fred_md_id=" + f"{self.fred_md_id}\n"
                "api_id=" + f"{self.api_id}\n"
                "name=" + f"{self.name}\n"
                "source_title=" + f"{self.source_title}\n"
                "source_link=" + f"{self.source_link}\n"
                "release_title=" + f"{self.release_title}\n"
                "release_link=" + f"{self.release_link}\n"
                "tcode=" + f"{self.tcode}\n"
                f"latex_equation={self.latex_equation}\n"
                f"series_data={series_data_repr}\n"
                f"positive_correlations={correlations_repr}"
        )

    def __hash__(self) -> int:
        return hash(self.symbol)  # Make the instance hashable using its symbol attribute

    def __eq__(self, other) -> bool:
        if isinstance(other, Security):
            return self.symbol == other.symbol
        return False

    def to_dict(self):
        return self.__dict__


class FredapiSeries(FredSeriesBase):
    def __init__(self, api_symbol: str, revised: bool, save_data: bool = False, custom_data: pd.Series = None):
        super().__init__(api_symbol, 'api_id')
        if not revised:
            self.name = self.name + ' (UNREVISED)'
        if not custom_data:
            series = self.get_fred_series(revised, save_data)
            self.set_data_years(series)
        else:  # Custom data is given
            self.name = self.name + ' (CUSTOM)'
            series: pd.Series = custom_data.rename(self.symbol)  # Eikon data has a "VALUE" column
            self.set_data_years(series)

    def get_fred_series(self, revised, save_data) -> pd.Series:
        """For getting a series from the FRED API"""
        def fetch_data_with_rate_limiting(api_call_func_: Callable[[], pd.DataFrame]) -> pd.DataFrame:
            i = 1
            while True:
                try:
                    return api_call_func_()
                except HTTPError as err:
                    if '429' in str(err):  # Too Many Requests error
                        sleep_time: int = min(i * 10, 30)
                        i += 1
                        time.sleep(sleep_time)  # Sleep before trying again
                        print(f"Exceeding rate limit, sleeping {sleep_time} seconds")
                    else:
                        raise

        def api_call_as_reported() -> pd.DataFrame:
            return fred.api.series.observations.get_first_observations(
                self.symbol, observation_start="1980-02-27", observation_end=observation_end, api_key=FRED_KEY,
            )

        def api_call_revised() -> pd.DataFrame:
            return fred.api.series.observations.get(
                self.symbol, observation_start="1980-02-27", observation_end=observation_end, api_key=FRED_KEY,
            )

        api_call_func: Callable[[], pd.DataFrame] = api_call_revised if revised else api_call_as_reported
        df: pd.DataFrame = fetch_data_with_rate_limiting(api_call_func)

        # Reformatting names, datatypes, index
        df: pd.DataFrame = df.rename(columns={'date': 'Date'})
        df = df.rename(columns={'value': self.symbol})
        df['Date'] = pd.to_datetime(df['Date'])
        series: pd.Series = df.set_index('Date')[self.symbol]

        if save_data:
            if revised:
                filepath = f"fred_md_historical/{self.symbol}.parquet"
            else:
                filepath = f"fred_md_historical_unrevised/{self.symbol}.parquet"
            df.to_parquet(FRED_DIR / filepath)

        return series


class FredmdSeries(FredSeriesBase):
    def __init__(self, fred_md_symbol: str):
        super().__init__(fred_md_symbol, 'fred_md_id')
        df = self.set_fred_series()
        self.set_data_years(df)

    def set_fred_series(self):
        """For getting a series from the FRED-MD dataset"""
        md_data = pd.read_csv(FRED_DIR / 'fred_md/MD_2023-08-02.csv')
        md_data = md_data.rename(columns={'sasdate': 'Date'})
        md_data['Date'] = pd.to_datetime(md_data['Date'])
        md_data = md_data.set_index('Date')[self.fred_md_id]  # Extract the 'series_id' column for correlation

        return md_data


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
