"""
Import as:

import dataflow.model.tiled_flows as dtfmotiflo
"""

import datetime
import logging

import pandas as pd

_LOG = logging.getLogger(__name__)

from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from tqdm.autonotebook import tqdm

import core.signal_processing as csigproc
import dataflow.model.forecast_evaluator_from_prices as dtfmfefrpr
import dataflow.model.forecast_mixer as dtfmofomix
import dataflow.model.parquet_tile_analyzer as dtfmpatian
import dataflow.model.regression_analyzer as dtfmoreana
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque


def yield_processed_parquet_tiles_by_year(
    dir_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    asset_id_col: str,
    data_cols: List[Union[int, str]],
    *,
    asset_ids: Optional[List[int]] = None,
) -> Iterator[pd.DataFrame]:
    """
    Process parquet tiles as dataflow multi-indexed column dataframes.

    :param dir_name: dir of tiled results
    :param start_date: date specifying first month/year to read
    :param end_date: date specifying last month/year to read
    :param asset_id_col: name of the asset id column
    :param data_cols: names of data columns to load
    :param asset_ids: if `None`, load all available; otherwise load specified
        subset
    :return: dataframe with multi-indexed columns
    """
    hdbg.dassert_isinstance(asset_id_col, str)
    hdbg.dassert_isinstance(data_cols, list)
    cols = [asset_id_col] + data_cols
    #
    hdbg.dassert_isinstance(start_date, datetime.date)
    hdbg.dassert_isinstance(end_date, datetime.date)
    hdbg.dassert_lte(start_date, end_date)
    #
    tiles = hparque.yield_parquet_tiles_by_year(
        dir_name,
        start_date,
        end_date,
        cols,
        asset_ids=asset_ids,
        asset_id_col=asset_id_col,
    )
    num_years = end_date.year - start_date.year + 1
    for tile in tqdm(tiles, total=num_years):
        # Convert the `from_parquet()` dataframe to a dataflow-style dataframe.
        df = process_parquet_read_df(
            tile,
            asset_id_col,
        )
        yield df


def yield_processed_parquet_tile_dict(
    simulations: pd.DataFrame,
    start_date: datetime.date,
    end_date: datetime.date,
    asset_id_col: str,
    *,
    asset_ids: Optional[List[int]] = None,
) -> Iterator[Dict[str, pd.DataFrame]]:
    """
    Yield a dictionary of processed dataframes, keyed by simulation.

    `simulations` should look like:

    ```
             dir_name   prediction_col
    sim1    dir_name1         col_name
    sim2    dir_name2         col_name
    ```
    """
    # Sanity-check the simulation dataframe.
    hdbg.dassert_isinstance(simulations, pd.DataFrame)
    hdbg.dassert_is_subset(["dir_name", "prediction_col"], simulations.columns)
    hdbg.dassert(not simulations.index.has_duplicates)
    # Build time filters.
    # TODO(Paul): Allow loading smaller tiles once we are memory-constrained.
    time_filters = hparque.build_year_month_filter(start_date, end_date)
    hdbg.dassert_isinstance(time_filters, list)
    hdbg.dassert(time_filters)
    if not isinstance(time_filters[0], list):
        time_filters = [time_filters]
    # Build asset id filter.
    if asset_ids is None:
        asset_ids = []
    asset_id_filter = hparque.build_asset_id_filter(asset_ids, asset_id_col)
    # Iterate through time slices.
    for time_filter in time_filters:
        # Create a single parquet filter by combining `time_filter` and, if
        # one exists, the `asset_id_filter`.
        if asset_id_filter:
            combined_filter = [
                id_filter + time_filter for id_filter in asset_id_filter
            ]
        else:
            combined_filter = time_filter
        # Create a dictionary of processed dataframes, indexed by simulation.
        dfs = {}
        for idx, row in simulations.iterrows():
            dir_name = row["dir_name"]
            prediction_col = row["prediction_col"]
            columns = [asset_id_col] + [prediction_col]
            tile = hparque.from_parquet(
                dir_name,
                columns=columns,
                filters=combined_filter,
            )
            # TODO(Grisha): @Dan Add assert for empty tile df.
            df = process_parquet_read_df(
                tile,
                asset_id_col,
            )[prediction_col]
            dfs[idx] = df
        yield dfs


# TODO(ShaopengZ): Clean up the classes by initializing `forecast_evaluator`
# objects outside the tiling function.
def annotate_forecasts_by_tile(
    dir_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    asset_id_col: str,
    price_col: str,
    volatility_col: str,
    prediction_col: str,
    *,
    asset_ids: Optional[List[int]] = None,
    annotate_forecasts_kwargs: Dict[str, Any],
    return_portfolio_df: bool = True,
    forecast_evaluator: Any = dtfmfefrpr.ForecastEvaluatorFromPrices,
    optimizer_config_dict: Optional[dict] = None,
) -> Tuple[Optional[pd.DataFrame], pd.DataFrame]:
    """
    Combine yearly tiled loading with forecast evaluation.

    :param dir_name: as in `yield_processed_parquet_tiles_by_year()`
    :param start_date: as in `yield_processed_parquet_tiles_by_year()`
    :param end_date: as in `yield_processed_parquet_tiles_by_year()`
    :param asset_id_col: as in `yield_processed_parquet_tiles_by_year()`
    :param price_col: as in `ForecastEvaluatorFromPrices.annotate_forecasts()`
    :param volatility_col: as in `ForecastEvaluatorFromPrices.annotate_forecasts()`
    :param prediction_col: as in `ForecastEvaluatorFromPrices.annotate_forecasts()`
    :param asset_ids: as in `yield_processed_parquet_tiles_by_year()`
    :param annotate_forecasts_kwargs: as in `ForecastEvaluatorFromPrices.annotate_forecasts()`
    :param return_portfolio_df: if `True`, return the
        ForecastEvaluatorFromPrices portfolio in addition to the bar metrics,
        else discard the portfolio (e.g., to reduce memory requirements).
    :param forecast_evaluator: a forecast evaluator object.
    :param optimizer_config_dict: optional configuration dictionary. If
     not None, forecast with optimization.
    :return: (portfolio_df, bar_metrics), unless `return_portfolio_df=False`,
        in which case the first element of the tuple is `None`.
    """
    # Create backtest dataframe tile iterator.
    data_cols = [price_col, volatility_col, prediction_col]
    backtest_df_iter = yield_processed_parquet_tiles_by_year(
        dir_name,
        start_date,
        end_date,
        asset_id_col,
        data_cols=data_cols,
        asset_ids=asset_ids,
    )
    args = [
        price_col,
        volatility_col,
        prediction_col,
    ]
    if optimizer_config_dict is not None:
        args.append(optimizer_config_dict)
    fepo = forecast_evaluator(*args)
    # Process the dataframes in the interator.
    bar_metrics = []
    portfolio_df = []
    for df in backtest_df_iter:
        portfolio_df_slice, bar_metrics_slice = fepo.annotate_forecasts(
            df,
            **annotate_forecasts_kwargs,
        )
        bar_metrics.append(bar_metrics_slice)
        if return_portfolio_df:
            portfolio_df.append(portfolio_df_slice)
        else:
            _ = portfolio_df_slice
    if return_portfolio_df:
        portfolio_df = pd.concat(portfolio_df)
    else:
        portfolio_df = None
    bar_metrics = pd.concat(bar_metrics)
    return portfolio_df, bar_metrics


def evaluate_weighted_forecasts(
    simulations: pd.DataFrame,
    weights: pd.DataFrame,
    market_data_and_volatility: pd.DataFrame,
    start_date: datetime.date,
    end_date: datetime.date,
    asset_id_col: str,
    *,
    asset_ids: Optional[List[int]] = None,
    annotate_forecasts_kwargs: Optional[dict] = None,
    target_freq_str: Optional[str] = None,
    preapply_gaussian_ranking: bool = False,
    index_mode: str = "assert_equal",
) -> pd.DataFrame:
    """
    Mix forecasts with weights and evaluate the portfolio.

    `weights` should look like

    ```
             weights1   weights2   weights3 ...
    sim1
    sim2
    ```

    `market_data_and_volatility` should look like

    ```
                   dir_name              col
    price         dir_name1         col_name
    volatility    dir_name2         col_name
    ```

    :param simulations: df indexed by backtest id; columns are "dir_name" and
        "prediction_col"
    :param weights: df indexed by backtest id; columns are weights
    :param market_data_and_volatility: df with "price" and "volatility" in
        index; columns are "dir_name" and "col"
    :param start_date: start date for tile loading
    :param end_date: end date for tile loading
    :param asset_id_col: name of column with asset ids in tiles
    :param asset_ids: if `None`, select all available
    :param annotate_forecasts_kwargs: options for
        `ForecastEvaluatorFromPrice.annotate_forecasts()`
    :param target_freq_str: if not `None`, resample all forecasts to target
        frequency
    :param preapply_gaussian_ranking: whether to preprocess predictions with
        Gaussian ranking. May be useful if predictions are on different
        scales.
    :param index_mode: same as `mode` in `apply_index_mode()`
    :return: bar metrics dataframe
    """
    forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices(
        "price",
        "volatility",
        "prediction",
    )
    pred_dict_iter = yield_processed_parquet_tile_dict(
        simulations, start_date, end_date, asset_id_col, asset_ids=asset_ids
    )
    #
    hdbg.dassert_isinstance(market_data_and_volatility, pd.DataFrame)
    hdbg.dassert_is_subset(
        ["dir_name", "col"], market_data_and_volatility.columns
    )
    hdbg.dassert(not simulations.index.has_duplicates)
    hdbg.dassert_is_subset(
        ["price", "volatility"], market_data_and_volatility.index
    )
    # Set forecast annotation defaults.
    annotate_forecasts_kwargs = annotate_forecasts_kwargs or {}
    #
    if target_freq_str is not None:
        hdbg.dassert_isinstance(target_freq_str, str)
    # Create volatility time slice iterator.
    vol_dir = market_data_and_volatility.loc["volatility"]["dir_name"]
    vol_col = market_data_and_volatility.loc["volatility"]["col"]
    volatility_iter = yield_processed_parquet_tiles_by_year(
        vol_dir,
        start_date,
        end_date,
        asset_id_col,
        [vol_col],
        asset_ids=asset_ids,
    )
    # Create price time slice iterator.
    price_dir = market_data_and_volatility.loc["price"]["dir_name"]
    price_col = market_data_and_volatility.loc["price"]["col"]
    price_iter = yield_processed_parquet_tiles_by_year(
        price_dir,
        start_date,
        end_date,
        asset_id_col,
        [price_col],
        asset_ids=asset_ids,
    )
    bar_metrics = []
    for dfs in pred_dict_iter:
        volatility = next(volatility_iter)[vol_col]
        price = next(price_iter)[price_col]
        idx = volatility.index
        if target_freq_str is not None:
            bar_length = pd.Series(idx).diff().min()
            _LOG.info("bar_length=%s", bar_length)
            hdbg.dassert_eq(
                bar_length,
                pd.Timedelta(target_freq_str),
                "bar length of market and volatility data must equal `target_freq_str`",
            )
        # Cross-sectionally normalize the predictions.
        for key, val in dfs.items():
            # Resample provided `target_freq_str` is not `None`.
            if target_freq_str is not None:
                # TODO(Paul): Revisit this scale factor.
                # freq = pd.Series(val.index).diff().min()
                # scale_factor = np.sqrt(pd.Timedelta(target_freq_str) / freq)
                val = val.resample(target_freq_str).ffill().reindex(idx)
                val.index = idx
            # Cross-sectionally normalize.
            if preapply_gaussian_ranking:
                val = csigproc.gaussian_rank(val)
            # TODO(Paul): Enable should we set `scale_factor` above.
            # if target_freq_str is not None:
            #     val *= scale_factor
            dfs[key] = val
        bar_metrics_dict = {}
        weighted_sum = hpandas.compute_weighted_sum(
            dfs, weights, index_mode=index_mode
        )
        for key, val in weighted_sum.items():
            df = pd.concat(
                [val, volatility, price],
                axis=1,
                keys=["prediction", "volatility", "price"],
            )
            _, stats = forecast_evaluator.annotate_forecasts(
                df,
                **annotate_forecasts_kwargs,
            )
            bar_metrics_dict[key] = stats
        bar_metrics_df = pd.concat(
            bar_metrics_dict.values(),
            axis=1,
            keys=bar_metrics_dict.keys(),
        )
        bar_metrics.append(bar_metrics_df)
    bar_metrics = pd.concat(bar_metrics)
    return bar_metrics


def compute_forecast_correlations(
    simulations: pd.DataFrame,
    start_date: datetime.date,
    end_date: datetime.date,
    asset_id_col: str,
    *,
    asset_ids: Optional[List[int]] = None,
    target_freq_str: Optional[str] = None,
    preapply_gaussian_ranking: bool = False,
) -> List[pd.DataFrame]:
    """
    Compute per-asset correlations between forecasts and summarize.

    :param simulations: df indexed by backtest id; columns are "dir_name" and
        "prediction_col"
    :param start_date: start date for tile loading
    :param end_date: end date for tile loading
    :param asset_id_col: name of column with asset ids in tiles
    :param asset_ids: if `None`, select all available
    :param target_freq_str: if not `None`, resample all forecasts to target
        frequency
    :param preapply_gaussian_ranking: whether to preprocess predictions with
        Gaussian ranking before calculating correlations.
    :return: list of correlation dataframes
    """
    pred_dict_iter = yield_processed_parquet_tile_dict(
        simulations, start_date, end_date, asset_id_col, asset_ids=asset_ids
    )
    hdbg.dassert(not simulations.index.has_duplicates)
    if target_freq_str is not None:
        hdbg.dassert_isinstance(target_freq_str, str)
    # Compute correlations across all simulations for each dictionary of
    #  predictions in the iterator.
    correlation_dfs = []
    stats_dfs = []
    for dfs in pred_dict_iter:
        correlation_df = pd.DataFrame(
            index=dfs.keys(),
            columns=dfs.keys(),
        )
        stats_df = pd.DataFrame(
            index=dfs.keys(),
            columns=[
                "mean_of_means",
                "mean_of_std",
                "mean_of_skew",
                "mean_of_kurt",
            ],
        )
        for key1, value1 in dfs.items():
            if preapply_gaussian_ranking:
                value1 = csigproc.gaussian_rank(value1)
            for key2, value2 in dfs.items():
                if preapply_gaussian_ranking:
                    value2 = csigproc.gaussian_rank(value2)
                # TODO(Paul): perform a Fisher transformation first, average,
                #  then undo.
                corr = value1.corrwith(value2).mean()
                correlation_df.loc[key1, key2] = corr
            mean_of_means = value1.mean(axis=0).mean()
            mean_of_std = value1.std(axis=0).mean()
            mean_of_skew = value1.skew(axis=0).mean()
            mean_of_kurt = value1.kurt(axis=0).mean()
            stats_df.loc[key1] = (
                mean_of_means,
                mean_of_std,
                mean_of_skew,
                mean_of_kurt,
            )
        correlation_dfs.append(correlation_df)
        stats_dfs.append(stats_df)
    return correlation_dfs, stats_dfs


def process_parquet_read_df(
    df: pd.DataFrame,
    asset_id_col: str,
) -> pd.DataFrame:
    """
    Post-process a multiindex dataflow result dataframe re-read from parquet.

    :param df: dataframe in "long" format
    :param asset_id_col: asset id column to pivot on
    :return: multiindexed dataframe with asset id's at the inner column
        level
    """
    # Convert the asset id column to an integer column.
    df = hpandas.convert_col_to_int(df, asset_id_col)
    # If a (non-asset id) column can be represented as an int, then do so.
    df = df.rename(columns=hparque.maybe_cast_to_int)
    # Convert from long format to column-multiindexed format.
    df = df.pivot(columns=asset_id_col)
    # NOTE: the asset ids may already be sorted and so this may not be needed.
    df.sort_index(axis=1, level=-2, inplace=True)
    return df


def load_mix_evaluate(
    file_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    asset_id_col: str,
    returns_col: str,
    volatility_col: str,
    feature_cols: List[Union[int, str]],
    weights: pd.DataFrame,
    target_gmv: Optional[float] = None,
    dollar_neutrality: str = "no_constraint",
) -> pd.DataFrame:
    """
    Load a tiled backtest, mix features, and evaluate the portfolio.

    :param file_name: as in hparque.yield_parquet_tiles_by_year()
    :param start_date: as in hparque.yield_parquet_tiles_by_year()
    :param end_date: hparque.yield_parquet_tiles_by_year()
    :param asset_id_col: name of asset id column
    :param returns_col: name of realize returns column
    :param volatility_col: name of volatility forecast column
    :param feature_cols: names of predictive feature columns
    :param weights: feature weights, indexed by feature column name; one
        set of weights per column
    :param target_gmv: target gmv for forecast evaluation
    :param dollar_neutrality: dollar neutrality constraint for forecast
        evaluation, e.g.,
    :return: a portfolio bar metrics dataframe (see
        dtfmofomix.get_portfolio_bar_metrics_dataframe() for an
        example).
    """
    hdbg.dassert_isinstance(weights, pd.DataFrame)
    hdbg.dassert_set_eq(weights.index, feature_cols)
    #
    data_cols = [returns_col, volatility_col] + feature_cols
    df_iter = yield_processed_parquet_tiles_by_year(
        file_name,
        start_date,
        end_date,
        asset_id_col,
        data_cols,
    )
    fm = dtfmofomix.ForecastMixer(
        returns_col=returns_col,
        volatility_col=volatility_col,
        prediction_cols=feature_cols,
    )
    results = []
    for df in df_iter:
        bar_metrics = fm.generate_portfolio_bar_metrics_df(
            df,
            weights,
            target_gmv=target_gmv,
            dollar_neutrality=dollar_neutrality,
        )
        results.append(bar_metrics)
    df = pd.concat(results)
    df.sort_index(inplace=True)
    return df


def regress(
    file_name: str,  # TODO(Paul): change to `dir_name`.
    asset_id_col: str,
    target_col: str,
    feature_cols: List[Union[int, str]],
    feature_lag: int,
    batch_size: int,
    *,
    num_autoregression_lags=0,
    sigma_cut: float = 0.0,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Perform per-asset regressions over a tiled backtest.

    For each asset, the regression is performed over the entire time
    window.
    """
    # Perform sanity-checks.
    hdbg.dassert_dir_exists(file_name)
    hdbg.dassert_isinstance(asset_id_col, str)
    hdbg.dassert_isinstance(target_col, str)
    hdbg.dassert_isinstance(feature_cols, list)
    hdbg.dassert_not_in(target_col, feature_cols)
    hdbg.dassert_lt(0, batch_size)
    hdbg.dassert_lte(0, sigma_cut)
    #
    cols = [asset_id_col, target_col] + feature_cols
    parquet_tile_analyzer = dtfmpatian.ParquetTileAnalyzer()
    parquet_tile_metadata = parquet_tile_analyzer.collate_parquet_tile_metadata(
        file_name
    )
    asset_ids = parquet_tile_metadata.index.levels[0].to_list()
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("Num assets=%d", len(asset_ids))
    if num_autoregression_lags > 0:
        lagged_cols = [
            target_col + f"_lag_{lag}"
            for lag in range(0, num_autoregression_lags)
        ]
        feature_cols = feature_cols + lagged_cols
    #
    ra = dtfmoreana.RegressionAnalyzer(
        y_col=target_col,
        x_cols=feature_cols,
        x_col_lag=feature_lag,
    )
    results = []
    corrs = {}
    tile_iter = hparque.yield_parquet_tiles_by_assets(
        file_name,
        asset_ids,
        asset_id_col,
        batch_size,
        cols,
    )
    for tile in tile_iter:
        df = process_parquet_read_df(
            tile,
            asset_id_col,
        )
        if num_autoregression_lags > 0:
            lagged_dfs = {}
            for lag in range(0, num_autoregression_lags):
                col_name = target_col + f"_lag_{lag}"
                lagged_dfs[col_name] = df[target_col].shift(lag)
            lagged_df = pd.concat(
                lagged_dfs.values(), axis=1, keys=lagged_dfs.keys()
            )
            df = df.merge(lagged_df, left_index=True, right_index=True)
        if sigma_cut > 0:
            stdevs = df[feature_cols].std().groupby(level=0).mean()
            for feature_col in feature_cols:
                left_tail = df[feature_col] < -sigma_cut * stdevs[feature_col]
                right_tail = df[feature_col] > sigma_cut * stdevs[feature_col]
                df[feature_col] = df[feature_col][left_tail | right_tail]
        coeffs = ra.compute_regression_coefficients(
            df,
        )
        col_swapped_df = df.swaplevel(axis=1).sort_index(axis=1)
        for col in col_swapped_df.columns.levels[0]:
            corrs[col] = col_swapped_df[col].corr()
        results.append(coeffs)
    df = pd.concat(results)
    df.sort_index(inplace=True)
    corr_df = pd.concat(corrs.values(), axis=0, keys=corrs.keys())
    return df, corr_df


def compute_bar_col_abs_stats(
    file_name: str,
    asset_id_col: str,
    cols: List[str],
    batch_size: int,
) -> pd.DataFrame:
    cols = [asset_id_col] + cols
    parquet_tile_analyzer = dtfmpatian.ParquetTileAnalyzer()
    parquet_tile_metadata = parquet_tile_analyzer.collate_parquet_tile_metadata(
        file_name
    )
    asset_ids = parquet_tile_metadata.index.levels[0].to_list()
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("Num assets=%d", len(asset_ids))
    results = []
    tile_iter = hparque.yield_parquet_tiles_by_assets(
        file_name,
        asset_ids,
        asset_id_col,
        batch_size,
        cols,
    )
    for tile in tile_iter:
        df = process_parquet_read_df(
            tile,
            asset_id_col,
        )
        grouped_df = df.abs().groupby(lambda x: x.time())
        # TODO(Paul): Factor out these manipulations.
        count = grouped_df.count().stack(asset_id_col)
        count = count.swaplevel(axis=0)
        median = grouped_df.median().stack(asset_id_col)
        median = median.swaplevel(axis=0)
        mean = grouped_df.mean().stack(asset_id_col)
        mean = mean.swaplevel(axis=0)
        stdev = grouped_df.std().stack(asset_id_col)
        stdev = stdev.swaplevel(axis=0)
        stats_df = pd.concat(
            [count, median, mean, stdev],
            axis=1,
            keys=["count", "median", "mean", "stdev"],
        )
        results.append(stats_df)
    df = pd.concat(results)
    df.sort_index(inplace=True)
    return df
