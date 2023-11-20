from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from clickhouse_driver import Client

from config import STOCKS_DIR

CH_HOST = 'localhost'
CH_PORT = 9000
CH_DATABASE = 'stock_data'
CH_TABLE = 'yfinance'
BATCH_SIZE = 5000
source_dir = STOCKS_DIR / 'yahoo_daily/'
NUM_PROCESSES = 100  # Adjust this based on your preference

client = Client(host=CH_HOST, port=CH_PORT, database=CH_DATABASE)


def insert_data_to_clickhouse(data_tuples):
    ch_client = Client(host=CH_HOST, port=CH_PORT, database=CH_DATABASE)
    ch_client.execute("SET max_insert_block_size = 100000")
    ch_client.execute("SET max_insert_threads = 12")
    query = f"INSERT INTO {CH_TABLE} FORMAT TabSeparated"
    ch_client.execute(query, data_tuples)


def process_csv_file(csv_file):
    print(f"Processing {csv_file.name}...")
    df = pd.read_csv(csv_file)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    # Add the Ticker column
    ticker = csv_file.stem  # Get the filename without extension
    df['Ticker'] = ticker
    df = df.rename(columns={"Adj Close": "Adj_Close"})
    data_tuples = list(df.itertuples(index=False, name=None))

    # Split data into batches and insert
    for i in range(0, len(data_tuples), BATCH_SIZE):
        insert_data_to_clickhouse(data_tuples[i:i + BATCH_SIZE])


def migrate_data_to_clickhouse():
    with ThreadPoolExecutor(max_workers=NUM_PROCESSES) as executor:
        list(executor.map(process_csv_file, source_dir.glob("*.csv")))
    print("Migration completed!")


################################################################
# GROUP END


def example_retrieve_data_from_clickhouse(ticker, save_to_csv=False):
    client = Client(host=CH_HOST, port=CH_PORT, database=CH_DATABASE)

    # Query to retrieve data for the specified ticker
    query = f"SELECT * FROM {CH_TABLE} WHERE Ticker = '{ticker}'"

    # Execute the query
    result = client.execute(query, with_column_types=True)

    # Convert the result into a DataFrame
    df = pd.DataFrame(result[0], columns=[col[0] for col in result[1]])

    if save_to_csv:
        df.to_csv(f"{ticker}_retrieved.csv", index=False)

    return df


def get_data_from_ch_stock_data(symbol, start_date=None):
    query = f"""
        SELECT Date, Adj_Close
        FROM {CH_TABLE}
        WHERE Ticker = '{symbol}'
    """

    if start_date:
        query += f" AND Date >= '{start_date}'"

    results = client.execute(query)
    df = pd.DataFrame(results, columns=["Date", "Adj_Close"])
    df['Date'] = pd.to_datetime(df['Date'])

    # print("Used clickhouse to get df:\n", df)
    return df.set_index('Date')['Adj_Close']
