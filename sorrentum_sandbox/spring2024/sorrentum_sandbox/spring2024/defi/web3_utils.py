"""
Import as:

import defi.web3_utils as dwebutil
"""

import functools
import os
from typing import Any, List

import brownie
import etherscan
import web3


def dir_(
    obj: Any, *, skip_underscore: str = True, skip_dunder: str = True
) -> List[str]:
    """
    Print information about one object.
    """
    dirs = dir(obj)
    dirs_tmp = []
    dirs_tmp.append(str(type(obj)))
    for dir_name in dirs:
        if skip_underscore and dir_name.startswith("_"):
            continue
        if skip_dunder and dir_name.startswith("__"):
            continue
        dirs_tmp.append(dir_name)
    return dirs_tmp


def connect_to_brownie(brownie_project_dir: str, net: str) -> Any:
    # brownie.network.web3.Web3:
    # From https://ethereum.stackexchange.com/questions/111254/how-to-call-brownie-run-with-extra-script-parameters
    print("brownie_project_dir=", brownie_project_dir)
    if brownie.network.is_connected():
        brownie.network.disconnect(net)
    brownie.network.connect(net)
    try:
        project = brownie.project.load(brownie_project_dir)
    except brownie.exceptions.ProjectAlreadyLoaded:
        pass
    print("brownie.is_connected()=", brownie.network.is_connected())
    w3 = brownie.web3
    print("w3.is_connected()=", w3.isConnected())
    return w3


@functools.cache
def get_eth_price(provider: str = "main") -> float:
    """
    Return the price of 1 ETH in USD using EtherScan.

    :param provider: main, goerli
    """
    eth = etherscan.Etherscan(os.environ["ETHERSCAN_TOKEN"], net=provider)
    # {'ethbtc': '0.07236',
    #  'ethbtc_timestamp': '1671818137',
    #  'ethusd': '1218.86',
    # 'ethusd_timestamp': '1671818141'}
    eth_price = float(eth.get_eth_last_price()["ethusd"])
    return eth_price


def ether_to_str(w3: web3.Web3, value_in_wei, *, units="gwei") -> str:
    """
    Return the value in wei in the desired unit (e.g., `ether`, `gwei`, `usd`).
    """
    if units == "usd":
        eth_price_in_usd = get_eth_price("main")
        eth = w3.fromWei(value_in_wei, "ether")
        # print(eth, eth_price_in_usd)
        value_in_usd = float(eth) * eth_price_in_usd
        value = value_in_usd
    else:
        value = w3.fromWei(value_in_wei, units)
    ret = "%s [%s]" % (value, units)
    return ret


def gas_price_as_str(w3: web3.Web3, *, units="gwei") -> str:
    """
    Return the gas price as string.
    """
    gas_price = w3.eth.gas_price
    return ether_to_str(w3, gas_price, units=units)


def print_gas_price(w3) -> None:
    """
    Print gas price in gwei and USD.
    """
    print(
        "gas_price=%s=%s"
        % (gas_price_as_str(w3, units="Gwei"), gas_price_as_str(w3, units="usd"))
    )


def print_balance(w3: web3.Web3, account, units="ether", token=None):
    if isinstance(token, web3.contract.Contract):
        balance = token.functions.balanceOf(str(account)).call()
        symbol = token.functions.symbol().call()
    elif isinstance(token, brownie.network.contract.ProjectContract):
        balance = token.balanceOf(account)
        symbol = token.symbol()
    elif token is None:
        if isinstance(account, str):
            balance = w3.eth.get_balance(account)
        else:
            # elif isinstance(token, brownie.network.account.Account):
            balance = account.balance()
        symbol = None
    else:
        raise ValueError(f"Invalid token='{token}'")
    balance_as_str = ether_to_str(w3, balance, units=units)
    ret = "balance '%s': %s" % (account, balance_as_str)
    if symbol is not None:
        ret += " " + symbol
    print(ret)


def print_tx(tx_id):
    print("tx_id=", tx_id)
    tx = brownie.chain.get_transaction(tx_id)
    print(tx.info())
    print("tx.status=", tx.status)
