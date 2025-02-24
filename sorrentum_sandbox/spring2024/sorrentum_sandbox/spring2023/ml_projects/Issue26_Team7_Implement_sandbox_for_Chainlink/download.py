"""
Extract part of the ETL and QA pipeline.

Import as:


import sorrentum_sandbox.examples.ml_projects.Issue26_Team7_Implement_sandbox_for_Chainlink.download as sisebido
"""
import logging
import time

import pandas as pd
from web3 import Web3
from tqdm import tqdm

import sorrentum_sandbox.common.download as ssandown

_LOG = logging.getLogger(__name__)


def downloader(pair, start_roundid, **kwargs):

    """
    Download data in Euthereum Mainnet from Web3 Socket.
    """
    web3 = Web3(
        Web3.HTTPProvider("https://rpc.ankr.com/eth")
    )  # Euthereum Mainnet Web3 Http provider address.
    abi = '[{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"description","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint80","name":"_roundId","type":"uint80"}],"name":"getRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"latestRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"version","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'

    # Contract address for different pair.
    addr_dict = {
        "BTC/USD": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
        "BUSD/USD": "0x833D8Eb16D306ed1FbB5D7A2E019e106B960965A",
        "ETH/USD": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "DOGE/USD": "0x2465CefD3b488BE410b941b1d4b2767088e2A028",
    }
    addr = addr_dict.get(pair)

    data_lst = []

    # If end_roundid is specified, download from the start_roundid to the end_roundid.
    if "end_roundid" in kwargs:
        end_roundid = kwargs["end_roundid"]
        for i in tqdm(range(start_roundid, end_roundid + 1)):
            contract = web3.eth.contract(address=addr, abi=abi)
            data = contract.functions.getRoundData(i).call()
            data_lst.append(data)
            if len(data_lst) % 2000 == 0:  # sleep 10 min for every 2000 request.
                time.sleep(600)

    # end_roundid is not specified download from start_roundid to the latest_roundid
    else:
        contract = web3.eth.contract(address=addr, abi=abi)
        latestData = (
            contract.functions.latestRoundData().call()
        )  # The latest data for the pair.
        for i in tqdm(range(start_roundid + 1, latestData[0])):
            data = contract.functions.getRoundData(i).call()
            data_lst.append(data)
            if len(data_lst) % 2000 == 0:  # sleep 10 min for every 2000 request.
                time.sleep(600)

    data_df = pd.DataFrame(
        data_lst,
        columns=["roundId", "price", "startedAt", "updatedAt", "answeredInRound"],
    )  # List to Dataframe

    data_df[
        "pair"
    ] = (
        contract.functions.description().call()
    )  # Add pair column to the dataframe.
    data_df[
        "decimals"
    ] = (
        contract.functions.decimals().call()
    )  # Add decimals column to the dataframe.
    data_df["startedAt"] = pd.to_datetime(
        data_df["startedAt"], unit="s"
    )  # Covert the startedAt column data type from timestamp to datetime.
    data_df["updatedAt"] = pd.to_datetime(
        data_df["updatedAt"], unit="s"
    )  # Covert the updatedAt column data type from timestamp to datetime.

    _LOG.info(f"Downloaded data: \n\t {data_df.head()}")
    return ssandown.RawData(data_df)
