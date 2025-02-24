"""
Import as:

import dataflow.model.metrics as dtfmodmetr
"""
import logging
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import core.statistics as cstats
import dataflow.core as dtfcore
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import im_v2.common.universe as ivcu

_LOG = logging.getLogger(__name__)


# #############################################################################
# Data preprocessing
# #############################################################################


# TODO(Paul): Consider deprecating this format, since it seems unique to this
#  file.
def _dassert_is_metrics_df(df: pd.DataFrame) -> None:
    """
    Check if the given df is a metrics_df.

    A metrics_df:
       - is indexed by the pair (end timestamp, asset id)
       - has all the features as columns

    E.g.,
    ```
                                            close        ...  close.ret_0
    end_ts                      asset_id
    2022-08-31 20:00:00-04:00   1030828978  0.6696       ...  NaN
                                1182743717  20016.4000   ...  NaN
                                1464553467  1551.9500    ...  NaN
    ...
    ```
    """
    # Check that df is not empty.
    hdbg.dassert_lt(0, df.shape[0])
    # Check for number of index levels.
    idx_length = len(df.index.levels)
    hdbg.dassert_eq(idx_length, 2)
    hdbg.dassert_isinstance(df.columns, pd.Index)
    # We need to check both levels since timestamps of different assets have
    # an intersection, that means the 1st level is not unique among all assets.
    # However, it's unique for every asset separately.
    hpandas.dassert_strictly_increasing_index(df.index)
    # Check that the 1st level index is valid.
    dt_idx = df.index.get_level_values(0)
    hpandas.dassert_index_is_datetime(dt_idx)
    hdbg.dassert_eq(dt_idx.name, "end_ts")
    # Check that the 2nd level index is valid.
    asset_id_idx = df.index.get_level_values(1)
    hpandas.dassert_series_type_is(pd.Series(asset_id_idx), np.int64)
    hdbg.dassert_eq(asset_id_idx.name, "asset_id")


# TODO(Grisha): consider adding `ResultDf` as a type hint so that we
# can refer to it in the interfaces.
# TODO(Grisha): consider moving the function to `result_bundle.py`.
def dassert_is_result_df(df: pd.DataFrame) -> None:
    """
    Check if the given df is a result_df. A result_df:

       - has 2 column levels
       - has all the features as the 1st column level
       - has asset ids as the 2nd column level
       - is indexed by end timestamp
    E.g.:
    ```
                              vwap.ret_0.vol_adj.lag2   ...   vwap.ret_0.vol_adj.c
                              8968126878   1030828978   ...   8968126878  1030828978
    end_ts
    2022-08-31 20:00:00-04:00 NaN          0.09         ...   0.07        0.06
    2022-08-31 20:05:00-04:00 0.08         NaN          ...   NaN         0.05
    ...
    ```
    """
    # Check that df is not empty.
    hdbg.dassert_lt(0, df.shape[0])
    # Check for number of column levels.
    col_length = df.columns.nlevels
    hdbg.dassert_eq(col_length, 2)
    # Check type of column levels.
    hdbg.dassert_container_type(df.columns.get_level_values(0), pd.Index, str)
    hdbg.dassert_container_type(df.columns.get_level_values(1), pd.Index, int)
    # Check if index is a datetime type that strictly increasing.
    hpandas.dassert_index_is_datetime(df.index)
    hpandas.dassert_strictly_increasing_index(df.index)


def convert_to_metrics_format(
    result_df: pd.DataFrame,
    y_column_name: str,
    y_hat_column_name: str,
    *,
    asset_id_column_name: str = "asset_id",
) -> pd.DataFrame:
    """
    Transform a result_df (i.e. output of the DataFlow pipeline) into a
    metrics_df.
    """
    dassert_is_result_df(result_df)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("result_df=\n%s", hpandas.df_to_str(result_df))
    # Drop NaNs.
    drop_kwargs = {
        "drop_infs": True,
        "report_stats": True,
        "subset": [y_column_name, y_hat_column_name],
    }
    metrics_df = result_df.stack()
    metrics_df = hpandas.dropna(metrics_df, **drop_kwargs)
    #
    metrics_df.index.names = [metrics_df.index.names[0], asset_id_column_name]
    _dassert_is_metrics_df(metrics_df)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("metrics_df=\n%s", hpandas.df_to_str(metrics_df))
    return metrics_df


# TODO(Grisha): specific of C3a and C8b, ideally we should add target variable
# in `DagBuilder` so that `result_df` contains everything we need.
def add_target_var(
    result_df: pd.DataFrame, config: cconfig.Config, *, inplace: bool = False
) -> pd.DataFrame:
    """
    Add target variable to a result_df.

    :param result_df: DAG output
    :param config: config that controls column names
    :param inplace: allow to change the original df if set to `True`, otherwise,
        make a copy
    :return: result_df with target variable
    """
    dassert_is_result_df(result_df)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("result_df in=\n%s", hpandas.df_to_str(result_df))
    hdbg.dassert_isinstance(config, cconfig.Config)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("config=\n%s", config)
    dag_builder_name = config["dag_builder_name"]
    if dag_builder_name in ["C1b", "C1c", "C8a"]:
        pass
    elif dag_builder_name == "C3a":
        if not inplace:
            # Make a df copy in order not to modify the original one.
            result_df = result_df.copy()
        # Compute returns.
        rets = cofinanc.compute_ret_0(
            result_df[config["column_names"]["price"]], mode="log_rets"
        )
        result_df = hpandas.add_multiindex_col(
            result_df, rets, col_name=config["cols_to_use"]["returns"]
        )
        # Adjust returns by volatility.
        rets_vol_adj = result_df[config["cols_to_use"]["returns"]] / result_df[
            config["column_names"]["volatility"]
        ].shift(2)
        result_df = hpandas.add_multiindex_col(
            result_df,
            rets_vol_adj,
            col_name=config["cols_to_use"]["vol_adj_returns"],
        )
        # Shift 2 steps ahead.
        rets_vol_adj_lead2 = result_df[
            config["cols_to_use"]["vol_adj_returns"]
        ].shift(2)
        result_df = hpandas.add_multiindex_col(
            result_df,
            rets_vol_adj_lead2,
            col_name=config["column_names"]["target_variable"],
        )
    elif dag_builder_name == "C8b":
        if not inplace:
            # Make a df copy in order not to modify the original one.
            result_df = result_df.copy()
        rets_vol_adj_lead2 = result_df[
            config["column_names"]["vol_adj_returns"]
        ].shift(2)
        result_df = hpandas.add_multiindex_col(
            result_df,
            rets_vol_adj_lead2,
            col_name=config["column_names"]["target_variable"],
        )
    else:
        raise ValueError(f"Unsupported dag_builder_name={dag_builder_name}")
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("result_df out=\n%s", hpandas.df_to_str(result_df))
    return result_df


# #############################################################################
# Tags
# #############################################################################


def _parse_universe_version_str(universe_version_str: str) -> Tuple[str, str]:
    """
    Extract vendor name and universe version from universe version as string.

    :param universe_version_str: universe version as str, e.g., `ccxt_v7_4`
    :return: vendor name and universe version, e.g., `("ccxt", "v7.4")`
    """
    vendor, universe_version = universe_version_str.split("_", 1)
    # TODO(Grisha): this is specific of ccxt, we should either convert all vendors
    # to uppercase or convert everything to lowercase.
    vendor = vendor.upper()
    universe_version = universe_version.replace("_", ".")
    return vendor, universe_version


# TODO(Paul): Review the design and possibly deprecate.
# TODO(Grisha): @Dan Pass a list of tag modes instead of just 1.
def annotate_metrics_df(
    metrics_df: pd.DataFrame,
    tag_mode: str,
    config: cconfig.Config,
    *,
    tag_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Compute a tag (stored in `tag_col`) for each row of a `metrics_df` based on
    the requested `tag_mode`.

    The `tag_mode` is used to split the `metrics_df` in different chunks to
    compute metrics.

    :param tag_mode: symbolic name representing which criteria needs to be used
        to generate the tag
    :param tag_col: if None the standard name based on the `tag_mode` is used
    :return: `metrics_df` with a new column, e.g., if `tag_mode="hour"` a new column
        representing the number of hours is added
    """
    _dassert_is_metrics_df(metrics_df)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("metrics_df in=\n%s", hpandas.df_to_str(metrics_df))
    hdbg.dassert_isinstance(tag_mode, str)
    hdbg.dassert_isinstance(config, cconfig.Config)
    # Use the standard name based on `tag_mode`.
    if tag_col is None:
        tag_col = tag_mode
    # Check both index and columns as we cannot add a tag
    # that is an index already, e.g., `asset_id`.
    hdbg.dassert_not_in(tag_col, metrics_df.reset_index().columns)
    if tag_mode == "all":
        metrics_df[tag_col] = tag_mode
    elif tag_mode == "full_symbol":
        # Get a vendor universe.
        backtest_config = config["backtest_config"]
        universe_str, _, _ = cconfig.parse_backtest_config(backtest_config)
        universe_version_str, _ = cconfig.parse_universe_str(universe_str)
        vendor, universe_version = _parse_universe_version_str(
            universe_version_str
        )
        universe_mode = "trade"
        full_symbol_universe = ivcu.get_vendor_universe(
            vendor, universe_mode, version=universe_version, as_full_symbol=True
        )
        # Build map asset_id to full symbol.
        asset_id_to_full_symbol_mapping = (
            ivcu.build_numerical_to_string_id_mapping(full_symbol_universe)
        )
        # Add a tag with full symbol mapping.
        asset_ids = metrics_df.index.get_level_values(1)
        metrics_df[tag_col] = hpandas.remap_obj(
            asset_ids, asset_id_to_full_symbol_mapping
        )
    elif tag_mode == "target_var_magnitude_quantile_rank":
        # Get the asset id index name to group data by.
        idx_name = metrics_df.index.names[1]
        # Get a variable to calculate rank for.
        target_var = config["column_names"]["target_variable"]
        # Calculate magnitude quantile rank for each data point.
        n_quantiles = config["metrics"]["n_quantiles"]
        qcut_func = lambda x: pd.qcut(x, n_quantiles, labels=False)
        magnitude_quantile_rank = metrics_df.groupby(idx_name)[
            target_var
        ].transform(qcut_func)
        # Add a tag with the rank.
        metrics_df[tag_col] = magnitude_quantile_rank
    elif tag_mode == "prediction_magnitude_quantile_rank":
        # Get the asset id index name to group data by.
        idx_name = metrics_df.index.names[1]
        # Get a variable to calculate rank for.
        prediction_var = config["column_names"]["prediction"]
        # Calculate magnitude quantile rank for each data point.
        n_quantiles = config["metrics"]["n_quantiles"]
        qcut_func = lambda x: pd.qcut(x, n_quantiles, labels=False)
        magnitude_quantile_rank = metrics_df.groupby(idx_name)[
            prediction_var
        ].transform(qcut_func)
        # Add a tag with the rank.
        metrics_df[tag_col] = magnitude_quantile_rank
    elif tag_mode == "hour":
        idx_datetime = metrics_df.index.get_level_values(0)
        metrics_df[tag_col] = idx_datetime.hour
    else:
        raise ValueError(f"Invalid tag_mode={tag_mode}")
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("metrics_df out=\n%s", hpandas.df_to_str(metrics_df))
    return metrics_df


# #############################################################################
# Metrics
# #############################################################################


# TODO(Paul): Consider deprecating.
# TODO(Grisha): double check the return type, i.e. 1 and -1,
# it seems working well with `calculate_hit_rate()` but is
# counter-intuitive.
# TODO(Grisha): move to `core/finance.py`.
def compute_hit(
    y: pd.Series,
    y_hat: pd.Series,
) -> pd.Series:
    """
    Compute hit.

    Hit is 1 when prediction's sign matches target variable's sign,
    otherwise it is -1. The function returns -1 and 1 for compatibility
    with `calculate_hit_rate()`.

    :param y: target variable
    :param y_hat: predicted value of y
    :return: hit for each pair of (y, y_hat)
    """
    hdbg.dassert_isinstance(y, pd.Series)
    hdbg.dassert_lt(0, y.shape[0])
    hdbg.dassert_isinstance(y_hat, pd.Series)
    hdbg.dassert_lt(0, y_hat.shape[0])
    # Compute hit and convert boolean values to 1 and -1.
    hit = ((y * y_hat) >= 0).astype(int)
    hit[hit == 0] = -1
    return hit


def apply_metrics(
    metrics_df: pd.DataFrame,
    tag_col: str,
    metric_modes: List[str],
    config: cconfig.Config,
) -> pd.DataFrame:
    """
    Given a metric_dfs tagged with `tag_col`, compute the metrics corresponding
    to `metric_modes`.

    E.g., `using tag_col = "asset_id"` and `metric_modes=["pnl", "hit_rate"]` the
    output is like:
    ```
                hit_rate   pnl
    asset_id
    1030828978  0.327243   0.085995
    1182743717  0.330533   0.045795
    1464553467  0.328712   0.095809
    1467591036  0.331297   0.059772
    ...
    ```

    :param metrics_df: metrics_df annotated with tag
    :param tag_col: the column to be used to split the metrics_df
    :param metric_modes: a list of strings representing the metrics to compute
        (e.g., hit rate, pnl)
    :param config: config that controls metrics parameters
    :return: the result is a df that has:
        - as index the values of the tags
        - as columns the names of the applied metrics
    """
    _dassert_is_metrics_df(metrics_df)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("metrics_df in=\n%s", hpandas.df_to_str(metrics_df))
    # Check both index and columns, e.g., `asset_id` is an index but
    # we still can group by it.
    hdbg.dassert_in(tag_col, metrics_df.reset_index().columns)
    #
    y_column_name = config["column_names"]["target_variable"]
    y_hat_column_name = config["column_names"]["prediction"]
    hit_col_name = config["metrics"]["column_names"]["hit"]
    bar_pnl_col_name = config["metrics"]["column_names"]["bar_pnl"]
    #
    y = metrics_df[y_column_name]
    y_hat = metrics_df[y_hat_column_name]
    #
    out_dfs = []
    for metric_mode in metric_modes:
        if metric_mode == "hit_rate":
            if hit_col_name not in metrics_df.columns:
                # Compute hit.
                metrics_df[hit_col_name] = compute_hit(y, y_hat)
            # Compute hit rate per tag column.
            group_df = metrics_df.groupby(tag_col)
            srs = group_df[hit_col_name].apply(
                lambda x: cstats.calculate_hit_rate(
                    x, **config["metrics"]["calculate_hit_rate_kwargs"]
                )
            )
            df_tmp = srs.to_frame()
            # Set output to the desired format.
            df_tmp = df_tmp.unstack(level=1)
            df_tmp.columns = df_tmp.columns.droplevel(0)
        elif metric_mode == "pnl":
            if bar_pnl_col_name not in metrics_df.columns:
                # Compute bar PnL.
                metrics_df[bar_pnl_col_name] = cofinanc.compute_bar_pnl(
                    metrics_df, y_column_name, y_hat_column_name
                )
            # Compute bar PnL per tag column.
            group_df = metrics_df.groupby(tag_col)
            srs = group_df.apply(
                lambda x: cofinanc.compute_total_pnl(
                    x, y_column_name, y_hat_column_name
                )
            )
            # TODO(Grisha): ideally we should pass it via config too, same below.
            srs.name = "total_pnl"
            df_tmp = srs.to_frame()
        elif metric_mode == "sharpe_ratio":
            # We need computed PnL to compute Sharpe ratio.
            if bar_pnl_col_name not in metrics_df.columns:
                # Compute bar PnL.
                metrics_df[bar_pnl_col_name] = cofinanc.compute_bar_pnl(
                    metrics_df, y_column_name, y_hat_column_name
                )
            time_scaling = config["metrics"]["time_scaling"]
            # Compute Sharpe ratio per tag column.
            group_df = metrics_df.groupby(tag_col)
            srs = group_df[bar_pnl_col_name].apply(
                lambda x: cstats.compute_sharpe_ratio(x, time_scaling)
            )
            srs.name = "SR"
            df_tmp = srs.to_frame()
        else:
            raise ValueError(f"Invalid metric_mode={metric_mode}")
        out_dfs.append(df_tmp)
    out_df = pd.concat(out_dfs, axis=1)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("metrics_df out=\n%s", hpandas.df_to_str(out_df))
    return out_df


# TODO(Grisha): the problem is that the function computes for a single `tag_mode`.
def cross_val_apply_metrics(
    result_dfs: List[pd.DataFrame],
    tag_mode: str,
    metric_modes: List[str],
    config: cconfig.Config,
) -> pd.DataFrame:
    """
    Apply metrics for multiple test set estimates.

    Return an average value of computed metrics across multiple cross
    validation splits.

    E.g.:
    ```
    hit_rate_point_est_(%)    hit_rate_97.50%CI_lower_bound_(%) hit_rate_97.50%CI_upper_bound_(%)    total_pnl    SR
    all
    all    51.241884        51.124107              51.35965                13904.318774    3.879794
    ```
    :param result_dfs: dfs with prediction for different cross
        validation splits
    :param tag_mode: see `annotate_metrics_df()`
    :param metric_modes: see `apply_metrics()`
    :param config: config that control the metrics parameters
    :return: an average value of computed metrics across multiple cross
        validation splits
    """
    hdbg.dassert_container_type(
        result_dfs, container_type=list, elem_type=pd.DataFrame
    )
    hdbg.dassert_container_type(metric_modes, container_type=list, elem_type=str)
    out_dfs = []
    for result_df in result_dfs:
        # Add the target variable.
        # TODO(Grisha): this is a hack for C3a, ideally we should
        # get target variable from the DAG.
        result_df = add_target_var(result_df, config)
        # Convert to metrics format.
        y_column_name = config["column_names"]["target_variable"]
        y_hat_column_name = config["column_names"]["prediction"]
        metrics_df = convert_to_metrics_format(
            result_df, y_column_name, y_hat_column_name
        )
        # Annotate with a tag.
        metrics_df = annotate_metrics_df(metrics_df, tag_mode, config)
        # Compute metrcis.
        # TODO(Grisha): pass as a separate parameter.
        tag_col = tag_mode
        out_df = apply_metrics(metrics_df, tag_col, metric_modes, config)
        out_dfs.append(out_df)
    out_df = pd.concat(out_dfs)
    # Average the results.
    # TODO(Grisha): consider passing mean as a function to the interface so that
    # it is possible to use other stats functions, e.g., median.
    # TODO(gp): return the res_df and then let another function do the operation.
    res_df = out_df.groupby(level=0).mean()
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("res_df out=\n%s", hpandas.df_to_str(res_df))
    return res_df


def _build_index_from_backtest_config(backtest_config: str) -> pd.Index:
    """
    Build a `DatetimeIndex` given a backtest config.

    :param backtest_config: backtest_config,
        e.g.,`ccxt_v7-all.5T.2022-09-01_2022-11-30`
    :return: pandas index with the start, end, freq specified by a
        backtest config
    """
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("backtest_config"))
    _, trading_period_str, time_interval_str = cconfig.parse_backtest_config(
        backtest_config
    )
    start_timestamp, end_timestamp = cconfig.get_period(time_interval_str)
    # Convert both timestamps to ET.
    start_timestamp = start_timestamp.tz_convert("America/New_York")
    end_timestamp = end_timestamp.tz_convert("America/New_York")
    idx = pd.date_range(start_timestamp, end_timestamp, freq=trading_period_str)
    return idx


# TODO(Grisha): is it used? revisit.
# TODO(Grisha): maybe pass a DAG?
def cross_val_predict(
    dag_runner: dtfcore.FitPredictDagRunner,
    backtest_config: str,
    train_test_splits_mode: str,
    *train_test_splits_args: Any,
) -> List[pd.DataFrame]:
    """
    Generate result_df from cross-validation of the model.

    Note: since multiple test sets is assumed, multiple result_dfs are returned.

    :param backtest_config: backtest config, e.g., `ccxt_v7-all.5T.2022-09-01_2022-11-30`
    :param train_test_splits_mode: correspond to the inputs to `get_train_test_splits()`
    :param train_test_splits_args: correspond to the inputs to `get_train_test_splits()`
    :return: list of result_dfs with estimates for each cross validation split
    """
    hdbg.dassert_isinstance(dag_runner, dtfcore.FitPredictDagRunner)
    idx = _build_index_from_backtest_config(backtest_config)
    train_test_splits = cstats.get_train_test_splits(
        idx, train_test_splits_mode, *train_test_splits_args
    )
    result_dfs = []
    for split in train_test_splits:
        # 1) Split.
        idx_train, idx_test = split
        # 2) Fit.
        dag_runner.set_fit_intervals([(idx_train[0], idx_train[-1])])
        # TODO(gp): Store also the fit_df.
        _ = dag_runner.fit()
        # 3) Predict.
        dag_runner.set_predict_intervals([(idx_test[0], idx_test[-1])])
        predict_result_bundle = dag_runner.predict()
        result_df = predict_result_bundle.result_df
        result_dfs.append(result_df)
    return result_dfs
