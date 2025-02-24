"""
Implement several data source nodes.

Import as:

import dataflow.core.nodes.sources as dtfconosou
"""
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

import core.artificial_signal_generators as carsigen
import core.statistics as costatis
import dataflow.core.node as dtfcornode
import dataflow.core.nodes.base as dtfconobas
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hs3 as hs3

_LOG = logging.getLogger(__name__)


# #############################################################################


class DummyDataSource(dtfconobas.DataSource):
    """
    Placeholder node for a DataSource factory.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        **func_kwargs: Any,
    ) -> None:
        super().__init__(nid)
        _ = func_kwargs


# #############################################################################


class DfDataSource(dtfconobas.DataSource):
    """
    Accept data as a DataFrame passed through the constructor and output the
    data.
    """

    def __init__(self, nid: dtfcornode.NodeId, df: pd.DataFrame) -> None:
        super().__init__(nid)
        hdbg.dassert_isinstance(df, pd.DataFrame)
        self.df = df


# #############################################################################


class FunctionDataSource(dtfconobas.DataSource):
    """
    Use the passed function and arguments to generate the data outputted by the
    node.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        func: Callable,
        func_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Constructor.

        :param func: function used to generate data. Typically it accepts
            `start_date` and `end_date` as parameters
        :param func_kwargs: kwargs passed to the function when generating and loading
            the data
        """
        super().__init__(nid)
        self._func = func
        self._func_kwargs = func_kwargs or {}

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().fit()  # type: ignore[no-any-return]

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().predict()  # type: ignore[no-any-return]

    def _lazy_load(self) -> None:
        if self.df is not None:  # type: ignore[has-type]
            return
        df_out = self._func(**self._func_kwargs)
        # TODO(gp): Add more checks like df.index is an increasing timestamp.
        hdbg.dassert_isinstance(df_out, pd.DataFrame)
        self.df = df_out


# #############################################################################


# TODO(gp): This should go in a lower layer API, but it's not clear where.
def load_data_from_disk(
    file_path: str,
    # TODO(gp): -> index_col? (Like pandas naming)
    timestamp_col: Optional[str] = None,
    start_date: Optional[hdateti.Datetime] = None,
    end_date: Optional[hdateti.Datetime] = None,
    aws_profile: hs3.AwsProfile = None,
    reader_kwargs: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Read data from CSV or Parquet `file_path`.

    :param file_path: path to the file to read with ".csv" or ".pq" extension
    # TODO(*): Don't the readers support this already?
    :param timestamp_col: name of the timestamp column. If `None`, assume
        that index contains timestamps
    :param start_date: data start date in timezone of the dataset, included
    :param end_date: data end date in timezone of the dataset, included
    :param aws_profile: the name of an AWS profile or a s3fs filesystem
    :param reader_kwargs: kwargs for the data reading function
    """
    reader_kwargs = reader_kwargs or {}
    kwargs = reader_kwargs.copy()
    # Add S3 credentials, if needed.
    if aws_profile is not None:
        s3fs = hs3.get_s3fs(aws_profile)
        kwargs["s3fs"] = s3fs
    # Get the extension.
    ext = os.path.splitext(file_path)[-1]
    # Select the reading method based on the extension.
    if ext == ".csv":
        # Assume that the first column is the index, unless specified.
        if "index_col" not in reader_kwargs:
            kwargs["index_col"] = 0
        read_data = hpandas.read_csv_to_df
    elif ext == ".pq":
        read_data = hpandas.read_parquet_to_df
    else:
        raise ValueError("Invalid file extension='%s'" % ext)
    # Read the data.
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("filepath=%s kwargs=%s", file_path, str(kwargs))
    stream, kwargs = hs3.get_local_or_s3_stream(file_path, **kwargs)
    df = read_data(stream, **kwargs)
    # Process the data.
    # Use the specified timestamp column as index, if needed.
    if timestamp_col is not None:
        df.set_index(timestamp_col, inplace=True)
    # Convert index in timestamps.
    df.index = pd.to_datetime(df.index)
    hpandas.dassert_strictly_increasing_index(df)
    # Filter by start / end date.
    # TODO(gp): Not sure that a view is enough to force discarding the unused
    #  rows in the DataFrame. Maybe do a copy, delete the old data, and call the
    #  garbage collector.
    # TODO(gp): A bit inefficient since Parquet might allow to read only the needed
    #  data.
    df = df.loc[start_date:end_date]
    hdbg.dassert(not df.empty, "Dataframe is empty")
    return df


# #############################################################################


class DiskDataSource(dtfconobas.DataSource):
    """
    Read CSV or Parquet data from disk or S3 and output the data.

    This is a wrapper node around `load_data_from_disk()`.
    """

    def __init__(
        self, nid: dtfcornode.NodeId, **load_data_from_disk_kwargs: Dict[str, Any]
    ) -> None:
        """
        Constructor.

        :param nid: node identifier
        """
        super().__init__(nid)
        self._load_data_from_disk_kwargs = load_data_from_disk_kwargs

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        """
        Load the data on the first invocation and then delegate to the base
        class.

        We don't need to implement `predict()` since the data is read
        only on the first call to `fit()`, so the behavior of the base
        class is sufficient.

        :return: dict from output name to DataFrame
        """
        self._lazy_load()
        return super().fit()  # type: ignore[no-any-return]

    def _lazy_load(self) -> None:
        """
        Load the data if it was not already done.
        """
        if self.df is not None:  # type: ignore[has-type]
            return
        df = load_data_from_disk(
            **self._load_data_from_disk_kwargs  # type: ignore[arg-type]
        )
        self.df = df


# #############################################################################


class ArmaDataSource(dtfconobas.DataSource):
    """
    Generate price data from ARMA process returns.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        frequency: str,
        start_date: hdateti.Datetime,
        end_date: hdateti.Datetime,
        ar_coeffs: Optional[List[float]] = None,
        ma_coeffs: Optional[List[float]] = None,
        scale: Optional[float] = None,
        # TODO(gp): -> burn_in_period? Otherwise it seems burning without the final g.
        burnin: Optional[float] = None,
        seed: Optional[float] = None,
    ) -> None:
        super().__init__(nid)
        self._frequency = frequency
        self._start_date = start_date
        self._end_date = end_date
        self._ar_coeffs = ar_coeffs or [0]
        self._ma_coeffs = ma_coeffs or [0]
        self._scale = scale or 1
        self._burnin = burnin or 0
        self._seed = seed
        self._arma_process = carsigen.ArmaProcess(
            ar_coeffs=self._ar_coeffs, ma_coeffs=self._ma_coeffs
        )
        self._poisson_process = carsigen.PoissonProcess(mu=100)

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().fit()  # type: ignore[no-any-return]

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load()
        return super().predict()  # type: ignore[no-any-return]

    def _lazy_load(self) -> None:
        if self.df is not None:  # type: ignore[has-type]
            return
        rets = self._arma_process.generate_sample(
            date_range_kwargs={
                "start": self._start_date,
                "end": self._end_date,
                "freq": self._frequency,
            },
            scale=self._scale,
            burnin=self._burnin,
            seed=self._seed,
        )
        bid_volume = self._poisson_process.generate_sample(
            date_range_kwargs={
                "start": self._start_date,
                "end": self._end_date,
                "freq": self._frequency,
            },
            seed=self._seed,
        )
        ask_volume = self._poisson_process.generate_sample(
            date_range_kwargs={
                "start": self._start_date,
                "end": self._end_date,
                "freq": self._frequency,
            },
            seed=self._seed + 1,
        )
        # Cumulatively sum to generate a price series (implicitly assumes the
        # returns are log returns; at small enough scales and short enough
        # times this is practically interchangeable with percentage returns).
        # TODO(Paul): Allow specification of annualized target volatility.
        prices = np.exp(0.1 * rets.cumsum())
        prices.name = "close"
        df = prices.to_frame()
        self.df = df.loc[self._start_date : self._end_date]
        # Use constant volume (for now).
        self.df["volume"] = 10000  # type: ignore[index]
        self.df["bid"] = self.df["close"] - 0.01
        self.df["ask"] = self.df["close"] + 0.01
        self.df["bid_size"] = bid_volume
        self.df["ask_size"] = ask_volume


# #############################################################################


class MultivariateNormalDataSource(dtfconobas.DataSource):
    """
    Generate price data from multivariate normal returns.
    """

    def __init__(
        self,
        nid: dtfcornode.NodeId,
        frequency: str,
        start_date: hdateti.Datetime,
        end_date: hdateti.Datetime,
        dim: int,
        target_volatility: Optional[float] = None,
        seed: Optional[float] = None,
    ) -> None:
        super().__init__(nid)
        self._frequency = frequency
        self._start_date = start_date
        self._end_date = end_date
        self._dim = dim
        self._target_volatility = target_volatility
        self._volatility_scale_factor = 1
        self._seed = seed
        self._multivariate_normal_process = carsigen.MultivariateNormalProcess()
        # Initialize process with appropriate dimension.
        self._multivariate_normal_process.set_cov_from_inv_wishart_draw(
            dim=self._dim, seed=self._seed
        )

    def fit(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load(fit=True)
        return super().fit()  # type: ignore[no-any-return]

    def predict(self) -> Optional[Dict[str, pd.DataFrame]]:
        self._lazy_load(fit=False)
        return super().predict()  # type: ignore[no-any-return]

    def _generate_returns(self, fit: bool) -> pd.DataFrame:
        rets = self._multivariate_normal_process.generate_sample(
            date_range_kwargs={
                "start": self._start_date,
                "end": self._end_date,
                "freq": self._frequency,
            },
            seed=self._seed,
        )
        if self._target_volatility is None:
            return rets
        if fit:
            avg_rets = rets.mean(axis=1)
            vol = costatis.compute_annualized_volatility(avg_rets)
            self._volatility_scale_factor = self._target_volatility / vol
        return rets * self._volatility_scale_factor

    def _lazy_load(self, fit: bool) -> None:
        if self.df is not None:  # type: ignore[has-type]
            return
        rets = self._generate_returns(fit)
        # Cumulatively sum to generate a price series (implicitly assumes the
        # returns are log returns; at small enough scales and short enough
        # times this is practically interchangeable with percentage returns).
        prices = np.exp(rets.cumsum())
        prices = prices.rename(columns=lambda x: "MN" + str(x))
        # Use constant volume (for now).
        volume = pd.DataFrame(
            index=prices.index, columns=prices.columns, data=100
        )
        df = pd.concat([prices, volume], axis=1, keys=["close", "volume"])
        self.df = df.loc[self._start_date : self._end_date]
