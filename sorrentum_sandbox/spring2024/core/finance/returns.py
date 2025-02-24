"""
Import as:

import core.finance.returns as cfinretu
"""
import datetime
import logging
from typing import Dict, List, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hsql as hsql

_LOG = logging.getLogger(__name__)


def compute_overnight_returns(
    df: pd.DataFrame,
    asset_id_col: str,
    *,
    date_col: str = "date",
    open_col: str = "open_",
    close_col: str = "close",
    total_return_col: str = "total_return",
    previous_total_return_col: str = "prev_total_return",
    market_open: datetime.time = datetime.time(9, 30),
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """
    Compute overnight returns.

    :param df: dataframe with the following columns:
        ["asset_id_col", "date", "open", "close", "total_return",
         "previous_total_return"]
      - the "date" column represents the given day (and so the data in the
        row is available at the end of the day rather than the beginning)
      - the total return columns must be combined to calculate a percentage
        return; these reflect adjusted values (at the close).
      - "open" and "close" are unadjusted
    :param asset_id_col: str,
    :param market_open: the time of the market open
    :param timezone: the timezone of the market open
    :return: a dataframe of overnight returns timestamped at the market open;
        columns are asset ids
    """
    # Ensure that the dataframe has the necessary columns.
    hdbg.dassert_is_subset(
        [
            asset_id_col,
            date_col,
            close_col,
            total_return_col,
            previous_total_return_col,
        ],
        df.columns.to_list(),
    )
    # Ensure that asset ids are ints.
    hpandas.dassert_series_type_is(
        df[asset_id_col],
        np.int64,
    )
    # Compute the close-to-close adjusted percentage return.
    total_returns = (df[total_return_col] - df[previous_total_return_col]) / df[
        previous_total_return_col
    ]
    # Compute intraday percentage returns.
    intraday_returns = (df[close_col] - df[open_col]) / df[open_col]
    # Compute overnight returns from total and intraday returns.
    overnight_returns = (total_returns - intraday_returns) / (
        1 + intraday_returns
    )
    # TODO(Paul): Consider moving this step outside of this function.
    # Localize to timestamps.
    market_open_offset = pd.Timedelta(
        hours=market_open.hour, minutes=market_open.minute
    )
    datetime = pd.to_datetime(df[date_col]) + market_open_offset
    overnight_returns_df = pd.DataFrame(
        {
            "datetime": datetime,
            asset_id_col: df[asset_id_col],
            "overnight_returns": overnight_returns,
        }
    )
    overnight_returns_df.set_index("datetime", inplace=True)
    overnight_returns_df.index = overnight_returns_df.index.tz_localize(timezone)
    # Convert from a long to a wide format.
    overnight_returns_df = overnight_returns_df.pivot(columns=[asset_id_col])
    return overnight_returns_df


def query_by_assets_and_dates(
    db_connection: hsql.DbConnection,
    table_name: str,
    asset_ids: List[int],
    asset_id_col: str,
    start_date: datetime.date,
    end_date: datetime.date,
    date_col: str,
    select_cols: List[str],
) -> pd.DataFrame:
    """
    Query `table_name` for `select_cols` for assets and in date range.
    """
    query = []
    # Ensure that `asset_id_col` and `date_col` are selected exactly once.
    hdbg.dassert_isinstance(asset_id_col, str)
    hdbg.dassert_isinstance(date_col, str)
    select_cols = list(set(select_cols + [asset_id_col, date_col]))
    select_col_str = ", ".join(select_cols)
    query.append(f"SELECT {select_col_str} FROM {table_name}")
    # Add date range restriction to WHERE clause.
    hdbg.dassert_isinstance(start_date, datetime.date)
    hdbg.dassert_isinstance(end_date, datetime.date)
    WHERE = f"{date_col} BETWEEN '{start_date}' AND '{end_date}'"
    # Add asset id membership to WHERE caluse.
    hdbg.dassert_isinstance(asset_ids, list)
    asset_ids = tuple(asset_ids)
    asset_id_str = str(asset_ids)[:-2] + ")"
    WHERE += f" AND {asset_id_col} IN {asset_id_str}"
    query.append(f"WHERE {WHERE}")
    # Order by `date_col`.
    query.append(f"ORDER BY {date_col}")
    # Create the full query.
    query = "\n".join(query)
    _LOG.debug("query=%s", query)
    # Execute the query.
    df = hsql.execute_query_to_df(db_connection, query)
    # Enforce `int` types on asset ids (dropping NaN asset ids first).
    df = df.dropna(subset=[asset_id_col])
    df = df.convert_dtypes()
    hpandas.dassert_series_type_is(df[asset_id_col], np.int64)
    return df


def compute_ret_0(
    prices: Union[pd.Series, pd.DataFrame], mode: str
) -> Union[pd.Series, pd.DataFrame]:
    if mode == "pct_change":
        ret_0 = prices.divide(prices.shift(1)) - 1
    elif mode == "log_rets":
        ret_0 = np.log(prices) - np.log(prices.shift(1))
    elif mode == "diff":
        # TODO(gp): Use shifts for clarity, e.g.,
        # ret_0 = prices - prices.shift(1)
        ret_0 = prices.diff()
    elif mode == "symmetric_pct_change":
        ret_0 = 2 * prices.diff().divide(prices + prices.shift(1))
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    if isinstance(ret_0, pd.Series):
        ret_0.name = "ret_0"
    return ret_0


def compute_ret_0_from_multiple_prices(
    prices: Dict[str, pd.DataFrame], col_name: str, mode: str
) -> pd.DataFrame:
    hdbg.dassert_isinstance(prices, dict)
    rets = []
    for s, price_df in prices.items():
        _LOG.debug("Processing s=%s", s)
        rets_tmp = compute_ret_0(price_df[col_name], mode)
        rets_tmp = pd.DataFrame(rets_tmp)
        rets_tmp.columns = ["%s_ret_0" % s]
        rets.append(rets_tmp)
    rets = pd.concat(rets, sort=True, axis=1)
    return rets


# TODO(*): Add a decorator for handling multi-variate prices as in
#  https://github.com/.../.../issues/568


def compute_prices_from_rets(
    price: pd.Series,
    rets: pd.Series,
    mode: str,
) -> pd.Series:
    """
    Compute price p_1 at moment t_1 with given price p_0 at t_0 and return
    ret_1.

    This implies that input has ret_1 at moment t_1 and uses price p_0 from
    previous step t_0. If we have forward returns instead (ret_1 and p_0 are at
    t_0), we need to shift input returns index one step ahead.

    :param price: series with prices
    :param rets: series with returns
    :param mode: returns mode as in compute_ret_0
    :return: series with computed prices
    """
    hdbg.dassert_isinstance(price, pd.Series)
    hdbg.dassert_isinstance(rets, pd.Series)
    price = price.reindex(rets.index).shift(1)
    if mode == "pct_change":
        price_pred = price * (rets + 1)
    elif mode == "log_rets":
        price_pred = price * np.exp(rets)
    elif mode == "diff":
        price_pred = price + rets
    else:
        raise ValueError("Invalid mode='%s'" % mode)
    return price_pred


def convert_log_rets_to_pct_rets(
    log_rets: Union[float, pd.Series, pd.DataFrame]
) -> Union[float, pd.Series, pd.DataFrame]:
    """
    Convert log returns to percentage returns.

    :param log_rets: time series of log returns
    :return: time series of percentage returns
    """
    return np.exp(log_rets) - 1


def convert_pct_rets_to_log_rets(
    pct_rets: Union[float, pd.Series, pd.DataFrame]
) -> Union[float, pd.Series, pd.DataFrame]:
    """
    Convert percentage returns to log returns.

    :param pct_rets: time series of percentage returns
    :return: time series of log returns
    """
    return np.log(pct_rets + 1)
