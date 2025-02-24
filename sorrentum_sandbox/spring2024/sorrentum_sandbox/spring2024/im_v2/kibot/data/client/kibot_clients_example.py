"""
Import as:

import im_v2.kibot.data.client.kibot_clients_example as imvkdckcex
"""

import os

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import im_v2.kibot.data.client.kibot_clients as imvkdckicl


def get_test_data_dir() -> str:
    """
    Get dir with data files for the tests.

    The files in the dir are copies of some Kibot data files from S3
    that were loaded for our research purposes. These copies are checked
    out locally in order to test functions without dependencies on S3.

    The data looks like:
    ```
    datetime,open,high,low,close,vol,time
    2009-09-27 18:06:00,1.6945,1.6945,1.6945,1.6945,3,18:06:00
    2009-09-27 18:07:00,1.6964,1.6964,1.6964,1.6964,4,18:07:00
    2009-09-27 18:38:00,1.6877,1.6877,1.6877,1.6877,5,18:38:00
    2009-09-27 18:44:00,1.6893,1.6893,1.6893,1.6893,1,18:44:00

    Raw data for the current extension has no header.
    """
    # Get path to the dir with the test data.
    test_data_dir = os.path.join(
        hgit.get_amp_abs_path(),
        "im_v2/kibot/data/client/test/test_data",
    )
    hdbg.dassert_dir_exists(test_data_dir)
    return test_data_dir


def get_KibotEquitiesCsvParquetByAssetClient_example1(
    unadjusted: bool,
) -> imvkdckicl.KibotEquitiesCsvParquetByAssetClient:
    """
    Return a Kibot object with:

       - local `csv.gz` data
       - using equity data

    :param unadjusted: whether asset class prices are unadjusted (i.e., True or False)
    """
    # Initialize client.
    universe_version = "small"
    resample_1min = True
    root_dir = get_test_data_dir()
    extension = "csv.gz"
    asset_class = "stocks"
    kibot_file_client = imvkdckicl.KibotEquitiesCsvParquetByAssetClient(
        universe_version,
        root_dir,
        extension,
        asset_class,
        unadjusted,
        resample_1min=resample_1min,
    )
    return kibot_file_client


def get_KibotEquitiesCsvParquetByAssetClient_example2(
    unadjusted: bool,
) -> imvkdckicl.KibotEquitiesCsvParquetByAssetClient:
    """
    Return a Kibot object with:

       - local `pq` data
       - using equity data

    :param unadjusted: whether asset class prices are unadjusted (i.e., True or False)
    """
    universe_version = "small"
    resample_1min = True
    root_dir = get_test_data_dir()
    extension = "pq"
    asset_class = "stocks"
    kibot_file_client = imvkdckicl.KibotEquitiesCsvParquetByAssetClient(
        universe_version,
        root_dir,
        extension,
        asset_class,
        unadjusted,
        resample_1min=resample_1min,
    )
    return kibot_file_client


def get_KibotFuturesCsvParquetByAssetClient_example1(
    contract_type: str, resample_1min: bool
) -> imvkdckicl.KibotFuturesCsvParquetByAssetClient:
    """
    Return a Kibot object with:

       - local `csv.gz` data
       - using futures data

    :param contract_type: futures contract type (e.g., "continuous", "expiry")
    :param resample_1min: whether to resample data to 1 minute or not
    """
    universe_version = "small"
    root_dir = get_test_data_dir()
    extension = "csv.gz"
    kibot_file_client = imvkdckicl.KibotFuturesCsvParquetByAssetClient(
        universe_version,
        root_dir,
        extension,
        contract_type,
        resample_1min=resample_1min,
    )
    return kibot_file_client


def get_KibotFuturesCsvParquetByAssetClient_example2(
    contract_type: str, resample_1min: bool
) -> imvkdckicl.KibotFuturesCsvParquetByAssetClient:
    """
    Return a Kibot object with:

       - local `pq` data
       - using futures data

    :param contract_type: futures contract type (e.g., "continuous", "expiry")
    :param resample_1min: whether to resample data to 1 minute or not
    """
    universe_version = "small"
    root_dir = get_test_data_dir()
    extension = "pq"
    kibot_file_client = imvkdckicl.KibotFuturesCsvParquetByAssetClient(
        universe_version,
        root_dir,
        extension,
        contract_type,
        resample_1min=resample_1min,
    )
    return kibot_file_client
