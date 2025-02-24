"""
Import as:

import defi.tulip.adapters.twap_vwap_adapter as dtatvwad
"""

import json
import os
from functools import wraps
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import requests
from flask import Flask, abort, jsonify, request

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
# Specify FLASK_DEBUG_MODE=0 To turn off debug mode.
DEBUG_MODE = os.environ.get("FLASK_DEBUG_MODE", "1") == "1"


def require_api_key(func: Callable) -> Callable:
    """
    Perform authorization of a request.
    """

    @wraps(func)
    def check_api_key(*args, **kwargs):
        api_key = request.headers.get("X-API-KEY")
        if not api_key or api_key != API_KEY:
            abort(401, "Unauthorized: Invalid API key")
        return func(*args, **kwargs)

    return check_api_key


def _get_price_volume_data() -> Dict[str, Any]:
    """
    Query price and volume data from the CoinGecko API.
    """
    # Get parameters from the Chainlink node request.
    data = request.json.get("data", {})
    symbol = data.get("symbol", "")
    start_time = data.get("start_time", "")
    end_time = data.get("end_time", "")
    # Query the CoinGecko API for price data within the specified time range.
    response = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart/range?vs_currency=eth&from={start_time}&to={end_time}"
    )
    if response.status_code >= 400:
        # Process an error.
        error_data = {
            "jobRunID": request.json.get("id", ""),
            "status": "errored",
            "error": response.text,
        }
        return error_data
    price_data = json.loads(response.text)
    return price_data


def _process_price_data(
    price_data: Dict[str, Any]
) -> Tuple[List[int], List[float]]:
    """
    Get the sequence of volumes and prices in WEI.
    """
    # Select and convert prices to WEI.
    prices = np.array(
        [int(price[1] * 10**18) for price in price_data["prices"]]
    )
    # Select volumes.
    volumes = np.array([volume[1] for volume in price_data["total_volumes"]])
    return prices, volumes


@app.route("/get_twap", methods=["POST"])
@require_api_key
def get_twap() -> Dict[str, Any]:
    """
    Get TWAP for the Chainlink node.
    """
    price_data = _get_price_volume_data()
    if price_data.get("error"):
        return price_data
    prices, _ = _process_price_data(price_data)
    twap = np.mean(prices)
    twap = jsonify(
        {
            "jobRunID": request.json.get("id", ""),
            "data": {"result": str(twap)},
        }
    )
    return twap


@app.route("/get_vwap", methods=["POST"])
@require_api_key
def get_vwap() -> Dict[str, Any]:
    """
    Get VWAP for the Chainlink node.
    """
    price_data = _get_price_volume_data()
    if price_data.get("error"):
        return price_data
    prices, volumes = _process_price_data(price_data)
    vwap = np.average(prices, weights=volumes)
    vwap = jsonify(
        {
            "jobRunID": request.json.get("id", ""),
            "data": {"result": str(vwap)},
        }
    )
    return vwap


if __name__ == "__main__":
    app.run(debug=DEBUG_MODE)
