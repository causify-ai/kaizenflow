import logging

import pandas as pd

import core.finance.share_quantization as cfishqua
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_quantize_shares(hunitest.TestCase):
    @staticmethod
    def get_shares() -> pd.DataFrame:
        index = pd.date_range(
            "2000-01-01 09:35:00",
            "2000-01-01 10:05:00",
            freq="5T",
            tz="America/New_York",
        )
        shares = [
            [0.00, 0.00],
            [-49.90, 100.10],
            [-50.00, 100.00],
            [-50.01, 99.00],
            [-99.00, 50.01],
            [-100.00, 50.00],
            [-100.10, 49.90],
        ]
        columns = [101, 202]
        holdings = pd.DataFrame(shares, index, columns)
        return holdings

    def test_no_quantization(self) -> None:
        shares = self.get_shares()
        quantization = 30
        quantized_shares = cfishqua.quantize_shares(shares, quantization)
        actual = hpandas.df_to_str(quantized_shares, num_rows=None)
        expected = r"""
                              101     202
2000-01-01 09:35:00-05:00    0.00    0.00
2000-01-01 09:40:00-05:00  -49.90  100.10
2000-01-01 09:45:00-05:00  -50.00  100.00
2000-01-01 09:50:00-05:00  -50.01   99.00
2000-01-01 09:55:00-05:00  -99.00   50.01
2000-01-01 10:00:00-05:00 -100.00   50.00
2000-01-01 10:05:00-05:00 -100.10   49.90"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_round_to_nearest_share(self) -> None:
        shares = self.get_shares()
        quantization = 0
        quantized_shares = cfishqua.quantize_shares(shares, quantization)
        actual = hpandas.df_to_str(quantized_shares, num_rows=None)
        expected = r"""
                             101    202
2000-01-01 09:35:00-05:00    0.0    0.0
2000-01-01 09:40:00-05:00  -50.0  100.0
2000-01-01 09:45:00-05:00  -50.0  100.0
2000-01-01 09:50:00-05:00  -50.0   99.0
2000-01-01 09:55:00-05:00  -99.0   50.0
2000-01-01 10:00:00-05:00 -100.0   50.0
2000-01-01 10:05:00-05:00 -100.0   50.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_round_to_nearest_lot(self) -> None:
        shares = self.get_shares()
        quantization = -2
        quantized_shares = cfishqua.quantize_shares(shares, quantization)
        actual = hpandas.df_to_str(
            quantized_shares, handle_signed_zeros=True, num_rows=None
        )
        expected = r"""
                             101    202
2000-01-01 09:35:00-05:00    0.0    0.0
2000-01-01 09:40:00-05:00    0.0  100.0
2000-01-01 09:45:00-05:00    0.0  100.0
2000-01-01 09:50:00-05:00 -100.0  100.0
2000-01-01 09:55:00-05:00 -100.0  100.0
2000-01-01 10:00:00-05:00 -100.0    0.0
2000-01-01 10:05:00-05:00 -100.0    0.0"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_asset_specific_rounding(self) -> None:
        shares = self.get_shares()
        quantization = None
        asset_id_to_decimals = {
            101: -1,
            202: 1,
        }
        quantized_shares = cfishqua.quantize_shares(
            shares,
            quantization,
            asset_id_to_decimals=asset_id_to_decimals,
        )
        actual = hpandas.df_to_str(quantized_shares, num_rows=None)
        expected = r"""
                             101    202
2000-01-01 09:35:00-05:00    0.0    0.0
2000-01-01 09:40:00-05:00  -50.0  100.1
2000-01-01 09:45:00-05:00  -50.0  100.0
2000-01-01 09:50:00-05:00  -50.0   99.0
2000-01-01 09:55:00-05:00 -100.0   50.0
2000-01-01 10:00:00-05:00 -100.0   50.0
2000-01-01 10:05:00-05:00 -100.0   49.9
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_asset_specific_rounding_for_series(self) -> None:
        shares = self.get_shares().iloc[1]
        quantization = None
        asset_id_to_decimals = {
            101: -1,
            202: 1,
        }
        quantized_shares = cfishqua.quantize_shares(
            shares,
            quantization,
            asset_id_to_decimals=asset_id_to_decimals,
        )
        actual = hpandas.df_to_str(quantized_shares, num_rows=None)
        expected = r"""
     2000-01-01 09:40:00-05:00
101                      -50.0
202                      100.1
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
