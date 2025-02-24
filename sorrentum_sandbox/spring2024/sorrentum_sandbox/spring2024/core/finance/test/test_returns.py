import datetime
import logging

import numpy as np
import pandas as pd

import core.finance.returns as cfinretu
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestComputeOvernightReturns(hunitest.TestCase):
    def test1(self) -> None:
        data = (
            pd.Series(
                {
                    "date": datetime.date(2022, 1, 3),
                    "asset_id": 100,
                    "open_": 1000.0,
                    "close": 1010.0,
                    "total_return": 500,
                    "prev_total_return": 495,
                }
            )
            .to_frame()
            .T
        )
        data = data.convert_dtypes()
        actual = cfinretu.compute_overnight_returns(
            data,
            "asset_id",
        )
        precision = 5
        actual_str = hpandas.df_to_str(actual, precision=precision)
        expected_str = r"""
                          overnight_returns
asset_id                                100
datetime
2022-01-03 09:30:00-05:00            0.0001"""
        self.assert_equal(actual_str, expected_str, fuzzy_match=True)


class Test_compute_prices_from_rets(hunitest.TestCase):
    def test1(self) -> None:
        sample = self._get_sample()
        sample["rets"] = cfinretu.compute_ret_0(sample.price, mode="pct_change")
        sample["price_pred"] = cfinretu.compute_prices_from_rets(
            sample.price, sample.rets, "pct_change"
        )
        sample = sample.dropna()
        np.testing.assert_array_almost_equal(sample.price_pred, sample.price)

    def test2(self) -> None:
        sample = self._get_sample()
        sample["rets"] = cfinretu.compute_ret_0(sample.price, mode="log_rets")
        sample["price_pred"] = cfinretu.compute_prices_from_rets(
            sample.price, sample.rets, "log_rets"
        )
        sample = sample.dropna()
        np.testing.assert_array_almost_equal(sample.price_pred, sample.price)

    def test3(self) -> None:
        sample = self._get_sample()
        sample["rets"] = cfinretu.compute_ret_0(sample.price, mode="diff")
        sample["price_pred"] = cfinretu.compute_prices_from_rets(
            sample.price, sample.rets, "diff"
        )
        sample = sample.dropna()
        np.testing.assert_array_almost_equal(sample.price_pred, sample.price)

    def test4(self) -> None:
        """
        Check prices from forward returns.
        """
        sample = pd.DataFrame({"price": [1, 2, 3], "fwd_ret": [1, 0.5, np.nan]})
        sample["ret_0"] = sample.fwd_ret.shift(1)
        sample["price_pred"] = cfinretu.compute_prices_from_rets(
            sample.price, sample.ret_0, "pct_change"
        ).shift(1)
        sample = sample.dropna()
        np.testing.assert_array_almost_equal(sample.price_pred, sample.price)

    def test5(self) -> None:
        """
        Check output with forward returns.
        """
        np.random.seed(0)
        sample = self._get_sample()
        sample["ret_0"] = cfinretu.compute_ret_0(sample.price, mode="log_rets")
        sample["ret_1"] = sample["ret_0"].shift(-1)
        sample["price_pred"] = cfinretu.compute_prices_from_rets(
            sample.price, sample.ret_1.shift(1), "log_rets"
        )
        output_txt = hpandas.df_to_str(sample, num_rows=None)
        self.check_string(output_txt)

    def test6(self) -> None:
        """
        Check future price prediction.
        """
        np.random.seed(1)
        sample = self._get_sample()
        sample["ret_1"] = cfinretu.compute_ret_0(
            sample.price, mode="log_rets"
        ).shift(-1)
        future_price_expected = sample.iloc[-1, 0]
        # Drop latest date price.
        sample.dropna(inplace=True)
        rets = sample["ret_1"]
        rets.index = rets.index.shift(1)
        # Make future prediction for the dropped price.
        future_price_actual = cfinretu.compute_prices_from_rets(
            sample.price, rets, "log_rets"
        )[-1]
        np.testing.assert_almost_equal(future_price_expected, future_price_actual)

    @staticmethod
    def _get_sample() -> pd.DataFrame:
        date_range = pd.date_range(start="2010-01-01", periods=40, freq="B")
        sample = pd.DataFrame(index=date_range)
        sample["price"] = np.random.uniform(low=0, high=1, size=40)
        return sample
