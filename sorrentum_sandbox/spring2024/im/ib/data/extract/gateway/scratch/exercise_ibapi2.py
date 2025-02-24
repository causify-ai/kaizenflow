#!/usr/bin/env python
"""
Import as:

import im.ib.data.extract.gateway.scratch.exercise_ibapi2 as imidegsei
"""

import threading
import time

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def historicalData(self, reqId, bar):
        print(f"Time: {bar.date} Close: {bar.close}")


def run_loop():
    app.run()


app = IBapi()
app.connect("127.0.0.1", 7492, 123)

# Start the socket in a thread
api_thread = threading.Thread(target=run_loop, daemon=True)
api_thread.start()

time.sleep(1)  # Sleep interval to allow time for connection to server

# Create contract object
if False:
    contract = Contract()
    contract.symbol = "EUR"
    contract.secType = "CASH"
    contract.exchange = "IDEALPRO"
    contract.currency = "USD"

if False:
    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

if True:
    contract = Contract()
    contract.symbol = "ES"
    contract.secType = "FUT"
    contract.exchange = "GLOBEX"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "202103"
    contract.includeExpired = True
    # contract.multiplier = "5"

# app.reqMarketDataType(3)
# app.reqMktData(897,contract,"",False)

# app.reqMarketDataType(3)
app.reqMarketDataType(1)
# app.reqHistoricalData(50, contract, '', "30 D", "1 day", "TRADES", 1, "1", False, [])

# Request historical candles
app.reqHistoricalData(1, contract, "", "2 D", "1 hour", "BID", 0, 2, False, [])

time.sleep(5)  # sleep to allow enough time for data to be returned
app.disconnect()
