"""
Import as:

import dataflow.model.forecast_evaluator_from_prices as dtfmfefrpr
"""

import datetime
import logging
import os
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import sklearn

import core.finance as cofinanc
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


class ForecastEvaluatorFromPrices:
    """
    Evaluate returns/volatility forecasts.
    """

    def __init__(
        self,
        price_col: str,
        volatility_col: str,
        prediction_col: str,
        *,
        first_bar_of_day_open: datetime.time = datetime.time(9, 30),
        first_bar_of_day_close: datetime.time = datetime.time(9, 45),
        last_bar_of_day_close: datetime.time = datetime.time(16, 00),
        remove_weekends: bool = True,
    ) -> None:
        """
        Initialize column names.

        Note:
        - the `prediction_col` is a prediction of vol-adjusted returns
        - the `price_col` is unadjusted
        - by passing `volatility_col` explicitly, we can easily calculate PnL
          at a specified GMV and under a dollar neutrality constraint

        :param price_col: price per share
        :param volatility_col: volatility used for adjustment of forward returns
        :param prediction_col: prediction of volatility-adjusted returns, two
            steps ahead
        """
        # Initialize dataframe columns.
        hdbg.dassert_isinstance(price_col, str)
        self._price_col = price_col
        hdbg.dassert_isinstance(volatility_col, str)
        self._volatility_col = volatility_col
        hdbg.dassert_isinstance(prediction_col, str)
        self._prediction_col = prediction_col
        #
        hdbg.dassert_isinstance(first_bar_of_day_open, datetime.time)
        self._first_bar_of_day_open = first_bar_of_day_open
        hdbg.dassert_isinstance(first_bar_of_day_close, datetime.time)
        self._first_bar_of_day_close = first_bar_of_day_close
        hdbg.dassert_isinstance(last_bar_of_day_close, datetime.time)
        self._last_bar_of_day_close = last_bar_of_day_close
        #
        self._remove_weekends = remove_weekends

    def to_str(
        self,
        df: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
        quantization: str = "no_quantization",
    ) -> str:
        """
        Return the state of the Portfolio in terms of the holdings as a string.

        :param df: as in `compute_portfolio`
        :param target_gmv: as in `compute_portfolio`
        :param dollar_neutrality: as in `compute_portfolio`
        """
        holdings, positions, flows, pnl, stats = self.compute_portfolio(
            df,
            target_gmv=target_gmv,
            dollar_neutrality=dollar_neutrality,
            quantization=quantization,
        )
        act = []
        round_precision = 6
        precision = 2
        act.append(
            "# holdings=\n%s"
            % hpandas.df_to_str(
                holdings.round(round_precision),
                num_rows=None,
                precision=precision,
            )
        )
        act.append(
            "# holdings marked to market=\n%s"
            % hpandas.df_to_str(
                positions.round(round_precision),
                num_rows=None,
                precision=precision,
            )
        )
        act.append(
            "# flows=\n%s"
            % hpandas.df_to_str(
                flows.round(round_precision),
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
        quantization: str = "no_quantization",
        reindex_like_input: bool = False,
    ) -> str:
        hdbg.dassert(log_dir, "Must specify `log_dir` to log portfolio.")
        holdings, position, flow, pnl, statistics = self.compute_portfolio(
            df,
            target_gmv=target_gmv,
            dollar_neutrality=dollar_neutrality,
            quantization=quantization,
            reindex_like_input=reindex_like_input,
        )
        last_timestamp = df.index[-1]
        hdbg.dassert_isinstance(last_timestamp, pd.Timestamp)
        last_time_str = last_timestamp.strftime("%Y%m%d_%H%M%S")
        file_name = f"{last_time_str}.csv"
        #
        ForecastEvaluatorFromPrices._write_df(
            df[self._price_col], log_dir, "price", file_name
        )
        ForecastEvaluatorFromPrices._write_df(
            df[self._volatility_col], log_dir, "volatility", file_name
        )
        ForecastEvaluatorFromPrices._write_df(
            df[self._prediction_col], log_dir, "prediction", file_name
        )
        ForecastEvaluatorFromPrices._write_df(
            holdings, log_dir, "holdings", file_name
        )
        ForecastEvaluatorFromPrices._write_df(
            position, log_dir, "position", file_name
        )
        ForecastEvaluatorFromPrices._write_df(flow, log_dir, "flow", file_name)
        ForecastEvaluatorFromPrices._write_df(pnl, log_dir, "pnl", file_name)
        ForecastEvaluatorFromPrices._write_df(
            statistics, log_dir, "statistics", file_name
        )
        return file_name

    def compute_portfolio(
        self,
        df: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
        quantization: str = "no_quantization",
        reindex_like_input: bool = False,
    ) -> Tuple[
        pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame
    ]:
        """
        Compute target positions, PnL, and portfolio stats.

        :param df: multiindexed dataframe with predictions, returns, volatility
        :param target_gmv: if `None`, then GMV may float
        :param dollar_neutrality: enforce a hard dollar neutrality constraint
        :param reindex_like_input: output dataframes to have the same input as
            `df` (e.g., including any weekends or values outside of the
            `start_time`-`end_time` range)
        :param quantization: indicate whether to round to nearest share, lot
        :return: (holdings, position, flow, pnl, stats)
        """
        self._validate_df(df)
        # Record index in case we reindex the results.
        if reindex_like_input:
            idx = df.index
        df = self._apply_trimming(df)
        # Extract prediction and volatility dataframes.
        prediction_df = ForecastEvaluatorFromPrices._get_df(
            df, self._prediction_col
        )
        volatility_df = ForecastEvaluatorFromPrices._get_df(
            df, self._volatility_col
        )
        # The values of`target_positions` represent cash values.
        target_positions = (
            ForecastEvaluatorFromPrices._compute_target_positions_from_forecasts(
                volatility_df,
                prediction_df,
                target_gmv=target_gmv,
                dollar_neutrality=dollar_neutrality,
            )
        )
        # Compute target holdings.
        price_df = ForecastEvaluatorFromPrices._get_df(df, self._price_col)
        holdings, flows = self._compute_holdings_and_flows(
            price_df, target_positions, quantization=quantization
        )
        # Current positions in dollars.
        positions = holdings.multiply(price_df)
        pnl = positions.diff().add(flows, fill_value=0)
        # Compute statistics.
        stats = self._compute_statistics(positions, flows, pnl)
        # Convert one-step-ahead target positions to "point-in-time"
        # (hypothetically) realized positions.
        # Possibly reindex dataframes.
        if reindex_like_input:
            holdings = holdings.reindex(idx)
            positions = positions.reindex(idx)
            flows = flows.reindex(idx)
            pnl = pnl.reindex(idx)
            stats = stats.reindex(idx)
        return holdings, positions, flows, pnl, stats

    def annotate_forecasts(
        self,
        df: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
        quantization: str = "no_quantization",
        reindex_like_input: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Wraps `compute_portfolio()`, returns a single multiindexed dataframe.

        :param df: as in `compute_portfolio()`
        :param target_gmv: as in `compute_portfolio()`
        :param dollar_neutrality: as in `compute_portfolio()`
        :return: multiindexed dataframe with level-0 columns
            "returns", "volatility", "prediction", "position", "pnl"
        """
        holdings, position, flow, pnl, statistics_df = self.compute_portfolio(
            df,
            target_gmv=target_gmv,
            dollar_neutrality=dollar_neutrality,
            quantization=quantization,
            reindex_like_input=reindex_like_input,
        )
        portfolio_df = ForecastEvaluatorFromPrices._build_multiindex_df(
            df[self._price_col],
            df[self._volatility_col],
            df[self._prediction_col],
            holdings,
            position,
            flow,
            pnl,
        )
        return portfolio_df, statistics_df

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
            dir_name = os.path.join(log_dir, "price")
            pattern = "*"
            only_files = True
            file_paths = hio.listdir(dir_name, pattern, only_files)
            # Remove directory paths and leave relative file paths.
            files = [file_path.lstrip(dir_name) for file_path in file_paths]
            files.sort()
            file_name = files[-1]
        price = ForecastEvaluatorFromPrices._read_df(
            log_dir, "price", file_name, tz
        )
        volatility = ForecastEvaluatorFromPrices._read_df(
            log_dir, "volatility", file_name, tz
        )
        predictions = ForecastEvaluatorFromPrices._read_df(
            log_dir, "prediction", file_name, tz
        )
        holdings = ForecastEvaluatorFromPrices._read_df(
            log_dir, "holdings", file_name, tz
        )
        positions = ForecastEvaluatorFromPrices._read_df(
            log_dir, "position", file_name, tz
        )
        flows = ForecastEvaluatorFromPrices._read_df(
            log_dir, "flow", file_name, tz
        )
        pnl = ForecastEvaluatorFromPrices._read_df(log_dir, "pnl", file_name, tz)
        if cast_asset_ids_to_int:
            for df in [
                price,
                volatility,
                predictions,
                holdings,
                positions,
                flows,
                pnl,
            ]:
                ForecastEvaluatorFromPrices._cast_cols_to_int(df)
        portfolio_df = ForecastEvaluatorFromPrices._build_multiindex_df(
            price,
            volatility,
            predictions,
            holdings,
            positions,
            flows,
            pnl,
        )
        statistics_df = ForecastEvaluatorFromPrices._read_df(
            log_dir, "statistics", file_name, tz
        )
        return portfolio_df, statistics_df

    def _validate_df(self, df: pd.DataFrame) -> None:
        hdbg.dassert_isinstance(df, pd.DataFrame)
        hdbg.dassert_isinstance(df.index, pd.DatetimeIndex)
        hpandas.dassert_strictly_increasing_index(df)
        hdbg.dassert_eq(df.columns.nlevels, 2)
        hdbg.dassert_is_subset(
            [self._price_col, self._volatility_col, self._prediction_col],
            df.columns.levels[0].to_list(),
        )

    @staticmethod
    def _build_multiindex_df(
        price: pd.DataFrame,
        volatility: pd.DataFrame,
        prediction: pd.DataFrame,
        holdings: pd.DataFrame,
        position: pd.DataFrame,
        flow: pd.DataFrame,
        pnl: pd.DataFrame,
    ) -> pd.DataFrame:
        dfs = {
            "price": price,
            "volatility": volatility,
            "prediction": prediction,
            "holdings": holdings,
            "position": position,
            "flow": flow,
            "pnl": pnl,
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

    def _apply_trimming(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Trim `df` according to ATH, weekends, missing data.
        """
        # Restrict to required columns.
        df = df[[self._price_col, self._volatility_col, self._prediction_col]]
        # Remove weekends if enabled.
        if self._remove_weekends:
            df = cofinanc.remove_weekends(df)
        # Filter dateframe by time.
        _LOG.debug(
            "Filtering to data between time %s and %s",
            self._first_bar_of_day_open,
            self._last_bar_of_day_close,
        )
        df = df.between_time(
            self._first_bar_of_day_open, self._last_bar_of_day_close
        )
        # Drop rows with no prices (this is an approximate way to handle half-days).
        df = df.dropna(how="all")
        return df

    def _compute_holdings_and_flows(
        self,
        price: pd.DataFrame,
        target_positions: pd.DataFrame,
        *,
        quantization: str = "no_quantization",
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Compute holdings in shares from price and dollar position targets.
        """
        # NOTE: We pull prices from the next bar to handle overnight splits
        # more easily. The intraday price difference is unlikely to make a
        # difference with respect to trading, at least post-quantization.
        price_shift = -1
        target_holdings = target_positions.divide(price.shift(price_shift))
        target_holdings = ForecastEvaluatorFromPrices._apply_quantization(
            target_holdings, quantization
        )
        # Compute first approximation of current holdings in shares.
        holdings = target_holdings.shift(1)
        # Handle overnight period.
        first_bar_of_day_close_idx = holdings.index.indexer_between_time(
            start_time=self._first_bar_of_day_close,
            end_time=self._first_bar_of_day_close,
        )
        holdings.iloc[first_bar_of_day_close_idx] = np.nan
        # Compute first approximation of positions in dollars, excluding the
        # first bar of the day.
        positions = holdings.multiply(price)
        # Forward fill the dollar positions to estimate next-day first bar
        # holdings.
        ffill_positions = positions.ffill()
        holdings = ffill_positions.divide(price)
        # Re-quantize (to quantize first-bar holdings).
        # NOTE: We have estimated the beginning-of-day share holdings based on
        # previous day holdings in dollars and next day end-of-opening bar
        # price. This enables us to approximately handle corporate actions, but
        # at the cost of mitigating the impact of large overnight price
        # movements.
        holdings = ForecastEvaluatorFromPrices._apply_quantization(
            holdings, quantization
        )
        # Change in shares priced at end of bar. Only valid intraday.
        flows = -1 * holdings.subtract(holdings.shift(1), fill_value=0).multiply(
            price
        )
        # Set the overnight flow to zero (since we do not trade and since
        # the share count may change due to corporate actions).
        first_bar_of_day_close_idx = flows.index.indexer_between_time(
            start_time=self._first_bar_of_day_close,
            end_time=self._first_bar_of_day_close,
        )
        flows.iloc[first_bar_of_day_close_idx] = np.nan
        return holdings, flows

    @staticmethod
    def _compute_target_positions_from_forecasts(
        volatility: pd.DataFrame,
        predictions: pd.DataFrame,
        *,
        target_gmv: Optional[float] = None,
        dollar_neutrality: str = "no_constraint",
    ) -> pd.DataFrame:
        """
        Compute target dollar positions based on forecasts, basic constraints.
        """
        target_positions = predictions.divide(volatility)
        _LOG.debug(
            "target_positions=\n%s",
            hpandas.df_to_str(target_positions, num_rows=None),
        )
        target_positions = ForecastEvaluatorFromPrices._apply_dollar_neutrality(
            target_positions, dollar_neutrality
        )
        target_positions = ForecastEvaluatorFromPrices._apply_gmv_scaling(
            target_positions, target_gmv
        )
        return target_positions

    @staticmethod
    def _apply_dollar_neutrality(
        target_positions: pd.DataFrame,
        dollar_neutrality: str,
    ) -> pd.DataFrame:
        hdbg.dassert_isinstance(dollar_neutrality, str)
        if dollar_neutrality == "no_constraint":
            pass
        elif dollar_neutrality == "gaussian_rank":
            quantile_transformer = sklearn.preprocessing.QuantileTransformer(
                n_quantiles=200,
                output_distribution="normal",
            )
            vals = quantile_transformer.fit_transform(target_positions.T.values).T
            target_positions = pd.DataFrame(
                vals,
                target_positions.index,
                target_positions.columns,
            )
        elif dollar_neutrality == "demean":
            # Cross-sectionally demean signals on a per-bar basis.
            # This is equivalent to a dollar neutralizing linear projection.
            hdbg.dassert_lt(
                1,
                target_positions.shape[1],
                "Unable to enforce dollar neutrality with a single asset.",
            )
            net_asset_value = target_positions.mean(axis=1)
            _LOG.debug(
                "net asset value=\n%s"
                % hpandas.df_to_str(net_asset_value, num_rows=None)
            )
            target_positions = target_positions.subtract(net_asset_value, axis=0)
            _LOG.debug(
                "dollar neutral target_positions=\n%s"
                % hpandas.df_to_str(target_positions, num_rows=None)
            )
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
            _LOG.debug(
                "scale factor=\n%s",
                hpandas.df_to_str(scale_factor, num_rows=None),
            )
            target_positions = target_positions.divide(scale_factor, axis=0)
            _LOG.debug(
                "gmv scaled target_positions=\n%s",
                hpandas.df_to_str(target_positions, num_rows=None),
            )
        return target_positions

    @staticmethod
    def _apply_quantization(
        holdings: pd.DataFrame,
        quantization: str,
    ) -> pd.DataFrame:
        if quantization == "no_quantization":
            pass
        elif quantization == "nearest_share":
            holdings = np.rint(holdings)
        elif quantization == "nearest_lot":
            holdings = 100 * np.rint(holdings / 100)
        else:
            raise ValueError(f"Invalid quantization strategy `{quantization}`")
        return holdings

    @staticmethod
    def _compute_statistics(
        positions: pd.DataFrame,
        flows: pd.DataFrame,
        pnl: pd.DataFrame,
    ) -> pd.DataFrame:
        # Gross market value (gross exposure).
        gmv = positions.abs().sum(axis=1, min_count=1)
        # Net market value (net asset value or net exposure).
        nmv = positions.sum(axis=1, min_count=1)
        # This is an approximation that does not take into account returns.
        traded_volume = -1 * flows
        # Absolute volume traded.
        gross_volume = flows.abs().sum(axis=1, min_count=1)
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
