"""
Import as:

import dataflow.model.abstract_forecast_evaluator as dtfmabfoev
"""

import abc
import logging
import os
from typing import Any, Dict, Optional, Tuple

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hparquet as hparque

_LOG = logging.getLogger(__name__)


class AbstractForecastEvaluator(abc.ABC):
    def __init__(
        self,
        price_col: str,
        volatility_col: str,
        prediction_col: str,
    ) -> None:
        """
        Construct Abstract with necessary dataframe columns.

        :param price_col: price per share
            - the `price_col` is unadjusted price (no adjustment for splits,
              dividends, or volatility); it is used for marking to market and,
              unless buy/sell prices columns are also supplied, execution
              simulation
        :param volatility_col: volatility used for adjustment of forward returns
            - the `volatility_col` is used for position sizing
        :param prediction_col: prediction of volatility-adjusted returns, two
            steps ahead
            - the `prediction_col` is a prediction of vol-adjusted returns
              (presumably with volatility given by `volatility_col`)
        """
        # Initialize dataframe columns.
        hdbg.dassert_isinstance(price_col, str)
        self._price_col = price_col
        #
        hdbg.dassert_isinstance(volatility_col, str)
        self._volatility_col = volatility_col
        #
        hdbg.dassert_isinstance(prediction_col, str)
        self._prediction_col = prediction_col

    def save_portfolio(
        self,
        df: pd.DataFrame,
        log_dir: str,
        **kwargs: Dict[str, Any],
    ) -> str:
        """
        Save portfolio state to the file system.

        The dir structure of the data output is:
        ```
        - holdings_shares
        - holdings_notional
        - executed_trades_shares
        - executed_trades_notional
        - pnl
        - prediction
        - price
        - statistics
        - volatility
        ```

        :param df: as in `compute_portfolio()`
        :param log_dir: directory for writing log files of portfolio state
        :param kwargs: forwarded to `compute_portfolio()`
        :return: name of log files with timestamp, e.g.
            '20240131_000000.parquet'
        """
        hdbg.dassert(log_dir, "Must specify `log_dir` to log portfolio.")
        derived_dfs = self.compute_portfolio(
            df,
            **kwargs,
        )
        hdbg.dassert_lte(1, df.shape[1])
        last_timestamp = df.index[-1]
        hdbg.dassert_isinstance(last_timestamp, pd.Timestamp)
        last_timestamp_str = last_timestamp.strftime("%Y%m%d_%H%M%S")
        file_name = f"{last_timestamp_str}.parquet"
        #
        self._write_df(df[self._price_col], log_dir, "price", file_name)
        self._write_df(df[self._volatility_col], log_dir, "volatility", file_name)
        self._write_df(df[self._prediction_col], log_dir, "prediction", file_name)
        self._write_df(
            derived_dfs["holdings_shares"], log_dir, "holdings_shares", file_name
        )
        self._write_df(
            derived_dfs["holdings_notional"],
            log_dir,
            "holdings_notional",
            file_name,
        )
        self._write_df(
            derived_dfs["executed_trades_shares"],
            log_dir,
            "executed_trades_shares",
            file_name,
        )
        self._write_df(
            derived_dfs["executed_trades_notional"],
            log_dir,
            "executed_trades_notional",
            file_name,
        )
        self._write_df(derived_dfs["pnl"], log_dir, "pnl", file_name)
        self._write_df(derived_dfs["stats"], log_dir, "statistics", file_name)
        return file_name

    def to_str(
        self,
        df: pd.DataFrame,
        **kwargs: Dict[str, Any],
    ) -> str:
        """
        Return the state of the Portfolio as a string.

        :param df: as in `compute_portfolio`
        :param kwargs: forwarded to `compute_portfolio()`
        :return: portfolio state (rounded) as a string
        """
        dfs = self.compute_portfolio(
            df,
            **kwargs,
        )
        #
        act = []
        round_precision = 6
        precision = 2

        def _append_col_to_str(dfs: pd.DataFrame, col: str) -> None:
            """
            Append a portfolio dataframe to the string output.
            """
            act.append(f"# {col}=")
            act.append(
                hpandas.df_to_str(
                    dfs[col].round(round_precision),
                    handle_signed_zeros=True,
                    num_rows=None,
                    precision=precision,
                    log_level=logging.INFO,
                )
            )

        _append_col_to_str(dfs, "holdings_shares")
        _append_col_to_str(dfs, "holdings_notional")
        _append_col_to_str(dfs, "executed_trades_shares")
        _append_col_to_str(dfs, "executed_trades_notional")
        _append_col_to_str(dfs, "pnl")
        # Append `statistics` dataframe.
        # TODO(Danya): not using `_append_col_to_str` since label "statistics"
        # used in tests for ForecastSystems is not equal to the DF label.
        act.append(f"# statistics=")
        act.append(
            hpandas.df_to_str(
                dfs["stats"].round(round_precision),
                handle_signed_zeros=True,
                num_rows=None,
                precision=precision,
                log_level=logging.INFO,
            )
        )
        act = "\n".join(act)
        return act

    def compute_portfolio(
        self, df: pd.DataFrame, **kwargs: Any
    ) -> Dict[str, pd.DataFrame]:
        """
        Compute target positions, PnL, and portfolio stats.

        The actual implementation is delegated to `_compute_portfolio()`
        in the subclasses.

        :param df: multiindexed dataframe with predictions, price,
            volatility :param **kwargs: kwargs for the particular
            implementation of the portfolio.
        """
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("df=\n%s", hpandas.df_to_str(df, print_shape_info=True))
        self._validate_df(df)
        # Trim to indices with prices and beginning of forecast availability.
        df = self._apply_trimming(df)
        return self._compute_portfolio(df, **kwargs)

    @classmethod
    def load_portfolio(
        self,
        log_dir: str,
        *,
        file_name: Optional[str] = None,
        tz: str = "America/New_York",
        cast_asset_ids_to_int: bool = True,
    ) -> pd.DataFrame:
        """
        Load and process saved portfolio.

        :param log_dir: directory for loading log files of portfolio state
        :param file_name: if `None`, find and use the latest
        :param tz: timezone to apply to timestamps (this information is lost in
            the logging/reading round trip)
        :param cast_asset_ids_to_int: cast asset ids from integers-as-strings
            to integers (the data type is lost in the logging/reading round
            trip)
        """
        if file_name is None:
            file_name = self._get_latest_file_in_log_dir(log_dir)
        price = self._read_df(log_dir, "price", file_name, tz)
        volatility = self._read_df(log_dir, "volatility", file_name, tz)
        predictions = self._read_df(log_dir, "prediction", file_name, tz)
        holdings_shares = self._read_df(log_dir, "holdings_shares", file_name, tz)
        holdings_notional = self._read_df(
            log_dir, "holdings_notional", file_name, tz
        )
        executed_trades_shares = self._read_df(
            log_dir, "executed_trades_shares", file_name, tz
        )
        executed_trades_notional = self._read_df(
            log_dir, "executed_trades_notional", file_name, tz
        )
        pnl = self._read_df(log_dir, "pnl", file_name, tz)
        if cast_asset_ids_to_int:
            for df in [
                price,
                volatility,
                predictions,
                holdings_shares,
                holdings_notional,
                executed_trades_shares,
                executed_trades_notional,
                pnl,
            ]:
                self._cast_cols_to_int(df)
        dfs = {
            "price": price,
            "volatility": volatility,
            "prediction": predictions,
            "holdings_shares": holdings_shares,
            "holdings_notional": holdings_notional,
            "executed_trades_shares": executed_trades_shares,
            "executed_trades_notional": executed_trades_notional,
            "pnl": pnl,
        }
        portfolio_df = self._build_multiindex_df(dfs)
        return portfolio_df
    
    @classmethod
    def load_portfolio_stats(
        self,
        log_dir: str,
        *,
        file_name: Optional[str] = None,
        tz: str = "America/New_York",
    ) -> pd.DataFrame:
        """
        Load portfolio stats.

        Used when portfolio is too large to load alongside the stats DataFrame.

        :param log_dir: directory for loading log files of portfolio state
        :param file_name: if `None`, find and use the latest
        :param tz: timezone to apply to timestamps (this information is lost in
            the logging/reading round trip)
        """
        if file_name is None:
            file_name = self._get_latest_file_in_log_dir(log_dir)
        #
        statistics_df = self._read_df(log_dir, "statistics", file_name, tz)
        return statistics_df
    
    @classmethod
    def load_portfolio_and_stats(
        self,
        log_dir: str,
        *,
        file_name: Optional[str] = None,
        tz: str = "America/New_York",
        cast_asset_ids_to_int: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load and process saved portfolio together with stats.
        """
        if file_name is None:
            file_name = self._get_latest_file_in_log_dir(log_dir)
        portfolio_df = self.load_portfolio(
            log_dir,
            file_name=file_name,
            tz=tz,
            cast_asset_ids_to_int=cast_asset_ids_to_int,
        )
        statistics_df = self.load_portfolio_stats(
            log_dir, file_name=file_name, tz=tz
        )
        return portfolio_df, statistics_df

    @abc.abstractmethod
    def annotate_forecasts(
        self,
        df: pd.DataFrame,
        **kwargs: Dict[str, Any],
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Wrap `compute_portfolio()`, return a single multiindexed dataframe.

        :param df: as in `compute_portfolio()`
        :param kwargs: forwarded to `compute_portfolio()`
        :return: multiindexed portfolio dataframe, stats dataframe
        """

    # /////////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _get_latest_file_in_log_dir(log_dir: str) -> str:
        """
        Get the latest file in the log directory.
        """
        dir_name = os.path.join(log_dir, "price")
        pattern = "*"
        only_files = True
        use_relative_paths = True
        files = hio.listdir(dir_name, pattern, only_files, use_relative_paths)
        hdbg.dassert_lte(1, len(files), "No files in %s", dir_name)
        files.sort()
        file_name = files[-1]
        _LOG.info("file_name=%s", file_name)
        return file_name

    @staticmethod
    def _write_df(
        df: pd.DataFrame,
        log_dir: str,
        name: str,
        file_name: str,
    ) -> None:
        path = os.path.join(log_dir, name, file_name)
        hio.create_enclosing_dir(path, incremental=True)
        hparque.to_parquet(df, path)

    @staticmethod
    def _read_df(
        log_dir: str,
        name: str,
        file_name: str,
        tz: str,
    ) -> pd.DataFrame:
        path = os.path.join(log_dir, name, file_name)
        df = hparque.from_parquet(path)
        df.index = df.index.tz_convert(tz)
        return df

    @staticmethod
    def _cast_cols_to_int(
        df: pd.DataFrame,
    ) -> None:
        # If integers are converted to floats and then strings, then upon
        # being read they must be cast to floats before being cast to ints.
        df.columns = df.columns.astype("float64").astype("int64")

    @staticmethod
    def _build_multiindex_df(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        portfolio_df = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
        return portfolio_df

    @staticmethod
    def _get_df(df: pd.DataFrame, col: str) -> pd.DataFrame:
        hdbg.dassert_in(col, df.columns)
        return df[col]

    def _apply_burn_in_and_reindex(
        self,
        df: pd.DataFrame,
        derived_dfs: Dict[str, pd.DataFrame],
        burn_in_bars: int,
        burn_in_days: int,
        input_idx: Optional[None],
    ) -> Dict[str, pd.DataFrame]:
        # Remove initial bars.
        if burn_in_bars > 0:
            for key, value in derived_dfs.items():
                derived_dfs[key] = value.iloc[burn_in_bars:]
        if burn_in_days > 0:
            # TODO(Paul): Consider making this more efficient (and less
            # awkward).
            date_idx = df.groupby(lambda x: x.date()).count().index
            hdbg.dassert_lt(burn_in_days, date_idx.size)
            first_date = pd.Timestamp(date_idx[burn_in_days], tz=df.index.tz)
            _LOG.info("Initial date after burn-in=%s", first_date)
            for key, value in derived_dfs.items():
                derived_dfs[key] = value.loc[first_date:]
        # Possibly reindex dataframes.
        if input_idx is not None:
            for key, value in derived_dfs.items():
                derived_dfs[key] = value.reindex(input_idx)
        return derived_dfs

    @abc.abstractmethod
    def _apply_trimming(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Trim `df` according to ATH, weekends, missing data.

        :param df: as in `compute_portfolio()`
        :return: `df` trimmed down to:
          - required and possibly optional columns
          - "active" bars (bars where at least one instrument has an end-of-bar
            price)
          - first index with both a returns prediction and a volatility
        """

    @abc.abstractmethod
    def _compute_holdings_notional(
        self,
        df: pd.DataFrame,
        holdings_shares: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute positions in dollars from share holdings.

        :param df: as in `compute_portfolio()`
        :param holdings_shares: from `_compute_holdings_shares()`
        :return: end-of-bar indexed dataframe of holdings valued using
            `self.price_col` of `df`
        """

    @abc.abstractmethod
    def _compute_portfolio(
        self, df: pd.DataFrame, **kwargs: Any
    ) -> Dict[str, pd.DataFrame]:
        """
        Compute target positions, PnL and portfolio stats.

        See instance implementations for details.
        """

    def _validate_df(self, df: pd.DataFrame) -> None:
        hpandas.dassert_time_indexed_df(
            df, allow_empty=True, strictly_increasing=True
        )
        hdbg.dassert_eq(df.columns.nlevels, 2)
        hdbg.dassert_is_subset(
            [self._price_col, self._volatility_col, self._prediction_col],
            df.columns.levels[0].to_list(),
        )
