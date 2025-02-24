#!/usr/bin/env python
"""
Generate Parquet files for testing.

# Use example:
> im_v2/common/test/generate_pq_test_data.py \
    --start_date 2021-11-23 \
    --end_date 2021-11-25 \
    --freq 1T \
    --partition_mode by_year_month \
    --output_type verbose_close \
    --assets 10689,10690 \
    --dst_dir im_v2/common/test/tiled.bar_data

# In command sample above, data is created for certain interval with minutely frequency
# that is further partitioned by Parquet dataset for year and month.
```
.../tiled.bar_data/asset_id=10689/year=2021/month=11
.../tiled.bar_data/asset_id=10689/year=2021/month=11/data.parquet
.../tiled.bar_data/asset_id=10690/year=2021/month=11
.../tiled.bar_data/asset_id=10690/year=2021/month=11/data.parquet
```

# TODO(Grisha): consider moving out from `*/test` since importing `test` folders
# is not a good practice.
Import as:

import im_v2.common.test.generate_pq_test_data as imvctgptd
"""

import argparse
import logging
from typing import Callable, List, Union

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


class ParquetDataFrameGenerator:
    # Allowed types.
    OUTPUT_TYPES = ("basic", "verbose_open", "cm_task_1103")

    def __init__(
        self,
        start_date: str,
        end_date: str,
        output_type: str,
        assets: List[Union[str, int]],
        asset_col_name: str,
        freq: str,
    ) -> None:
        """
        Constructor.

        :param start_date: start of date range including start_date
        :param end_date: end of date range excluding end_date
        :param output_type: type of data that is generated
        :param assets: list of desired assets that can be names or ids
        :param asset_col_name: name of the column that stores assets
        :param freq: frequency of steps between start and end date
        """
        self._start_date = start_date
        self._end_date = end_date
        self._output_type = output_type
        self._assets = assets
        self._asset_col_name = asset_col_name
        self._freq = freq
        self._dataframe_index = pd.date_range(
            self._start_date,
            self._end_date,
            freq=self._freq,
            inclusive="left",
            tz="UTC",
        )
        self._OUTPUT_TYPE_FUNCTION_MAP = {
            "basic": self._get_daily_basic_dataframe,
            "verbose_open": self._get_verbose_open_dataframe,
            "cm_task_1103": self._get_cm_task_1103_dataframe,
        }

    @property
    def output_type_function(self) -> Callable:
        """
        Return proper function for data generation depending on output type.
        """
        return self._OUTPUT_TYPE_FUNCTION_MAP[self._output_type]

    def generate(self) -> pd.DataFrame:
        """
        Generate specific dataframe based on inputs provided in instance
        creation.
        """
        if self._output_type not in self.OUTPUT_TYPES:
            raise ValueError(f"Unsupported data type `{self._output_type}`!")
        return self.output_type_function()

    @staticmethod
    def _wrap_all_assets_df(df: List[pd.DataFrame]) -> pd.DataFrame:
        # Create a single dataframe for all the assets.
        df = pd.concat(df)
        _LOG.debug(hpandas.df_to_str(df, print_shape_info=True, tag="df"))
        return df

    def _get_core_dataframes(self) -> List[pd.DataFrame]:
        """
        Create core dataframes that are updated according to the output type.

        :return: list of core dataframes for specified assets with string values
        Example:

        ```
                     asset
        2000-01-01       A
        2000-01-02       A
        2000-01-03       A
        ```
        """
        # Generate core dataframe for each asset.
        df = []
        for asset in self._assets:
            asset_df = pd.DataFrame(
                {self._asset_col_name: asset},
                index=self._dataframe_index,
            )
            _LOG.debug(
                hpandas.df_to_str(asset_df, print_shape_info=True, tag="asset_df")
            )
            df.append(asset_df)
        return df

    def _get_daily_basic_dataframe(self) -> pd.DataFrame:
        """
        Update core dataframes with additional columns.

        :return: updated core dataframe as presented below
        Example:

        ```
                    idx asset  val1  val2
        2000-01-01    0     A    00    00
        2000-01-02    0     A    01    01
        2000-01-03    0     A    02    02
        ```
        """
        asset_dataframes = self._get_core_dataframes()
        for idx, asset_dataframe in enumerate(asset_dataframes):
            # Positioned left from `asset` column.
            asset_dataframe.insert(loc=0, column="idx", value=idx)
            # Positioned right from `asset` column.
            asset_dataframe.insert(
                loc=2,
                column="val1",
                value=list(range(len(self._dataframe_index))),
            )
            asset_dataframe.insert(
                loc=3,
                column="val2",
                value=list(range(len(self._dataframe_index))),
            )
        return self._wrap_all_assets_df(asset_dataframes)

    def _get_verbose_open_dataframe(self) -> pd.DataFrame:
        """
        Update core dataframes with additional columns.

        :return: update core dataframe as presented below
        Example:

        ```
        vendor_date  interval  start_time    end_time ticker currency  open    id
         2021-11-24        60  1637762400  1637762460      A      USD   100     1
         2021-11-24        60  1637762400  1637762460      A      USD   200     2
        ```
        """
        interval = self._dataframe_index[1] - self._dataframe_index[0]
        interval = interval.seconds
        asset_dataframes = self._get_core_dataframes()
        for id_, asset_dataframe in enumerate(asset_dataframes):
            start_time = (
                asset_dataframe.index - pd.Timestamp("1970-01-01")
            ) // pd.Timedelta("1s")
            end_time = start_time + interval
            # Positioned left from `ticker` column.
            asset_dataframe.insert(
                loc=0,
                column="vendor_date",
                value=asset_dataframe.index.date.astype(str),
            )
            asset_dataframe.insert(loc=1, column="interval", value=interval)
            asset_dataframe.insert(loc=2, column="start_time", value=start_time)
            asset_dataframe.insert(loc=3, column="end_time", value=end_time)
            # Positioned right from `ticker` column.
            asset_dataframe.insert(loc=5, column="currency", value="USD")
            asset_dataframe.insert(
                loc=6,
                column="open",
                value=list(range(len(self._dataframe_index))),
            )
            asset_dataframe.insert(loc=7, column="id", value=id_)
        return self._wrap_all_assets_df(asset_dataframes)

    # TODO(Dan): CmTask1490.
    def _get_cm_task_1103_dataframe(self) -> pd.DataFrame:
        """
        Update core dataframes with additional columns.

        :return: updated core dataframe as presented below
        Example:

        ```
                    full_symbol   close
        2000-01-01        10689     100
        2000-01-02        10689     200
        2000-01-03        10689     300
        ```
        """
        asset_dataframes = self._get_core_dataframes()
        for asset_dataframe in asset_dataframes:
            # Positioned right from asset column.
            asset_dataframe.insert(
                loc=1,
                column="close",
                value=list(range(len(self._dataframe_index))),
            )
        return self._wrap_all_assets_df(asset_dataframes)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dst_dir",
        action="store",
        type=str,
        required=True,
        help="Destination dir for generated data",
    )
    parser.add_argument(
        "--start_date",
        action="store",
        type=str,
        required=True,
        help="Date from which the data is generated, value included",
    )
    parser.add_argument(
        "--end_date",
        action="store",
        type=str,
        required=True,
        help="Date until which the data is generated, value excluded",
    )
    parser.add_argument(
        "--freq",
        action="store",
        type=str,
        default="1H",
        help="Frequency of data generation",
    )
    parser.add_argument(
        "--assets",
        action="store",
        type=str,
        required=True,
        help="Comma separated string of assets that can be either names or ids",
    )
    parser.add_argument(
        "--asset_col_name",
        action="store",
        type=str,
        required=True,
        help="Name of the column that stores assets",
    )
    parser.add_argument(
        "--output_type",
        action="store",
        type=str,
        default="basic",
        help="Type of data that is generated",
    )
    parser.add_argument(
        "--partition_mode",
        action="store",
        type=str,
        default="by_date",
        help="Partition mode for parquet DataFrame, default by date",
    )
    parser.add_argument(
        "--custom_partition_cols",
        action="store",
        type=str,
        default=None,
        help="Overrides default partition by time",
    )
    parser.add_argument(
        "--reset_index",
        action="store_true",
        help="Resets dataframe index to default sequential integer values",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def generate_parquet_files(
    start_date: str,
    end_date: str,
    assets: List[Union[str, int]],
    asset_col_name: str,
    dst_dir: str,
    *,
    freq: str = "1H",
    output_type: str = "basic",
    partition_mode: str = "by_date",
    custom_partition_cols: str = None,
    reset_index: bool = False,
) -> None:
    """
    Generate parquet files for testing.

    :param start_date: date from which the data is generated, value
        included
    :param end_date: date until which the data is generated, value
        excluded
    :param assets: list of assets that can be either names or ids
    :param asset_col_name: name of the column that stores assets
    :param dst_dir: destination dir for generated data
    :param freq: frequency of data generation
    :param output_type: type of data that is generated
    :param partition_mode: Partition mode for parquet DataFrame, default
        by date
    :param custom_partition_cols: overrides default partition by time
    :param reset_index: reset dataframe index to default sequential
        integer values
    """
    # Generate timespan.
    hdbg.dassert_lt(start_date, end_date)
    timespan = pd.date_range(start_date, end_date)
    hdbg.dassert_lt(2, len(timespan))
    # Run dataframe generation.
    pdg = ParquetDataFrameGenerator(
        start_date, end_date, output_type, assets, asset_col_name, freq
    )
    parquet_df = pdg.generate()
    # Add partition columns to the dataframe.
    df, partition_cols = hparque.add_date_partition_columns(
        parquet_df, partition_mode
    )
    if custom_partition_cols:
        # If custom partition is provided, it will override date partition.
        # Sample: `["asset", "year", "month"]`
        custom_partition_cols = custom_partition_cols.split(",")
        # Ensure that date partition columns are present.
        hdbg.dassert_is_subset(partition_cols, custom_partition_cols)
        partition_cols = custom_partition_cols
    # Partition and write dataset.
    if reset_index:
        df = df.reset_index(drop=True)
    # TODO(Nikola): When direct run is possible, expose usage of `aws_profile`
    #   so generator can be used in conjunction with `helpers.hmoto.S3Mock_TestCase`.
    #   Will probably be part of CMTask #1490.
    hparque.to_partitioned_parquet(df, partition_cols, dst_dir)


def _main(parser: argparse.ArgumentParser) -> None:
    # Parse args.
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    assets = args.assets.split(",")
    generate_parquet_files(
        args.start_date,
        args.end_date,
        assets,
        args.asset_col_name,
        args.dst_dir,
        freq=args.freq,
        output_type=args.output_type,
        partition_mode=args.partition_mode,
        custom_partition_cols=args.custom_partition_cols,
        reset_index=args.reset_index,
    )


if __name__ == "__main__":
    _main(_parse())
