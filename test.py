import unittest
import pandas as pd
from scripts.correlation_constants import Security
from scripts.find_correlated_symbols import *


class TestCorrelationComputations(unittest.TestCase):

    def setUp(self):
        # Mock data or a subset of real data
        dates = pd.date_range(start="2023-08-01", periods=5)

        self.security1 = Security('AAPL')

        self.security2 = Security('MSFT')

        self.all_base_series = [self.security1]

    def test_compute_correlation(self):
        # Expected correlation between self.security1 and self.security2
        expected_corr = self.security1.series_data.corr(self.security2.series_data)

        # Use the function to compute the correlation
        computed_corr = get_correlation_for_series(self.security2.series_data, self.security1.series_data)

        # Directly compute using pandas
        direct_corr = self.security1.series_data.diff().dropna().corr(self.security2.series_data.diff().dropna())
        print("Direct Correlation:", direct_corr)  # Add this line

        # Compute standard deviations of detrended Data1 and Data2
        combined_data = pd.concat([self.security2.series_data.diff().dropna(), self.security1.series_data.diff().dropna()], axis=1)
        std_dev_data1 = combined_data.iloc[:, 0].std()
        std_dev_data2 = combined_data.iloc[:, 1].std()
        print("Standard Deviation of Data1:", std_dev_data1)
        print("Standard Deviation of Data2:", std_dev_data2)

        # Check if the computed correlation matches the expected correlation
        self.assertAlmostEqual(computed_corr, expected_corr, places=5)

    def test_compute_correlations_for_symbol(self):
        compute_correlations_for_symbol('MSFT', self.all_base_series, '2010-01-01', '2020-01-01', 'yahoo', False, False)

        # Check if the all_correlations dictionary for security1 contains MSFT and its correlation
        self.assertIn('MSFT', self.security1.all_correlations)
        self.assertAlmostEqual(self.security1.all_correlations['MSFT'],
                               self.security1.series_data.corr(self.security2.series_data), places=5)

    # You can add more tests for other functions and scenarios.

    def test_compute_correlation_function(self):
        corr_value = compute_correlation(self.security1.series_data, self.security2.series_data)
        expected_corr = self.security1.series_data.corr(self.security2.series_data)
        self.assertAlmostEqual(corr_value, expected_corr, places=5)

    def tearDown(self):
        # Clean up resources, if necessary.
        pass

if __name__ == '__main__':
    unittest.main()
