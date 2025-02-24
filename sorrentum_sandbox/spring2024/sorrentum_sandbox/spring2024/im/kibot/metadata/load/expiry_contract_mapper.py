"""
Import as:

import im.kibot.metadata.load.expiry_contract_mapper as imkmlecoma
"""

import functools
import re
from typing import Iterable, Tuple, Union

import helpers.hdbg as hdbg


class ExpiryContractMapper:
    """
    Implement functions to handle expiry contracts, e.g., "ESH19".
    """

    _MONTH_TO_EXPIRY = {
        "January": "F",
        "February": "G",
        "March": "H",
        "April": "J",
        "May": "K",
        "June": "M",
        "July": "N",
        "August": "Q",
        "September": "U",
        "October": "V",
        "November": "X",
        "December": "Z",
    }

    _MONTH_TO_EXPIRY_NUM = {
        1: "F",
        2: "G",
        3: "H",
        4: "J",
        5: "K",
        6: "M",
        7: "N",
        8: "Q",
        9: "U",
        10: "V",
        11: "X",
        12: "Z",
    }

    _EXPIRY_TO_MONTH = {v: k for k, v in _MONTH_TO_EXPIRY.items()}
    _EXPIRY_TO_MONTH_NUM = {v: k for k, v in _MONTH_TO_EXPIRY_NUM.items()}

    @staticmethod
    def parse_expiry_contract(v: str) -> Tuple[str, str, Union[int, str]]:
        """
        Parse a futures contract name into its components, e.g., in a futures
        contract name like "ESH10":

        - base symbol is ES
        - month is H
        - year is 10 (i.e., 2010)
        """
        m = re.match(r"^(\S+)(\S)(\d{2})$", v)
        if m is None:
            hdbg.dassert(m, "Invalid '%s'", v)
            return "", "", 0
        base_symbol, month, year = m.groups()
        return base_symbol, month, year

    @staticmethod
    def compare_expiry_contract(v1: str, v2: str) -> int:
        """
        Compare function for two expiry contracts in terms of month and year (
        e.g., "U10") according to python `cmp` convention.

        :return: -1, 0, 1 in case of <, ==, > relationship between v1 and v2.
        """
        base_symbol1, month1, year1 = ExpiryContractMapper.parse_expiry_contract(
            v1
        )
        base_symbol2, month2, year2 = ExpiryContractMapper.parse_expiry_contract(
            v2
        )
        hdbg.dassert_eq(base_symbol1, base_symbol2)
        # Compare.
        if year1 < year2 or (year1 == year2 and month1 < month2):
            res = -1
        elif year1 == year2 and month1 == month2:
            res = 0
        else:
            res = 1
        return res

    @staticmethod
    def sort_expiry_contract(contracts: Iterable[str]) -> Iterable[str]:
        # python3 removed `cmp` from sort so we need to convert it into a key.
        contracts = sorted(
            contracts,
            key=functools.cmp_to_key(
                ExpiryContractMapper.compare_expiry_contract
            ),
        )
        return contracts

    @staticmethod
    def parse_year(year: str) -> int:
        """
        Convert 2 digit years to 4 digit years, e.g. 20 -> 2020 & 99 -> 1999.
        """
        year = int(year)
        year = year + 2000 if year < 50 else year + 1900
        return year

    def month_to_expiry(self, month: str) -> str:
        hdbg.dassert_in(month, self._MONTH_TO_EXPIRY)
        return self._MONTH_TO_EXPIRY[month]

    def expiry_to_month(self, expiry: str) -> str:
        hdbg.dassert_in(expiry, self._EXPIRY_TO_MONTH)
        return self._EXPIRY_TO_MONTH[expiry]

    def month_to_expiry_num(self, month: int) -> str:
        hdbg.dassert_in(month, self._MONTH_TO_EXPIRY_NUM)
        return self._MONTH_TO_EXPIRY_NUM[month]

    def expiry_to_month_num(self, expiry: str) -> int:
        hdbg.dassert_in(expiry, self._EXPIRY_TO_MONTH_NUM)
        return self._EXPIRY_TO_MONTH_NUM[expiry]
