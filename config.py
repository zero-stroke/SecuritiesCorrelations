from pathlib import Path
import pandas as pd


def find_project_root(current_path: Path) -> Path:
    """Find the project root by looking for a marker file or directory."""
    if (current_path / 'data').exists():
        return current_path
    if current_path.parent == current_path:
        raise FileNotFoundError("Could not find 'data' directory in any parent directories.")
    return find_project_root(current_path.parent)


BASE_DIR = find_project_root(Path(__file__))
DATA_DIR = BASE_DIR / 'data'
STOCKS_DIR = DATA_DIR / 'Stock_data'
FRED_DIR = DATA_DIR / 'FRED'

etf_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_etf_data.csv', index_col='symbol')
stock_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_stock_data.csv', index_col='symbol')
index_metadata = pd.read_csv(STOCKS_DIR / 'FinDB/updated_fin_db_indices_data.csv', index_col='symbol')

securities_metadata = (etf_metadata, stock_metadata, index_metadata)

FRED_KEY = 'YOUR_API_KEY'

