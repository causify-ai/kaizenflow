import datetime
import os
import pprint
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

import core.real_time as creatime
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import oms.broker.ccxt.abstract_ccxt_broker as obcaccbr
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.fill as omfill
import oms.order.order as oordorde

# #############################################################################
# Child order responses.
# #############################################################################


def _get_dummy_ccxt_child_order_responses() -> List[obcccclo.CcxtData]:
    """
    Return two CCXT child order responses.
    """
    ccxt_order_resp1 = {
        "info": {
            "orderId": "7954906695",
            "symbol": "APEUSDT",
            "status": "NEW",
            "clientOrderId": "x-xcKtGhcub89989e55d47273a3610a9",
            "price": "4.1200",
            "avgPrice": "0.0000",
            "origQty": "10",
            "executedQty": "0",
            "cumQty": "0",
            "cumQuote": "0",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "reduceOnly": False,
            "closePosition": False,
            "side": "BUY",
            "positionSide": "BOTH",
            "stopPrice": "0",
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "origType": "LIMIT",
            "updateTime": np.int64("1678898138582"),
        },
        "id": np.int64("7954906695"),
        "clientOrderId": "x-xcKtGhcub89989e55d47273a3610a9",
        "timestamp": 1678898138582,
        "datetime": pd.Timestamp("2023-03-15T16:35:38.582Z"),
        "lastTradeTimestamp": None,
        "symbol": "APE/USDT",
        "type": "limit",
        "timeInForce": "GTC",
        "postOnly": False,
        "reduceOnly": False,
        "side": "buy",
        "price": np.float64(4.12),
        "stopPrice": np.float64(None),
        "amount": np.float64(10.0),
        "cost": np.float64(0.0),
        "average": np.float64(None),
        "filled": np.float64(0.0),
        "remaining": np.float64(10.0),
        "status": "open",
        "fee": np.float64(None),
        "trades": [],
        "fees": [],
    }
    ccxt_order_resp2 = {
        "info": {
            "orderId": "14412582631",
            "symbol": "AVAXUSDT",
            "status": "NEW",
            "clientOrderId": "x-xcKtGhcub03933b03766705d9d532f",
            "price": "15.8050",
            "avgPrice": "0.0000",
            "origQty": "1",
            "executedQty": "0",
            "cumQty": "0",
            "cumQuote": "0",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "reduceOnly": False,
            "closePosition": False,
            "side": "SELL",
            "positionSide": "BOTH",
            "stopPrice": "0",
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "origType": "LIMIT",
            "updateTime": np.int64("1678898139409"),
        },
        "id": np.int64("14412582631"),
        "clientOrderId": "x-xcKtGhcub03933b03766705d9d532f",
        "timestamp": 1678898139409,
        "datetime": pd.Timestamp("2023-03-15T16:35:39.409Z"),
        "lastTradeTimestamp": None,
        "symbol": "AVAX/USDT",
        "type": "limit",
        "timeInForce": "GTC",
        "postOnly": False,
        "reduceOnly": False,
        "side": "sell",
        "price": np.float64(15.805),
        "stopPrice": np.float64(None),
        "amount": np.float64(1.0),
        "cost": np.float64(0.0),
        "average": np.float64(None),
        "filled": np.float64(0.0),
        "remaining": np.float64(1.0),
        "status": "open",
        "fee": np.float64(None),
        "trades": [],
        "fees": [],
    }
    return [ccxt_order_resp1, ccxt_order_resp2]


def _get_dummy_reduce_only_ccxt_child_order_responses() -> obcccclo.CcxtData:
    """
    Return a dictionary with CCXT reduce-only child order responses.
    """
    ccxt_order_resp1 = {
        "info": {
            "orderId": "7954906695",
            "symbol": "APEUSDT",
            "status": "NEW",
            "clientOrderId": "x-xcKtGhcub89989e55d47273a3610a9",
            "price": "4.1200",
            "avgPrice": "0.0000",
            "origQty": "10",
            "executedQty": "0",
            "cumQty": "0",
            "cumQuote": "0",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "reduceOnly": True,
            "closePosition": False,
            "side": "BUY",
            "positionSide": "BOTH",
            "stopPrice": "0",
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "origType": "LIMIT",
            "updateTime": np.int64("1678898138582"),
        },
        "id": np.int64("7954906695"),
        "clientOrderId": "x-xcKtGhcub89989e55d47273a3610a9",
        "timestamp": 1678898138582,
        "datetime": pd.Timestamp("2023-03-15T16:35:38.582Z"),
        "lastTradeTimestamp": None,
        "symbol": "APE/USDT",
        "type": "limit",
        "timeInForce": "GTC",
        "postOnly": False,
        "reduceOnly": False,
        "side": "buy",
        "price": np.float64(4.12),
        "stopPrice": np.float64(None),
        "amount": np.float64(10.0),
        "cost": np.float64(0.0),
        "average": np.float64(None),
        "filled": np.float64(0.0),
        "remaining": np.float64(10.0),
        "status": "open",
        "fee": np.float64(None),
        "trades": [],
        "fees": [],
    }
    return ccxt_order_resp1


# #############################################################################
# CCXT trades.
# #############################################################################


def _get_dummy_ccxt_trades() -> List[List[obcccclo.CcxtData]]:
    """
    Return CCXT trades.
    """
    ccxt_trades1 = [
        {
            "info": {
                "symbol": "APEUSDT",
                "id": "352824923",
                "orderId": "7954906695",
                "side": "BUY",
                "price": "4.1200",
                "qty": "10",
                "realizedPnl": np.float64("0"),
                "marginAsset": "USDT",
                "quoteQty": "41.2000",
                "commission": "0.00824000",
                "commissionAsset": "USDT",
                "time": "1678898139268",
                "positionSide": "BOTH",
                "buyer": True,
                "maker": True,
            },
            "timestamp": 1678898139268,
            "datetime": pd.Timestamp("2023-03-15T16:35:39.268Z"),
            "symbol": "APE/USDT",
            "asset_id": 6051632686,
            "id": np.int64("352824923"),
            "order": np.int64("7954906695"),
            "type": None,
            "side": "buy",
            "takerOrMaker": "maker",
            "price": 4.12,
            "amount": 10.0,
            "cost": 41.2,
            "fee": {"cost": 0.00824, "currency": "USDT"},
            "fees": [{"currency": "USDT", "cost": 0.00824}],
        },
        {
            "info": {
                "symbol": "APEUSDT",
                "id": "352825168",
                "orderId": "7954913312",
                "side": "BUY",
                "price": "4.1100",
                "qty": "10",
                "realizedPnl": np.float64("0"),
                "marginAsset": "USDT",
                "quoteQty": "41.1000",
                "commission": "0.01644000",
                "commissionAsset": "USDT",
                "time": "1678898162247",
                "positionSide": "BOTH",
                "buyer": True,
                "maker": False,
            },
            "timestamp": 1678898162247,
            "datetime": pd.Timestamp("2023-03-15T16:36:02.247Z"),
            "symbol": "APE/USDT",
            "asset_id": 6051632686,
            "id": np.int64("352825168"),
            "order": np.int64("7954913312"),
            "type": None,
            "side": "buy",
            "takerOrMaker": "taker",
            "price": 4.11,
            "amount": 10.0,
            "cost": 41.1,
            "fee": {"cost": 0.01644, "currency": "USDT"},
            "fees": [{"currency": "USDT", "cost": 0.01644}],
        },
    ]
    #
    ccxt_trades2 = [
        {
            "info": {
                "symbol": "AVAXUSDT",
                "id": "469887880",
                "orderId": "14412662588",
                "side": "BUY",
                "price": "15.5590",
                "qty": "2",
                "realizedPnl": np.float64("0"),
                "marginAsset": "USDT",
                "quoteQty": "31.1180",
                "commission": "0.01244720",
                "commissionAsset": "USDT",
                "time": "1678898523121",
                "positionSide": "BOTH",
                "buyer": True,
                "maker": False,
            },
            "timestamp": 1678898523121,
            "datetime": pd.Timestamp("2023-03-15T16:42:03.121Z"),
            "symbol": "AVAX/USDT",
            "asset_id": 8717633868,
            "id": np.int64("469887880"),
            "order": np.int64("14412662588"),
            "type": None,
            "side": "buy",
            "takerOrMaker": "taker",
            "price": 15.559,
            "amount": 2.0,
            "cost": 31.118,
            "fee": {"cost": 0.0124472, "currency": "USDT"},
            "fees": [{"currency": "USDT", "cost": 0.0124472}],
        },
        {
            "info": {
                "symbol": "AVAXUSDT",
                "id": "469890039",
                "orderId": "14412678428",
                "side": "BUY",
                "price": "15.5690",
                "qty": "2",
                "realizedPnl": np.float64("0"),
                "marginAsset": "USDT",
                "quoteQty": "31.1380",
                "commission": "0.01245520",
                "commissionAsset": "USDT",
                "time": "1678898583042",
                "positionSide": "BOTH",
                "buyer": True,
                "maker": False,
            },
            "timestamp": 1678898583042,
            "datetime": pd.Timestamp("2023-03-15T16:43:03.042Z"),
            "symbol": "AVAX/USDT",
            "asset_id": 8717633868,
            "id": np.int64("469890039"),
            "order": np.int64("14412678428"),
            "type": None,
            "side": "buy",
            "takerOrMaker": "taker",
            "price": 15.569,
            "amount": 2.0,
            "cost": 31.138,
            "fee": {"cost": 0.0124552, "currency": "USDT"},
            "fees": [{"currency": "USDT", "cost": 0.0124552}],
        },
    ]
    #
    ccxt_trades3 = [
        {
            "info": {
                "symbol": "APEUSDT",
                "id": "352839121",
                "orderId": "7955072984",
                "side": "BUY",
                "price": "4.0380",
                "qty": "6",
                "realizedPnl": np.float64("0"),
                "marginAsset": "USDT",
                "quoteQty": "24.2280",
                "commission": "0.00484560",
                "commissionAsset": "USDT",
                "time": "1678898740515",
                "positionSide": "BOTH",
                "buyer": True,
                "maker": True,
            },
            "timestamp": 1678898740515,
            "datetime": pd.Timestamp("2023-03-15T16:45:40.515Z"),
            "symbol": "APE/USDT",
            "asset_id": 6051632686,
            "id": np.int64("352839121"),
            "order": np.int64("7955072984"),
            "type": None,
            "side": "buy",
            "takerOrMaker": "maker",
            "price": 4.038,
            "amount": 6.0,
            "cost": 24.228,
            "fee": {"cost": 0.0048456, "currency": "USDT"},
            "fees": [{"currency": "USDT", "cost": 0.0048456}],
        },
        {
            "info": {
                "symbol": "APEUSDT",
                "id": "352841649",
                "orderId": "7955107622",
                "side": "BUY",
                "price": "4.0560",
                "qty": "6",
                "realizedPnl": np.float64("0"),
                "marginAsset": "USDT",
                "quoteQty": "24.3360",
                "commission": "0.00973440",
                "commissionAsset": "USDT",
                "time": "1678898882325",
                "positionSide": "BOTH",
                "buyer": True,
                "maker": False,
            },
            "timestamp": 1678898882325,
            "datetime": pd.Timestamp("2023-03-15T16:48:02.325Z"),
            "symbol": "APE/USDT",
            "asset_id": 6051632686,
            "id": np.int64("352841649"),
            "order": np.int64("7955107622"),
            "type": None,
            "side": "buy",
            "takerOrMaker": "taker",
            "price": 4.056,
            "amount": 6.0,
            "cost": 24.336,
            "fee": {"cost": 0.0097344, "currency": "USDT"},
            "fees": [{"currency": "USDT", "cost": 0.0097344}],
        },
    ]
    #
    ccxt_trades4 = [
        {
            "info": {
                "symbol": "APEUSDT",
                "id": "356819245",
                "orderId": "8077704766",
                "side": "SELL",
                "price": "4.0400",
                "qty": "6",
                "realizedPnl": np.float64("0"),
                "marginAsset": "USDT",
                "quoteQty": "24.2400",
                "commission": "0.00969600",
                "commissionAsset": "USDT",
                "time": "1679560540879",
                "positionSide": "BOTH",
                "buyer": False,
                "maker": False,
            },
            "timestamp": 1679560540879,
            "datetime": pd.Timestamp("2023-03-23T08:35:40.879Z"),
            "symbol": "APE/USDT",
            "asset_id": 6051632686,
            "id": np.int64("356819245"),
            "order": np.int64("8077704766"),
            "type": None,
            "side": "sell",
            "takerOrMaker": "taker",
            "price": 4.04,
            "amount": 6.0,
            "cost": 24.24,
            "fee": {"cost": 0.009696, "currency": "USDT"},
            "fees": [{"currency": "USDT", "cost": 0.009696}],
        },
        {
            "info": {
                "symbol": "AXSUSDT",
                "id": "420185708",
                "orderId": "8889302610",
                "side": "BUY",
                "price": "8.45500",
                "qty": "8",
                "realizedPnl": np.float64("0.11900000"),
                "marginAsset": "USDT",
                "quoteQty": "67.64000",
                "commission": "0.01352800",
                "commissionAsset": "USDT",
                "time": "1679560584427",
                "positionSide": "BOTH",
                "buyer": True,
                "maker": True,
            },
            "timestamp": 1679560584427,
            "datetime": pd.Timestamp("2023-03-23T08:36:24.427Z"),
            "symbol": "AXS/USDT",
            "asset_id": 2540896331,
            "id": np.int64("420185708"),
            "order": np.int64("8889302610"),
            "type": None,
            "side": "buy",
            "takerOrMaker": "maker",
            "price": 8.455,
            "amount": 8.0,
            "cost": 67.64,
            "fee": {"cost": 0.013528, "currency": "USDT"},
            "fees": [{"currency": "USDT", "cost": 0.013528}],
        },
    ]
    return [
        ccxt_trades1,
        ccxt_trades2,
        ccxt_trades3,
        ccxt_trades4,
    ]


# #############################################################################
# CCXT fills.
# #############################################################################


def _get_dummy_ccxt_fills() -> List[List[obcccclo.CcxtData]]:
    """
    Return two examples of CCXT fills.
    """
    ccxt_fills1 = [
        {
            "info": {
                "orderId": "14901643572",
                "symbol": "AVAXUSDT",
                "status": "FILLED",
                "clientOrderId": "x-xcKtGhcu8261da0e4a2533b528e0e2",
                "price": 14.7610,
                "avgPrice": 14.7540,
                "origQty": 1,
                "executedQty": "1",
                "cumQuote": "14.7540",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": False,
                "closePosition": False,
                "side": "BUY",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": "LIMIT",
                "time": "1684843129172",
                "updateTime": np.int64("1684843129172"),
            },
            "id": np.int64("14901643572"),
            "clientOrderId": "x-xcKtGhcu8261da0e4a2533b528e0e2",
            "timestamp": 1684843129172,
            "datetime": pd.Timestamp("2023-05-23T11:58:49.172Z"),
            "lastTradeTimestamp": None,
            "symbol": "AVAX/USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": False,
            "reduceOnly": False,
            "side": "buy",
            "price": np.float64(14.761),
            "stopPrice": np.float64(None),
            "amount": np.float64(1.0),
            "cost": np.float64(14.754),
            "average": np.float64(14.754),
            "filled": np.float64(1.0),
            "remaining": np.float64(0.0),
            "status": "closed",
            "fee": np.float64(None),
            "trades": [],
            "fees": [],
        },
        {
            "info": {
                "orderId": "153017797793",
                "symbol": "BTCUSDT",
                "status": "FILLED",
                "clientOrderId": "x-xcKtGhcua8e7e261598721e6c6295c",
                "price": "27341.90",
                "avgPrice": "27330.40000",
                "origQty": "0.001",
                "executedQty": "0.001",
                "cumQuote": "27.33040",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": False,
                "closePosition": False,
                "side": "BUY",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": "LIMIT",
                "time": "1684843129687",
                "updateTime": np.int64("1684843129687"),
            },
            "id": np.int64("153017797793"),
            "clientOrderId": "x-xcKtGhcua8e7e261598721e6c6295c",
            "timestamp": 1684843129687,
            "datetime": pd.Timestamp("2023-05-23T11:58:49.687Z"),
            "lastTradeTimestamp": None,
            "symbol": "BTC/USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": False,
            "reduceOnly": False,
            "side": "buy",
            "price": np.float64(27341.9),
            "stopPrice": np.float64(None),
            "amount": np.float64(0.001),
            "cost": np.float64(27.3304),
            "average": np.float64(27330.4),
            "filled": np.float64(0.001),
            "remaining": np.float64(0.0),
            "status": "closed",
            "fee": np.float64(None),
            "trades": [],
            "fees": [],
        },
    ]
    ccxt_fills2 = [
        {
            "info": {
                "orderId": "2187830797",
                "symbol": "CTKUSDT",
                "status": "FILLED",
                "clientOrderId": "x-xcKtGhcuda5dde8563a5c1568a5893",
                "price": "0.74810",
                "avgPrice": "0.74810",
                "origQty": "93",
                "executedQty": "93",
                "cumQuote": "69.57330",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": False,
                "closePosition": False,
                "side": "BUY",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": "LIMIT",
                "time": "1684843130201",
                "updateTime": np.int64("1684843130201"),
            },
            "id": np.int64("2187830797"),
            "clientOrderId": "x-xcKtGhcuda5dde8563a5c1568a5893",
            "timestamp": 1684843130201,
            "datetime": pd.Timestamp("2023-05-23T11:58:50.201Z"),
            "lastTradeTimestamp": None,
            "symbol": "CTK/USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": False,
            "reduceOnly": False,
            "side": "buy",
            "price": np.float64(0.7481),
            "stopPrice": np.float64(None),
            "amount": np.float64(93.0),
            "cost": np.float64(69.5733),
            "average": np.float64(0.7481),
            "filled": np.float64(93.0),
            "remaining": np.float64(0.0),
            "status": "closed",
            "fee": np.float64(None),
            "trades": [],
            "fees": [],
        },
        {
            "info": {
                "orderId": "8378993779",
                "symbol": "DYDXUSDT",
                "status": "FILLED",
                "clientOrderId": "x-xcKtGhcucc938a1e2341d522e5f1da",
                "price": "2.180",
                "avgPrice": "2.1820",
                "origQty": "3",
                "executedQty": "3",
                "cumQuote": "6.5460",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": False,
                "closePosition": False,
                "side": "SELL",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": "LIMIT",
                "time": "1684843130456",
                "updateTime": np.int64("1684843130456"),
            },
            "id": np.int64("8378993779"),
            "clientOrderId": "x-xcKtGhcucc938a1e2341d522e5f1da",
            "timestamp": 1684843130456,
            "datetime": pd.Timestamp("2023-05-23T11:58:50.456Z"),
            "lastTradeTimestamp": None,
            "symbol": "DYDX/USDT",
            "type": "limit",
            "timeInForce": "GTC",
            "postOnly": False,
            "reduceOnly": False,
            "side": "sell",
            "price": np.float64(2.18),
            "stopPrice": np.float64(False),
            "amount": np.float64(3.0),
            "cost": np.float64(6.546),
            "average": np.float64(2.182),
            "filled": np.float64(3.0),
            "remaining": np.float64(0.0),
            "status": "closed",
            "fee": np.float64(False),
            "trades": [],
            "fees": [],
        },
    ]
    return [ccxt_fills1, ccxt_fills2]


# #############################################################################
# OMS fills.
# #############################################################################


def _get_dummy_oms_fills() -> List[List[obcccclo.CcxtData]]:
    """
    Return two OMS fills.
    """
    oms_fills1 = [
        {
            "asset_id": np.int64(8717633868),
            "fill_id": np.int64(2),
            "timestamp": pd.Timestamp("2023-05-23T11:58:49.172000+00:00"),
            "num_shares": np.float64(1.0),
            "price": np.float64(14.7540),
        },
        {
            "asset_id": np.int64(1467591036),
            "fill_id": np.int64(4),
            "timestamp": pd.Timestamp("2023-05-23T11:58:49.687000+00:00"),
            "num_shares": np.float64(0.001),
            "price": np.float64(27.3304),
        },
    ]
    oms_fills2 = [
        {
            "asset_id": np.int64(5115052901),
            "fill_id": np.int64(6),
            "timestamp": pd.Timestamp("2023-05-23T11:58:50.201000+00:00"),
            "num_shares": np.float64(93.0),
            "price": np.float64(69.5733),
        },
        {
            "asset_id": np.int64(3401245610),
            "fill_id": np.int64(7),
            "timestamp": pd.Timestamp("2023-05-23T11:58:50.456000+00:00"),
            "num_shares": np.float64(3.0),
            "price": np.float64(6.546),
        },
    ]
    return [oms_fills1, oms_fills2]


# #############################################################################
# OMS parent orders.
# #############################################################################


def _get_dummy_oms_parent_orders() -> List[obcccclo.CcxtData]:
    """
    Return two OMS parent orders.
    """
    parent_order1 = {
        "order_id": 0,
        "creation_timestamp": pd.Timestamp("2023-03-15 12:34:38.718960-04:00"),
        "asset_id": np.int64(6051632686),
        "type_": "limit",
        "start_timestamp": pd.Timestamp("2023-03-15 12:34:38.718960-04:00"),
        "end_timestamp": pd.Timestamp("2023-03-15 12:39:38.718960-04:00"),
        "curr_num_shares": np.float64(0.0),
        "diff_num_shares": np.float64(50.0),
        "tz": "America/New_York",
        "extra_params": dict(),
    }
    parent_order2 = {
        "order_id": 1,
        "creation_timestamp": pd.Timestamp("2023-03-15 12:34:39.718960-04:00"),
        "asset_id": np.int64(8717633868),
        "type_": "limit",
        "start_timestamp": pd.Timestamp("2023-03-15 12:34:39.718960-04:00"),
        "end_timestamp": pd.Timestamp("2023-03-15 12:39:39.718960-04:00"),
        "curr_num_shares": np.float64(0.0),
        "diff_num_shares": np.float64(-5.0),
        "tz": "America/New_York",
        "extra_params": dict(),
    }
    return [parent_order1, parent_order2]


# #############################################################################
# OMS child orders.
# #############################################################################


def _get_dummy_oms_child_orders() -> List[obcccclo.CcxtData]:
    """
    Return two OMS child orders.
    """
    child_order1 = {
        "order_id": 20,
        "creation_timestamp": pd.Timestamp("2023-03-15 12:35:37.825835-04:00"),
        "asset_id": np.int64(6051632686),
        "type_": "limit",
        "start_timestamp": pd.Timestamp("2023-03-15 12:35:37.825835-04:00"),
        "end_timestamp": pd.Timestamp("2023-03-15 12:36:37.825835-04:00"),
        "curr_num_shares": np.float64(0.0),
        "diff_num_shares": np.float64(10.0),
        "tz": "America/New_York",
        "passivity_factor": np.float64(0.55),
        "latest_bid_price": np.float64(4.12),
        "latest_ask_price": np.float64(4.121),
        "bid_price_mean": np.float64(4.125947368421053),
        "ask_price_mean": np.float64(4.126973684210526),
        "used_bid_price": "latest_bid_price",
        "used_ask_price": "latest_ask_price",
        "limit_price": np.float64(4.12045),
        "ccxt_id": [np.int64(7954906695)],
    }
    child_order1_extra_params = {
        "stats": {
            "order_generated_timestamp": datetime.datetime(
                2023, 5, 23, 11, 58, 51, 97108
            ),
            "order_prepared_for_submission_inside_class_timestamp": datetime.datetime(
                2023, 5, 23, 11, 58, 51, 97500
            ),
            "order_submitted_to_ccxt_inside_class_timestamp": datetime.datetime(
                2023, 5, 23, 11, 58, 51, 363107
            ),
            "order_submitted_inside_coroutine_timestamp": datetime.datetime(
                2023, 5, 23, 11, 58, 51, 363716
            ),
            "after_sleep_inside_coroutine_timestamp": datetime.datetime(
                2023, 5, 23, 11, 59, 1, 299605
            ),
            "cancelled_open_order_timestamp": datetime.datetime(
                2023, 5, 23, 11, 59, 1, 548572
            ),
            "_submit_single_order_to_ccxt::attempt_num": 1,
        },
        "order_coroutine_timed_scope_output": "generating_single_order_and_submitting done (10.455 s)",
        "ccxt_id": [11381353660],
    }
    child_order1["extra_params"] = child_order1_extra_params
    #
    child_order2 = {
        "order_id": 21,
        "creation_timestamp": pd.Timestamp("2023-03-15 12:35:38.718960-04:00"),
        "asset_id": np.int64(8717633868),
        "type_": "limit",
        "start_timestamp": pd.Timestamp("2023-03-15 12:35:38.718960-04:00"),
        "end_timestamp": pd.Timestamp("2023-03-15 12:36:38.718960-04:00"),
        "curr_num_shares": np.float64(0.0),
        "diff_num_shares": np.float64(-1.0),
        "tz": "America/New_York",
        "passivity_factor": np.float64(0.55),
        "latest_bid_price": np.float64(15.804),
        "latest_ask_price": np.float64(15.805),
        "bid_price_mean": np.float64(15.81816216216216),
        "ask_price_mean": np.float64(15.819432432432428),
        "used_bid_price": "latest_bid_price",
        "used_ask_price": "latest_ask_price",
        "limit_price": np.float64(15.804549999999999),
        "ccxt_id": [np.int64(14412582631)],
    }
    child_order2_extra_params = {
        "stats": {
            "order_generated_timestamp": datetime.datetime(
                2023, 5, 23, 11, 58, 50, 584038
            ),
            "order_prepared_for_submission_inside_class_timestamp": datetime.datetime(
                2023, 5, 23, 11, 58, 50, 584405
            ),
            "order_submitted_to_ccxt_inside_class_timestamp": datetime.datetime(
                2023, 5, 23, 11, 58, 50, 835601
            ),
            "order_submitted_inside_coroutine_timestamp": datetime.datetime(
                2023, 5, 23, 11, 58, 50, 836047
            ),
            "after_sleep_inside_coroutine_timestamp": datetime.datetime(
                2023, 5, 23, 11, 59, 3, 800553
            ),
            "cancelled_open_order_timestamp": datetime.datetime(
                2023, 5, 23, 11, 59, 4, 49388
            ),
            "_submit_single_order_to_ccxt::attempt_num": 1,
        },
        "ccxt_id": [8389765599793650580],
        "order_coroutine_timed_scope_output": "generating_single_order_and_submitting done (13.469 s)",
    }
    child_order2["extra_params"] = child_order2_extra_params
    return [child_order1, child_order2]


# #############################################################################
# Bid ask data.
# #############################################################################


def _get_dummy_bid_ask_data() -> pd.DataFrame:
    """
    Return a dataframe with bid ask data.
    """
    data = [
        {
            "timestamp": 1697754290111,
            "currency_pair": "GMT_USDT",
            "exchange_id": "binance",
            "end_download_timestamp": "2023-10-19 22:24:50.315872+00:00",
            "knowledge_timestamp": "2023-10-19 22:24:50.740828+00:00",
            "bid_size_l1": 270752.0,
            "bid_price_l1": 0.1407,
            "ask_size_l1": 31142.0,
            "ask_price_l1": 0.1408,
        },
        {
            "timestamp": 1697754290114,
            "currency_pair": "UNFI_USDT",
            "exchange_id": "binance",
            "end_download_timestamp": "2023-10-19 22:24:50.317413+00:00",
            "knowledge_timestamp": "2023-10-19 22:24:50.740828+00:00",
            "bid_size_l1": 286.6,
            "bid_price_l1": 5.85,
            "ask_size_l1": 35.6,
            "ask_price_l1": 5.851,
        },
        {
            "timestamp": 1697754290121,
            "currency_pair": "ETH_USDT",
            "exchange_id": "binance",
            "end_download_timestamp": "2023-10-19 22:24:50.313784+00:00",
            "knowledge_timestamp": "2023-10-19 22:24:50.740828+00:00",
            "bid_size_l1": 89.346,
            "bid_price_l1": 1566.49,
            "ask_size_l1": 19.878,
            "ask_price_l1": 1566.5,
        },
    ]
    bid_ask_data = pd.DataFrame(data)
    bid_ask_data.set_index("timestamp", inplace=True)
    return bid_ask_data


# #############################################################################
# CCXT exchange market info.
# #############################################################################


def _get_dummy_ccxt_exchange_markets() -> List[Dict[str, Any]]:
    """
    Return dictionary with CCXT exchange markets info.
    """
    exchange_markets = {
        "ETH/BTC": {
            "id": "ETHBTC",
            "symbol": "ETH/BTC",
            "base": "ETH",
            "quote": "BTC",
            "baseId": "ETH",
            "quoteId": "BTC",
            "active": True,
            "type": "spot",
            "linear": None,
            "inverse": None,
            "spot": True,
            "swap": False,
            "future": False,
            "option": False,
            "margin": True,
            "contract": False,
            "contractSize": None,
            "expiry": None,
            "expiryDatetime": None,
            "optionType": None,
            "strike": None,
            "settle": None,
            "settleId": None,
            "precision": {"amount": 4, "price": 5, "base": 8, "quote": 8},
        },
        "LTC/BTC": {
            "id": "LTCBTC",
            "symbol": "LTC/BTC",
            "base": "LTC",
            "quote": "BTC",
            "baseId": "LTC",
            "quoteId": "BTC",
            "active": True,
            "type": "spot",
            "linear": None,
            "inverse": None,
            "spot": True,
            "swap": False,
            "future": False,
            "option": False,
            "margin": True,
            "contract": False,
            "contractSize": None,
            "expiry": None,
            "expiryDatetime": None,
            "optionType": None,
            "strike": None,
            "settle": None,
            "settleId": None,
            "precision": {"amount": 3, "price": 6, "base": 8, "quote": 8},
        },
    }
    return exchange_markets


# #############################################################################
# CCXT leverage info.
# #############################################################################


def _get_dummy_ccxt_leverage_info() -> List[Dict[str, Any]]:
    """
    Build and return JSON objects with leverage info.
    """
    leverage_info = {
        "WAVES/USDT:USDT": [
            {
                "tier": 1.0,
                "currency": "USDT",
                "minNotional": 0.0,
                "maxNotional": 5000.0,
                "maintenanceMarginRate": 0.02,
                "maxLeverage": 25.0,
                "info": {
                    "bracket": "1",
                    "initialLeverage": "25",
                    "notionalCap": "5000",
                    "notionalFloor": "0",
                    "maintMarginRatio": "0.02",
                    "cum": "0.0",
                },
            },
            {
                "tier": 2.0,
                "currency": "USDT",
                "minNotional": 5000.0,
                "maxNotional": 50000.0,
                "maintenanceMarginRate": 0.025,
                "maxLeverage": 20.0,
                "info": {
                    "bracket": "2",
                    "initialLeverage": "20",
                    "notionalCap": "50000",
                    "notionalFloor": "5000",
                    "maintMarginRatio": "0.025",
                    "cum": "25.0",
                },
            },
        ],
        "BNB/USDT:USDT": [
            {
                "tier": 1.0,
                "currency": "USDT",
                "minNotional": 0.0,
                "maxNotional": 5000.0,
                "maintenanceMarginRate": 0.005,
                "maxLeverage": 75.0,
                "info": {
                    "bracket": "1",
                    "initialLeverage": "75",
                    "notionalCap": "5000",
                    "notionalFloor": "0",
                    "maintMarginRatio": "0.005",
                    "cum": "0.0",
                },
            },
            {
                "tier": 2.0,
                "currency": "USDT",
                "minNotional": 5000.0,
                "maxNotional": 10000.0,
                "maintenanceMarginRate": 0.006,
                "maxLeverage": 50.0,
                "info": {
                    "bracket": "2",
                    "initialLeverage": "50",
                    "notionalCap": "10000",
                    "notionalFloor": "5000",
                    "maintMarginRatio": "0.006",
                    "cum": "5.0",
                },
            },
        ],
    }
    return leverage_info


# #############################################################################
# CCXT positions.
# #############################################################################


def _get_dummy_ccxt_positions() -> List[obcccclo.CcxtData]:
    """
    Return dictionary with CCXT positions.
    """
    positions = [
        {
            "info": {
                "symbol": "SUSHIUSDT",
                "positionAmt": "0",
                "entryPrice": "0.0",
                "breakEvenPrice": "0.0",
                "markPrice": "0.00000000",
                "unRealizedProfit": "0.00000000",
                "liquidationPrice": "0",
                "leverage": "20",
                "maxNotionalValue": "25000",
                "marginType": "cross",
                "isolatedMargin": "0.00000000",
                "isAutoAddMargin": "false",
                "positionSide": "BOTH",
                "notional": "0",
                "isolatedWallet": "0",
                "updateTime": "0",
            },
            "id": None,
            "symbol": "SUSHI/USDT:USDT",
            "contracts": 0.0,
            "contractSize": 1.0,
            "unrealizedPnl": 0.0,
            "leverage": 20.0,
            "liquidationPrice": None,
            "collateral": 0.0,
            "notional": 0.0,
            "markPrice": None,
            "entryPrice": 0.0,
            "timestamp": None,
            "initialMargin": 0.0,
            "initialMarginPercentage": 0.05,
            "maintenanceMargin": 0.0,
            "maintenanceMarginPercentage": 0.01,
            "marginRatio": None,
            "datetime": None,
            "marginMode": "cross",
            "marginType": "cross",
            "side": None,
            "hedged": False,
            "percentage": None,
        },
        {
            "info": {
                "symbol": "BTSUSDT",
                "positionAmt": "0",
                "entryPrice": "0.0",
                "breakEvenPrice": "0.0",
                "markPrice": "0.00000000",
                "unRealizedProfit": "0.00000000",
                "liquidationPrice": "0",
                "leverage": "20",
                "maxNotionalValue": "25000",
                "marginType": "cross",
                "isolatedMargin": "0.00000000",
                "isAutoAddMargin": "false",
                "positionSide": "BOTH",
                "notional": "0",
                "isolatedWallet": "0",
                "updateTime": "0",
            },
            "id": None,
            "symbol": "BTS/USDT:USDT",
            "contracts": 0.0,
            "contractSize": 1.0,
            "unrealizedPnl": 0.0,
            "leverage": 20.0,
            "liquidationPrice": None,
            "collateral": 0.0,
            "notional": 0.0,
            "markPrice": None,
            "entryPrice": 0.0,
            "timestamp": None,
            "initialMargin": 0.0,
            "initialMarginPercentage": 0.05,
            "maintenanceMargin": 0.0,
            "maintenanceMarginPercentage": 0.01,
            "marginRatio": None,
            "datetime": None,
            "marginMode": "cross",
            "marginType": "cross",
            "side": None,
            "hedged": False,
            "percentage": None,
        },
    ]
    return positions


# #############################################################################
# CCXT balance.
# #############################################################################


def _get_dummy_ccxt_balance() -> List[Dict[str, Any]]:
    """
    Return object storing CCXT balance.
    """
    balance = {
        "BTC": {"free": 0.01920606, "used": 0.0, "total": 0.0},
        "XRP": {"free": 1053.43017081, "used": 0.0, "total": 0.0},
        "TUSD": {"free": 563.69921443, "used": 0.0, "total": 0.0},
        "BNB": {"free": 2.53888014, "used": 0.0, "total": 0.0},
        "ETH": {"free": 0.34075085, "used": 0.0, "total": 0.0},
        "USDT": {
            "free": 568.69011311,
            "used": 226.40951999,
            "total": 795.25866961,
        },
        "USDP": {"free": 563.34116224, "used": 0.0, "total": 0.0},
        "USDC": {"free": 563.22847138, "used": 0.0, "total": 0.0},
        "BUSD": {"free": 568.6914262, "used": 0.0, "total": 0.0},
        "timestamp": None,
        "datetime": None,
        "free": {
            "BTC": 0.01920606,
            "XRP": 1053.43017081,
            "TUSD": 563.69921443,
            "BNB": 2.53888014,
            "ETH": 0.34075085,
            "USDT": 568.69011311,
            "USDP": 563.34116224,
            "USDC": 563.22847138,
            "BUSD": 568.6914262,
        },
        "used": {
            "BTC": 0.0,
            "XRP": 0.0,
            "TUSD": 0.0,
            "BNB": 0.0,
            "ETH": 0.0,
            "USDT": 226.40951999,
            "USDP": 0.0,
            "USDC": 0.0,
            "BUSD": 0.0,
        },
        "total": {
            "BTC": 0.0,
            "XRP": 0.0,
            "TUSD": 0.0,
            "BNB": 0.0,
            "ETH": 0.0,
            "USDT": 795.25866961,
            "USDP": 0.0,
            "USDC": 0.0,
            "BUSD": 0.0,
        },
    }
    return balance


# #############################################################################
# Write CcxtLogger data.
# #############################################################################


def _write_ccxt_trades(target_dir: str) -> None:
    """
    Generate and save JSON files with CCXT trades.
    """
    (
        ccxt_trades_json1,
        ccxt_trades_json2,
        ccxt_trades_json3,
        ccxt_trades_json4,
    ) = _get_dummy_ccxt_trades()
    # Create directory.
    scratch_fills_path = os.path.join(
        target_dir, obcccclo.CcxtLogger.CCXT_CHILD_ORDER_TRADES
    )
    incremental = False
    hio.create_dir(scratch_fills_path, incremental)
    # Save JSON files.
    file_name_prefix = "ccxt_trades_"
    trades1_path = os.path.join(
        scratch_fills_path,
        f"{file_name_prefix}20230315_123830_20230315_123500.json",
    )
    hio.to_json(trades1_path, ccxt_trades_json1, use_types=True)
    trades2_path = os.path.join(
        scratch_fills_path,
        f"{file_name_prefix}20230315_124333_20230315_124000.json",
    )
    hio.to_json(trades2_path, ccxt_trades_json2, use_types=True)
    trades3_path = os.path.join(
        scratch_fills_path,
        f"{file_name_prefix}20230315_124930_20230315_124500.json",
    )
    hio.to_json(trades3_path, ccxt_trades_json3, use_types=True)
    trades4_path = os.path.join(
        scratch_fills_path,
        f"{file_name_prefix}20230315_163600_20230323_083700.json",
    )
    hio.to_json(trades4_path, ccxt_trades_json4, use_types=True)


def _write_ccxt_child_order_responses(target_dir: str) -> None:
    """
    Save JSON files with CCXT child order responses.
    """
    order_resp1, order_resp2 = _get_dummy_ccxt_child_order_responses()
    # Create directory.
    scratch_order_resp_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.CCXT_CHILD_ORDER_RESPONSE
    )
    incremental = False
    hio.create_dir(scratch_order_resp_space, incremental)
    # Save JSON files.
    order_resp1_path = os.path.join(
        scratch_order_resp_space,
        "20230315_123500.20230315_123538.json",
    )
    hio.to_json(order_resp1_path, order_resp1, use_types=True)
    order_resp2_path = os.path.join(
        scratch_order_resp_space,
        "20230315_123500.20230315_123539.json",
    )
    hio.to_json(order_resp2_path, order_resp2, use_types=True)


def _write_oms_child_orders(target_dir: str) -> None:
    """
    Save individual OMS child orders.
    """
    child_order1, child_order2 = _get_dummy_oms_child_orders()
    # Create directory.
    oms_orders_scratch_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.OMS_CHILD_ORDERS
    )
    incremental = False
    hio.create_dir(oms_orders_scratch_space, incremental)
    # Save JSON files.
    child_order1_path = os.path.join(
        oms_orders_scratch_space,
        "20230315_123500.20230315_123538.json",
    )
    hio.to_json(child_order1_path, child_order1, use_types=True)
    child_order2_path = os.path.join(
        oms_orders_scratch_space,
        "20230315_123500.20230315_123539.json",
    )
    hio.to_json(child_order2_path, child_order2, use_types=True)


def _write_oms_parent_orders(target_dir: str) -> None:
    """
    Save JSON file with OMS parent orders.
    """
    parent_orders = _get_dummy_oms_parent_orders()
    # Create OMS parent orders child directory.
    oms_parent_orders_scratch_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.OMS_PARENT_ORDERS
    )
    incremental = False
    hio.create_dir(oms_parent_orders_scratch_space, incremental)
    # Save JSON file.
    parent_orders_path = os.path.join(
        oms_parent_orders_scratch_space,
        "oms_parent_orders_20230315_123500.20230315_123539.json",
    )
    hio.to_json(parent_orders_path, parent_orders, use_types=True)


def _write_ccxt_fills(target_dir: str) -> None:
    """
    Save JSON files with CCXT fills.
    """
    ccxt_fills1, ccxt_fills2 = _get_dummy_ccxt_fills()
    # Create directory.
    ccxt_fills_scratch_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.CCXT_FILLS
    )
    incremental = False
    hio.create_dir(ccxt_fills_scratch_space, incremental)
    # Save JSON files.
    ccxt_fills1_path = os.path.join(
        ccxt_fills_scratch_space,
        "ccxt_fills_20230315_123500.20230315_123538.json",
    )
    hio.to_json(ccxt_fills1_path, ccxt_fills1, use_types=True)
    ccxt_fills2_path = os.path.join(
        ccxt_fills_scratch_space,
        "ccxt_fills_20230315_123500.20230315_123539.json",
    )
    hio.to_json(ccxt_fills2_path, ccxt_fills2, use_types=True)


def _write_oms_fills(target_dir: str) -> None:
    """
    Save JSON files with OMS fills.
    """
    oms_fills1, oms_fills2 = _get_dummy_oms_fills()
    # Create directory.
    oms_fills_scratch_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.OMS_FILLS
    )
    incremental = False
    hio.create_dir(oms_fills_scratch_space, incremental)
    # Save CSV files.
    oms_fills1_path = os.path.join(
        oms_fills_scratch_space,
        "oms_fills_20230315_123500.20230315_123538.json",
    )
    hio.to_json(oms_fills1_path, oms_fills1, use_types=True)
    oms_fills2_path = os.path.join(
        oms_fills_scratch_space,
        "oms_fills_20230315_123500.20230315_123539.json",
    )
    hio.to_json(oms_fills2_path, oms_fills2, use_types=True)


def _write_bid_ask_data(target_dir: str) -> None:
    """
    Save CSV files with bid ask data.
    """
    bid_ask_data = _get_dummy_bid_ask_data()
    # Create directory.
    bid_ask_scratch_space = os.path.join(target_dir, obcccclo.CcxtLogger.BID_ASK)
    incremental = False
    hio.create_dir(bid_ask_scratch_space, incremental)
    # Save data.
    bid_ask_data.to_csv(
        os.path.join(bid_ask_scratch_space, "mock.csv"), index=False
    )


def _write_exchange_markets(target_dir: str) -> None:
    """
    Save JSON files with exchange markets.
    """
    exchange_markets = _get_dummy_ccxt_exchange_markets()
    # Create directory.
    exchange_markets_scratch_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.EXCHANGE_MARKETS
    )
    incremental = False
    hio.create_dir(exchange_markets_scratch_space, incremental)
    # Save JSON files.
    exchange_markets_path = os.path.join(
        exchange_markets_scratch_space,
        "exchange_markets.20230315_123538.json",
    )
    hio.to_json(exchange_markets_path, exchange_markets, use_types=True)


def _write_leverage_info(target_dir: str) -> None:
    """
    Save JSON files with leverage info.
    """
    leverage_info = _get_dummy_ccxt_leverage_info()
    # Create directory.
    leverage_info_scratch_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.LEVERAGE_INFO
    )
    incremental = False
    hio.create_dir(leverage_info_scratch_space, incremental)
    # Save JSON files.
    leverage_info_path = os.path.join(
        leverage_info_scratch_space,
        "leverage_info.20230315_123538.json",
    )
    hio.to_json(leverage_info_path, leverage_info, use_types=True)


def _write_positions(target_dir: str) -> None:
    """
    Generate and save JSON files with positions.
    """
    # TODO(Sameep): CmTask5723 make the dir static in logger.
    positions = _get_dummy_ccxt_positions()
    # Create directory.
    positions_scratch_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.POSITIONS
    )
    incremental = False
    hio.create_dir(positions_scratch_space, incremental)
    # Save JSON files.
    positions_info_path = os.path.join(
        positions_scratch_space,
        "positions.20230315_123538.json",
    )
    hio.to_json(positions_info_path, positions, use_types=True)


def _write_balances(target_dir: str) -> None:
    """
    Save JSON files with balances.
    """
    # TODO(Sameep): CmTask5723 make the dir static in logger.
    balance = _get_dummy_ccxt_balance()
    # Create directory.
    balances_scratch_space = os.path.join(
        target_dir, obcccclo.CcxtLogger.BALANCES
    )
    incremental = False
    hio.create_dir(balances_scratch_space, incremental)
    # Save JSON files.
    balances_info_path = os.path.join(
        balances_scratch_space,
        "balance.20230315_123538.json",
    )
    hio.to_json(balances_info_path, balance, use_types=True)


def _write_reduce_only_order_responses(target_dir: str) -> None:
    """
    Save JSON files with CCXT reduce only order responses.
    """
    order_resp1 = _get_dummy_reduce_only_ccxt_child_order_responses()
    # Create directory.
    scratch_order_resp_space = os.path.join(
        target_dir, "reduce_only", obcccclo.CcxtLogger.CCXT_CHILD_ORDER_RESPONSE
    )
    incremental = False
    hio.create_dir(scratch_order_resp_space, incremental)
    # Save JSON files.
    order_resp1_path = os.path.join(
        scratch_order_resp_space,
        "20230315_123500.20230315_123538.json",
    )
    hio.to_json(order_resp1_path, order_resp1, use_types=True)


def _write_args_file(target_dir: str) -> None:
    """
    Save JSON with args data.
    """
    args_file_path = os.path.join(target_dir, obcccclo.CcxtLogger.ARGS_FILE)
    args = {
        "secret_id": 4,
        "max_parent_order_notional": 100,
        "randomize_orders": True,
        "log_dir": "/shared_data/sameep/daily_experiments/20231205_experiment3",
        "clean_up_before_run": True,
        "clean_up_after_run": True,
        "parent_order_duration_in_min": 5,
        "num_parent_orders_per_bar": 5,
        "num_bars": 6,
        "close_positions_using_twap": False,
        "db_stage": "prod",
        "child_order_execution_freq": "10S",
        "incremental": False,
        "log_level": "DEBUG",
    }
    hio.to_json(args_file_path, args)


def _write_broker_config(target_dir: str) -> None:
    """
    Save JSON with Broker config.
    """
    broker_config_path = os.path.join(
        target_dir, obcccclo.CcxtLogger.BROKER_CONFIG
    )
    broker_config = {
        "universe_version": "v7.4",
        "stage": "preprod",
        "log_dir": "/app/system_log_dir",
        "secret_identifier": "binance.preprod.trading.4",
        "bid_ask_lookback": "60S",
        "limit_price_computer": {
            "object_type": "LimitPriceComputerUsingSpread",
            "passivity_factor": 0.55,
            "max_deviation": 0.01,
        },
        "child_order_quantity_computer": {
            "object_type": "StaticSchedulingChildOrderQuantityComputer"
        },
        "raw_data_reader": "RawDataReader",
    }
    hio.to_json(broker_config_path, broker_config)


def _write_test_data(target_dir: str) -> None:
    """
    Write test data into the target directory.

    :param target_dir: the target directory to write into
    """
    _write_args_file(target_dir)
    _write_broker_config(target_dir)
    _write_ccxt_trades(target_dir)
    _write_ccxt_child_order_responses(target_dir)
    _write_oms_child_orders(target_dir)
    _write_oms_parent_orders(target_dir)
    _write_ccxt_fills(target_dir)
    _write_oms_fills(target_dir)
    _write_bid_ask_data(target_dir)
    _write_exchange_markets(target_dir)
    _write_leverage_info(target_dir)
    _write_positions(target_dir)
    _write_balances(target_dir)
    _write_reduce_only_order_responses(target_dir)


def _check(self_: Any, actual: pd.DataFrame, expected: str) -> None:
    actual = hpandas.df_to_str(actual, num_rows=None)
    self_.assert_equal(actual, expected, fuzzy_match=True)


# #############################################################################
# TestCcxtLogger1
# #############################################################################


class TestCcxtLogger1(hunitest.TestCase):
    def test_init1(self) -> None:
        """
        Verify that the CCXT logs for CcxtBroker is initialized correctly.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        expected_config_file = os.path.join(target_dir, reader.BROKER_CONFIG)
        self.assertEqual(reader._broker_config_file, expected_config_file)
        #
        expected_trades_dir = os.path.join(
            target_dir, reader.CCXT_CHILD_ORDER_TRADES
        )
        self.assertEqual(reader._ccxt_trades_dir, expected_trades_dir)
        #
        expected_child_orders_dir = os.path.join(
            target_dir, reader.OMS_CHILD_ORDERS
        )
        self.assertEqual(reader._oms_child_orders_dir, expected_child_orders_dir)
        #
        expected_oms_parent_orders_dir = os.path.join(
            target_dir, reader.OMS_PARENT_ORDERS
        )
        self.assertEqual(
            reader._oms_parent_orders_dir, expected_oms_parent_orders_dir
        )
        #
        expected_order_responses_dir = os.path.join(
            target_dir, reader.CCXT_CHILD_ORDER_RESPONSE
        )
        self.assertEqual(
            reader._ccxt_order_responses_dir, expected_order_responses_dir
        )
        #
        expected_ccxt_fills_dir = os.path.join(target_dir, reader.CCXT_FILLS)
        self.assertEqual(reader._ccxt_fills_dir, expected_ccxt_fills_dir)
        #
        expected_oms_fills_dir = os.path.join(target_dir, reader.OMS_FILLS)
        self.assertEqual(reader._oms_fills_dir, expected_oms_fills_dir)

    def test_get_dummy_files1(self) -> None:
        """
        Verify that files in the scratch space for CcxtBroker are listed
        correctly.
        """
        # Create fills data.
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        actual_trades_files = reader._get_files(reader._ccxt_trades_dir)
        expected_trades_files = [
            os.path.join(
                target_dir,
                reader.CCXT_CHILD_ORDER_TRADES,
                "ccxt_trades_20230315_123830_20230315_123500.json",
            ),
            os.path.join(
                target_dir,
                reader.CCXT_CHILD_ORDER_TRADES,
                "ccxt_trades_20230315_124333_20230315_124000.json",
            ),
            os.path.join(
                target_dir,
                reader.CCXT_CHILD_ORDER_TRADES,
                "ccxt_trades_20230315_124930_20230315_124500.json",
            ),
            os.path.join(
                target_dir,
                reader.CCXT_CHILD_ORDER_TRADES,
                "ccxt_trades_20230315_163600_20230323_083700.json",
            ),
        ]
        self.assertListEqual(actual_trades_files, expected_trades_files)

    def test_load_broker_config1(self) -> None:
        """
        Verify that the broker config is correctly loaded.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        actual = reader.load_broker_config()
        actual = hprint.to_pretty_str(actual)
        #
        self.check_string(actual)

    def test_load_oms_child_order_df1(self) -> None:
        """
        Verify that child orders are loaded and transformed correctly without
        extra parameters unpacked.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        child_orders = reader.load_oms_child_order(
            unpack_extra_params=False, convert_to_dataframe=True
        )
        actual = hpandas.df_to_str(child_orders)
        #
        self.check_string(actual)

    def test_load_oms_child_order_df2(self) -> None:
        """
        Verify that child orders are loaded and transformed correctly and with
        extra parameters unpacked.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        child_orders = reader.load_oms_child_order(
            unpack_extra_params=True, convert_to_dataframe=True
        )
        actual = hpandas.df_to_str(child_orders)
        #
        self.check_string(actual)

    def test_load_oms_parent_order_df(self) -> None:
        """
        Verify that parent orders are loaded and normalized correctly.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        parent_orders = reader.load_oms_parent_order(convert_to_dataframe=True)
        actual = hpandas.df_to_str(parent_orders)
        #
        self.check_string(actual)

    def test_load_ccxt_trades_df(self) -> None:
        """
        Verify that CCXT trades are loaded and transformed correctly.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        child_order_fills = reader.load_ccxt_trades(convert_to_dataframe=True)
        actual = hpandas.df_to_str(child_order_fills)
        self.check_string(actual)

    def test_load_ccxt_order_response_df(self) -> None:
        """
        Verify that child order responses from CCXT are loaded and transformed
        correctly.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        ccxt_child_order_responses = reader.load_ccxt_order_response(
            convert_to_dataframe=True
        )
        actual = hpandas.df_to_str(ccxt_child_order_responses)
        self.check_string(actual)

    def test_load_ccxt_fills_df(self) -> None:
        """
        Verify that CCXT fills are loaded and transformed correctly.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        ccxt_fills_df = reader.load_ccxt_fills(convert_to_dataframe=True)
        actual = hpandas.df_to_str(ccxt_fills_df)
        self.check_string(actual)

    def test_load_oms_fills_df(self) -> None:
        """
        Verify that OMS fills are loaded and transformed correctly.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        oms_fills_df = reader.load_oms_fills(convert_to_dataframe=True)
        actual = hpandas.df_to_str(oms_fills_df)
        self.check_string(actual)

    def test_load_all_data(self) -> None:
        """
        Verify that all data is loaded correctly.
        """
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        #
        all_data = reader.load_all_data(convert_to_dataframe=True)
        # Assert the method loads the expected data types.
        self.assertEqual(
            list(all_data),
            [
                "args",
                "broker_config",
                "ccxt_order_responses",
                "oms_parent_orders",
                "ccxt_trades",
                "oms_child_orders",
                "oms_fills",
                "ccxt_fills",
                "exchange_markets",
                "leverage_info",
                "bid_ask_files",
                "positions",
                "balances",
                "reduce_only_order_responses",
            ],
        )
        # Assert the dataframes are not empty.
        # TODO(Sameep): Discuss with Danya if we want to convert the new added
        # list to dataframe and if yes what should be the format.
        df_list = [
            "ccxt_order_responses",
            "oms_parent_orders",
            "ccxt_trades",
            "oms_child_orders",
            "oms_fills",
            "ccxt_fills",
            "exchange_markets",
            "leverage_info",
            "positions",
            "balances",
        ]
        all_data_df = {key: all_data[key] for key in df_list}
        for df in all_data_df.values():
            self.assertFalse(df.empty)


class TestCcxtLogger2(hunitest.TestCase):
    def test_log_child_order1(self) -> None:
        """
        Verify that a child order with CCXT order info and additional
        parameters is logged correctly.
        """
        # Get an order and set a CCXT id.
        order = self._get_dummy_test_order("price@twap")[0]
        order = obcaccbr.AbstractCcxtBroker._set_ccxt_id_to_child_order(
            order, 7954906695
        )
        # Get a child order response.
        child_order_response = _get_dummy_ccxt_child_order_responses()[0]
        # Check.
        exp_child_order = r"""
        OrderedDict([('order_id', 0),
                    ('creation_timestamp',
                    Timestamp('2022-08-05 14:36:44.976104+0000', tz='UTC')),
                    ('asset_id', 1464553467),
                    ('type_', 'price@twap'),
                    ('start_timestamp',
                    Timestamp('2022-08-05 14:36:44.976104+0000', tz='UTC')),
                    ('end_timestamp',
                    Timestamp('2022-08-05 14:38:44.976104+0000', tz='UTC')),
                    ('curr_num_shares', 0.0),
                    ('diff_num_shares', 0.121),
                    ('tz', datetime.timezone.utc),
                    ('extra_params', {'ccxt_id': [7954906695]}),
                    ('ccxt_id', [7954906695])])
        """
        exp_ccxt_order_response = r"""
        {'amount': 10.0,
        'average': nan,
        'clientOrderId': 'x-xcKtGhcub89989e55d47273a3610a9',
        'cost': 0.0,
        'datetime': Timestamp('2023-03-15 16:35:38.582000+0000', tz='UTC'),
        'fee': nan,
        'fees': [],
        'filled': 0.0,
        'id': 7954906695,
        'info': {'avgPrice': '0.0000',
                'clientOrderId': 'x-xcKtGhcub89989e55d47273a3610a9',
                'closePosition': False,
                'cumQty': '0',
                'cumQuote': '0',
                'executedQty': '0',
                'orderId': '7954906695',
                'origQty': '10',
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': '4.1200',
                'priceProtect': False,
                'reduceOnly': False,
                'side': 'BUY',
                'status': 'NEW',
                'stopPrice': '0',
                'symbol': 'APEUSDT',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': 1678898138582,
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': None,
        'postOnly': False,
        'price': 4.12,
        'reduceOnly': False,
        'remaining': 10.0,
        'side': 'buy',
        'status': 'open',
        'stopPrice': nan,
        'symbol': 'APE/USDT',
        'timeInForce': 'GTC',
        'timestamp': 1678898138582,
        'trades': [],
        'type': 'limit'}
        """
        self._test_log_child_order(
            order, child_order_response, exp_child_order, exp_ccxt_order_response
        )

    def test_log_child_order2(self) -> None:
        """
        Verify that a child order without a corresponding order response is
        logged without a CCXT ID.
        """
        # Get an order and a CCXT id is absent.
        order = self._get_dummy_test_order("price@twap")[0]
        # Get a child order response.
        child_order_response = {}
        #
        exp_child_order = r"""
        OrderedDict([('order_id', 0),
                    ('creation_timestamp',
                    Timestamp('2022-08-05 14:36:44.976104+0000', tz='UTC')),
                    ('asset_id', 1464553467),
                    ('type_', 'price@twap'),
                    ('start_timestamp',
                    Timestamp('2022-08-05 14:36:44.976104+0000', tz='UTC')),
                    ('end_timestamp',
                    Timestamp('2022-08-05 14:38:44.976104+0000', tz='UTC')),
                    ('curr_num_shares', 0.0),
                    ('diff_num_shares', 0.121),
                    ('tz', datetime.timezone.utc),
                    ('extra_params', {}),
                    ('ccxt_id', -1)])
        """
        exp_ccxt_order_response = str(child_order_response)
        self._test_log_child_order(
            order, child_order_response, exp_child_order, exp_ccxt_order_response
        )

    def test_log_child_order3(self) -> None:
        """
        Verify that a reduce only child order is logged in the correct
        directory.
        """
        # Create logger and wall_clock_time.
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        # Get dummy child order and child order response data.
        child_order = self._get_dummy_test_reduce_only_order("price@twap")[0]
        child_order_response = _get_dummy_reduce_only_ccxt_child_order_responses()
        # Log child order and child order response data.
        logger.log_child_order(
            get_wall_clock_time, child_order, child_order_response, {}
        )
        # Find child order json log file.
        child_order_log_dir = os.path.join(
            log_dir,
            "reduce_only",
            logger.OMS_CHILD_ORDERS,
        )
        cmd = f"find {child_order_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        OrderedDict([('order_id', 0),
                    ('creation_timestamp',
                    Timestamp('2022-08-05 14:36:44.976104+0000', tz='UTC')),
                    ('asset_id', 1464553467),
                    ('type_', 'price@twap'),
                    ('start_timestamp',
                    Timestamp('2022-08-05 14:36:44.976104+0000', tz='UTC')),
                    ('end_timestamp',
                    Timestamp('2022-08-05 14:38:44.976104+0000', tz='UTC')),
                    ('curr_num_shares', 0.0),
                    ('diff_num_shares', 0.121),
                    ('tz', datetime.timezone.utc),
                    ('extra_params', {'reduce_only': True}),
                    ('ccxt_id', -1)])
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # Find child order response json log file.
        child_order_log_dir = os.path.join(
            log_dir,
            "reduce_only",
            logger.CCXT_CHILD_ORDER_RESPONSE,
        )
        cmd = f"find {child_order_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        {'amount': 10.0,
        'average': nan,
        'clientOrderId': 'x-xcKtGhcub89989e55d47273a3610a9',
        'cost': 0.0,
        'datetime': Timestamp('2023-03-15 16:35:38.582000+0000', tz='UTC'),
        'fee': nan,
        'fees': [],
        'filled': 0.0,
        'id': 7954906695,
        'info': {'avgPrice': '0.0000',
                'clientOrderId': 'x-xcKtGhcub89989e55d47273a3610a9',
                'closePosition': False,
                'cumQty': '0',
                'cumQuote': '0',
                'executedQty': '0',
                'orderId': '7954906695',
                'origQty': '10',
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': '4.1200',
                'priceProtect': False,
                'reduceOnly': True,
                'side': 'BUY',
                'status': 'NEW',
                'stopPrice': '0',
                'symbol': 'APEUSDT',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': 1678898138582,
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': None,
        'postOnly': False,
        'price': 4.12,
        'reduceOnly': False,
        'remaining': 10.0,
        'side': 'buy',
        'status': 'open',
        'stopPrice': nan,
        'symbol': 'APE/USDT',
        'timeInForce': 'GTC',
        'timestamp': 1678898138582,
        'trades': [],
        'type': 'limit'}
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_log_ccxt_fills(self) -> None:
        """
        Verify that CCXT fills are logged correctly.
        """
        # Get dummy CCXT fills data.
        fills = _get_dummy_ccxt_fills()[0]
        _get_dummy_ccxt_trades()[0]
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        # Log test order fills.
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        logger.log_ccxt_fills(get_wall_clock_time, fills)
        # Find a JSON file where CCXT fills are saved.
        ccxt_fills_log_dir = os.path.join(log_dir, logger.CCXT_FILLS)
        cmd = f"find {ccxt_fills_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        [{'amount': 1.0,
        'average': 14.754,
        'clientOrderId': 'x-xcKtGhcu8261da0e4a2533b528e0e2',
        'cost': 14.754,
        'datetime': Timestamp('2023-05-23 11:58:49.172000+0000', tz='UTC'),
        'fee': nan,
        'fees': [],
        'filled': 1.0,
        'id': 14901643572,
        'info': {'avgPrice': 14.754,
                'clientOrderId': 'x-xcKtGhcu8261da0e4a2533b528e0e2',
                'closePosition': False,
                'cumQuote': '14.7540',
                'executedQty': '1',
                'orderId': '14901643572',
                'origQty': 1,
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': 14.761,
                'priceProtect': False,
                'reduceOnly': False,
                'side': 'BUY',
                'status': 'FILLED',
                'stopPrice': '0',
                'symbol': 'AVAXUSDT',
                'time': '1684843129172',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': 1684843129172,
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': None,
        'postOnly': False,
        'price': 14.761,
        'reduceOnly': False,
        'remaining': 0.0,
        'side': 'buy',
        'status': 'closed',
        'stopPrice': nan,
        'symbol': 'AVAX/USDT',
        'timeInForce': 'GTC',
        'timestamp': 1684843129172,
        'trades': [],
        'type': 'limit'},
        {'amount': 0.001,
        'average': 27330.4,
        'clientOrderId': 'x-xcKtGhcua8e7e261598721e6c6295c',
        'cost': 27.3304,
        'datetime': Timestamp('2023-05-23 11:58:49.687000+0000', tz='UTC'),
        'fee': nan,
        'fees': [],
        'filled': 0.001,
        'id': 153017797793,
        'info': {'avgPrice': '27330.40000',
                'clientOrderId': 'x-xcKtGhcua8e7e261598721e6c6295c',
                'closePosition': False,
                'cumQuote': '27.33040',
                'executedQty': '0.001',
                'orderId': '153017797793',
                'origQty': '0.001',
                'origType': 'LIMIT',
                'positionSide': 'BOTH',
                'price': '27341.90',
                'priceProtect': False,
                'reduceOnly': False,
                'side': 'BUY',
                'status': 'FILLED',
                'stopPrice': '0',
                'symbol': 'BTCUSDT',
                'time': '1684843129687',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'updateTime': 1684843129687,
                'workingType': 'CONTRACT_PRICE'},
        'lastTradeTimestamp': None,
        'postOnly': False,
        'price': 27341.9,
        'reduceOnly': False,
        'remaining': 0.0,
        'side': 'buy',
        'status': 'closed',
        'stopPrice': nan,
        'symbol': 'BTC/USDT',
        'timeInForce': 'GTC',
        'timestamp': 1684843129687,
        'trades': [],
        'type': 'limit'}]
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_log_ccxt_trades(self) -> None:
        """
        Verify that CCXT fills are logged correctly.
        """
        # Get dummy CCXT trades data.
        trades = _get_dummy_ccxt_trades()[0]
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        # Log test order fills.
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        logger.log_ccxt_trades(get_wall_clock_time, trades)
        # Find a JSON file where CCXT trades are saved.
        ccxt_trades_log_dir = os.path.join(
            log_dir, logger.CCXT_CHILD_ORDER_TRADES
        )
        cmd = f"find {ccxt_trades_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        [{'amount': 10.0,
        'asset_id': 6051632686,
        'cost': 41.2,
        'datetime': Timestamp('2023-03-15 16:35:39.268000+0000', tz='UTC'),
        'fee': {'cost': 0.00824, 'currency': 'USDT'},
        'fees': [{'cost': 0.00824, 'currency': 'USDT'}],
        'id': 352824923,
        'info': {'buyer': True,
                'commission': '0.00824000',
                'commissionAsset': 'USDT',
                'id': '352824923',
                'maker': True,
                'marginAsset': 'USDT',
                'orderId': '7954906695',
                'positionSide': 'BOTH',
                'price': '4.1200',
                'qty': '10',
                'quoteQty': '41.2000',
                'realizedPnl': 0.0,
                'side': 'BUY',
                'symbol': 'APEUSDT',
                'time': '1678898139268'},
        'order': 7954906695,
        'price': 4.12,
        'side': 'buy',
        'symbol': 'APE/USDT',
        'takerOrMaker': 'maker',
        'timestamp': 1678898139268,
        'type': None},
        {'amount': 10.0,
        'asset_id': 6051632686,
        'cost': 41.1,
        'datetime': Timestamp('2023-03-15 16:36:02.247000+0000', tz='UTC'),
        'fee': {'cost': 0.01644, 'currency': 'USDT'},
        'fees': [{'cost': 0.01644, 'currency': 'USDT'}],
        'id': 352825168,
        'info': {'buyer': True,
                'commission': '0.01644000',
                'commissionAsset': 'USDT',
                'id': '352825168',
                'maker': False,
                'marginAsset': 'USDT',
                'orderId': '7954913312',
                'positionSide': 'BOTH',
                'price': '4.1100',
                'qty': '10',
                'quoteQty': '41.1000',
                'realizedPnl': 0.0,
                'side': 'BUY',
                'symbol': 'APEUSDT',
                'time': '1678898162247'},
        'order': 7954913312,
        'price': 4.11,
        'side': 'buy',
        'symbol': 'APE/USDT',
        'takerOrMaker': 'taker',
        'timestamp': 1678898162247,
        'type': None}]
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_log_oms_fills(self) -> None:
        """
        Verify that OMS fills are logged correctly.
        """
        # Create logger and wall_clock_time.
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        # Get dummy OMS fills data.
        oms_fills = self._create_oms_fills_object()
        # Log OMS fills data.
        logger.log_oms_fills(get_wall_clock_time, oms_fills)
        # Find OMS fills json log file.
        oms_fills_log_dir = os.path.join(log_dir, logger.OMS_FILLS)
        cmd = f"find {oms_fills_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        [OrderedDict([('asset_id', 8717633868),
                    ('fill_id', 2),
                    ('timestamp',
                    Timestamp('2023-05-23 11:58:49.172000+0000', tz='UTC')),
                    ('num_shares', 1.0),
                    ('price', 14.754)]),
        OrderedDict([('asset_id', 1467591036),
                    ('fill_id', 4),
                    ('timestamp',
                    Timestamp('2023-05-23 11:58:49.687000+0000', tz='UTC')),
                    ('num_shares', 0.001),
                    ('price', 27.3304)])]
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_log_oms_parent_orders(self) -> None:
        """
        Verify that OMS parent oreders are logged correctly.
        """
        # Create logger and wall_clock_time.
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        # Get dummy OMS parent order data.
        oms_parent_orders = self._create_oms_parent_orders()
        # Log OMS parent order data.
        logger.log_oms_parent_orders(get_wall_clock_time, oms_parent_orders)
        # TODO(gp): Factor out this snippet of code in a function.
        # Find OMS parent order json log file.
        oms_parent_order_log_dir = os.path.join(log_dir, logger.OMS_PARENT_ORDERS)
        hdbg.dassert_dir_exists(oms_parent_order_log_dir)
        cmd = f"find {oms_parent_order_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        hdbg.dassert_lte(1, len(path), "No JSON files in %s", oms_parent_order_log_dir)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        [OrderedDict([('order_id', 0),
                    ('creation_timestamp',
                    Timestamp('2023-03-15 16:34:38.718960+0000', tz='UTC')),
                    ('asset_id', 6051632686),
                    ('type_', 'limit'),
                    ('start_timestamp',
                    Timestamp('2023-03-15 16:34:38.718960+0000', tz='UTC')),
                    ('end_timestamp',
                    Timestamp('2023-03-15 16:39:38.718960+0000', tz='UTC')),
                    ('curr_num_shares', 0.0),
                    ('diff_num_shares', 50.0),
                    ('tz', datetime.timezone.utc),
                    ('extra_params', {})]),
        OrderedDict([('order_id', 1),
                    ('creation_timestamp',
                    Timestamp('2023-03-15 16:34:39.718960+0000', tz='UTC')),
                    ('asset_id', 8717633868),
                    ('type_', 'limit'),
                    ('start_timestamp',
                    Timestamp('2023-03-15 16:34:39.718960+0000', tz='UTC')),
                    ('end_timestamp',
                    Timestamp('2023-03-15 16:39:39.718960+0000', tz='UTC')),
                    ('curr_num_shares', 0.0),
                    ('diff_num_shares', -5.0),
                    ('tz', datetime.timezone.utc),
                    ('extra_params', {})])]
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # Logger does not overwrite the log file instead it creates another log
        # file ```oms_parent_orders_{bar_timestamp}.json.{wallclock_time}```.
        # Verify that there is a single log file with *.json.
        logger.log_oms_parent_orders(get_wall_clock_time, oms_parent_orders)
        _, path = hsystem.system_to_string(cmd)
        self.assertEqual(1, len(path.split("\n")))

    def test_log_bid_ask_data(self) -> None:
        """
        Verify that bid ask data is logged correctly.
        """
        # Create logger and wall_clock_time.
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        # Get dummy bid ask data.
        bid_ask_data = _get_dummy_bid_ask_data()
        # Log bid ask data.
        logger.log_bid_ask_data(get_wall_clock_time, bid_ask_data)
        # Find bid ask data CSV log file.
        bid_ask_log_dir = os.path.join(log_dir, logger.BID_ASK)
        cmd = f"find {bid_ask_log_dir} -type f -name *.csv"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        df = pd.read_csv(path)
        act = pprint.pformat(df)
        exp = r"""
            timestamp currency_pair exchange_id            end_download_timestamp  \
        0  1697754290111      GMT_USDT     binance  2023-10-19 22:24:50.315872+00:00
        1  1697754290114     UNFI_USDT     binance  2023-10-19 22:24:50.317413+00:00
        2  1697754290121      ETH_USDT     binance  2023-10-19 22:24:50.313784+00:00

                        knowledge_timestamp  bid_size_l1  bid_price_l1  ask_size_l1  \
        0  2023-10-19 22:24:50.740828+00:00   270752.000        0.1407    31142.000
        1  2023-10-19 22:24:50.740828+00:00      286.600        5.8500       35.600
        2  2023-10-19 22:24:50.740828+00:00       89.346     1566.4900       19.878

        ask_price_l1
        0        0.1408
        1        5.8510
        2     1566.5000
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_log_exchange_markets(self) -> None:
        """
        Verify that exchange markets and leverage info is logged correctly.
        """
        # Create logger and wall_clock_time.
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        # Get dummy exchange markets and leverage info.
        exchange_markets_data = _get_dummy_ccxt_exchange_markets()
        leverage_info_data = _get_dummy_ccxt_leverage_info()
        # Log exchange markets and leverage info.
        logger.log_exchange_markets(
            get_wall_clock_time, exchange_markets_data, leverage_info_data
        )
        # Find exchange markets JSON log file.
        exchange_markets_log_dir = os.path.join(log_dir, logger.EXCHANGE_MARKETS)
        cmd = f"find {exchange_markets_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        {'ETH/BTC': {'active': True,
                    'base': 'ETH',
                    'baseId': 'ETH',
                    'contract': False,
                    'contractSize': None,
                    'expiry': None,
                    'expiryDatetime': None,
                    'future': False,
                    'id': 'ETHBTC',
                    'inverse': None,
                    'linear': None,
                    'margin': True,
                    'option': False,
                    'optionType': None,
                    'precision': {'amount': 4, 'base': 8, 'price': 5, 'quote': 8},
                    'quote': 'BTC',
                    'quoteId': 'BTC',
                    'settle': None,
                    'settleId': None,
                    'spot': True,
                    'strike': None,
                    'swap': False,
                    'symbol': 'ETH/BTC',
                    'type': 'spot'},
        'LTC/BTC': {'active': True,
                    'base': 'LTC',
                    'baseId': 'LTC',
                    'contract': False,
                    'contractSize': None,
                    'expiry': None,
                    'expiryDatetime': None,
                    'future': False,
                    'id': 'LTCBTC',
                    'inverse': None,
                    'linear': None,
                    'margin': True,
                    'option': False,
                    'optionType': None,
                    'precision': {'amount': 3, 'base': 8, 'price': 6, 'quote': 8},
                    'quote': 'BTC',
                    'quoteId': 'BTC',
                    'settle': None,
                    'settleId': None,
                    'spot': True,
                    'strike': None,
                    'swap': False,
                    'symbol': 'LTC/BTC',
                    'type': 'spot'}}
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # Find leverage info JSON log file.
        leverage_info_log_dir = os.path.join(log_dir, logger.LEVERAGE_INFO)
        cmd = f"find {leverage_info_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        {'BNB/USDT:USDT': [{'currency': 'USDT',
                            'info': {'bracket': '1',
                                    'cum': '0.0',
                                    'initialLeverage': '75',
                                    'maintMarginRatio': '0.005',
                                    'notionalCap': '5000',
                                    'notionalFloor': '0'},
                            'maintenanceMarginRate': 0.005,
                            'maxLeverage': 75.0,
                            'maxNotional': 5000.0,
                            'minNotional': 0.0,
                            'tier': 1.0},
                        {'currency': 'USDT',
                            'info': {'bracket': '2',
                                    'cum': '5.0',
                                    'initialLeverage': '50',
                                    'maintMarginRatio': '0.006',
                                    'notionalCap': '10000',
                                    'notionalFloor': '5000'},
                            'maintenanceMarginRate': 0.006,
                            'maxLeverage': 50.0,
                            'maxNotional': 10000.0,
                            'minNotional': 5000.0,
                            'tier': 2.0}],
        'WAVES/USDT:USDT': [{'currency': 'USDT',
                            'info': {'bracket': '1',
                                    'cum': '0.0',
                                    'initialLeverage': '25',
                                    'maintMarginRatio': '0.02',
                                    'notionalCap': '5000',
                                    'notionalFloor': '0'},
                            'maintenanceMarginRate': 0.02,
                            'maxLeverage': 25.0,
                            'maxNotional': 5000.0,
                            'minNotional': 0.0,
                            'tier': 1.0},
                            {'currency': 'USDT',
                            'info': {'bracket': '2',
                                    'cum': '25.0',
                                    'initialLeverage': '20',
                                    'maintMarginRatio': '0.025',
                                    'notionalCap': '50000',
                                    'notionalFloor': '5000'},
                            'maintenanceMarginRate': 0.025,
                            'maxLeverage': 20.0,
                            'maxNotional': 50000.0,
                            'minNotional': 5000.0,
                            'tier': 2.0}]}
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_log_positions1(self) -> None:
        """
        Verify that positions are logged correctly.
        """
        # Create logger and wall_clock_time.
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        # Get dummy positions data.
        positions = _get_dummy_ccxt_positions()
        # Log positions data.
        logger.log_positions(get_wall_clock_time, positions)
        # Find positions json log file.
        positions_log_dir = os.path.join(log_dir, logger.POSITIONS)
        cmd = f"find {positions_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        [{'collateral': 0.0,
        'contractSize': 1.0,
        'contracts': 0.0,
        'datetime': None,
        'entryPrice': 0.0,
        'hedged': False,
        'id': None,
        'info': {'breakEvenPrice': '0.0',
                'entryPrice': '0.0',
                'isAutoAddMargin': 'false',
                'isolatedMargin': '0.00000000',
                'isolatedWallet': '0',
                'leverage': '20',
                'liquidationPrice': '0',
                'marginType': 'cross',
                'markPrice': '0.00000000',
                'maxNotionalValue': '25000',
                'notional': '0',
                'positionAmt': '0',
                'positionSide': 'BOTH',
                'symbol': 'SUSHIUSDT',
                'unRealizedProfit': '0.00000000',
                'updateTime': '0'},
        'initialMargin': 0.0,
        'initialMarginPercentage': 0.05,
        'leverage': 20.0,
        'liquidationPrice': None,
        'maintenanceMargin': 0.0,
        'maintenanceMarginPercentage': 0.01,
        'marginMode': 'cross',
        'marginRatio': None,
        'marginType': 'cross',
        'markPrice': None,
        'notional': 0.0,
        'percentage': None,
        'side': None,
        'symbol': 'SUSHI/USDT:USDT',
        'timestamp': None,
        'unrealizedPnl': 0.0},
        {'collateral': 0.0,
        'contractSize': 1.0,
        'contracts': 0.0,
        'datetime': None,
        'entryPrice': 0.0,
        'hedged': False,
        'id': None,
        'info': {'breakEvenPrice': '0.0',
                'entryPrice': '0.0',
                'isAutoAddMargin': 'false',
                'isolatedMargin': '0.00000000',
                'isolatedWallet': '0',
                'leverage': '20',
                'liquidationPrice': '0',
                'marginType': 'cross',
                'markPrice': '0.00000000',
                'maxNotionalValue': '25000',
                'notional': '0',
                'positionAmt': '0',
                'positionSide': 'BOTH',
                'symbol': 'BTSUSDT',
                'unRealizedProfit': '0.00000000',
                'updateTime': '0'},
        'initialMargin': 0.0,
        'initialMarginPercentage': 0.05,
        'leverage': 20.0,
        'liquidationPrice': None,
        'maintenanceMargin': 0.0,
        'maintenanceMarginPercentage': 0.01,
        'marginMode': 'cross',
        'marginRatio': None,
        'marginType': 'cross',
        'markPrice': None,
        'notional': 0.0,
        'percentage': None,
        'side': None,
        'symbol': 'BTS/USDT:USDT',
        'timestamp': None,
        'unrealizedPnl': 0.0}]
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_log_balance1(self) -> None:
        """
        Verify that balances are logged correctly.
        """
        # Create logger and wall_clock_time.
        log_dir = self.get_scratch_space()
        creation_timestamp = pd.Timestamp("2022-08-05 10:35:55-04:00")
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, creation_timestamp
        )
        # Get dummy balances data.
        balance = _get_dummy_ccxt_balance()
        # Log balances data.
        logger.log_balance(get_wall_clock_time, balance)
        # Find balances json log file.
        balances_log_dir = os.path.join(log_dir, logger.BALANCES)
        cmd = f"find {balances_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        # Read log.
        data = hio.from_json(path, use_types=True)
        act = pprint.pformat(data)
        exp = r"""
        {'BNB': {'free': 2.53888014, 'total': 0.0, 'used': 0.0},
        'BTC': {'free': 0.01920606, 'total': 0.0, 'used': 0.0},
        'BUSD': {'free': 568.6914262, 'total': 0.0, 'used': 0.0},
        'ETH': {'free': 0.34075085, 'total': 0.0, 'used': 0.0},
        'TUSD': {'free': 563.69921443, 'total': 0.0, 'used': 0.0},
        'USDC': {'free': 563.22847138, 'total': 0.0, 'used': 0.0},
        'USDP': {'free': 563.34116224, 'total': 0.0, 'used': 0.0},
        'USDT': {'free': 568.69011311, 'total': 795.25866961, 'used': 226.40951999},
        'XRP': {'free': 1053.43017081, 'total': 0.0, 'used': 0.0},
        'datetime': None,
        'free': {'BNB': 2.53888014,
                'BTC': 0.01920606,
                'BUSD': 568.6914262,
                'ETH': 0.34075085,
                'TUSD': 563.69921443,
                'USDC': 563.22847138,
                'USDP': 563.34116224,
                'USDT': 568.69011311,
                'XRP': 1053.43017081},
        'timestamp': None,
        'total': {'BNB': 0.0,
                'BTC': 0.0,
                'BUSD': 0.0,
                'ETH': 0.0,
                'TUSD': 0.0,
                'USDC': 0.0,
                'USDP': 0.0,
                'USDT': 795.25866961,
                'XRP': 0.0},
        'used': {'BNB': 0.0,
                'BTC': 0.0,
                'BUSD': 0.0,
                'ETH': 0.0,
                'TUSD': 0.0,
                'USDC': 0.0,
                'USDP': 0.0,
                'USDT': 226.40951999,
                'XRP': 0.0}}
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def _get_dummy_test_order(self, order_type: str) -> List[oordorde.Order]:
        """
        Build toy list of 1 order for tests.
        """
        # Prepare test data.
        order_str = f"Order: order_id=0 creation_timestamp=2022-08-05 10:36:44.976104-04:00\
        asset_id=1464553467 type_={order_type} start_timestamp=2022-08-05 10:36:44.976104-04:00\
        end_timestamp=2022-08-05 10:38:44.976104-04:00 curr_num_shares=0.0 diff_num_shares=0.121"
        order_str += " tz=UTC extra_params={}"
        # Get orders.
        orders = oordorde.orders_from_string(order_str)
        return orders

    def _get_dummy_test_reduce_only_order(
        self, order_type: str
    ) -> List[oordorde.Order]:
        """
        Build toy list of 1 reduce only order for tests.
        """
        # Prepare test data.
        order_str = f"Order: order_id=0 creation_timestamp=2022-08-05 10:36:44.976104-04:00\
        asset_id=1464553467 type_={order_type} start_timestamp=2022-08-05 10:36:44.976104-04:00\
        end_timestamp=2022-08-05 10:38:44.976104-04:00 curr_num_shares=0.0 diff_num_shares=0.121"
        order_str += " tz=UTC extra_params={'reduce_only':True}"
        # Get orders.
        orders = oordorde.orders_from_string(order_str)
        return orders

    def _get_dummy_logger_and_wall_clock_time(
        self, log_dir: str, initial_replayed_timestamp: pd.Timestamp
    ) -> Tuple[obcccclo.CcxtLogger, callable]:
        """
        Get logger object and `wall_clock_time` required for logging.

        :param log_dir: path where logs will be saved
        :param initial_replayed_timestamp: intial start timestamp for
            `wall_clock_time`
        """
        speed_up_factor = 1.0
        tz = "ET"
        event_loop = None
        get_wall_clock_time = creatime.get_replayed_wall_clock_time(
            tz,
            initial_replayed_timestamp,
            event_loop=event_loop,
            speed_up_factor=speed_up_factor,
        )
        logger = obcccclo.CcxtLogger(log_dir, mode="write")
        return logger, get_wall_clock_time

    def _create_oms_parent_orders(self) -> List[oordorde.Order]:
        """
        Create list of orders object from dummy OMS parent orders data.
        """
        parent_orders = _get_dummy_oms_parent_orders()
        oms_parent_orders = []
        for p_order in parent_orders:
            order = oordorde.Order(
                p_order["creation_timestamp"].tz_convert("UTC"),
                p_order["asset_id"],
                p_order["type_"],
                p_order["start_timestamp"].tz_convert("UTC"),
                p_order["end_timestamp"].tz_convert("UTC"),
                p_order["curr_num_shares"],
                p_order["diff_num_shares"],
                order_id=p_order["order_id"],
                extra_params=p_order["extra_params"],
            )
            oms_parent_orders.append(order)
        return oms_parent_orders

    def _create_oms_fills_object(self) -> List[omfill.Fill]:
        """
        Create list of OMS fills object from dummy OMS fills data.
        """
        fills = _get_dummy_oms_fills()[0]
        oms_fills = []
        for fill_data in fills:
            order = oordorde.Order(
                pd.Timestamp("2022-08-05 10:35:55-04:00"),
                fill_data["asset_id"],
                "market",
                pd.Timestamp("2022-08-05 10:36:00-04:00"),
                pd.Timestamp("2022-08-05 10:37:00-04:00"),
                0.0,
                fill_data["num_shares"],
                order_id=fill_data["fill_id"],
            )
            fill = omfill.Fill(
                order,
                fill_data["timestamp"],
                fill_data["num_shares"],
                fill_data["price"],
            )
            oms_fills.append(fill)
        return oms_fills

    def _test_log_child_order(
        self,
        order: oordorde.Order,
        child_order_response: obcccclo.CcxtData,
        expected_child_order: str,
        expected_ccxt_order_response: str,
    ) -> None:
        """
        Test that child orders are logged properly.

        :param order: order that needs to be logged
        :param child_order_response: CCXT response for that order
        :param expected_child_order: output expected from OMS child
            orders logs
        :param expected_ccxt_order_response: output expected from CCXT
            order response logs
        """
        log_dir = self.get_scratch_space()
        logger, get_wall_clock_time = self._get_dummy_logger_and_wall_clock_time(
            log_dir, order.creation_timestamp
        )
        extra_info = {}
        logger.log_child_order(
            get_wall_clock_time, order, child_order_response, extra_info
        )
        # Build a path to a child orders log dir.
        child_order_log_dir = os.path.join(log_dir, logger.OMS_CHILD_ORDERS)
        # Find a csv file where child order information is saved.
        cmd = f"find {child_order_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        data = hio.from_json(path, use_types=True)
        actual = pprint.pformat(data)
        self.assert_equal(actual, expected_child_order, fuzzy_match=True)
        # Build a path to a CCXT order response log dir.
        ccxt_log_dir = os.path.join(log_dir, logger.CCXT_CHILD_ORDER_RESPONSE)
        # Find a csv file where CCXT order response information is saved.
        cmd = f"find {ccxt_log_dir} -type f -name '*.json'"
        _, path = hsystem.system_to_string(cmd)
        data = hio.from_json(path, use_types=True)
        actual = pprint.pformat(data)
        self.assert_equal(actual, expected_ccxt_order_response, fuzzy_match=True)


@pytest.mark.skip("CMTask5079: Disabled due to obsolete data format.")
class Test_read_rt_data1(hunitest.TestCase):
    """
    Read back data from the logs of a real time execution done with
    run_ccxt_broker.py.
    """

    def test_load_ccxt_order_response_df(self) -> None:
        """
        Verify that child order responses from CCXT are loaded and transformed
        correctly.
        """
        reader = self._get_reader()
        ccxt_order_response = reader.load_ccxt_order_response(
            convert_to_dataframe=True
        )
        actual = hpandas.df_to_str(ccxt_order_response)
        self.check_string(actual)

    def test_load_ccxt_trades_df(self) -> None:
        """
        Verify that CCXT trades are loaded and transformed correctly.
        """
        reader = self._get_reader()
        daccxt_trades = reader.load_ccxt_trades(convert_to_dataframe=True)
        actual = hpandas.df_to_str(daccxt_trades)
        self.check_string(actual)

    def test_load_oms_child_order_df1(self) -> None:
        """
        Verify that child orders are loaded and transformed correctly without
        extra parameters unpacked.
        """
        reader = self._get_reader()
        oms_child_order = reader.load_oms_child_order(
            unpack_extra_params=False, convert_to_dataframe=True
        )
        actual = hpandas.df_to_str(oms_child_order)
        self.check_string(actual)

    def test_load_oms_child_order_df2(self) -> None:
        """
        Verify that child orders are loaded and transformed correctly and with
        extra parameters unpacked.
        """
        reader = self._get_reader()
        oms_child_order = reader.load_oms_child_order(
            unpack_extra_params=True, convert_to_dataframe=True
        )
        actual = hpandas.df_to_str(oms_child_order)
        self.check_string(actual)

    def test_load_oms_parent_order_df1(self) -> None:
        """
        Verify that parent orders are loaded and transformed correctly.
        """
        reader = self._get_reader()
        oms_parent_orders = reader.load_oms_parent_order(
            convert_to_dataframe=True
        )
        actual = hpandas.df_to_str(oms_parent_orders)
        self.check_string(actual)

    def _get_reader(
        self,
    ) -> obcccclo.CcxtLogger:
        """
        Get `CcxtLogger` instance.
        """
        target_dir = os.path.join(self._base_dir_name, "rt_data")
        reader = obcccclo.CcxtLogger(target_dir)
        return reader


class Test_process_child_order_timestamps1(hunitest.TestCase):
    def test_process_child_order_timestamps1(self) -> None:
        """
        Verify that child order timestamps are processed correctly.
        """
        # Get an example child order.
        # Copied from a real experiment.
        child_order = {
            "creation_timestamp": pd.Timestamp(
                "2023-08-29 12:35:00.939164+0000", tz="UTC"
            ),
            "asset_id": 1030828978,
            "type_": "limit",
            "start_timestamp": pd.Timestamp(
                "2023-08-29 12:35:00.939164+0000", tz="UTC"
            ),
            "end_timestamp": pd.Timestamp("2023-08-29 12:36:00+0000", tz="UTC"),
            "curr_num_shares": 0.0,
            "diff_num_shares": -162.0,
            "tz": "America/New-York",
            "extra_params": {
                "stats": {
                    "_submit_twap_child_order::wave_id": 0,
                    "_submit_twap_child_order::bid_ask_market_data.start": pd.Timestamp(
                        "2023-08-29 08:34:59.759931-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::bid_ask_market_data.done": pd.Timestamp(
                        "2023-08-29 08:34:59.833602-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::get_open_positions.done": pd.Timestamp(
                        "2023-08-29 08:35:00.880168-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::child_order.created": pd.Timestamp(
                        "2023-08-29 08:35:00.942109-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::child_order.limit_price_calculated": pd.Timestamp(
                        "2023-08-29 08:35:00.949721-0400", tz="America/New_York"
                    ),
                    "_submit_single_order_to_ccxt::start.timestamp": pd.Timestamp(
                        "2023-08-29 08:35:00.951506-0400", tz="America/New_York"
                    ),
                    "_submit_single_order_to_ccxt::attempt_num": 0,
                    "_submit_single_order_to_ccxt::all_attempts_end.timestamp": pd.Timestamp(
                        "2023-08-29 08:35:05.776272-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::child_order.submitted": pd.Timestamp(
                        "2023-08-29 08:35:05.779206-0400", tz="America/New_York"
                    ),
                },
                "oms_parent_order_id": 4,
                "max_leverage": 25,
                "ccxt_id": [12049653207],
            },
            "passivity_factor": 0.55,
            "latest_bid_price": 0.1552,
            "latest_ask_price": 0.1553,
            "bid_price_mean": 0.1552,
            "ask_price_mean": 0.15530000000000002,
            "used_bid_price": "latest_bid_price",
            "used_ask_price": "latest_ask_price",
            "exchange_timestamp": pd.Timestamp(
                "2023-08-29 12:34:58.561000+0000", tz="UTC"
            ),
            "knowledge_timestamp": pd.Timestamp(
                "2023-08-29 12:34:58.710276+0000", tz="UTC"
            ),
            "end_download_timestamp": pd.Timestamp(
                "2023-08-29 12:34:58.685410+0000", tz="UTC"
            ),
            "limit_price": 0.155255,
            "ccxt_id": 12049653207,
            "name": 9,
        }
        child_order = pd.Series(child_order)
        # Process child order timestamps.
        actual = obcccclo.process_child_order_execution_timestamps(child_order)
        actual = hpandas.df_to_str(actual, num_rows=None)
        expected = r"""
                                                                                    timestamp  limit_price  signed_quantity  snapshot_bid_price  snapshot_ask_price
event
knowledge_timestamp                                          2023-08-29 12:34:58.710276+00:00          NaN              NaN              0.1552              0.1553
_submit_twap_child_order::child_order.limit_price_calculated 2023-08-29 12:35:00.949721+00:00     0.155255           -162.0                 NaN                 NaN
_submit_twap_child_order::child_order.submitted              2023-08-29 12:35:05.779206+00:00          NaN              NaN                 NaN                 NaN
end_timestamp                                                       2023-08-29 12:36:00+00:00          NaN              NaN                 NaN                 NaN
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_process_child_order_trades_timestamps1(hunitest.TestCase):
    # TODO(Danya): Add test for multiple trades.
    def test_process_child_order_trades_timestamps1(self) -> None:
        """
        Verify that CCXT child order trades timestamps are processed correctly.
        """
        # Get CCXT trades DF.
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        ccxt_trades_df = reader.load_ccxt_trades(convert_to_dataframe=True)
        # Get a ccxt_id of a parent order.
        ccxt_id = 8077704766
        actual = obcccclo.process_child_order_trades_timestamps(
            ccxt_trades_df, ccxt_id
        )
        actual = hpandas.df_to_str(actual)
        expected = r"""
                               timestamp  limit_price  signed_quantity
event
trade.1 2023-03-23 08:35:40.879000+00:00         4.04             -6.0
"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_process_timestamps_and_prices_for_a_single_order(hunitest.TestCase):
    def test_process_timestamps_and_prices_for_a_single_order(self) -> None:
        """
        Verify that, for a single order, timestamps and prices are aggregated
        correctly.
        """
        # Get an example child order.
        # Copied from a real experiment.
        child_order = {
            "creation_timestamp": pd.Timestamp(
                "2023-08-29 12:35:00.939164+0000", tz="UTC"
            ),
            "asset_id": 1030828978,
            "type_": "limit",
            "start_timestamp": pd.Timestamp(
                "2023-08-29 12:35:00.939164+0000", tz="UTC"
            ),
            "end_timestamp": pd.Timestamp("2023-08-29 12:36:00+0000", tz="UTC"),
            "curr_num_shares": 0.0,
            "diff_num_shares": -162.0,
            "tz": "America/New-York",
            "extra_params": {
                "stats": {
                    "_submit_twap_child_order::wave_id": 0,
                    "_submit_twap_child_order::bid_ask_market_data.start": pd.Timestamp(
                        "2023-08-29 08:34:59.759931-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::bid_ask_market_data.done": pd.Timestamp(
                        "2023-08-29 08:34:59.833602-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::get_open_positions.done": pd.Timestamp(
                        "2023-08-29 08:35:00.880168-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::child_order.created": pd.Timestamp(
                        "2023-08-29 08:35:00.942109-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::child_order.limit_price_calculated": pd.Timestamp(
                        "2023-08-29 08:35:00.949721-0400", tz="America/New_York"
                    ),
                    "_submit_single_order_to_ccxt::start.timestamp": pd.Timestamp(
                        "2023-08-29 08:35:00.951506-0400", tz="America/New_York"
                    ),
                    "_submit_single_order_to_ccxt::attempt_num": 0,
                    "_submit_single_order_to_ccxt::all_attempts_end.timestamp": pd.Timestamp(
                        "2023-08-29 08:35:05.776272-0400", tz="America/New_York"
                    ),
                    "_submit_twap_child_order::child_order.submitted": pd.Timestamp(
                        "2023-08-29 08:35:05.779206-0400", tz="America/New_York"
                    ),
                },
                "oms_parent_order_id": 4,
                "max_leverage": 25,
                "ccxt_id": [8077704766],
            },
            "passivity_factor": 0.55,
            "latest_bid_price": 0.1552,
            "latest_ask_price": 0.1553,
            "bid_price_mean": 0.1552,
            "ask_price_mean": 0.15530000000000002,
            "used_bid_price": "latest_bid_price",
            "used_ask_price": "latest_ask_price",
            "exchange_timestamp": pd.Timestamp(
                "2023-08-29 12:34:58.561000+0000", tz="UTC"
            ),
            "knowledge_timestamp": pd.Timestamp(
                "2023-08-29 12:34:58.710276+0000", tz="UTC"
            ),
            "end_download_timestamp": pd.Timestamp(
                "2023-08-29 12:34:58.685410+0000", tz="UTC"
            ),
            "limit_price": 0.155255,
            "ccxt_id": 8077704766,
            "name": 9,
        }
        child_order = pd.Series(child_order)
        # Get CCXT trades DataFrame.
        target_dir = self.get_scratch_space()
        _write_test_data(target_dir)
        reader = obcccclo.CcxtLogger(target_dir)
        ccxt_trades_df = reader.load_ccxt_trades(convert_to_dataframe=True)
        resample_freq = "100ms"
        actual = obcccclo.process_timestamps_and_prices_for_a_single_order(
            child_order, ccxt_trades_df, resample_freq
        )
        actual = hpandas.df_to_str(actual)
        expected = r"""
                                                                                         event limit_price signed_quantity snapshot_ask_price snapshot_bid_price
                                                                                    1030828978  1030828978      1030828978         1030828978         1030828978
timestamp
2023-03-23 08:35:40.900000+00:00                                                       trade.1    4.040000            -6.0                NaN                NaN
2023-08-29 12:34:58.800000+00:00                                           knowledge_timestamp         NaN             NaN             0.1553             0.1552
2023-08-29 12:35:01+00:00         _submit_twap_child_order::child_order.limit_price_calculated    0.155255          -162.0                NaN                NaN
2023-08-29 12:35:05.800000+00:00               _submit_twap_child_order::child_order.submitted         NaN             NaN                NaN                NaN
2023-08-29 12:36:00+00:00                                                        end_timestamp         NaN             NaN                NaN                NaN
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
