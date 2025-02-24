from typing import Dict

import pandas as pd

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import oms.order.order_converter as oororcon


def _get_orders() -> pd.DataFrame:
    """
    Generate synthetic orders.
    """
    df_as_str = """
                creation_timestamp    asset_id       type_           start_timestamp             end_timestamp  curr_num_shares  diff_num_shares   tz extra_params
    order_id
    0        "2023-08-15 15:45:00+00:00"  1464553467  price@twap "2023-08-15 15:45:00+00:00" "2023-08-15 15:50:00+00:00"            0.000        -0.128214  UTC           {}
    1        "2023-08-15 15:50:00+00:00"  1464553467  price@twap "2023-08-15 15:50:00+00:00" "2023-08-15 15:55:00+00:00"           -0.130         0.107065  UTC           {}
    2        "2023-08-15 15:55:00+00:00"  1464553467  price@twap "2023-08-15 15:55:00+00:00" "2023-08-15 16:00:00+00:00"           -0.046        -0.058212  UTC           {}
    3        "2023-08-15 16:00:00+00:00"  1464553467  price@twap "2023-08-15 16:00:00+00:00" "2023-08-15 16:05:00+00:00"           -0.094         0.124464  UTC           {}
    4        "2023-08-15 16:05:00+00:00"  1464553467  price@twap "2023-08-15 16:05:00+00:00" "2023-08-15 16:10:00+00:00"           -0.019         0.019000  UTC           {}
    5        "2023-08-15 15:45:00+00:00"  1030828978  price@twap "2023-08-15 15:45:00+00:00" "2023-08-15 15:50:00+00:00"            0.000      -402.827474  UTC           {}
    6        "2023-08-15 15:50:00+00:00"  1030828978  price@twap "2023-08-15 15:50:00+00:00" "2023-08-15 15:55:00+00:00"         -324.000       336.926686  UTC           {}
    7        "2023-08-15 15:55:00+00:00"  1030828978  price@twap "2023-08-15 15:55:00+00:00" "2023-08-15 16:00:00+00:00"           -123.0     -1080.730129  UTC           {}
    8        "2023-08-15 16:00:00+00:00"  1030828978  price@twap "2023-08-15 16:00:00+00:00" "2023-08-15 16:05:00+00:00"           -771.0      1116.992220  UTC           {}
    9        "2023-08-15 16:05:00+00:00"  1030828978  price@twap "2023-08-15 16:05:00+00:00" "2023-08-15 16:10:00+00:00"           -102.0       102.000000  UTC           {}"""
    #
    col_to_type = {
        "__index__": int,
        "creation_timestamp": pd.Timestamp,
        "asset_id": int,
        "start_timestamp": pd.Timestamp,
        "end_timestamp": pd.Timestamp,
        "curr_num_shares": float,
        "diff_num_shares": float,
        "extra_params": dict,
    }
    col_to_name_type: Dict[str, type] = {}
    df = hpandas.str_to_df(df_as_str, col_to_type, col_to_name_type)
    return df


def _get_prices() -> pd.DataFrame:
    """
    Generate synthetic price data.
    """
    df_as_str = """
                                   1030828978  1464553467
    end_timestamp
    "2023-08-15 11:45:00-04:00"     0.20136    1838.812
    "2023-08-15 11:50:00-04:00"     0.20158    1839.690
    "2023-08-15 11:55:00-04:00"     0.20162    1839.936
    "2023-08-15 12:00:00-04:00"     0.20128    1839.430
    "2023-08-15 12:05:00-04:00"     0.20134    1840.016
    "2023-08-15 12:10:00-04:00"     0.20110    1839.615"""
    #
    col_to_type = {
        "__index__": pd.Timestamp,
        "1030828978": float,
        "1464553467": float,
    }
    col_to_name_type = {
        "1030828978": int,
        "1464553467": int,
    }
    df = hpandas.str_to_df(df_as_str, col_to_type, col_to_name_type)
    # Set index frequency.
    df = df.asfreq("5T")
    return df


class Test_convert_single_asset_order_df_to_target_position_df(hunitest.TestCase):
    """
    Verify that a single asset order df is converted into a target position df
    correctly.
    """

    def test1(self) -> None:
        """
        Test a single asset.
        """
        order_df = _get_orders()
        price_df = _get_prices()
        # Keep only one asset.
        asset_to_keep = 1464553467
        order_df = order_df[order_df["asset_id"] == asset_to_keep]
        price_srs = price_df[asset_to_keep]
        #
        target_position_df = (
            oororcon.convert_single_asset_order_df_to_target_position_df(
                order_df, price_srs
            )
        )
        actual = hpandas.df_to_str(target_position_df)
        self.check_string(actual)


class Test_convert_order_df_to_target_position_df(hunitest.TestCase):
    """
    Verify that orders are converted into a target position df correctly.
    """

    def test1(self) -> None:
        """
        Test multiple assets, no gaps in timestamps.
        """
        order_df = _get_orders()
        price_df = _get_prices()
        target_position_df = oororcon.convert_order_df_to_target_position_df(
            order_df, price_df
        )
        actual = hpandas.df_to_str(target_position_df)
        self.check_string(actual)

    def test2(self) -> None:
        """
        Test multiple assets, with gaps in timestamps.
        """
        order_df = _get_orders()
        price_df = _get_prices()
        # Omit some orders by timestamp.
        timestamps_to_drop = [
            pd.Timestamp("2023-08-15 11:50:00-04:00"),
            pd.Timestamp("2023-08-15 12:00:00-04:00"),
        ]
        order_df = order_df[~order_df["end_timestamp"].isin(timestamps_to_drop)]
        #
        target_position_df = oororcon.convert_order_df_to_target_position_df(
            order_df, price_df
        )
        actual = hpandas.df_to_str(target_position_df)
        self.check_string(actual)
