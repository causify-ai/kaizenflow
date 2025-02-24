"""
Tools for Kaiko API

Import as:

import sorrentum_sandbox.examples.ml_projects.Issue28_Team9_Implement_sandbox_for_Kaiko.kaiko-api-master.kaiko.utils as ssempitisfkkku
"""
import pandas as pd
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from time import sleep
import logging

default_headers = {"Accept": "application/json", "Accept-Encoding": "gzip"}
default_df_formatter = lambda res, extra_args={}: pd.DataFrame(res["data"])

# Sleep time between consecutive queries (in seconds)
sleep_time = 0.01


def requests_retry_session(
    retries=5, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None
):
    """
    Adapted from https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def request_data(
    url: str,
    headers: dict = default_headers,
    params: dict = None,
    session_params: dict = {},
    pagination: bool = True,
    **kwargs,
):
    """
    Makes the request from the REST endpoint and returns the json response.

    :param url:
    :param headers:
    :param params: Dictionary containing the request parameters.
    :type params: dict
    :param session_params: Session parameters for the get request.
    :type session_params: dict
    :param pagination: Continue requests using pagination with next_urls?
    :type pagination: bool
    :return: JSON response if the field 'result' is 'success'.
    """
    # use default session
    session = requests_retry_session(**session_params)
    response = session.get(url, headers=headers, params=params)
    res = response.json()
    if pagination:
        res_tmp = res
        res["total_queries"] = 1
        while "next_url" in res_tmp.keys():
            logging.warning(f"total_queries = {res['total_queries']}")
            response = session.get(res_tmp["next_url"], headers=headers)
            res_tmp = response.json()
            # append data to previous query
            res["data"] = res["data"] + res_tmp["data"]
            res["total_queries"] += 1
            sleep(sleep_time)

    try:
        if ("result" in res and res["result"] == "success") or (
            "result" not in res
        ):
            pass
    except Exception as e:
        logging.error(f"{e}")
        logging.error(
            "Data request failed - here is what was returned:\n%s" % (res)
        )
    return res


def request_next_data(
    next_url: str,
    n_next: int = 1,
    headers: dict = default_headers,
    session_params: dict = {},
    **kwargs,
):
    """
    Makes the request from the REST endpoint and returns the json response.

    :param url:
    :param headers:
    :param params: Dictionary containing the request parameters.
    :type params: dict
    :param session_params: Session parameters for the get request.
    :type session_params: dict
    :param pagination: Continue requests using pagination with next_urls?
    :type pagination: bool
    :return: JSON response if the field 'result' is 'success'.
    """
    # use default session
    session = requests_retry_session(**session_params)

    response = session.get(next_url, headers=headers)
    res = response.json()

    res_tmp = res
    counter = 1
    while "next_url" in res_tmp.keys():
        response = session.get(res_tmp["next_url"], headers=headers)
        res_tmp = response.json()
        # append data to previous query
        res["data"] = res["data"] + res_tmp["data"]
        counter += 1
        sleep(sleep_time)
        if counter > n_next:
            break
    try:
        if ("result" in res and res["result"] == "success") or (
            "result" not in res
        ):
            pass
    except Exception as e:
        logging.error(f"{e}")
        logging.error(
            "Data request failed - here is what was returned:\n%s" % (res)
        )
    return res


def request_next_df(
    next_url: str,
    return_query: bool = False,
    return_res: bool = False,
    df_formatter=default_df_formatter,
    n_next: int = 1,
    extra_args: dict = {},
    **kwargs,
):
    """
    Make a simple request from the API.

    :param url: Full URL of the query.
    :type url: str
    :param return_query: Whether to return the query used or not
    :type return_query: bool
    :param headers: Headers for the query.
    :type headers: dict, optional
    :param df_formatter: Formatter function to transform the JSON's data result into a DataFrame.
    :return: DataFrame containing the data.
    """
    res = request_next_data(next_url, n_next, **kwargs)
    try:
        df = df_formatter(res, extra_args=extra_args)
        if "query" in res.keys():
            query = res["query"]
        else:
            query = None
    except Exception as e:
        query = (e, res)
        df = pd.DataFrame()
    if return_query and return_res:
        return df, query, res
    elif return_query and not (return_res):
        return df, query
    elif not (return_query) and return_res:
        return df, res
    else:
        return df


def request_df(
    url: str,
    return_query: bool = False,
    return_res: bool = False,
    df_formatter=default_df_formatter,
    extra_args: dict = {},
    **kwargs,
):
    """
    Make a simple request from the API.

    :param url: Full URL of the query.
    :type url: str
    :param return_query: Whether to return the query used or not
    :type return_query: bool
    :param headers: Headers for the query.
    :type headers: dict, optional
    :param df_formatter: Formatter function to transform the JSON's data result into a DataFrame.
    :return: DataFrame containing the data.
    """
    res = request_data(url, **kwargs)
    try:
        df = df_formatter(res, extra_args=extra_args)
        if "query" in res.keys():
            query = res["query"]
        else:
            query = None
    except Exception as e:
        query = (e, res)
        df = pd.DataFrame()
    if return_query and return_res:
        return df, query, res
    elif return_query and not (return_res):
        return df, query
    elif not (return_query) and return_res:
        return df, res
    else:
        return df


def convert_timestamp_unix_to_datetime(ts, unit="ms"):
    """
    Convert a unix millisecond timestamp to pandas datetime format.

    :param ts: Timestamp in unix millisecond format.
    :return:
    """
    return pd.to_datetime(ts, unit=unit)


def convert_timestamp_str_to_datetime(ts: str):
    """
    Takes any type of string timestamp and converts it to a pandas datetime format.

    :param ts: Timestamp in a string format understandable by pandas.to_datetime().
    :type ts: str
    :return:
    """
    # removing UTC timezone if ISO 8601 format
    if ts.endswith("Z"):
        ts = ts.replace("Z", "")

    return pd.to_datetime(ts)


def convert_timestamp_datetime_to_unix(ts: str):
    """
    Converts pandas datetime to unix millisecond timestamp.

    :param ts:
    :return:
    """
    return int(ts.timestamp() * 1e3)


def convert_timestamp_to_apiformat(ts):
    """
    Takes multiple types of timestamp and converts it to a format readable by the API.
    https://docs.kaiko.com/#timestamps

    :param ts: Timestamp in string, unix, or pandas.datetime format.
    :type ts: str, int, float, pandas.datetime
    :return: Timestamp in ISO 8601 format.
    :rtype: str
    """
    # For all recognized types, convert the timestamp to pandas.datetime format

    # Strings (can be just a year, day, or a full ISO 8601 formatted string)
    if type(ts) == str:
        ts = convert_timestamp_str_to_datetime(ts)

    # Unix millisecond format
    elif type(ts) in [int, float]:
        ts = convert_timestamp_unix_to_datetime(ts)

    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


if __name__ == "__main__":
    headers = default_headers.copy()
    headers["X-Api-Key"] = "YOUR API KEY"
    URL = (
        "https://us.market-api.kaiko.io/v1/data/trades.latest/exchanges/{exchange}/spot/{pair}/aggregations"
        "/count_ohlcv_vwap"
    )
    # df = request_df(URL)
