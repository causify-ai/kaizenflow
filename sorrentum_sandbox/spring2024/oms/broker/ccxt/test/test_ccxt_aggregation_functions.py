from typing import Any

import numpy as np
import pandas as pd

import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import oms.broker.ccxt.ccxt_aggregation_functions as obccagfu


def _get_child_order_response_df1() -> pd.DataFrame:
    """
    Generate synthetic data.
    """
    timestamps = [
        "2023-03-15 16:35:41.205000+00:00",
        "2023-03-15 16:35:42.205000+00:00",
        "2023-03-15 16:35:43.205000+00:00",
        "2023-03-15 16:35:44.205000+00:00",
    ]
    data = {
        "symbol": ["APE/USDT", "AVAX/USDT ", "APE/USDT", "AVAX/USDT "],
        "asset_id": [6051632686, 8717633868, 6051632686, 8717633868],
        "order": [7954906695, 4551306695, 7909906645, 3154906699],
        "client_order_id": [
            "x-xcKtGhcub89989e55d47273a3610a9",
            "x-xcKtGhcub03933b03766705d9d532f",
            "x-xcKtGhcue1c5f0b2aaddb6ba451d6c",
            "x-xcKtGhcub89981j55d47273a3610a9",
        ],
        "order_type": ["limit", "limit", "limit", "limit"],
        "time_in_force": ["GTC", "GTC", "GTC", "GTC"],
        "post_only": [False, False, False, False],
        "reduce_only": [False, False, False, False],
        "side": ["buy", "sell", "sell", "buy"],
        "order_price": [8.2, 9.85, 2.7, 10.1],
        "stop_price": [None, None, None, None],
        "order_amount": [10, 1, 0, 3],
        "order_update_timestamp": timestamps,
        "order_update_datetime": timestamps,
    }
    df = pd.DataFrame(data)
    df["order_update_datetime"] = pd.to_datetime(df["order_update_datetime"])
    return df


def _get_child_order_response_df2() -> pd.DataFrame:
    """
    Generate a snippet of real-life data.

    `info` column is not included to improve readability.
    """
    data = {
        "order": [
            "11920923848",
            "11920927830",
            "11920930926",
            "11920933124",
            "11920935877",
        ],
        "client_order_id": [
            "x-xcKtGhcu7de99899f96ded39b93078",
            "x-xcKtGhcue8e7d05012504570bdc9c4",
            "x-xcKtGhcu906d612be97431dcf4e73f",
            "x-xcKtGhcu6421301bf8ea37a0eb20b0",
            "x-xcKtGhcudf299f5379765760a389c0",
        ],
        "timestamp": [
            1690887905439.0,
            1690887965384.0,
            1690888024845.0,
            1690888083959.0,
            1690888143604.0,
        ],
        "datetime": [
            "2023-08-01T11:05:05.439Z",
            "2023-08-01T11:06:05.384Z",
            "2023-08-01T11:07:04.845Z",
            "2023-08-01T11:08:03.959Z",
            "2023-08-01T11:09:03.604Z",
        ],
        "last_trade_timestamp": [np.NaN, np.NaN, np.NaN, np.NaN, np.NaN],
        "symbol": ["GMT/USDT", "GMT/USDT", "GMT/USDT", "GMT/USDT", "GMT/USDT"],
        "order_type": ["limit", "limit", "limit", "limit", "limit"],
        "time_in_force": ["GTC", "GTC", "GTC", "GTC", "GTC"],
        "post_only": [False, False, False, False, False],
        "reduce_only": [False, False, False, False, False],
        "side": ["buy", "buy", "buy", "buy", "buy"],
        "order_price": [0.2123, 0.2124, 0.2124, 0.2124, 0.2124],
        "stop_price": [None, None, None, None, None],
        "order_amount": [370.0, 370.0, 370.0, 370.0, 370.0],
        "cost": [0.0, 0.0, 0.0, 0.0, 0.0],
        "average": [np.NaN, np.NaN, np.NaN, np.NaN, np.NaN],
        "filled": [0.0, 0.0, 0.0, 0.0, 0.0],
        "remaining": [370.0, 370.0, 370.0, 370.0, 370.0],
        "status": ["open", "open", "open", "open", "open"],
        "fee": [None, None, None, None, None],
        "trades": [[], [], [], [], []],
        "fees": [[], [], [], [], []],
        "order_update_timestamp": [
            "1690887905439",
            "1690887965384",
            "1690888024845",
            "1690888083959",
            "1690888143604",
        ],
        "order_update_datetime": [
            pd.Timestamp("2023-08-01 11:05:05.439000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 11:06:05.384000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 11:07:04.845000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 11:08:03.959000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 11:09:03.604000+0000", tz="UTC"),
        ],
    }
    return pd.DataFrame(data)


def _get_child_order_response_df3() -> pd.DataFrame:
    """
    Generate a 2-bar snippet of real-life data.

    `info` column is not included to improve readability.
    """
    data = {
        "order": [
            "11921729784",
            "11921735073",
            "11921741600",
            "11921746960",
            "11921752090",
            "11921757066",
            "11921762387",
            "11921766813",
            "11921770989",
            "11921775512",
        ],
        "client_order_id": [
            "x-xcKtGhcu8ae8fe9a52868967349e92",
            "x-xcKtGhcub8442396bc9465103845e9",
            "x-xcKtGhcue4b553f2fac970ed637563",
            "x-xcKtGhcub4fd13b72e48165539a861",
            "x-xcKtGhcuae70f24833e12c4b8f57b8",
            "x-xcKtGhcuaf4c7edabab1bfbcb3da10",
            "x-xcKtGhcuda7088b0ce67b92de10ccc",
            "x-xcKtGhcu6fd6fe8a6dfebda714652",
            "x-xcKtGhcua749d70ba11e51cb40081a",
            "x-xcKtGhcue55221aa6858d426c9ca92",
        ],
        "timestamp": [
            1690902005546.0,
            np.nan,
            np.nan,
            1690902183524.0,
            1690902245462.0,
            np.nan,
            np.nan,
            np.nan,
            1690902483196.0,
            1690902545062.0,
        ],
        "datetime": [
            "2023-08-01T15:00:05.546Z",
            None,
            None,
            "2023-08-01T15:03:03.524Z",
            "2023-08-01T15:04:05.462Z",
            None,
            None,
            None,
            "2023-08-01T15:08:03.196Z",
            "2023-08-01T15:09:05.062Z",
        ],
        "last_trade_timestamp": [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "symbol": [
            "GMT/USDT",
            "GMT/USDT",
            "GMT/USDT",
            "GMT/USDT",
            "GMT/USDT",
            "GMT/USDT",
            "GMT/USDT",
            "GMT/USDT",
            "GMT/USDT",
            "GMT/USDT",
        ],
        "order_type": [
            "limit",
            "limit",
            "limit",
            "limit",
            "limit",
            "limit",
            "limit",
            "limit",
            "limit",
            "limit",
        ],
        "time_in_force": [
            "GTC",
            "GTC",
            "GTC",
            "GTC",
            "GTC",
            "GTC",
            "GTC",
            "GTC",
            "GTC",
            "GTC",
        ],
        "post_only": [
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        ],
        "reduce_only": [
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        ],
        "side": [
            "buy",
            "buy",
            "buy",
            "buy",
            "buy",
            "sell",
            "sell",
            "sell",
            "sell",
            "sell",
        ],
        "order_price": [
            0.2111,
            0.2114,
            0.2113,
            0.211,
            0.2113,
            0.2116,
            0.2118,
            0.2121,
            0.2122,
            0.2121,
        ],
        "stop_price": [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "order_amount": [
            152.0,
            152.0,
            152.0,
            152.0,
            152.0,
            222.0,
            222.0,
            222.0,
            222.0,
            222.0,
        ],
        "cost": [
            0.0,
            32.1176,
            32.0872,
            0.0,
            0.0,
            46.9974,
            47.064,
            47.0862,
            0.0,
            0.0,
        ],
        "average": [
            np.nan,
            0.2113,
            0.2111,
            np.nan,
            np.nan,
            0.2117,
            0.212,
            0.2121,
            np.nan,
            np.nan,
        ],
        "filled": [0.0, 152.0, 152.0, 0.0, 0.0, 222.0, 222.0, 222.0, 0.0, 0.0],
        "remaining": [152.0, 0.0, 0.0, 152.0, 152.0, 0.0, 0.0, 0.0, 222.0, 222.0],
        "status": [
            "open",
            "closed",
            "closed",
            "open",
            "open",
            "closed",
            "closed",
            "closed",
            "open",
            "open",
        ],
        "fee": [None, None, None, None, None, None, None, None, None, None],
        "trades": [[], [], [], [], [], [], [], [], [], []],
        "fees": [[], [], [], [], [], [], [], [], [], []],
        "order_update_timestamp": [
            "1690902005546",
            "1690902065354",
            "1690902124728",
            "1690902183524",
            "1690902245462",
            "1690902305149",
            "1690902363869",
            "1690902423595",
            "1690902483196",
            "1690902545062",
        ],
        "order_update_datetime": [
            pd.Timestamp("2023-08-01 15:00:05.546000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:01:05.354000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:02:04.728000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:03:03.524000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:04:05.462000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:05:05.149000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:06:03.869000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:07:03.595000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:08:03.196000+0000", tz="UTC"),
            pd.Timestamp("2023-08-01 15:09:05.062000+0000", tz="UTC"),
        ],
    }
    return pd.DataFrame(data)


def _get_child_order_df() -> pd.DataFrame:
    """
    Generate synthetic data.
    """
    start_ts = [
        pd.Timestamp("2023-03-15 16:35:37.825835+0000", tz="UTC"),
        pd.Timestamp("2023-03-15 16:35:38.718960+0000", tz="UTC"),
        pd.Timestamp("2023-03-15 16:35:39.718960+0000", tz="UTC"),
        pd.Timestamp("2023-03-15 16:35:40.718960+0000", tz="UTC"),
    ]
    data = {
        "creation_timestamp": start_ts,
        "asset_id": [6051632686, 8717633868, 6051632686, 8717633868],
        "type_": ["limit", "limit", "limit", "limit"],
        "start_timestamp": start_ts,
        "end_timestamp": [
            pd.Timestamp("2023-03-15 16:36:37.825835+0000", tz="UTC"),
            pd.Timestamp("2023-03-15 16:36:38.718960+0000", tz="UTC"),
            pd.Timestamp("2023-03-15 16:36:39.825835+0000", tz="UTC"),
            pd.Timestamp("2023-03-15 16:36:40.718960+0000", tz="UTC"),
        ],
        "diff_num_shares": [10.0, -1.0, 10, -1],
        "limit_price": [4.12045, 15.804999, 12.88, 10.9],
    }
    df = pd.DataFrame(data)
    return df


def _get_fills_df() -> pd.DataFrame:
    """
    Generate synthetic data.
    """
    timestamps = [
        "2023-03-31 16:35:39.268000+00:00",
        "2023-03-31 16:35:40.268000+00:00",
        "2023-03-31 16:36:41.268000+00:00",
        "2023-03-31 16:36:42.268000+00:00",
    ]
    data = {
        "order": [7954906695, 4551306695, 7909906695, 3154906695],
        "id": [352825168, 762825168, 232825168, 972825168],
        "asset_id": ["6051632686", "8717633868", "6051632686", "8717633868"],
        "symbol": ["APE/USDT", "AVAX/USDT", "APE/USDT", "AVAX/USDT"],
        "buy_count": [1, 1, 0, 0],
        "sell_count": [0, 0, 1, 1],
        "taker_count": [1, 0, 1, 1],
        "maker_count": [0, 1, 0, 0],
        "buy_volume": [10, 1, 0, 0],
        "sell_volume": [0, 0, 12, 5],
        "taker_volume": [10, 0, 12, 5],
        "maker_volume": [0, 1, 0, 0],
        "buy_notional": [42.0, 5.85, 0, 0],
        "sell_notional": [0, 0, 93.6, 19.5],
        "taker_notional": [42.0, 0, 93.6, 19.5],
        "maker_notional": [0, 5.85, 0, 0],
        "price": [4.2, 5.85, 7.8, 3.9],
        "first_timestamp": timestamps,
        "last_timestamp": timestamps,
        "first_datetime": timestamps,
        "last_datetime": timestamps,
        "amount": [10, 1, 12, 5],
        "cost": [42.0, 5.85, 93.6, 19.5],
        "transaction_cost": [0.000009456, 0.0000096, 0.00000612, 0.0000056],
        "realized_pnl": [0, 0, 0, 0],
    }
    df = pd.DataFrame(data)
    datetime_col_names = [
        "first_timestamp",
        "last_timestamp",
        "first_datetime",
        "last_datetime",
    ]
    for col in datetime_col_names:
        df[col] = pd.to_datetime(df[col])
    return df


def _check(self_: Any, actual: pd.DataFrame, expected: str) -> None:
    actual = hpandas.df_to_str(actual, num_rows=None)
    self_.assert_equal(actual, expected, fuzzy_match=True)


class Test_aggregate_ccxt_orders_by_bar(hunitest.TestCase):
    """
    Verify that orders are aggregated by bar correctly.
    """

    def test1(self) -> None:
        """
        Verify order response aggregation based on synthetic data.
        """
        child_order_response_df = _get_child_order_response_df1()
        freq = "T"
        actual = obccagfu.aggregate_ccxt_orders_by_bar(
            child_order_response_df, freq
        )
        expected = r"""
                                order_count            buy_order_count            buy_limit_twap            buy_limit_vwap            buy_amount            buy_notional            sell_order_count            sell_limit_twap            sell_limit_vwap            sell_amount            sell_notional
        asset_id                   2766533309 6051632686      2766533309 6051632686     2766533309 6051632686     2766533309 6051632686 2766533309 6051632686   2766533309 6051632686       2766533309 6051632686      2766533309 6051632686      2766533309 6051632686  2766533309 6051632686    2766533309 6051632686
        bar_end_datetime
        2023-03-15 16:36:00+00:00           2          2               1          1           10.1        8.2           10.1        8.2          3         10         30.3       82.0                1          1            9.85        2.7            9.85        NaN           1          0          9.85        0.0
        """
        _check(self, actual, expected)

    def test2(self) -> None:
        """
        Verify order response aggregation based on real world data.
        """
        child_order_response_df = _get_child_order_response_df2()
        freq = "5T"
        actual = obccagfu.aggregate_ccxt_orders_by_bar(
            child_order_response_df, freq
        )
        expected = r"""order_count buy_order_count buy_limit_twap buy_limit_vwap buy_amount buy_notional
        asset_id 1030828978 1030828978 1030828978 1030828978 1030828978 1030828978
        bar_end_datetime
        2023-08-01 11:10:00+00:00 5 5 0.21238 0.21238 1850.0 392.903
        """
        _check(self, actual, expected)

    def test3(self) -> None:
        """
        Verify order response aggregation based on real world data.
        """
        child_order_response_df = _get_child_order_response_df3()
        freq = "5T"
        actual = obccagfu.aggregate_ccxt_orders_by_bar(
            child_order_response_df, freq
        )
        expected = r"""order_count buy_order_count buy_limit_twap buy_limit_vwap buy_amount buy_notional sell_order_count sell_limit_twap sell_limit_vwap sell_amount sell_notional
        asset_id 1030828978 1030828978 1030828978 1030828978 1030828978 1030828978 1030828978 1030828978 1030828978 1030828978 1030828978
        bar_end_datetime
        2023-08-01 15:05:00+00:00 5 5 0.21122 0.21122 760.0 160.5272 0 NaN NaN NaN NaN
        2023-08-01 15:10:00+00:00 5 0 NaN NaN NaN NaN 5 0.21196 0.21196 1110.0 235.2756
        """
        _check(self, actual, expected)


class Test_aggregate_child_limit_orders_by_bar(hunitest.TestCase):
    """
    Test that internal child orders are summarized by bar and instrument
    correctly.
    """

    def test1(self) -> None:
        df = _get_child_order_df()
        freq = "T"
        actual = obccagfu.aggregate_child_limit_orders_by_bar(df, freq)
        expected = r"""
                                order_count            buy_order_count buy_limit_twap buy_limit_vwap buy_amount buy_notional sell_order_count sell_limit_twap sell_limit_vwap sell_amount sell_notional
        asset_id                   6051632686 8717633868      6051632686     6051632686     6051632686 6051632686   6051632686       8717633868      8717633868      8717633868  8717633868    8717633868
        bar_end_datetime
        2023-03-15 16:36:00+00:00         2        2               2       8.500225       8.500225       20.0     170.0045                2         13.3525         13.3525         2.0     26.704999
        """
        _check(self, actual, expected)


class Test_aggregate_fills_by_bar(hunitest.TestCase):
    """
    Test that a fills dataframe aggregates by order id, then by bar at `freq`
    correctly.
    """

    def test1(self) -> None:
        fills_df = _get_fills_df()
        freq = "T"
        actual = obccagfu.aggregate_fills_by_bar(fills_df, freq)
        expected = r"""
                                                               first_timestamp                    last_timestamp                    first_datetime                     last_datetime     symbol    asset_id  buy_count  sell_count  taker_count  maker_count  buy_volume  sell_volume  taker_volume  maker_volume  buy_notional  sell_notional  taker_notional  maker_notional  price  amount   cost  transaction_cost  realized_pnl
        bar_end_datetime          asset_id
        2023-03-31 16:36:00+00:00 6051632686  2023-03-31 16:35:39.268000+00:00  2023-03-31 16:35:39.268000+00:00  2023-03-31 16:35:39.268000+00:00  2023-03-31 16:35:39.268000+00:00   APE/USDT  6051632686          1           0            1            0          10            0            10             0         42.00            0.0            42.0            0.00   4.20      10  42.00          0.000009             0
                                  8717633868  2023-03-31 16:35:40.268000+00:00  2023-03-31 16:35:40.268000+00:00  2023-03-31 16:35:40.268000+00:00  2023-03-31 16:35:40.268000+00:00  AVAX/USDT  8717633868          1           0            0            1           1            0             0             1          5.85            0.0             0.0            5.85   5.85       1   5.85          0.000010             0
        2023-03-31 16:37:00+00:00 6051632686  2023-03-31 16:36:41.268000+00:00  2023-03-31 16:36:41.268000+00:00  2023-03-31 16:36:41.268000+00:00  2023-03-31 16:36:41.268000+00:00   APE/USDT  6051632686          0           1            1            0           0           12            12             0          0.00           93.6            93.6            0.00   7.80      12  93.60          0.000006             0
                                  8717633868  2023-03-31 16:36:42.268000+00:00  2023-03-31 16:36:42.268000+00:00  2023-03-31 16:36:42.268000+00:00  2023-03-31 16:36:42.268000+00:00  AVAX/USDT  8717633868          0           1            1            0           0            5             5             0          0.00           19.5            19.5            0.00   3.90       5  19.50          0.000006             0
        """
        _check(self, actual, expected)


class Test_aggregate_fills_by_order(hunitest.TestCase):
    """
    Test that fills dataframe aggregates by order id correctly.
    """

    def test1(self) -> None:
        fills_df = _get_fills_df()
        fills_df = fills_df.loc[fills_df["symbol"] == "APE/USDT"]
        #
        actual = obccagfu.aggregate_fills_by_order(fills_df)
        expected = r"""
                                     first_timestamp                    last_timestamp                    first_datetime                     last_datetime    symbol    asset_id  buy_count  sell_count  taker_count  maker_count  buy_volume  sell_volume  taker_volume  maker_volume  buy_notional  sell_notional  taker_notional  maker_notional  price  amount  cost  transaction_cost  realized_pnl
        order
        7909906695  2023-03-31 16:36:41.268000+00:00  2023-03-31 16:36:41.268000+00:00  2023-03-31 16:36:41.268000+00:00  2023-03-31 16:36:41.268000+00:00  APE/USDT  6051632686          0           1            1            0           0           12            12             0           0.0           93.6            93.6             0.0    7.8      12  93.6          0.000006             0
        7954906695  2023-03-31 16:35:39.268000+00:00  2023-03-31 16:35:39.268000+00:00  2023-03-31 16:35:39.268000+00:00  2023-03-31 16:35:39.268000+00:00  APE/USDT  6051632686          1           0            1            0          10            0            10             0          42.0            0.0            42.0             0.0    4.2      10  42.0          0.000009             0
        """
        _check(self, actual, expected)


class Test_compute_buy_sell_prices_by_bar(hunitest.TestCase):
    """
    Check that buy/sell trade prices by symbol and bar are computed correctly.
    """

    def test1(self) -> None:
        fills_df = _get_fills_df()
        freq = "T"
        actual = obccagfu.compute_buy_sell_prices_by_bar(fills_df, freq)
        # There is no buy / sell order at timestamps with NaN values in the row.
        expected = r"""
                                buy_trade_price            sell_trade_price
        asset_id                       6051632686 8717633868       6051632686 8717633868
        bar_end_datetime
        2023-03-31 16:36:00+00:00             4.2       5.85              NaN        NaN
        2023-03-31 16:37:00+00:00             NaN        NaN              7.8        3.9
        """
        _check(self, actual, expected)
