"""
Import as:

import defi.dao_swap.twap_vwap_adapter as ddstvwad
"""

import json
from typing import Any, Dict, List, Tuple

import numpy as np
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)


def _get_price_volume_data() -> Tuple[List[int], List[float]]:
    """
    Query price and volume data from the CoinGecko API.
    """
    # Get parameters from the Chainlink node request.
    symbol = request.json["symbol"]
    start_time = request.json["start_time"]
    end_time = request.json["end_time"]
    time_interval = request.json["time_interval"]
    # Query the CoinGecko API for price data within the specified time range.
    response = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart/range?vs_currency=eth&from={start_time}&to={end_time}&interval={time_interval}"
    )
    price_data = json.loads(response.text)["prices"]
    # Get price and volume data.
    prices = [float(entry[1]) for entry in price_data]
    volumes = [float(entry[2]) for entry in price_data]
    # Convert prices to WEI.
    eth_to_wei = 10**18
    prices = [int(price * eth_to_wei) for price in prices]
    return prices, volumes


@app.route("/get_twap", methods=["POST"])
def get_twap() -> Dict[str, Any]:
    """
    Get TWAP for the Chainlink node.
    """
    prices, volumes = _get_price_volume_data()
    twap = np.average(prices, weights=volumes)
    twap = jsonify(
        {
            "jobRunID": request.json["jobRunID"],
            "data": {"result": str(twap)},
        }
    )
    return twap


@app.route("/get_vwap", methods=["POST"])
def get_vwap() -> Dict[str, Any]:
    """
    Get VWAP for the Chainlink node.
    """
    prices, volumes = _get_price_volume_data()
    vwap = np.sum(prices * volumes) / np.sum(volumes)
    vwap = jsonify(
        {
            "jobRunID": request.json["jobRunID"],
            "data": {"result": str(vwap)},
        }
    )
    return vwap


if __name__ == "__main__":
    app.run(debug=True)
