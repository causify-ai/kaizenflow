"""
Import as:

import dataflow.model.forecast_evaluator_from_returns as dtfmfefrre
"""

import datetime
import logging
import os
from typing import Optional, Tuple

import numpy as np
import pandas as pd

import core.finance as cofinanc
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


class ForecastEvaluatorFromReturns:
    """
    Evaluate returns/volatility forecasts.
    """

    def __init__(
        self,
        returns_col: str,
        volatility_col: str,
        prediction_col: str,
        *,
        start_time: datetime.time = datetime.time(9, 30),
        end_time: datetime.time = datetime.time(16, 00),
        remove_weekends: bool = False,
    ) -> None:
        """
        Initialize column names.

        Note:
        - the `prediction_col` is a prediction of vol-adjusted returns
        - the `returns_col` is not vol-adjusted
        - by passing `volatility_col` explicitly, we can easily calculate PnL
          at a specified GMV and under a dollar neutrality constraint

        :param returns_col: percentage change of underlying price (not
            volatility adjusted)
        :param volatility_col: volatility used for adjustment of forward returns
        :param prediction_col: prediction of volatility-adjusted returns, two
            steps ahead
        """
        hdbg.dassert_isinstance(returns_col, str)
        self._returns_col = returns_col
        hdbg.dassert_isinstance(volatility_col, str)
        self._volatility_col = volatility_col
        hdbg.dassert_isinstance(prediction_col, str)
        self._prediction_col = prediction_col
        #
        hdbg.dassert_isinstance(start_time, datetime.time)
        self._start_time = start_time
        hdbg.dassert_isinstance(end_time, datetime.time)
        self._end_time = end_time
        #
        self._remove_weekends = remove_weekends

    @staticmethod
    def read_portfolio(
        log_dir: str,
        *,
        file_name: Optional[str] = None,
        tz: str = "America/New_York",
        cast_asset_ids_to_int: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Read and process logged portfolio.

        :param file_name: if `None`, find and use the latest
        """
        if file_name is None:
            dir_name = os.path.join(log_dir, "returns")
            pattern = "*"
            only_files = True
            use_relative_paths = True
            files = hio.listdir(dir_name, pattern, only_files, use_relative_paths)
            files.sort()
            file_name = files[-1]
        returns = ForecastEvaluatorFromReturns._read_df(
            log_dir, "returns", file_name, tz
        )
        volatility = ForecastEvaluatorFromReturns._read_df(
            log_dir, "volatility", file_name, tz
        )
        prediction = ForecastEvaluatorFromReturns._read_df(
            log_dir, "prediction", file_name, tz
        )
        positions = ForecastEvaluatorFromReturns._read_df(
            log_dir, "position", file_name, tz
        )
        pnl = ForecastEvaluatorFromReturns._read_df(log_dir, "pnl", file_name, tz)
        if cast_asset_ids_to_int:
            for df in [returns, volatility, prediction, positions, pnl]:
                ForecastEvaluatorFromReturns._cast_cols_to_int(df)
        portfolio_df = ForecastEvaluatorFromReturns._build_multiindex_df(
            returns,
            volatility,
            prediction,
            positions,
            pnl,
        )
        statistics_df = ForecastEvaluatorFromReturns._read_df(
            log_dir, "statistics", file_name, tz
        )
        return portfolio_df, statistics_df

    def to_str(
        self,
        df: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
    ) -> str:
        """
        Return the state of the Portfolio in terms of the holdings as a string.

        :param df: as in `compute_portfolio`
        :param target_gmv: as in `compute_portfolio`
        :param dollar_neutrality: as in `compute_portfolio`
        """
        target_positions, pnl, stats = self.compute_portfolio(
            df,
            target_gmv=target_gmv,
            dollar_neutrality=dollar_neutrality,
        )
        act = []
        round_precision = 6
        precision = 2
        act.append(
            "# holdings marked to market=\n%s"
            % hpandas.df_to_str(
                target_positions.round(round_precision),
                num_rows=None,
                precision=precision,
            )
        )
        act.append(
            "# pnl=\n%s"
            % hpandas.df_to_str(
                pnl.round(round_precision),
                num_rows=None,
                precision=precision,
            )
        )
        act.append(
            "# statistics=\n%s"
            % hpandas.df_to_str(
                stats.round(round_precision), num_rows=None, precision=precision
            )
        )
        act = "\n".join(act)
        return act

    def log_portfolio(
        self,
        df: pd.DataFrame,
        log_dir: str,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
        reindex_like_input: bool = False,
    ) -> str:
        hdbg.dassert(log_dir, "Must specify `log_dir` to log portfolio.")
        positions, pnl, statistics = self.compute_portfolio(
            df,
            target_gmv=target_gmv,
            dollar_neutrality=dollar_neutrality,
            reindex_like_input=reindex_like_input,
        )
        last_timestamp = df.index[-1]
        hdbg.dassert_isinstance(last_timestamp, pd.Timestamp)
        last_time_str = last_timestamp.strftime("%Y%m%d_%H%M%S")
        file_name = f"{last_time_str}.csv"
        #
        ForecastEvaluatorFromReturns._write_df(
            df[self._returns_col], log_dir, "returns", file_name
        )
        ForecastEvaluatorFromReturns._write_df(
            df[self._volatility_col], log_dir, "volatility", file_name
        )
        ForecastEvaluatorFromReturns._write_df(
            df[self._prediction_col], log_dir, "prediction", file_name
        )
        ForecastEvaluatorFromReturns._write_df(
            positions, log_dir, "position", file_name
        )
        ForecastEvaluatorFromReturns._write_df(pnl, log_dir, "pnl", file_name)
        ForecastEvaluatorFromReturns._write_df(
            statistics, log_dir, "statistics", file_name
        )
        return file_name

    def compute_portfolio(
        self,
        df: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
        reindex_like_input: bool = False,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Compute target positions, PnL, and portfolio stats.

        :param df: multiindexed dataframe with predictions, returns, volatility
        :param target_gmv: if `None`, then GMV may float
        :param dollar_neutrality: enforce a hard dollar neutrality constraint
        :param reindex_like_input: output dataframes to have the same input as
            `df` (e.g., including any weekends or values outside of the
            `start_time`-`end_time` range)
        :return: (positions, pnl, stats)
        """
        self._validate_df(df)
        # Record index in case we reindex the results.
        if reindex_like_input:
            idx = df.index
        # Remove weekends if enabled.
        if self._remove_weekends:
            df = cofinanc.remove_weekends(df)
        # Filter dateframe by time.
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "Filtering to data between time %s and %s",
                self._start_time,
                self._end_time,
            )
        df = df.between_time(self._start_time, self._end_time)
        # Compute naive dollar value risk-adjusted positions.
        returns_predictions = ForecastEvaluatorFromReturns._get_df(
            df, self._prediction_col
        )
        volatility = ForecastEvaluatorFromReturns._get_df(
            df, self._volatility_col
        )
        # The values of`target_positions` represent cash values.
        target_positions = returns_predictions.divide(volatility)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug(
                "target_positions=\n%s",
                hpandas.df_to_str(target_positions, num_rows=None),
            )
        target_positions = ForecastEvaluatorFromReturns._apply_dollar_neutrality(
            target_positions, dollar_neutrality
        )
        target_positions = ForecastEvaluatorFromReturns._apply_gmv_scaling(
            target_positions, target_gmv
        )
        returns = ForecastEvaluatorFromReturns._get_df(df, self._returns_col)
        pnl = target_positions.shift(2).multiply(returns)
        # Compute statistics.
        stats = self._compute_statistics(target_positions, pnl)
        # Convert one-step-ahead target positions to "point-in-time"
        # (hypothetically) realized positions.
        positions = target_positions.shift(1)
        # Possibly reindex dataframes.
        if reindex_like_input:
            positions = positions.reindex(idx)
            pnl = pnl.reindex(idx)
            stats = stats.reindex(idx)
        return positions, pnl, stats

    def annotate_forecasts(
        self,
        df: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
        reindex_like_input: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Wraps `compute_portfolio()`, returns a single multiindexed dataframe.

        :param df: as in `compute_portfolio()`
        :param target_gmv: as in `compute_portfolio()`
        :param dollar_neutrality: as in `compute_portfolio()`
        :return: multiindexed dataframe with level-0 columns "returns",
            "volatility", "prediction", "position", "pnl"
        """
        positions, pnl, statistics_df = self.compute_portfolio(
            df,
            target_gmv=target_gmv,
            dollar_neutrality=dollar_neutrality,
            reindex_like_input=reindex_like_input,
        )
        portfolio_df = ForecastEvaluatorFromReturns._build_multiindex_df(
            df[self._returns_col],
            df[self._volatility_col],
            df[self._prediction_col],
            positions,
            pnl,
        )
        return portfolio_df, statistics_df

    def compute_overnight_pnl(
        self,
        df: pd.DataFrame,
        overnight_returns: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """ """
        positions, _, _ = self.compute_portfolio(
            df, target_gmv=target_gmv, dollar_neutrality=dollar_neutrality
        )
        start_loc = positions.index.min()
        end_loc = positions.index.max()
        # TODO(Paul): Take into account half days.
        positions = positions.between_time(self._end_time, self._end_time)
        hdbg.dassert(not positions.empty)
        #
        hdbg.dassert_isinstance(overnight_returns, pd.DataFrame)
        hdbg.dassert_isinstance(overnight_returns.index, pd.DatetimeIndex)
        hdbg.dassert_eq(overnight_returns.columns.nlevels, 1)
        # TODO(Paul): Check that the only time is `start_time`.
        max_num_dates = (
            overnight_returns.groupby(lambda x: x.date()).count().max().max()
        )
        hdbg.dassert_eq(max_num_dates, 1)
        num_times = overnight_returns.groupby(lambda x: x.time()).ngroups
        hdbg.dassert_eq(num_times, 1)
        # Restrict overnight returns to index range of `df`.
        overnight_returns = overnight_returns.loc[start_loc:end_loc]
        idx = positions.index.union(overnight_returns.index)
        positions = positions.reindex(index=idx)
        positions = positions.shift().dropna(how="all")
        pnl = positions.multiply(overnight_returns)
        stats = pd.DataFrame(
            {
                "pnl": pnl.sum(axis=1, min_count=1),
                "gross_volume": 0,
                "net_volume": 0,
                "gmv": positions.abs().sum(axis=1, min_count=1),
                "nmv": positions.sum(axis=1, min_count=1),
            }
        )
        return pnl, stats

    @staticmethod
    def _build_multiindex_df(
        returns_df: pd.DataFrame,
        volatility_df: pd.DataFrame,
        prediction_df: pd.DataFrame,
        position_df: pd.DataFrame,
        pnl_df: pd.DataFrame,
    ) -> pd.DataFrame:
        dfs = {
            "returns": returns_df,
            "volatility": volatility_df,
            "prediction": prediction_df,
            "position": position_df,
            "pnl": pnl_df,
        }
        portfolio_df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
        return portfolio_df

    @staticmethod
    def _cast_cols_to_int(
        df: pd.DataFrame,
    ) -> None:
        # If integers are converted to floats and then strings, then upon
        # being read they must be cast to floats before being cast to ints.
        df.columns = df.columns.astype("float64").astype("int64")

    @staticmethod
    def _write_df(
        df: pd.DataFrame,
        log_dir: str,
        name: str,
        file_name: str,
    ) -> None:
        path = os.path.join(log_dir, name, file_name)
        hio.create_enclosing_dir(path, incremental=True)
        df.to_csv(path)

    @staticmethod
    def _read_df(
        log_dir: str,
        name: str,
        file_name: str,
        tz: str,
    ) -> pd.DataFrame:
        path = os.path.join(log_dir, name, file_name)
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index = df.index.tz_convert(tz)
        return df

    @staticmethod
    def _apply_dollar_neutrality(
        target_positions: pd.DataFrame,
        dollar_neutrality: str,
    ) -> pd.DataFrame:
        hdbg.dassert_isinstance(dollar_neutrality, str)
        if dollar_neutrality == "no_constraint":
            pass
        elif dollar_neutrality == "demean":
            # Cross-sectionally demean signals on a per-bar basis.
            # This is equivalent to a dollar neutralizing linear projection.
            hdbg.dassert_lt(
                1,
                target_positions.shape[1],
                "Unable to enforce dollar neutrality with a single asset.",
            )
            net_asset_value = target_positions.mean(axis=1)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "net asset value=\n%s"
                    % hpandas.df_to_str(net_asset_value, num_rows=None)
                )
            target_positions = target_positions.subtract(net_asset_value, axis=0)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "dollar neutral target_positions=\n%s"
                    % hpandas.df_to_str(target_positions, num_rows=None)
                )
        elif dollar_neutrality == "side_preserving":
            # This method will not flip the sign of a prediction.
            # Note that in the event that all input signals are on the same
            #  side, this method will raise.
            hdbg.dassert_lt(
                1,
                target_positions.shape[1],
                "Unable to enforce dollar neutrality with a single asset.",
            )
            # Track long and short market exposures separately.
            positive_asset_value = target_positions.clip(lower=0).sum(axis=1)
            negative_asset_value = -1 * target_positions.clip(upper=0).sum(axis=1)
            min_sided_asset_value = np.minimum(
                positive_asset_value, negative_asset_value
            )
            hdbg.dassert_isinstance(positive_asset_value, pd.Series)
            hdbg.dassert_isinstance(negative_asset_value, pd.Series)
            hdbg.dassert_isinstance(min_sided_asset_value, pd.Series)
            # Downscale the side with more exposure to the same amount as the
            # side with less.
            positive_scale_factor = min_sided_asset_value.divide(
                positive_asset_value
            )
            negative_scale_factor = min_sided_asset_value.divide(
                negative_asset_value
            )
            positive_positions = target_positions.clip(lower=0).multiply(
                positive_scale_factor, axis=0
            )
            negative_positions = target_positions.clip(upper=0).multiply(
                negative_scale_factor, axis=0
            )
            # Reassemble the rescaled long and short positions.
            target_positions = positive_positions.add(negative_positions)
        else:
            raise ValueError(
                "Unrecognized option `dollar_neutrality`=%s" % dollar_neutrality
            )
        return target_positions

    @staticmethod
    def _apply_gmv_scaling(
        target_positions: pd.DataFrame,
        target_gmv: Optional[float],
    ) -> pd.DataFrame:
        if target_gmv is not None:
            hdbg.dassert_lt(0, target_gmv)
            l1_norm = target_positions.abs().sum(axis=1, min_count=1)
            scale_factor = l1_norm / target_gmv
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "scale factor=\n%s",
                    hpandas.df_to_str(scale_factor, num_rows=None),
                )
            target_positions = target_positions.divide(scale_factor, axis=0)
            if _LOG.isEnabledFor(logging.DEBUG):
                _LOG.debug(
                    "gmv scaled target_positions=\n%s",
                    hpandas.df_to_str(target_positions, num_rows=None),
                )
        return target_positions

    @staticmethod
    def _compute_statistics(
        target_positions: pd.DataFrame,
        pnl: pd.DataFrame,
    ) -> pd.DataFrame:
        positions = target_positions.shift(1)
        # Gross market value (gross exposure).
        gmv = positions.abs().sum(axis=1, min_count=1)
        # Net market value (net asset value or net exposure).
        nmv = positions.sum(axis=1, min_count=1)
        # This is an approximation that does not take into account returns.
        traded_volume = positions.diff()
        # Absolute volume traded.
        gross_volume = traded_volume.abs().sum(axis=1, min_count=1)
        # Net volume traded.
        net_volume = traded_volume.sum(axis=1, min_count=1)
        # Aggregated PnL.
        portfolio_pnl = pnl.sum(axis=1, min_count=1)
        stats = pd.DataFrame(
            {
                "pnl": portfolio_pnl,
                "gross_volume": gross_volume,
                "net_volume": net_volume,
                "gmv": gmv,
                "nmv": nmv,
            }
        )
        return stats

    @staticmethod
    def _get_df(df: pd.DataFrame, col: str) -> pd.DataFrame:
        hdbg.dassert_in(col, df.columns)
        return df[col]

    def _validate_df(self, df: pd.DataFrame) -> None:
        hpandas.dassert_time_indexed_df(
            df, allow_empty=True, strictly_increasing=True
        )
        hdbg.dassert_eq(df.columns.nlevels, 2)
        hdbg.dassert_is_subset(
            [self._returns_col, self._volatility_col, self._prediction_col],
            df.columns.levels[0].to_list(),
        )
