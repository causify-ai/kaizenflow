#!/usr/bin/env python
"""
Import as:

import im.ib.data.extract.gateway.scratch.exercise_ibapi as iidegseib
"""

import threading
import time

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper


def connect():
    class IBapi(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)

    app = IBapi()
    app.connect("127.0.0.1", 7492, 123)
    app.run()

    """
    #Uncomment this section if unable to connect
    #and to prevent errors on a reconnect
    import time
    time.sleep(2)
    app.disconnect()
    """


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 2 and reqId == 1:
            print("The current ask price is: ", price)


def run_loop():
    app.run()


app = IBapi()
app.connect("127.0.0.1", 7492, 123)

# Start the socket in a thread
api_thread = threading.Thread(target=run_loop, daemon=True)
api_thread.start()

time.sleep(1)  # Sleep interval to allow time for connection to server

# Create contract object
if True:
    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

if False:
    contract = Contract()
    contract.symbol = "XAUUSD"
    contract.secType = "CMDTY"
    contract.exchange = "SMART"
    contract.currency = "USD"

from ibapi.ticktype import TickTypeEnum

for i in range(91):
    print(TickTypeEnum.to_str(i), i)

# Request Market Data
# app.reqMktData(1, contract, '', False, False, [])
# app.reqMktData(1, contract, 'DELAYED_CLOSE', False, False, [])
app.reqMktData(1, contract, 4, False, False, [])

time.sleep(10)  # Sleep interval to allow time for incoming price data
app.disconnect()
