import unittest
from multiprocessing import Process, Manager
from scripts import get_validated_security_data
from scripts.correlation_constants import SecurityMetadata


def worker_function(cache, data):
    # Read from the cache
    for symbol in data:
        result = get_validated_security_data(symbol, '2021', '2022', 'yahoo', False, False)
        cache[symbol] = result


class TestSharedCache(unittest.TestCase):

    def setUp(self):
        self.metadata = SecurityMetadata()
        self.symbols = self.metadata.build_symbol_list()

    def test_multiprocessing_cache(self):
        with Manager() as manager:
            shared_cache = manager.dict()

            # Warm up the cache in the main process
            for symbol in self.symbols[:10]:  # taking a subset for simplicity
                get_validated_security_data(symbol, '2021', '2021', 'yahoo', False, False)

            # Now, spawn the worker processes and let them read from the cache
            data_for_p1 = self.symbols[:5]
            data_for_p2 = self.symbols[5:10]

            p1 = Process(target=worker_function, args=(shared_cache, data_for_p1))
            p2 = Process(target=worker_function, args=(shared_cache, data_for_p2))

            p1.start()
            p2.start()

            p1.join()
            p2.join()

            # Assert that cache was used correctly
            for symbol in self.symbols[:10]:
                self.assertIn(symbol, shared_cache.keys())


if __name__ == '__main__':
    unittest.main()
