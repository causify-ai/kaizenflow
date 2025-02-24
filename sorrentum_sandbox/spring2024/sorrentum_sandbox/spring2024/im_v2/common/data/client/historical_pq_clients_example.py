"""
Import as:

import im_v2.common.data.client.historical_pq_clients_example as imvcdchpce
"""

import os
from typing import Any, List

import im_v2.common.data.client.historical_pq_clients as imvcdchpcl
import im_v2.common.test as imvct
import im_v2.common.universe as ivcu


class MockHistoricalByTileClient(imvcdchpcl.HistoricalPqByTileClient):
    def get_universe(self) -> List[str]:
        return ["binance::BTC_USDT", "kucoin::FIL_USDT"]


def get_MockHistoricalByTileClient_example1(
    self_: Any,
    full_symbols: List[ivcu.FullSymbol],
    resample_1min: bool,
) -> imvcdchpcl.HistoricalPqByTileClient:
    """
    Build mock client example to test data in span of 2 days.
    """
    # Specify parameters for test data generation and client initialization.
    start_date = "2021-12-30"
    end_date = "2022-01-02"
    assets = full_symbols
    asset_col_name = "full_symbol"
    test_data_dir = self_.get_scratch_space()
    tiled_bar_data_dir = os.path.join(test_data_dir, "tiled.bar_data")
    freq = "1T"
    output_type = "cm_task_1103"
    partition_mode = "by_year_month"
    # Generate test data.
    imvct.generate_parquet_files(
        start_date,
        end_date,
        assets,
        asset_col_name,
        tiled_bar_data_dir,
        freq=freq,
        output_type=output_type,
        partition_mode=partition_mode,
    )
    # Init client for testing.
    vendor = "mock"
    universe_version = "small"
    infer_exchange_id = False
    im_client = MockHistoricalByTileClient(
        vendor,
        universe_version,
        test_data_dir,
        partition_mode,
        infer_exchange_id,
        resample_1min=resample_1min,
    )
    return im_client


def get_MockHistoricalByTileClient_example2(
    self_: Any,
    full_symbols: List[ivcu.FullSymbol],
) -> imvcdchpcl.HistoricalPqByTileClient:
    """
    Build mock client example to test Parquet filters building.
    """
    # Specify parameters for test data generation and client initialization.
    start_date = "2020-01-01"
    end_date = "2022-01-02"
    assets = full_symbols
    asset_col_name = "full_symbol"
    test_data_dir = self_.get_scratch_space()
    tiled_bar_data_dir = os.path.join(test_data_dir, "tiled.bar_data")
    freq = "1H"
    output_type = "cm_task_1103"
    partition_mode = "by_year_month"
    # Generate test data.
    imvct.generate_parquet_files(
        start_date,
        end_date,
        assets,
        asset_col_name,
        tiled_bar_data_dir,
        freq=freq,
        output_type=output_type,
        partition_mode=partition_mode,
    )
    # Init client for testing.
    vendor = "mock"
    universe_version = "small"
    resample_1min = False
    infer_exchange_id = False
    im_client = MockHistoricalByTileClient(
        vendor,
        universe_version,
        test_data_dir,
        partition_mode,
        infer_exchange_id,
        resample_1min=resample_1min,
    )
    return im_client


def get_MockHistoricalByTileClient_example3(
    self_: Any,
    full_symbols: List[ivcu.FullSymbol],
    start_date: str,
    end_date: str,
    resample_1min: bool,
) -> imvcdchpcl.HistoricalPqByTileClient:
    """
    Build mock client example to test randomly generated intervals.
    """
    # Specify parameters for test data generation and client initialization.
    assets = full_symbols
    asset_col_name = "full_symbol"
    test_data_dir = self_.get_scratch_space()
    tiled_bar_data_dir = os.path.join(test_data_dir, "tiled.bar_data")
    freq = "1H"
    output_type = "cm_task_1103"
    partition_mode = "by_year_month"
    # Generate test data.
    imvct.generate_parquet_files(
        start_date,
        end_date,
        assets,
        asset_col_name,
        tiled_bar_data_dir,
        freq=freq,
        output_type=output_type,
        partition_mode=partition_mode,
    )
    # Init client for testing.
    vendor = "mock"
    universe_version = "small"
    infer_exchange_id = False
    im_client = MockHistoricalByTileClient(
        vendor,
        universe_version,
        test_data_dir,
        partition_mode,
        infer_exchange_id,
        resample_1min=resample_1min,
    )
    return im_client
