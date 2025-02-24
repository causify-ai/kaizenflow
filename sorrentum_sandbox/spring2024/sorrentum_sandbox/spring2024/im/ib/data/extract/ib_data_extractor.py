"""
Extract data from IB Gateway and put it to S3.

Import as:

import im.ib.data.extract.ib_data_extractor as imideidaex
"""
# TODO(*): -> ib_data_extractor.py

import logging
import os
from typing import List, Optional, Tuple

import ib_insync
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import im.common.data.extract.data_extractor as imcdedaex
import im.common.data.types as imcodatyp
import im.ib.data.extract.gateway.download_data_ib_loop as imidegddil
import im.ib.data.extract.gateway.utils as imidegaut
import im.ib.data.load.ib_file_path_generator as imidlifpge

_LOG = logging.getLogger(__name__)


class IbDataExtractor(imcdedaex.AbstractDataExtractor):
    """
    Load data from IB and save it to S3.
    """

    _MAX_IB_CONNECTION_ATTEMPTS = 1000
    _MAX_IB_DATA_LOAD_ATTEMPTS = 3

    def __init__(self, ib_connect_client_id: Optional[int] = None):
        if ib_connect_client_id is not None:
            self._ib_connect_client_id = ib_connect_client_id
        else:
            self._ib_connect_client_id = imidegaut.get_free_client_id(
                self._MAX_IB_CONNECTION_ATTEMPTS
            )

    @staticmethod
    def get_default_part_files_dir(
        symbol: str,
        frequency: imcodatyp.Frequency,
        asset_class: imcodatyp.AssetClass,
        contract_type: imcodatyp.ContractType,
        exchange: str,
        currency: str,
    ) -> str:
        """
        Return a `symbol` directory on S3 near the main archive file.
        """
        arch_file = imidlifpge.IbFilePathGenerator().generate_file_path(
            symbol=symbol,
            frequency=frequency,
            asset_class=asset_class,
            contract_type=contract_type,
            exchange=exchange,
            currency=currency,
            ext=imcodatyp.Extension.CSV,
        )
        arch_path, _ = os.path.split(arch_file)
        return os.path.join(arch_path, symbol)

    def extract_data(
        self,
        exchange: str,
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        frequency: imcodatyp.Frequency,
        contract_type: Optional[imcodatyp.ContractType] = None,
        currency: Optional[str] = None,
        start_ts: Optional[pd.Timestamp] = None,
        end_ts: Optional[pd.Timestamp] = None,
        incremental: Optional[bool] = None,
        dst_dir: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Extract the data, save it and return all data for symbol.

        :param exchange: name of the exchange
        :param symbol: symbol to get the data for
        :param asset_class: asset class
        :param frequency: `D` or `T` for daily or minutely data respectively
        :param currency: contract currency
        :param contract_type: required for asset class of type `futures`
        :param start_ts: start time of data to extract,
            by default - the oldest available
        :param end_ts: end time of data to extract,
            by default - now
        :param incremental: if True - save only new data,
            if False - remove old firstly,
            True by default
        :param dst_dir: place to keep results of each IB request
        :return: a dataframe with the data
        :raises ValueError: if parameter values are not supported
        """
        hdbg.dassert_is_not(currency, None)
        part_files_dir = (
            self.get_default_part_files_dir(
                symbol=symbol,
                frequency=frequency,
                asset_class=asset_class,
                contract_type=contract_type,
                exchange=exchange,
                currency=currency,
            )
            if dst_dir is None
            else dst_dir
        )
        self.extract_data_parts_with_retry(
            exchange=exchange,
            symbol=symbol,
            asset_class=asset_class,
            frequency=frequency,
            currency=currency,
            contract_type=contract_type,
            start_ts=start_ts,
            end_ts=end_ts,
            incremental=incremental,
            part_files_dir=part_files_dir,
        )
        # Union all data from files and save to archive.
        saved_data = self.update_archive(
            symbol=symbol,
            asset_class=asset_class,
            contract_type=contract_type,
            exchange=exchange,
            currency=currency,
            frequency=frequency,
            part_files_dir=part_files_dir,
        )
        return saved_data

    def extract_data_parts_with_retry(
        self,
        part_files_dir: str,
        exchange: str,
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        frequency: imcodatyp.Frequency,
        currency: str,
        contract_type: Optional[imcodatyp.ContractType] = None,
        start_ts: Optional[pd.Timestamp] = None,
        end_ts: Optional[pd.Timestamp] = None,
        incremental: Optional[bool] = None,
    ) -> None:
        """
        Extract the data by chunks and save them.

        :param exchange: name of the exchange
        :param symbol: symbol to get the data for
        :param asset_class: asset class
        :param frequency: `D` or `T` for daily or minutely data respectively
        :param currency: contract currency
        :param contract_type: required for asset class of type `futures`
        :param start_ts: start time of data to extract,
            by default - the oldest available
        :param end_ts: end time of data to extract,
            by default - now
        :param incremental: if True - save only new data,
            if False - remove old firstly,
            True by default
        :param part_files_dir: place to keep results of each IB request
        """
        # Connect to IB.
        ib_connection = imidegaut.ib_connect(
            self._ib_connect_client_id, is_notebook=False
        )
        # Find right intervals for incremental mode.
        left_intervals = self._get_init_intervals(
            start_ts,
            end_ts,
            exchange=exchange,
            symbol=symbol,
            asset_class=asset_class,
            frequency=frequency,
            currency=currency,
            contract_type=contract_type,
            incremental=incremental,
        )
        # Save extracted data in parts.
        num_attempts_done = 0
        while (
            left_intervals and num_attempts_done < self._MAX_IB_DATA_LOAD_ATTEMPTS
        ):
            left_intervals_after_try = []
            for interval in left_intervals:
                # Try to extract the data. Save unsuccessful intervals.
                failed_intervals = self._extract_data_parts(
                    ib=ib_connection,
                    exchange=exchange,
                    symbol=symbol,
                    asset_class=asset_class,
                    frequency=frequency,
                    currency=currency,
                    contract_type=contract_type,
                    start_ts=interval[0],
                    end_ts=interval[1],
                    incremental=incremental or bool(num_attempts_done),
                    part_files_dir=part_files_dir,
                )
                left_intervals_after_try.extend(failed_intervals)
            num_attempts_done += 1
            left_intervals = left_intervals_after_try.copy()
        # Disconnect from IB.
        ib_connection.disconnect()

    @classmethod
    def update_archive(
        cls,
        part_files_dir: str,
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        contract_type: Optional[imcodatyp.ContractType],
        exchange: str,
        currency: str,
        frequency: imcodatyp.Frequency,
    ) -> pd.DataFrame:
        """
        Read data from parts, save it to archive.

        :param symbol: symbol to get the data for
        :param asset_class: asset class
        :param contract_type: required for asset class of type `futures`
        :param exchange: symbol exchange
        :param currency: symbol currency
        :param frequency: `D` or `T` for daily or minutely data respectively
        :param part_files_dir: place to keep results of each IB request
        :return: a dataframe with the data
        """
        # Find main archive file location.
        arch_file = imidlifpge.IbFilePathGenerator().generate_file_path(
            symbol=symbol,
            frequency=frequency,
            asset_class=asset_class,
            contract_type=contract_type,
            exchange=exchange,
            currency=currency,
            ext=imcodatyp.Extension.CSV,
        )
        _, arch_name = os.path.split(arch_file)
        # Find files with partial data locations.
        s3fs = hs3.get_s3fs("am")
        part_file_names = (
            s3fs.ls(part_files_dir + "/")
            if part_files_dir.startswith("s3://")
            else os.listdir(part_files_dir)
        )
        part_files = [
            os.path.join(part_files_dir, file_name)
            for file_name in part_file_names
        ]
        _LOG.info("Union files in `%s` to `%s`", part_files_dir, arch_file)
        # Read data.
        data: pd.DataFrame = pd.concat(
            [
                imidegddil.load_historical_data(part_file)
                for part_file in part_files
                if part_file != arch_name
            ]
        )
        # Sort index.
        data = data.sort_index(ascending=True)
        hpandas.dassert_monotonic_index(data)
        # Save data to archive.
        data.to_csv(arch_file, compression="gzip")
        _LOG.info("Finished, data in `%s`", arch_file)
        return data

    @staticmethod
    def _get_ib_target(
        asset_class: imcodatyp.AssetClass,
        contract_type: Optional[imcodatyp.ContractType],
    ) -> str:
        """
        Transform asset to a format known by IB gateway code.
        """
        target: str
        if (
            asset_class == imcodatyp.AssetClass.Futures
            and contract_type == imcodatyp.ContractType.Continuous
        ):
            target = "continuous_futures"
        elif (
            asset_class == imcodatyp.AssetClass.Futures
            and contract_type == imcodatyp.ContractType.Expiry
        ):
            target = "futures"
        elif asset_class == imcodatyp.AssetClass.Stocks:
            target = "stocks"
        elif asset_class == imcodatyp.AssetClass.Forex:
            target = "forex"
        else:
            raise ValueError(
                "Couldn't find corresponding IB target for asset class %s and contract type %s"
                % (asset_class, contract_type)
            )
        return target

    @staticmethod
    def _get_ib_frequency(frequency: imcodatyp.Frequency) -> str:
        """
        Transform frequency to a format known by IB gateway code.
        """
        ib_frequency: str
        if frequency == imcodatyp.Frequency.Daily:
            ib_frequency = "day"
        elif frequency == imcodatyp.Frequency.Hourly:
            ib_frequency = "hour"
        elif frequency == imcodatyp.Frequency.Minutely:
            ib_frequency = "intraday"
        else:
            raise ValueError(
                "Couldn't find corresponding IB frequency for %s" % frequency
            )
        return ib_frequency

    @staticmethod
    def _get_init_intervals(
        start_ts: Optional[pd.Timestamp],
        end_ts: Optional[pd.Timestamp],
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        contract_type: Optional[imcodatyp.ContractType],
        exchange: str,
        currency: str,
        frequency: imcodatyp.Frequency,
        incremental: Optional[bool],
    ) -> List[Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]]:
        """
        Find starting intervals to load the data.

        For non-incremental case it is just [`start_ts`, `end_ts`). For
        incremental we remove already loaded piece.
        """
        # Nothing to do for non-incremental mode.
        if not incremental:
            return [(start_ts, end_ts)]
        # For incremental mode, find first and last loaded timestamp.
        arch_file = imidlifpge.IbFilePathGenerator().generate_file_path(
            symbol=symbol,
            frequency=frequency,
            asset_class=asset_class,
            contract_type=contract_type,
            exchange=exchange,
            currency=currency,
            ext=imcodatyp.Extension.CSV,
        )
        if not imidegaut.check_file_exists(arch_file):
            return [(start_ts, end_ts)]
        df = imidegddil.load_historical_data(arch_file)
        min_ts = df.index.min()
        max_ts = df.index.max()
        # Find intervals to run.
        intervals: List[
            Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]
        ] = []
        if end_ts is None or imidegaut.to_ET(end_ts) > max_ts:
            intervals.append((max_ts, end_ts))
        if start_ts is None or imidegaut.to_ET(start_ts) < min_ts:
            intervals.append((start_ts, min_ts))
        _LOG.warning(
            "Incremental mode. Found file '%s': extracting data for %s",
            arch_file,
            intervals,
        )
        return intervals

    def _extract_data_parts(
        self,
        ib: ib_insync.ib.IB,
        part_files_dir: str,
        exchange: str,
        symbol: str,
        asset_class: imcodatyp.AssetClass,
        frequency: imcodatyp.Frequency,
        currency: str,
        contract_type: Optional[imcodatyp.ContractType] = None,
        start_ts: Optional[pd.Timestamp] = None,
        end_ts: Optional[pd.Timestamp] = None,
        incremental: Optional[bool] = None,
    ) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
        """
        Make a several requests to IB, each response is saved to a separate
        file.

        E.g. list of resultes files:
        - s3://*****/data/ib/futures/daily/ESH1/ESH1.20200101.20210101.csv
        - s3://*****/data/ib/futures/daily/ESH1/ESH1.20190101.20200101.csv
        - ...

        :param ib: IB connection
        :param part_files_dir: place to keep results of each IB request
        :param exchange: name of the exchange
        :param symbol: symbol to get the data for
        :param asset_class: asset class
        :param frequency: `D` or `T` for daily or minutely data respectively
        :param currency: contract currency
        :param contract_type: required for asset class of type `futures`
        :param start_ts: start time of data to extract,
            by default - the oldest available
        :param end_ts: end time of data to extract,
            by default - now
        :param incremental: if True - save only new data,
            if False - remove old firstly,
            True by default
        :return: a list of failed intervals
        """
        # Get tasks.
        tasks = imidegaut.get_tasks(
            ib=ib,
            target=self._get_ib_target(asset_class, contract_type),
            frequency=self._get_ib_frequency(frequency),
            symbols=[symbol],
            start_ts=start_ts,
            end_ts=end_ts,
            use_rth=False,
            exchange=exchange,
            currency=currency,
        )
        # Do tasks.
        file_name = imidlifpge.IbFilePathGenerator().generate_file_path(
            symbol=symbol,
            frequency=frequency,
            asset_class=asset_class,
            contract_type=contract_type,
            exchange=exchange,
            currency=currency,
            ext=imcodatyp.Extension.CSV,
        )
        failed_tasks_intervals = []
        for (
            contract,
            start_ts_task,
            end_ts_task,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
        ) in tasks:
            saved_intervals = (
                imidegddil.save_historical_data_by_intervals_IB_loop(
                    ib=ib,
                    contract=contract,
                    start_ts=start_ts_task,
                    end_ts=end_ts_task,
                    duration_str=duration_str,
                    bar_size_setting=bar_size_setting,
                    what_to_show=what_to_show,
                    use_rth=use_rth,
                    file_name=file_name,
                    part_files_dir=part_files_dir,
                    incremental=incremental,
                    num_retry=self._MAX_IB_DATA_LOAD_ATTEMPTS,
                )
            )
            # Find intervals with no data.
            for interval in saved_intervals:
                file_name_for_part = imidegddil.historical_data_to_filename(
                    contract=contract,
                    start_ts=interval[0],
                    end_ts=interval[1],
                    duration_str=duration_str,
                    bar_size_setting=bar_size_setting,
                    what_to_show=what_to_show,
                    use_rth=use_rth,
                    dst_dir=part_files_dir,
                )
                df_part = imidegddil.load_historical_data(file_name_for_part)
                if df_part.empty:
                    failed_tasks_intervals.append(interval)
        # Return failed intervals.
        return failed_tasks_intervals
