import logging
import time

from tqdm import tqdm

from batch_calculate import compute_security_correlations_and_plot
from scripts.file_reading_funcs import original_get_validated_security_data, read_series_data
from scripts.correlation_constants import SharedMemoryCache

log_format = '%(asctime)s - %(message)s'
date_format = '%H:%M:%S'

logging.basicConfig(filename='cache_info.log', level=logging.INFO,
                    format=log_format, datefmt=date_format, filemode='w')


def test_caching_large_simple(symbols_list: list, source: str):
    # Cache the results for all symbols initially
    for symbol in tqdm(symbols_list, desc="Caching results"):
        original_get_validated_security_data(symbol, '2022', '2023-06-02', source, dl_data=False, use_ch=False)

    # Pick a sample symbol for testing
    test_symbol = symbols_list[0]

    # Clear cache to simulate it being the first read for the test symbol
    read_series_data.cache_clear()

    # 1. Call the function for the first time for the test symbol
    start_time = time.time()
    original_get_validated_security_data(test_symbol, '2022', '2023-06-02', source, dl_data=False, use_ch=False)
    first_duration = time.time() - start_time

    # Simulate other thousands of calls
    for symbol in tqdm(symbols_list[1:], desc="Simulating other calls"):  # Skip the test_symbol
        original_get_validated_security_data(symbol, '2022', '2023-06-02', source, dl_data=False, use_ch=False)

    # 2. Call the function again for the test symbol
    start_time = time.time()
    original_get_validated_security_data(test_symbol, '2022', '2023-06-02', source, dl_data=False, use_ch=False)
    second_duration = time.time() - start_time

    print(f"First call duration for {test_symbol}: {first_duration:.4f} seconds")
    print(f"Second call duration for {test_symbol}: {second_duration:.4f} seconds")

    if second_duration < first_duration / 10:  # Assuming caching would make it at least 10 times faster
        print("Caching seems to be working as intended.")
    else:
        print("Caching may not be working correctly.")


def main_test(cache_param):
    compute_security_correlations_and_plot(
        symbol_list=['U'],
        fred_source=False,
        start_date='2023',
        end_date='2023-06-02',
        num_traces=4,

        source='yahoo',
        dl_data=False,
        display_plot=True,
        use_ch=False,
        use_multiprocessing=True,

        etf=False,
        stock=True,
        index=False,

        show_detrended=False,
        monthly_resample=False,
        otc_filter=False,

        cache=cache_param
    )


if __name__ == '__main__':
    cache = SharedMemoryCache()
    # First execution
    start_time_1 = time.time()
    main_test(cache)
    duration_1 = time.time() - start_time_1
    print(f"\nFirst run took {duration_1:.2f} seconds.")

    # Second execution
    start_time_2 = time.time()
    main_test(cache)
    duration_2 = time.time() - start_time_2
    print(f"\nSecond run took {duration_2:.2f} seconds.")

    # Check if the second execution is faster
    if duration_2 < duration_1:
        print("\nThe second run was faster, indicating caching might have had an effect.")
    else:
        print("\nThe second run wasn't significantly faster. Caching might not be working as intended or the time difference is marginal.")


