"""
Import as:

import im_v2.common.data_snapshot.data_snapshot_utils as imvcdsdsut
"""

import re
from typing import Optional

import helpers.hdbg as hdbg
import helpers.hs3 as hs3


# TODO(gp): not super clear what it does.
def get_data_snapshot(
    root_dir: str,
    data_snapshot: str,
    aws_profile: Optional[str],
) -> str:
    """
    Resolve and check data snapshot based on `root_dir`, `aws_profile` and
    `data_snapshot`.

    :param root_dir: the base root for a 
    :param data_snapshot: `latest`, date, or empty

    - Historical data: the latest available historical snapshot

        E.g.:
        ```
        root_dir = "s3://cryptokaizen-data/reorg/historical.manual.pq"
        data_snapshot = "latest"
        im_client = ImClient(root_dir, ..., data_snapshot, ...)
        ```
    - Historical specific snapshot: identified by a date in the format
      "YYYYMMDD"

         E.g.:
         ```
         root_dir = "s3://cryptokaizen-data/reorg/historical.manual.pq"
         data_snapshot = "20220508"
         im_client = ImClient(root_dir, ..., data_snapshot, ...)
         ```
    - Daily updated data: a snapshot updated daily. `data_snapshot` param
      is an empty string

         E.g.:
         ```
         root_dir = "s3://cryptokaizen-data/reorg/daily_staged.airflow.pq"
         data_snapshot = ""
         im_client = ImClient(root_dir, ..., data_snapshot, ...)
         ```
    :param aws_profile: needed AWS profile

    :return: return the data snapshot
    """
    # TODO(Toma): commented out since CmTask2704, should think about
    # whether we really need this check here.
    # _dassert_is_valid_root_dir(aws_profile, root_dir)
    if data_snapshot == "latest":
        # Find only dirs that are numeric representation of a date, e.g.,
        # "20230524".
        # Note that we can't use a more compact regex like `\d{8}` in
        # `hs3.listdir`.
        pattern = "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"
        only_files = False
        use_relatives_paths = True
        dirs = hs3.listdir(
            root_dir,
            pattern,
            only_files,
            use_relatives_paths,
            aws_profile=aws_profile,
        )
        hdbg.dassert_lte(1, len(dirs))
        # Sanity check the results.
        regex = r"^\d{8}$"
        _ = [
            snapshot
            for snapshot in dirs
            if hdbg.dassert(
                re.match(regex, snapshot),
                msg=f"Provided data_snapshot={snapshot} does not follow the date pattern (e.g., '20230524').",
            )
        ]
        data_snapshot = max(dirs)
    # Check.
    _dassert_is_valid_data_snapshot(data_snapshot)
    return data_snapshot


def _dassert_is_valid_data_snapshot(data_snapshot: str) -> None:
    """
    Check if data snapshot is either an 8-digit or an empty string.
    """
    if not data_snapshot.isnumeric():
        hdbg.dassert_eq(data_snapshot, "")
    else:
        hdbg.dassert_eq(len(data_snapshot), 8)


def _dassert_is_valid_root_dir(aws_profile: Optional[str], root_dir: str) -> None:
    """
    Check that the root dir is valid.
    """
    hs3.dassert_is_valid_aws_profile(root_dir, aws_profile)
    if aws_profile == "ck":
        # Root dir containing fixed data snapshots, e.g., "20220828".
        historical_manual_root_dir = (
            "s3://cryptokaizen-data/reorg/historical.manual.pq"
        )
        # Root dir containing data that is daily updated by Airflow.
        daily_staged_airflow_root_dir = (
            "s3://cryptokaizen-data/reorg/daily_staged.airflow.pq"
        )
        # Root dir containing fixed data snapshots for unit testing.
        unit_test_historical_manual_root_dir = (
            "s3://cryptokaizen-unit-test/outcomes/data/historical.manual.pq"
        )
        hdbg.dassert_in(
            root_dir,
            [
                historical_manual_root_dir,
                daily_staged_airflow_root_dir,
                unit_test_historical_manual_root_dir,
            ],
        )
    elif aws_profile is None:
        pass
    else:
        raise ValueError(f"Not supported aws_profile={aws_profile}")
