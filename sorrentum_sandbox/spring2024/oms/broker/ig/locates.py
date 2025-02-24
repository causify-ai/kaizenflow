"""
Import as:

import oms.broker.ig.locates as obrigloc
"""

import pandas as pd


class Locates:
    def __init__(self, strategy_id: str, account: str):
        self._strategy_id = strategy_id
        self._account = account

    def get_locates(self, trade_date) -> pd.DataFrame:
        # tradedate
        # id
        # strategyid
        # account
        # quantity
        # rate
        # timestamp_update
        # timestamp_db
        return
