import logging

import pandas as pd

import core.finance.market_impact as cfimaimp
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_estimate_market_order_price(hunitest.TestCase):
    @staticmethod
    def get_bid_data() -> pd.DataFrame:
        index = pd.RangeIndex(
            start=1,
            stop=6,
        )
        shares = [
            [0.3733, 62070.8],
            [0.3732, 378167.4],
            [0.3731, 387456.3],
            [0.3730, 554530.6],
            [0.3729, 425693.1],
        ]
        columns = ["bid", "size"]
        bid_data = pd.DataFrame(shares, index, columns)
        return bid_data

    def test_estimate_market_order_price(self) -> None:
        bid_data = self.get_bid_data()
        market_impact = cfimaimp.estimate_market_order_price(
            bid_data, "bid", "size"
        )
        actual = hpandas.df_to_str(market_impact, num_rows=None)
        expected = r"""
    price      size      notional  cumulative_size  cumulative_notional  mean_price_through_level  price_degradation_bps
1  0.3733   62070.8   23171.02964          62070.8          23171.02964                  0.373300               0.000000
2  0.3732  378167.4  141132.07368         440238.2         164303.10332                  0.373214               2.301115
3  0.3731  387456.3  144559.94553         827694.5         308863.04885                  0.373161               3.731912
4  0.3730  554530.6  206839.91380        1382225.1         515702.96265                  0.373096               5.458829
5  0.3729  425693.1  158740.95699        1807918.2         674443.91964                  0.373050               6.696506
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
