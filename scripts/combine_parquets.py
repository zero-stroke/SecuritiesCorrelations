# Unused file that was an experimental way to speed up file i/o operations
import pandas as pd
from config import STOCKS_DIR

combined_df_list = []

# Loop over all Parquet files in the directory
for file in (STOCKS_DIR / 'yahoo_daily/parquets').iterdir():
    if file.suffix == ".parquet":
        symbol = file.stem
        try:
            df = pd.read_parquet(file)

            # Check if 'Date' index exists
            if not isinstance(df.index, pd.DatetimeIndex) or df.index.name != 'Date':
                print(f"Skipping {symbol} - 'Date' index missing or not in expected format.")
                continue

            # Append the symbol as a level in the multi-index
            df['Symbol'] = symbol
            df.set_index('Symbol', append=True, inplace=True)

            # Reorder the multi-index levels for consistency
            df = df.reorder_levels(['Symbol', 'Date'])

            combined_df_list.append(df)
            print(symbol)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

# Concatenate all dataframes
combined_df = pd.concat(combined_df_list, axis=0)

# Save the combined dataframe as a new Parquet file
combined_df.to_parquet(STOCKS_DIR / 'combined_data.parquet')

