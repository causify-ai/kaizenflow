#!/usr/bin/env python

"""
Import as:

import im.ib.data.extract.gateway.scratch.exercise_ib as imidegseib
"""

import datetime

import ib_insync

ib = ib_insync.IB()
ib.connect(port=7492)


def get_nflx_data():
    nflx_contract = ib_insync.Stock("NFLX", "SMART", "USD")
    print(nflx_contract)
    ib.qualifyContracts(nflx_contract)
    print(nflx_contract)
    data = ib.reqMktData(nflx_contract)
    print(data.marketPrice())

    historical_data_nflx = ib.reqHistoricalData(
        nflx_contract,
        "",
        barSizeSetting="15 mins",
        durationStr="2 D",
        whatToShow="MIDPOINT",
        useRTH=True,
    )
    print(historical_data_nflx)


def get_es_data():
    # Future('ES', '20180921', 'GLOBEX')
    fut = ib_insync.Future("ES", "202103", "GLOBEX", includeExpired=True)
    print("\n".join(map(str, ib.reqContractDetails(fut))))

    bars = ib.reqHistoricalData(
        fut,
        endDateTime=datetime.date(2021, 2, 1),
        durationStr="60 D",
        barSizeSetting="1 hour",
        whatToShow="TRADES",
        useRTH=True,
        formatDate=1,
    )
    print(bars)


def get_es_expiry_data():
    # Use expired or not to get the expired contracts
    future = ib_insync.Future("ES", exchange="GLOBEX", currency="USD")
    active_futures = ib.reqContractDetails(future)
    future.includeExpired = True
    active_and_expired_futures = ib.reqContractDetails(future)

    print(
        "{:d} expired futures, {:d} active futures".format(
            len(active_and_expired_futures) - len(active_futures),
            len(active_futures),
        )
    )

    # show the expiration dates of the futures, confirming some expiration dates are in the past
    # and get the daily history
    for future in active_and_expired_futures:
        expiration = future.contract.lastTradeDateOrContractMonth
        bars = ib.reqHistoricalData(
            future.contract, "", "5 Y", "1 day", "TRADES", True
        )
        future_info = (
            "Future symbol "
            + future.contract.localSymbol
            + ", expiration: "
            + expiration
        )
        if bars:
            df = ib_insync.util.df(bars)
            print(
                future_info,
                " has available data between",
                df["date"].min(),
                df["date"].max(),
            )
        else:
            print(future_info, "has no historical data available")


# get_nflx_data()
# get_es_data()
get_es_expiry_data()

ib.disconnect()
