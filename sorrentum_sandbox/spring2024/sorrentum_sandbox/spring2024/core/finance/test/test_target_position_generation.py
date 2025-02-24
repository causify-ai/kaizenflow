import logging
from typing import List

import pandas as pd

import core.finance.target_position_generation as cftapoge
import core.finance_data_example as cfidaexa
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def get_data(
    start_datetime: pd.Timestamp,
    end_datetime: pd.Timestamp,
    asset_ids: List[int],
    *,
    bar_duration: str = "5T",
) -> pd.DataFrame:
    df = cfidaexa.get_target_position_generation_dataframe(
        start_datetime,
        end_datetime,
        asset_ids,
        bar_duration=bar_duration,
    )
    _LOG.debug(
        "df=\n%s",
        hpandas.df_to_str(
            df,
            num_rows=None,
        ),
    )
    return df


def get_data_1asset() -> pd.DataFrame:
    start_timestamp = pd.Timestamp("2022-01-10 09:30", tz="America/New_York")
    end_timestamp = pd.Timestamp("2022-01-10 10:30", tz="America/New_York")
    asset_ids = [101]
    data = get_data(start_timestamp, end_timestamp, asset_ids)
    return data


def get_data_4assets() -> pd.DataFrame:
    start_timestamp = pd.Timestamp("2022-01-10 09:30", tz="America/New_York")
    end_timestamp = pd.Timestamp("2022-01-10 10:30", tz="America/New_York")
    asset_ids = [101, 201, 301, 401]
    data = get_data(start_timestamp, end_timestamp, asset_ids)
    return data


class Test_compute_target_positions_cross_sectionally1(hunitest.TestCase):
    def test_1asset_with_defaults(self):
        data = get_data_1asset()
        prediction = data["prediction"]
        volatility = data["volatility"]
        target_positions = cftapoge.compute_target_positions_cross_sectionally(
            prediction, volatility
        )
        actual = convert_df_to_str(target_positions)
        expected = r"""
                                  101
2022-01-10 09:35:00-05:00 -1000000.00
2022-01-10 09:40:00-05:00 -1000000.00
2022-01-10 09:45:00-05:00 -1000000.00
2022-01-10 09:50:00-05:00  1000000.00
2022-01-10 09:55:00-05:00 -1000000.00
2022-01-10 10:00:00-05:00  1000000.00
2022-01-10 10:05:00-05:00  1000000.00
2022-01-10 10:10:00-05:00  1000000.00
2022-01-10 10:15:00-05:00  1000000.00
2022-01-10 10:20:00-05:00 -1000000.00
2022-01-10 10:25:00-05:00 -1000000.00
2022-01-10 10:30:00-05:00 -1000000.00
"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_4assets_with_defaults(self):
        data = get_data_4assets()
        prediction = data["prediction"]
        volatility = data["volatility"]
        target_positions = cftapoge.compute_target_positions_cross_sectionally(
            prediction, volatility
        )
        actual = convert_df_to_str(target_positions)
        expected = r"""
                                 101        201        301        401
2022-01-10 09:35:00-05:00 -674028.57  217098.53  -78675.28   30197.62
2022-01-10 09:40:00-05:00 -876007.35  118860.70     780.73   -4351.22
2022-01-10 09:45:00-05:00 -382977.25  205035.75  295639.15 -116347.85
2022-01-10 09:50:00-05:00  110449.75 -534973.64  -62873.71  291702.90
2022-01-10 09:55:00-05:00  -45346.50  -35642.93    3826.12  915184.45
2022-01-10 10:00:00-05:00      29.14    -649.00    -292.91  999028.95
2022-01-10 10:05:00-05:00  827030.33   74504.02  -74892.28  -23573.36
2022-01-10 10:10:00-05:00    1265.99      47.75 -998391.26    -294.99
2022-01-10 10:15:00-05:00  274748.24 -163506.46 -402586.98  159158.32
2022-01-10 10:20:00-05:00  -11981.92   82353.91  894793.15  -10871.03
2022-01-10 10:25:00-05:00  -22136.69  206293.73 -767043.55    4526.03
2022-01-10 10:30:00-05:00 -253170.55 -240332.64  473995.52   32501.28"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_4assets_with_custom_config(self):
        data = get_data_4assets()
        prediction = data["prediction"]
        volatility = data["volatility"]
        target_positions = cftapoge.compute_target_positions_cross_sectionally(
            prediction,
            volatility,
            bulk_frac_to_remove=0.5,
            bulk_fill_method="zero",
            target_gmv=1e5,
            volatility_lower_bound=1e-4,
        )
        actual = convert_df_to_str(target_positions)
        expected = r"""
                                101       201       301       401
2022-01-10 09:35:00-05:00 -75637.76  24362.24      0.00      0.00
2022-01-10 09:40:00-05:00 -99663.54      0.00    336.46      0.00
2022-01-10 09:45:00-05:00      0.00  63797.83      0.00 -36202.17
2022-01-10 09:50:00-05:00      0.00      0.00 -17732.05  82267.95
2022-01-10 09:55:00-05:00      0.00  -7758.05      0.00  92241.95
2022-01-10 10:00:00-05:00      0.00      0.00  -2848.43  97151.57
2022-01-10 10:05:00-05:00  97228.63      0.00      0.00  -2771.37
2022-01-10 10:10:00-05:00  81102.29      0.00      0.00 -18897.71
2022-01-10 10:15:00-05:00      0.00 -50673.79      0.00  49326.21
2022-01-10 10:20:00-05:00      0.00  88338.93      0.00 -11661.07
2022-01-10 10:25:00-05:00 -83024.89      0.00      0.00  16975.11
2022-01-10 10:30:00-05:00      0.00 -88087.52      0.00  11912.48"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_compute_target_positions_longitudinally1(hunitest.TestCase):
    def test_1asset_with_defaults(self):
        data = get_data_1asset()
        prediction = data["prediction"]
        volatility = data["volatility"]
        target_positions = cftapoge.compute_target_positions_longitudinally(
            prediction,
            volatility,
        )
        actual = convert_df_to_str(target_positions)
        expected = r"""
                                  101
2022-01-10 09:35:00-05:00  -290820.38
2022-01-10 09:40:00-05:00 -1000000.00
2022-01-10 09:45:00-05:00  -102851.70
2022-01-10 09:50:00-05:00    88145.53
2022-01-10 09:55:00-05:00  -327112.50
2022-01-10 10:00:00-05:00    54004.86
2022-01-10 10:05:00-05:00   564801.01
2022-01-10 10:10:00-05:00   234837.89
2022-01-10 10:15:00-05:00   101486.20
2022-01-10 10:20:00-05:00   -89850.96
2022-01-10 10:25:00-05:00  -131470.65
2022-01-10 10:30:00-05:00  -154315.13"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_1asset_with_params(self):
        data = get_data_1asset()
        prediction = data["prediction"]
        volatility = data["volatility"]
        target_positions = cftapoge.compute_target_positions_longitudinally(
            prediction,
            volatility,
            prediction_abs_threshold=3e-4,
            volatility_to_spread_threshold=2.0,
            volatility_lower_bound=2e-4,
            gamma=1e-5,
            target_dollar_risk_per_name=1e2,
            spread_lower_bound=1e-5,
            spread=data["spread"],
        )
        actual = convert_df_to_str(target_positions)
        expected = r"""
                                 101
2022-01-10 09:35:00-05:00 -290820.38
2022-01-10 09:40:00-05:00       0.00
2022-01-10 09:45:00-05:00 -102851.70
2022-01-10 09:50:00-05:00       0.00
2022-01-10 09:55:00-05:00       0.00
2022-01-10 10:00:00-05:00       0.00
2022-01-10 10:05:00-05:00  500000.00
2022-01-10 10:10:00-05:00       0.00
2022-01-10 10:15:00-05:00  101486.20
2022-01-10 10:20:00-05:00  -89850.96
2022-01-10 10:25:00-05:00 -131470.65
2022-01-10 10:30:00-05:00 -154315.13"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_4assets_with_defaults(self):
        data = get_data_4assets()
        prediction = data["prediction"]
        volatility = data["volatility"]
        target_positions = cftapoge.compute_target_positions_longitudinally(
            prediction, volatility
        )
        actual = convert_df_to_str(target_positions)
        expected = r"""
                                  101        201         301         401
2022-01-10 09:35:00-05:00  -290820.38  165049.47   -99358.45   -61556.24
2022-01-10 09:40:00-05:00 -1000000.00  716919.48    58103.39   137169.17
2022-01-10 09:45:00-05:00  -102851.70   75255.77   -90366.19   -56689.70
2022-01-10 09:50:00-05:00    88145.53 -193992.12   -66504.72   143247.90
2022-01-10 09:55:00-05:00  -327112.50 -290009.31   -95017.71  1000000.00
2022-01-10 10:00:00-05:00    54004.86 -254879.28  -171229.35  1000000.00
2022-01-10 10:05:00-05:00   564801.01  169521.43   169962.57   -95355.45
2022-01-10 10:10:00-05:00   234837.89   45610.10 -1000000.00  -113359.03
2022-01-10 10:15:00-05:00   101486.20  -78290.13  -122848.37    77242.13
2022-01-10 10:20:00-05:00   -89850.96  235560.07   776463.21   -85584.44
2022-01-10 10:25:00-05:00  -131470.65  401342.77  -773895.71    59447.14
2022-01-10 10:30:00-05:00  -154315.13 -150351.68  -211149.00   -55290.71"""
        self.assert_equal(actual, expected, fuzzy_match=True)


def convert_df_to_str(df: pd.DataFrame) -> str:
    precision = 2
    # TODO(Paul): Factor out this option context into `df_to_str()`.
    # TODO(Paul): Consider "{:,.2f}" so that commas are inserted (for human
    #  readability).
    with pd.option_context(
        "display.float_format",
        "{:.2f}".format,
    ):
        df_str = hpandas.df_to_str(
            df.round(precision),
            num_rows=None,
            precision=precision,
        )
    return df_str
