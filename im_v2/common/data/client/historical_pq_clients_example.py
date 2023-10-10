"""
Import as:

import im_v2.common.data.client.historical_pq_clients_example as imvcdchpce
"""

import os
from typing import Any, List

import helpers.hgit as hgit
import helpers.hsystem as hsystem
import im_v2.common.data.client.historical_pq_clients as imvcdchpcl
import im_v2.common.universe as ivcu


def _generate_test_data(
    test_data_dir: str,
    start_date: str,
    end_date: str,
    freq: str,
    assets: str,
    asset_col_name: str,
    output_type: str,
    partition_mode: str,
) -> None:
    """
    The parameters are the test data dir and the same as the script
    `im_v2/common/test/generate_pq_test_data.py`.
    """
    tiled_bar_data_dir = os.path.join(test_data_dir, "tiled.bar_data")
    # TODO(gp): @all replace the script with calling the library directly
    #  CmTask1490.
    cmd = []
    file_path = os.path.join(
        hgit.get_amp_abs_path(),
        "im_v2/common/test/generate_pq_test_data.py",
    )
    cmd.append(file_path)
    cmd.append(f"--start_date {start_date}")
    cmd.append(f"--end_date {end_date}")
    cmd.append(f"--freq {freq}")
    cmd.append(f"--assets {assets}")
    cmd.append(f"--asset_col_name {asset_col_name}")
    cmd.append(f"--partition_mode {partition_mode}")
    cmd.append(f"--dst_dir {tiled_bar_data_dir}")
    cmd.append(f"--output_type {output_type}")
    cmd = " ".join(cmd)
    hsystem.system(cmd)


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
    freq = "1T"
    assets = ",".join(full_symbols)
    asset_col_name = "full_symbol"
    output_type = "cm_task_1103"
    partition_mode = "by_year_month"
    test_data_dir = self_.get_scratch_space()
    # Generate test data.
    _generate_test_data(
        test_data_dir,
        start_date,
        end_date,
        freq,
        assets,
        asset_col_name,
        output_type,
        partition_mode,
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
    freq = "1H"
    assets = ",".join(full_symbols)
    asset_col_name = "full_symbol"
    output_type = "cm_task_1103"
    partition_mode = "by_year_month"
    test_data_dir = self_.get_scratch_space()
    # Generate test data.
    _generate_test_data(
        test_data_dir,
        start_date,
        end_date,
        freq,
        assets,
        asset_col_name,
        output_type,
        partition_mode,
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
    freq = "1H"
    assets = ",".join(full_symbols)
    asset_col_name = "full_symbol"
    output_type = "cm_task_1103"
    partition_mode = "by_year_month"
    test_data_dir = self_.get_scratch_space()
    # Generate test data.
    _generate_test_data(
        test_data_dir,
        start_date,
        end_date,
        freq,
        assets,
        asset_col_name,
        output_type,
        partition_mode,
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
