"""
Import as:

import im.ib.data.load.ib_s3_data_loader as imidlisdlo
"""

import functools
import logging
from typing import Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import im.common.data.load.abstract_data_loader as imcdladalo
import im.common.data.types as imcodatyp
import im.ib.data.load.ib_file_path_generator as imidlifpge

_LOG = logging.getLogger(__name__)


class IbS3DataLoader(imcdladalo.AbstractS3DataLoader):
    """
    Reads IB data from S3.
    """

    S3_COLUMNS = {
        "date": "object",
        "open": float,
        "high": float,
        "low": float,
        "close": float,
        "volume": int,
        "average": float,
        "barCount": int,
    }
    S3_DATE_COLUMNS = ["date"]

    # TODO(plyq): Uncomment once #1047 will be resolved.
    # @hcache.cache()
    # Use lru_cache for now.
    @functools.lru_cache(maxsize=64)
    def read_data(
        self,
        exchange: str,
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        frequency: imcodatyp.Frequency,
        contract_type: Optional[imcodatyp.ContractType] = None,
        currency: Optional[str] = None,
        unadjusted: Optional[bool] = None,
        nrows: Optional[int] = None,
        normalize: bool = True,
        start_ts: Optional[pd.Timestamp] = None,
        end_ts: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """
        Read ib data.

        :param exchange: name of the exchange
        :param symbol: symbol to get the data for
        :param asset_class: asset class
        :param frequency: `D` or `T` for daily or minutely data respectively
        :param contract_type: required for asset class of type: `futures`
        :param currency: currency of the symbol
        :param unadjusted: required for asset classes of type: `stocks` & `etfs`
        :param nrows: if not None, return only the first nrows of the data
        :param normalize: whether to normalize the dataframe by frequency
        :param start_ts: start time of data to read,
            by default - the oldest available
        :param end_ts: end time of data to read,
            by default - now
        :return: a dataframe with the symbol data
        """
        return self._read_data(
            symbol=symbol,
            asset_class=asset_class,
            frequency=frequency,
            contract_type=contract_type,
            exchange=exchange,
            currency=currency,
            unadjusted=unadjusted,
            nrows=nrows,
            normalize=normalize,
            start_ts=start_ts,
            end_ts=end_ts,
        )

    @staticmethod
    def _filter_by_dates(
        data: pd.DataFrame,
        start_ts: Optional[pd.Timestamp] = None,
        end_ts: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """
        Filter pandas DataFrame with a date range.

        :param data: dataframe for filtering
        :param start_ts: start time of data to read. `None` means the entire data
        :param end_ts: end time of data to read. `None` means the current timestamp
        :return: filtered data
        """
        # TODO(gp): Improve this.
        if start_ts or end_ts:
            start_ts = start_ts or pd.Timestamp.min
            end_ts = end_ts or pd.Timestamp.now()
            data = data[(data["date"] >= start_ts) & (data["date"] < end_ts)]
        return data

    @staticmethod
    def _normalize_1_min(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize minutes data. Not implemented yet.

        It is used only for external purposes to return aligned data.

        :param df: source data
        :return: normalized data
        """
        return df

    @staticmethod
    def _normalize_daily(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize daily data. Not implemented yet.

        It is used only for external purposes to return aligned data.

        :param df: source data
        :return: normalized data
        """
        return df

    @staticmethod
    def _normalize_1_hour(df: pd.DataFrame) -> pd.DataFrame:
        """
        Hour data normalization. Not implemented yet.

        It is used only for external purposes to return aligned data.

        :param df: source data
        :return: normalized data
        """
        return df

    def _read_data(
        self,
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        frequency: imcodatyp.Frequency,
        contract_type: Optional[imcodatyp.ContractType] = None,
        exchange: Optional[str] = None,
        currency: Optional[str] = None,
        unadjusted: Optional[bool] = None,
        nrows: Optional[int] = None,
        normalize: bool = True,
        start_ts: Optional[pd.Timestamp] = None,
        end_ts: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        # Generate path to retrieve data.
        file_path = imidlifpge.IbFilePathGenerator().generate_file_path(
            symbol=symbol,
            asset_class=asset_class,
            frequency=frequency,
            contract_type=contract_type,
            exchange=exchange,
            currency=currency,
            unadjusted=unadjusted,
            ext=imcodatyp.Extension.CSV,
        )
        # Check that file exists.
        aws_profile = "ck"
        s3fs = hs3.get_s3fs(aws_profile)
        if hs3.is_s3_path(file_path):
            hdbg.dassert(
                s3fs.exists(file_path), "S3 key not found: %s", file_path
            )
        # Read data.
        # cls.S3_COLUMNS.keys() -> list(cls.S3_COLUMNS.keys())
        # https://github.com/pandas-dev/pandas/issues/36928 fixed in Pandas 1.1.4
        names = list(self.S3_COLUMNS.keys())
        stream, kwargs = hs3.get_local_or_s3_stream(file_path, s3fs=s3fs)
        data = hpandas.read_csv_to_df(stream, nrows=nrows, names=names, **kwargs)
        # TODO(plyq): Reload ES data with a new extractor to have a header.
        # If header was already in data, remove it.
        if list(data.iloc[0]) == list(self.S3_COLUMNS.keys()):
            data = data[1:].reset_index(drop=True)
        # Cast columns to correct types.
        data = data.astype(
            {
                key: self.S3_COLUMNS[key]
                for key in self.S3_COLUMNS
                if key not in self.S3_DATE_COLUMNS
            }
        )
        for date_column in self.S3_DATE_COLUMNS:
            data[date_column] = pd.to_datetime(data[date_column])
        data = self._filter_by_dates(data, start_ts=start_ts, end_ts=end_ts)
        if normalize:
            data = self.normalize(df=data, frequency=frequency)
            data.set_index("date", drop=False, inplace=True)
        return data
