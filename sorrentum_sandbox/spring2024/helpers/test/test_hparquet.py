import datetime
import logging
import os
import random
from typing import Any, List, Optional, Tuple

import pandas as pd
import pyarrow
import pyarrow.parquet as parquet
import pytest

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hmoto as hmoto
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest
import im_v2.common.test as imvct

_LOG = logging.getLogger(__name__)


# Most of these unit tests are taken from
# `amp/helpers/notebooks/gallery_parquet.ipynb`


def _get_df(date: datetime.date, seed: int = 42) -> pd.DataFrame:
    """
    Create pandas random data, like:

    ```
                 idx instr  val1  val2
    2000-01-01     0     A    99    30
    2000-01-02     0     A    54    46
    2000-01-03     0     A    85    86
    ```
    """
    instruments = "A B C D E".split()
    date = pd.Timestamp(date, tz="America/New_York")
    start_date = date.replace(hour=9, minute=30)
    end_date = date.replace(hour=16, minute=0)
    df_idx = pd.date_range(start_date, end_date, freq="5T")
    _LOG.debug("df_idx=[%s, %s]", min(df_idx), max(df_idx))
    _LOG.debug("len(df_idx)=%s", len(df_idx))
    random.seed(seed)
    # For each instruments generate random data.
    df = []
    for idx, inst in enumerate(instruments):
        df_tmp = pd.DataFrame(
            {
                "idx": idx,
                "instr": inst,
                "val1": [random.randint(0, 100) for _ in range(len(df_idx))],
                "val2": [random.randint(0, 100) for _ in range(len(df_idx))],
            },
            index=df_idx,
        )
        df.append(df_tmp)
    # Create a single df for all the instruments.
    df = pd.concat(df)
    return df


def _get_test_df_with_timestamps() -> pd.DataFrame:
    """
    Create a DataFrame with timestamps.
    """
    timestamp = pd.Timestamp("2022-01-01 00:00:00.123456", tz="America/New_York")
    index = [timestamp for _ in range(6)]
    df = pd.DataFrame(
        {
            "n_legs": [2, 2, 4, 4, 5, 100],
            "animal": [
                "Flamingo",
                "Parrot",
                "Dog",
                "Horse",
                "Brittle stars",
                "Centipede",
            ],
            "year": [2001, 2002, 2001, 2003, 2003, 2001],
        },
        index=index,
    )
    knowledge_timestamp = pd.Timestamp.now(tz="UTC")
    df["knowledge_timestamp"] = knowledge_timestamp
    return df


def _get_df_example1() -> pd.DataFrame:
    date = datetime.date(2020, 1, 1)
    df = _get_df(date)
    _LOG.debug("df=\n%s", df.head(3))
    return df


def _compare_dfs(self: Any, df1: pd.DataFrame, df2: pd.DataFrame) -> str:
    df1_as_str: str = hpandas.df_to_str(df1, print_shape_info=True, tag="")
    df2_as_str = hpandas.df_to_str(df2, print_shape_info=True, tag="")
    self.assert_equal(df1_as_str, df2_as_str, fuzzy_match=True)
    # When Parquet reads partitioned dataset can convert partitioning columns into
    # categorical variables that can create false positives.
    pd.testing.assert_frame_equal(
        df1, df2, check_dtype=False, check_categorical=False
    )
    return df1_as_str


# #############################################################################


class TestParquet1(hunitest.TestCase):
    def test_get_df1(self) -> None:
        """
        Check the output of `_get_df()`.
        """
        # Prepare data.
        df = _get_df_example1()
        # Check.
        act = hpandas.df_to_str(df, print_shape_info=True, tag="df")
        exp = r"""# df=
        index=[2020-01-01 09:30:00-05:00, 2020-01-01 16:00:00-05:00]
        columns=idx,instr,val1,val2
        shape=(395, 4)
                                   idx instr  val1  val2
        2020-01-01 09:30:00-05:00    0     A    81    35
        2020-01-01 09:35:00-05:00    0     A    14    58
        2020-01-01 09:40:00-05:00    0     A     3    81
        ...
        2020-01-01 15:50:00-05:00    4     E    57     3
        2020-01-01 15:55:00-05:00    4     E    33    50
        2020-01-01 16:00:00-05:00    4     E    96    75"""
        self.assert_equal(act, exp, fuzzy_match=True)

    # //////////////////////////////////////////////////////////////////////////////

    def get_file_name(self) -> str:
        dir_name = self.get_scratch_space()
        file_name = os.path.join(dir_name, "df.parquet")
        return file_name

    def write_data_as_parquet(self) -> Tuple[pd.DataFrame, str]:
        # Prepare data.
        df = _get_df_example1()
        # Save data.
        file_name = self.get_file_name()
        hparque.to_parquet(df, file_name, log_level=logging.INFO)
        return df, file_name

    def write_and_read_helper(self, columns: List[str]) -> None:
        """
        - Save a dataframe as Parquet
        - Read back certain columns of the data from the file
        - Check that the df is what expected
        """
        df, file_name = self.write_data_as_parquet()
        # Read back one column of the data.
        df2 = hparque.from_parquet(
            file_name, columns=columns, log_level=logging.INFO
        )
        _LOG.debug("df2=\n%s", df2.head(3))
        # Check.
        df = df[columns]
        _compare_dfs(self, df, df2)

    def test_write_and_read_everything1(self) -> None:
        """
        Read all the columns from the file.
        """
        df, file_name = self.write_data_as_parquet()
        # Read data back.
        df2 = hparque.from_parquet(file_name, log_level=logging.INFO)
        _LOG.debug("df2=\n%s", df2.head(3))
        # Check.
        _compare_dfs(self, df, df2)

    def test_write_and_read_one_column1(self) -> None:
        """
        - Read back one column of the data from the file.
        """
        # Read back one column of the data.
        columns = ["val1"]
        self.write_and_read_helper(columns)

    def test_write_and_read_two_columns1(self) -> None:
        """
        Read back one column of the data from the file.
        """
        # Read back two columns of the data.
        columns = ["idx", "val1"]
        self.write_and_read_helper(columns)

    # //////////////////////////////////////////////////////////////////////////////

    def read_filtered_parquet(self, file_name: str, filters: Any) -> pd.DataFrame:
        filesystem = None
        dataset = parquet.ParquetDataset(
            file_name,
            filesystem=filesystem,
            filters=filters,
            use_legacy_dataset=False,
        )
        columns = None
        table = dataset.read(columns=columns)
        df = table.to_pandas()
        _LOG.debug("df=\n%s", df.head(3))
        return df

    def test_read_with_filter1(self) -> None:
        """
        Read only a subset of the rows.
        """
        _, file_name = self.write_data_as_parquet()
        # Read.
        filters = []
        filters.append([("idx", "=", 0)])
        df2 = self.read_filtered_parquet(file_name, filters)
        # Check.
        act = hpandas.df_to_str(df2, print_shape_info=True, tag="df")
        exp = r"""# df=
        index=[2020-01-01 09:30:00-05:00, 2020-01-01 16:00:00-05:00]
        columns=idx,instr,val1,val2
        shape=(79, 4)
                                   idx instr  val1  val2
        2020-01-01 09:30:00-05:00    0     A    81    35
        2020-01-01 09:35:00-05:00    0     A    14    58
        2020-01-01 09:40:00-05:00    0     A     3    81
        ...
        2020-01-01 15:50:00-05:00    0     A    29    76
        2020-01-01 15:55:00-05:00    0     A    12     8
        2020-01-01 16:00:00-05:00    0     A    48    49"""
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_write_and_read_partition_parquet_files_with_unit(self) -> None:
        """
        Write the Pandas DataFrame to partitioned Parquet files and read it
        back, verifying the retention of time unit information in the index.
        """
        # Prepare test data.
        dst_dir = os.path.join(self.get_scratch_space(), "tmp.partition_parquet")
        initial_df = _get_test_df_with_timestamps()
        initial_df.index = initial_df.index.as_unit("us")
        partition_columns = initial_df.columns.tolist()
        # The `to_partitioned_parquet` saves the given dataframe as Parquet
        # files partitioned along the given columns.
        hparque.to_partitioned_parquet(initial_df, partition_columns, dst_dir)
        df_from_parquet_files = hparque.from_parquet(dst_dir)
        # Check that the time unit is ns.
        self.assert_equal("ns", df_from_parquet_files.index.unit)
        # TODO(Vlad): Refactor after CmampTask7331 is resolved.
        # self.assert_equal(initial_df.index.unit, df.index.unit)

    def test_write_and_read_parquet_file_with_unit(self) -> None:
        """
        Write the provided DataFrame to Parquet file and read it back,
        verifying the retention of time unit information in the index.
        """
        test_parquet_file = os.path.join(
            self.get_scratch_space(), "tmp_dummy.parquet"
        )
        initial_df = _get_test_df_with_timestamps()
        initial_df.index = initial_df.index.as_unit("us")
        # The `to_parquet` function writes a DF to a single parquet file without
        # any partition.
        hparque.to_parquet(initial_df, test_parquet_file)
        df = hparque.from_parquet(test_parquet_file)
        self.assert_equal("ns", df.index.unit)
        # TODO(Vlad): Refactor after CmampTask7331 is resolved.
        # self.assert_equal(initial_df.index.unit, df.index.unit)

    def test_save_read_concat_data(self) -> None:
        """
        Verify that data produced by different version of Pandas preserves
        types when reading/writing to/from Parquet.
        """
        # Copy sample data that saved with the Pandas v.1.5.1 from S3 to the
        # scratch dir.
        s3_path = self.get_s3_input_dir()
        local_path = self.get_scratch_space()
        aws_profile = "ck"
        hs3.copy_data_from_s3_to_local_dir(s3_path, local_path, aws_profile)
        # Read sample data from the scratch dir.
        sample_data = hparque.from_parquet(local_path)
        # Generate artificial test data.
        data = {
            "timestamp": [1696896000000],
            "open": [27578.4],
            "high": [27584.3],
            "low": [27571.2],
            "close": [27571.3],
            "volume": [154.933],
            "exchange_id": ["binance"],
            "knowledge_timestamp": [
                pd.Timestamp("2023-11-06 14:15:11.241716+0000", tz="UTC")
            ],
        }
        index = pd.Series(
            [pd.Timestamp("2023-10-10T00:00:00+00:00")], name="timestamp"
        )
        test_data = pd.DataFrame(data, index=index)
        # Concatenate sample and test data and save it to the scratch dir.
        combined_test_data = pd.concat([sample_data, test_data])
        local_combined_file_path = os.path.join(
            local_path, "combined_dummy.parquet"
        )
        hparque.to_parquet(combined_test_data, local_combined_file_path)
        # Read the data back from the scratch dir.
        actual_df = hparque.from_parquet(local_combined_file_path)
        # Check that the data types the same as in the sample data.
        dtypes_sample = str(sample_data.dtypes)
        dtypes_actual = str(actual_df.dtypes)
        self.assert_equal(dtypes_sample, dtypes_actual, fuzzy_match=True)


# #############################################################################


class TestPartitionedParquet1(hunitest.TestCase):
    # From https://arrow.apache.org/docs/python/dataset.html#reading-partitioned-data
    # A dataset can exploit a nested structure, where the sub-dir names hold
    # information about which subset of the data is stored in that dir
    # E.g., "Hive" partitioning scheme "key=vale" dir names

    def write_partitioned_dataset_and_check(
        self,
        df: pd.DataFrame,
        partition_cols: List[str],
        exp_dir_signature: Optional[str],
    ) -> str:
        """
        - Write df as a partitioned dataset
        - (Optional) Check the signature of the directory

        :param partition_cols: columns used for
        :param exp_dir_signature: expected signature of the written directory
        :return path to the saved Parquet data
        """
        _LOG.debug(hprint.to_str("partition_cols"))
        # Prepare data.
        dir_name = os.path.join(self.get_scratch_space(), "data.parquet")
        table = pyarrow.Table.from_pandas(df)
        # Write partitioned dataset.
        parquet.write_to_dataset(
            table,
            dir_name,
            partition_cols,
        )
        # Check dir signature.
        if exp_dir_signature is not None:
            include_file_content = False
            remove_dir_name = True
            dir_signature = hunitest.get_dir_signature(
                dir_name, include_file_content, remove_dir_name=remove_dir_name
            )
            self.assert_equal(
                dir_signature,
                exp_dir_signature,
                fuzzy_match=True,
                purify_text=True,
            )
        return dir_name

    def write_and_read_helper(
        self,
        df: pd.DataFrame,
        partition_cols: List[str],
        exp_dir_signature: Optional[str],
        columns_to_read: Optional[List[str]],
    ) -> str:
        """
        - Write df as a partitioned dataset using `partitioned_cols`
        - Read certain column back

        :param partition_cols: columns used for
        :param exp_dir_signature: expected signature of the written directory
        :return: read df as string
        """
        _LOG.debug(hprint.to_str("partition_cols columns_to_read"))
        # Write and check.
        dir_name = self.write_partitioned_dataset_and_check(
            df, partition_cols, exp_dir_signature
        )
        # Read back certain columns.
        df2 = hparque.from_parquet(
            dir_name, columns=columns_to_read, log_level=logging.INFO
        )
        # Compare.
        if columns_to_read is not None:
            df = df[columns_to_read]
        #
        hdbg.dassert_set_eq(df.columns, df2.columns)
        df2 = df2[df.columns]
        df_as_str = _compare_dfs(self, df, df2)
        return df_as_str

    # //////////////////////////////////////////////////////////////////////////////

    def test_write_and_read1(self) -> None:
        """
        - Write a partitioned dataset with one partitioning column
        - Read everything back
        """
        df = _get_df_example1()
        partition_cols = ["idx"]
        exp_dir_signature = r"""
        # Dir structure
        .
        idx=0
        idx=0/data.parquet
        idx=1
        idx=1/data.parquet
        idx=2
        idx=2/data.parquet
        idx=3
        idx=3/data.parquet
        idx=4
        idx=4/data.parquet"""
        columns_to_read = None
        self.write_and_read_helper(
            df, partition_cols, exp_dir_signature, columns_to_read
        )

    def test_write_and_read2(self) -> None:
        """
        - Write a partitioned dataset with two partitioning columns
        - Read everything back
        """
        df = _get_df_example1()
        partition_cols = ["idx", "instr"]
        exp_dir_signature = r"""# Dir structure
        .
        idx=0
        idx=0/instr=A
        idx=0/instr=A/data.parquet
        idx=1
        idx=1/instr=B
        idx=1/instr=B/data.parquet
        idx=2
        idx=2/instr=C
        idx=2/instr=C/data.parquet
        idx=3
        idx=3/instr=D
        idx=3/instr=D/data.parquet
        idx=4
        idx=4/instr=E
        idx=4/instr=E/data.parquet"""
        # Read back everything.
        columns_to_read = None
        self.write_and_read_helper(
            df, partition_cols, exp_dir_signature, columns_to_read
        )

    def test_write_and_read3(self) -> None:
        """
        - Write a partitioned dataset with one partitioning column
        - Read two columns back
        """
        df = _get_df_example1()
        partition_cols = ["idx"]
        exp_dir_signature = None
        columns_to_read = ["idx", "instr"]
        df_as_str = self.write_and_read_helper(
            df, partition_cols, exp_dir_signature, columns_to_read
        )
        exp = r"""# =
        index=[2020-01-01 09:30:00-05:00, 2020-01-01 16:00:00-05:00]
        columns=idx,instr
        shape=(395, 2)
                                   idx instr
        2020-01-01 09:30:00-05:00    0     A
        2020-01-01 09:35:00-05:00    0     A
        2020-01-01 09:40:00-05:00    0     A
        ...
        2020-01-01 15:50:00-05:00    4     E
        2020-01-01 15:55:00-05:00    4     E
        2020-01-01 16:00:00-05:00    4     E"""
        self.assert_equal(df_as_str, exp, fuzzy_match=True)

    def test_write_and_read4(self) -> None:
        """
        - Write a partitioned dataset with one partitioning column
        - Read two columns back filtering by the one of the partitioned column
        """
        df = _get_df_example1()
        partition_cols = ["idx"]
        exp_dir_signature = None
        # Write and check.
        dir_name = self.write_partitioned_dataset_and_check(
            df, partition_cols, exp_dir_signature
        )
        # Read back everything.
        columns_to_read = ["idx", "instr"]
        filters = []
        filters.append(("idx", "=", 0))
        # Note that `from_parquet` doesn't work with filters.
        # df2 = hparque.from_parquet(
        #     dir_name,
        #     columns=columns_to_read,
        #     filters=filters,
        #     log_level=logging.INFO,
        # )
        filesystem = None
        dataset = parquet.ParquetDataset(
            dir_name,
            filesystem=filesystem,
            filters=filters,
            use_legacy_dataset=False,
        )
        table = dataset.read(columns=columns_to_read)
        df2 = table.to_pandas()
        # Compare.
        df_as_str = hpandas.df_to_str(df2, print_shape_info=True, tag="df")
        exp = r"""# df=
        index=[0, 78]
        columns=idx,instr
        shape=(79, 2)
          idx instr
        0   0     A
        1   0     A
        2   0     A
        ...
        76   0     A
        77   0     A
        78   0     A"""
        self.assert_equal(df_as_str, exp, fuzzy_match=True)

    # //////////////////////////////////////////////////////////////////////////////

    def test_merge1(self) -> None:
        """
        - Write a partitioned dataset in multiple chunks using the same partitioning
          column
        - Make sure that reading it back we get the original data.
        """
        df = _get_df_example1()
        #
        partition_cols = ["idx"]
        # Write the first chunk.
        df_chunk1 = df[df["idx"].isin([0, 1])]
        exp_dir_signature = """
        # Dir structure
        .
        idx=0
        idx=0/data.parquet
        idx=1
        idx=1/data.parquet"""
        # Write and check.
        _ = self.write_partitioned_dataset_and_check(
            df_chunk1, partition_cols, exp_dir_signature
        )
        # Write the second chunk.
        df_chunk2 = df[df["idx"].isin([2, 3, 4])]
        exp_dir_signature = """
        # Dir structure
        .
        idx=0
        idx=0/data.parquet
        idx=1
        idx=1/data.parquet
        idx=2
        idx=2/data.parquet
        idx=3
        idx=3/data.parquet
        idx=4
        idx=4/data.parquet"""
        # Write and check.
        dir_name = self.write_partitioned_dataset_and_check(
            df_chunk2, partition_cols, exp_dir_signature
        )
        # Read everything.
        columns_to_read = None
        df2 = hparque.from_parquet(
            dir_name, columns=columns_to_read, log_level=logging.INFO
        )
        # Compare.
        hdbg.dassert_set_eq(df.columns, df2.columns)
        df2 = df2[df.columns]
        df_as_str = _compare_dfs(self, df, df2)
        exp = r"""
        # =
        index=[2020-01-01 09:30:00-05:00, 2020-01-01 16:00:00-05:00]
        columns=idx,instr,val1,val2
        shape=(395, 4)
                                   idx instr  val1  val2
        2020-01-01 09:30:00-05:00    0     A    81    35
        2020-01-01 09:35:00-05:00    0     A    14    58
        2020-01-01 09:40:00-05:00    0     A     3    81
        ...
        2020-01-01 15:50:00-05:00    4     E    57     3
        2020-01-01 15:55:00-05:00    4     E    33    50
        2020-01-01 16:00:00-05:00    4     E    96    75"""
        self.assert_equal(df_as_str, exp, fuzzy_match=True)
        self.assert_equal(df_as_str, exp, fuzzy_match=True)

    def test_write_and_read_mixed_units_partition_dataset_1(self) -> None:
        """
        Write two DataFrames with different time units to a partitioned Parquet
        dataset and read it back.

        The combination `ns` and `us` should not raise an error.
        See CmampTask7331 for details.
        """
        self._run_write_and_read_mixed_units_partitioned_dataset("ns", "us")

    @pytest.mark.skip(
        reason="Since names and order the files is not guaranteed, the test is "
        "flaky, decided to skip it for now.",
    )
    def test_write_and_read_mixed_units_partition_dataset_2(self) -> None:
        """
        Write two DataFrames with different time units to a partitioned Parquet
        dataset and read it back.

        The combination `ms` and `us` should raise an error.
        """
        with self.assertRaises(pyarrow.lib.ArrowInvalid):
            self._run_write_and_read_mixed_units_partitioned_dataset("ms", "us")

    def _run_write_and_read_mixed_units_partitioned_dataset(
        self, first_unit: str, second_unit: str
    ) -> None:
        """
        Write two DataFrames with different time units to a partitioned Parquet
        dataset and read it back.

        :param first_unit: time unit of the first DataFrame
        :param second_unit: time unit of the second DataFrame
        """
        initial_df = _get_test_df_with_timestamps()
        partition_columns = ["n_legs", "animal", "year"]
        dst_dir = os.path.join(self.get_scratch_space(), "tmp.pp_mixed_units")
        # Write first DF as partitioned parquet.
        first_df = initial_df.copy()
        first_df.index = first_df.index.as_unit(first_unit)
        first_df["knowledge_timestamp"] = first_df["knowledge_timestamp"].astype(
            f"datetime64[{first_unit}, UTC]"
        )
        hparque.to_partitioned_parquet(first_df, partition_columns, dst_dir)
        # Write second DF as partitioned parquet.
        second_df = initial_df.copy()
        second_df.index = second_df.index.as_unit(second_unit)
        second_df["knowledge_timestamp"] = second_df[
            "knowledge_timestamp"
        ].astype(f"datetime64[{second_unit}, UTC]")
        hparque.to_partitioned_parquet(second_df, partition_columns, dst_dir)
        # Read it back.
        _ = hparque.from_parquet(dst_dir)


# #############################################################################


class TestGetParquetFiltersFromTimestampInterval1(hunitest.TestCase):
    def test_no_interval(self) -> None:
        """
        No timestamps provided.
        """
        partition_mode = "by_year_month"
        start_ts = None
        end_ts = None
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode, start_ts, end_ts
        )
        self.assertIsNone(filters)

    def test_by_month_half1(self) -> None:
        """
        Test a left-bound interval [..., None].
        """
        partition_mode = "by_year_month"
        start_ts = pd.Timestamp("2020-01-02 09:31:00+00:00")
        end_ts = None
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode, start_ts, end_ts
        )
        actual = str(filters)
        expected = (
            r"[[('year', '==', 2020), ('month', '>=', 1)], [('year', '>', 2020)]]"
        )
        self.assert_equal(actual, expected)

    def test_by_month_half2(self) -> None:
        """
        Test a right-bound interval [None, ...].
        """
        partition_mode = "by_year_month"
        start_ts = None
        end_ts = pd.Timestamp("2020-01-02 09:31:00+00:00")
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode, start_ts, end_ts
        )
        actual = str(filters)
        expected = (
            r"[[('year', '==', 2020), ('month', '<=', 1)], [('year', '<', 2020)]]"
        )
        self.assert_equal(actual, expected)

    def test_by_month_one_year1(self) -> None:
        """
        Test an interval contained in a whole year.
        """
        partition_mode = "by_year_month"
        start_ts = pd.Timestamp("2020-01-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2020-12-02 09:31:00+00:00")
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode, start_ts, end_ts
        )
        actual = str(filters)
        expected = (
            r"[[('year', '==', 2020), ('month', '>=', 1), ('month', '<=', 12)]]"
        )
        self.assert_equal(actual, expected)

    def test_by_month_one_year2(self) -> None:
        """
        Test an interval contained in a whole year.
        """
        partition_mode = "by_year_month"
        start_ts = pd.Timestamp("2020-01-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2020-01-02 09:32:00+00:00")
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode, start_ts, end_ts
        )
        actual = str(filters)
        expected = (
            r"[[('year', '==', 2020), ('month', '>=', 1), ('month', '<=', 1)]]"
        )
        self.assert_equal(actual, expected)

    def test_by_month_invalid1(self) -> None:
        """
        Test an invalid interval.
        """
        partition_mode = "by_year_month"
        start_ts = pd.Timestamp("2020-01-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2020-01-02 09:30:00+00:00")
        with self.assertRaises(AssertionError) as fail:
            hparque.get_parquet_filters_from_timestamp_interval(
                partition_mode, start_ts, end_ts
            )
        actual = str(fail.exception)
        expected = r"""
        * Failed assertion *
        2020-01-02 09:31:00+00:00 <= 2020-01-02 09:30:00+00:00
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_by_month_invalid2(self) -> None:
        """
        Test an invalid partition mode.
        """
        partition_mode = "new_mode"
        start_ts = pd.Timestamp("2020-01-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2020-01-02 09:32:00+00:00")
        with self.assertRaises(ValueError) as fail:
            hparque.get_parquet_filters_from_timestamp_interval(
                partition_mode, start_ts, end_ts
            )
        actual = str(fail.exception)
        expected = r"Unknown partition mode `new_mode`!"
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_by_month_two_years1(self) -> None:
        """
        Test an interval spanning two years.
        """
        partition_mode = "by_year_month"
        start_ts = pd.Timestamp("2020-06-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2021-12-02 09:31:00+00:00")
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode, start_ts, end_ts
        )
        actual = str(filters)
        expected = (
            r"[[('year', '==', 2020), ('month', '>=', 6)], "
            r"[('year', '==', 2021), ('month', '<=', 12)]]"
        )
        self.assert_equal(actual, expected)

    def test_by_month_over_two_years1(self) -> None:
        """
        Test an interval longer than two years.
        """
        partition_mode = "by_year_month"
        start_ts = pd.Timestamp("2020-06-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2022-12-02 09:31:00+00:00")
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode, start_ts, end_ts
        )
        actual = str(filters)
        expected = (
            r"[[('year', '==', 2020), ('month', '>=', 6)], "
            r"[('year', '>', 2020), ('year', '<', 2022)], "
            r"[('year', '==', 2022), ('month', '<=', 12)]]"
        )
        self.assert_equal(actual, expected)

    def test_additional_filters1(self) -> None:
        """
        No timestamps provided while a single additional filter is provided.
        """
        partition_mode = "by_year_month"
        start_ts = None
        end_ts = None
        additional_filters = [
            (
                "currency_pair",
                "in",
                ("BTC_USDT",),
            )
        ]
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode,
            start_ts,
            end_ts,
            additional_filters=additional_filters,
        )
        actual = str(filters)
        expected = r"[('currency_pair', 'in', ('BTC_USDT',))]"
        self.assert_equal(actual, expected)

    def test_additional_filters2(self) -> None:
        """
        Test an interval with multiple additional filters.
        """
        partition_mode = "by_year_month"
        start_ts = pd.Timestamp("2020-06-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2022-12-02 09:31:00+00:00")
        additional_filters = [
            ("exchange_id", "in", ("binance")),
            ("currency_pairs", "in", ("ADA_USDT", "BTC_USDT")),
        ]
        filters = hparque.get_parquet_filters_from_timestamp_interval(
            partition_mode,
            start_ts,
            end_ts,
            additional_filters=additional_filters,
        )
        actual = str(filters)
        expected = (
            r"[[('exchange_id', 'in', 'binance'), "
            r"('currency_pairs', 'in', ('ADA_USDT', 'BTC_USDT')), "
            r"('year', '==', 2020), ('month', '>=', 6)], "
            r"[('exchange_id', 'in', 'binance'), "
            r"('currency_pairs', 'in', ('ADA_USDT', 'BTC_USDT')), "
            r"('year', '>', 2020), ('year', '<', 2022)], "
            r"[('exchange_id', 'in', 'binance'), "
            r"('currency_pairs', 'in', ('ADA_USDT', 'BTC_USDT')), "
            r"('year', '==', 2022), ('month', '<=', 12)]]"
        )
        self.assert_equal(actual, expected)


# #############################################################################


class TestAddDatePartitionColumns(hunitest.TestCase):
    def add_date_partition_columns_helper(
        self, partition_mode: str, expected: str
    ) -> None:
        # Prepare inputs.
        test_data = {
            "dummy_value": [1, 2, 3],
            "dummy_timestamp": [1638646800000, 1638646860000, 1638646960000],
        }
        start_timestamp = "2021-12-04 19:40:00+00:00"
        end_timestamp = "2021-12-04 19:42:00+00:00"
        index = pd.date_range(start_timestamp, end_timestamp, freq="1T")
        df = pd.DataFrame(index=index, data=test_data)
        # Run.
        hparque.add_date_partition_columns(df, partition_mode)
        # Check output.
        actual = hpandas.df_to_str(df)
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_add_date_partition_columns1(self) -> None:
        partition_mode = "by_date"
        expected = r"""                           dummy_value  dummy_timestamp      date
        2021-12-04 19:40:00+00:00            1    1638646800000  20211204
        2021-12-04 19:41:00+00:00            2    1638646860000  20211204
        2021-12-04 19:42:00+00:00            3    1638646960000  20211204"""
        self.add_date_partition_columns_helper(partition_mode, expected)

    def test_add_date_partition_columns2(self) -> None:
        partition_mode = "by_year"
        expected = r"""                           dummy_value  dummy_timestamp  year
        2021-12-04 19:40:00+00:00            1    1638646800000  2021
        2021-12-04 19:41:00+00:00            2    1638646860000  2021
        2021-12-04 19:42:00+00:00            3    1638646960000  2021"""
        self.add_date_partition_columns_helper(partition_mode, expected)

    def test_add_date_partition_columns3(self) -> None:
        partition_mode = "by_year_month_day"
        # pylint: disable=line-too-long
        expected = r"""                           dummy_value  dummy_timestamp  year  month  day
        2021-12-04 19:40:00+00:00            1    1638646800000  2021     12    4
        2021-12-04 19:41:00+00:00            2    1638646860000  2021     12    4
        2021-12-04 19:42:00+00:00            3    1638646960000  2021     12    4"""
        self.add_date_partition_columns_helper(partition_mode, expected)

    def test_add_date_partition_columns4(self) -> None:
        partition_mode = "by_year_week"
        expected = r"""                           dummy_value  dummy_timestamp  year  weekofyear
        2021-12-04 19:40:00+00:00            1    1638646800000  2021          48
        2021-12-04 19:41:00+00:00            2    1638646860000  2021          48
        2021-12-04 19:42:00+00:00            3    1638646960000  2021          48"""
        self.add_date_partition_columns_helper(partition_mode, expected)


# #############################################################################


class TestToPartitionedDataset(hunitest.TestCase):
    @staticmethod
    def get_test_data1() -> pd.DataFrame:
        test_data = {
            "dummy_value_1": [1, 2, 3],
            "dummy_value_2": ["A", "B", "C"],
            "dummy_value_3": [0, 0, 0],
        }
        df = pd.DataFrame(data=test_data)
        return df

    def test_get_test_data1(self) -> None:
        test_data = self.get_test_data1()
        act = hpandas.df_to_str(test_data)
        exp = r"""
           dummy_value_1 dummy_value_2  dummy_value_3
        0              1             A              0
        1              2             B              0
        2              3             C              0"""
        self.assert_equal(act, exp, fuzzy_match=True)

    @pytest.mark.skip(
        reason="CmTask1305: after removing circular dependencies in "
        "`hio.from_file`, this test fails reading a parquet file"
    )
    def test_to_partitioned_dataset(self) -> None:
        """
        Test partitioned Parquet datasets with existing columns.
        """
        # Prepare inputs.
        test_dir = self.get_scratch_space()
        df = self.get_test_data1()
        # Run.
        partition_cols = ["dummy_value_1", "dummy_value_2"]
        hparque.to_partitioned_parquet(df, partition_cols, test_dir)
        # Check output.
        include_file_content = False
        remove_dir_name = True
        dir_signature = hunitest.get_dir_signature(
            test_dir, include_file_content, remove_dir_name=remove_dir_name
        )
        exp = r"""
        # Dir structure
        .
        dummy_value_1=1
        dummy_value_1=1/dummy_value_2=A
        dummy_value_1=1/dummy_value_2=A/data.parquet
        dummy_value_1=2
        dummy_value_1=2/dummy_value_2=B
        dummy_value_1=2/dummy_value_2=B/data.parquet
        dummy_value_1=3
        dummy_value_1=3/dummy_value_2=C
        dummy_value_1=3/dummy_value_2=C/data.parquet"""
        self.assert_equal(dir_signature, exp, purify_text=True, fuzzy_match=True)
        #
        include_file_content = True
        dir_signature = hunitest.get_dir_signature(
            test_dir, include_file_content, remove_dir_name=remove_dir_name
        )
        self.check_string(dir_signature, purify_text=True, fuzzy_match=True)

    def test_to_partitioned_dataset_wrong_column(self) -> None:
        """
        Assert that wrong columns are detected before partitioning.
        """
        # Prepare inputs.
        test_dir = self.get_scratch_space()
        df = self.get_test_data1()
        # Run.
        partition_cols = ["void_column", "dummy_value_2"]
        # Check output.
        with self.assertRaises(AssertionError) as cm:
            hparque.to_partitioned_parquet(df, partition_cols, test_dir)
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        val1=['dummy_value_2', 'void_column']
        issubset
        val2=['dummy_value_1', 'dummy_value_2', 'dummy_value_3']
        val1 - val2=['void_column']
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


@pytest.mark.requires_ck_infra
@pytest.mark.requires_aws
@pytest.mark.skipif(
    not henv.execute_repo_config_code("is_CK_S3_available()"),
    reason="Run only if CK S3 is available",
)
class TestListAndMergePqFiles(hmoto.S3Mock_TestCase):
    def generate_test_data(self) -> hs3.AwsProfile:
        """
        Upload test daily Parquet files for 3 days to the mocked S3 bucket.
        """
        start_date = "2022-02-02"
        end_date = "2022-02-04"
        assets = ["A", "B", "C", "D", "E", "F"]
        asset_col_name = "asset"
        test_dir = self.get_scratch_space()
        partition_mode = "by_year_month"
        custom_partition_cols = "asset,year,month"
        imvct.generate_parquet_files(
            start_date,
            end_date,
            assets,
            asset_col_name,
            test_dir,
            partition_mode=partition_mode,
            custom_partition_cols=custom_partition_cols,
        )
        s3fs_ = hs3.get_s3fs(self.mock_aws_profile)
        s3_bucket = f"s3://{self.bucket_name}"
        s3fs_.put(test_dir, s3_bucket, recursive=True)
        return s3fs_

    @pytest.mark.slow("~7 seconds.")
    def test_list_and_merge_pq_files(self) -> None:
        """
        Check if predefined generated Parquet files are properly merged.
        """
        s3fs_ = self.generate_test_data()
        # Prepare common `hs3.listdir` params.
        s3_bucket = f"s3://{self.bucket_name}"
        pattern = "*.parquet"
        only_files = True
        use_relative_paths = True
        # Check bucket content before merge.
        parquet_path_list_before = hs3.listdir(
            s3_bucket, pattern, only_files, use_relative_paths, aws_profile=s3fs_
        )
        self.assertEqual(len(parquet_path_list_before), 6)
        # Add extra parquet files and rename existing one.
        # e.g., `dummy.parquet`, `dummy_new.parquet`.
        # Every second file is left intact to replicate ready out-of-the-box folder.
        # e.g., `asset=A/year=2022/month=2/77a2534aaf9649fab6511cea53a6bf7f-0.parquet`.
        for path in parquet_path_list_before[::2]:
            original_path = f"{s3_bucket}/{path}"
            original_file_name = os.path.basename(original_path)
            renamed_path = original_path.replace(
                original_file_name, "dummy.parquet"
            )
            additional_path = original_path.replace(
                original_file_name, "dummy_new.parquet"
            )
            s3fs_.rename(original_path, renamed_path)
            s3fs_.copy(renamed_path, additional_path)
        # Check if edits are in place.
        updated_parquet_path_list = hs3.listdir(
            s3_bucket, pattern, only_files, use_relative_paths, aws_profile=s3fs_
        )
        data_parquet_path_list = [
            path for path in updated_parquet_path_list if "dummy" not in path
        ]
        self.assertEqual(len(updated_parquet_path_list), 9)
        self.assertEqual(len(data_parquet_path_list), 3)
        # Check bucket content after merge.
        hparque.list_and_merge_pq_files(self.bucket_name, aws_profile=s3fs_)
        parquet_path_list_after = hs3.listdir(
            s3_bucket, pattern, only_files, use_relative_paths, aws_profile=s3fs_
        )
        parquet_path_list_after.sort()
        expected_list = [
            "tmp.scratch/asset=A/year=2022/month=2/data.parquet",
            "tmp.scratch/asset=B/year=2022/month=2/data.parquet",
            "tmp.scratch/asset=C/year=2022/month=2/data.parquet",
            "tmp.scratch/asset=D/year=2022/month=2/data.parquet",
            "tmp.scratch/asset=E/year=2022/month=2/data.parquet",
            "tmp.scratch/asset=F/year=2022/month=2/data.parquet",
        ]
        self.assertListEqual(parquet_path_list_after, expected_list)

    def test_list_and_merge_pq_files_duplicate_drop(self) -> None:
        # Prepare test data.
        test_data = {
            "dummy_value_1": [1, 1, 1],
            "dummy_value_2": ["A", "A", "A"],
            "knowledge_timestamp": [1, 2, 3],
            "end_download_timestamp": [3, 2, 1],
        }
        df = pd.DataFrame(data=test_data)
        # Save test data to s3 bucket.
        s3fs_ = hs3.get_s3fs(self.mock_aws_profile)
        s3_bucket = f"s3://{self.bucket_name}"
        original_sample_path = f"{s3_bucket}/dummy/data.parquet"
        dummy_sample_path = original_sample_path.replace(
            "data.parquet", "dummy.parquet"
        )
        hparque.to_parquet(df, dummy_sample_path, aws_profile=s3fs_)
        # Check if new columns are in place.
        df = hparque.from_parquet(dummy_sample_path, aws_profile=s3fs_)
        self.assertIn("knowledge_timestamp", df.columns)
        self.assertIn("end_download_timestamp", df.columns)
        self.assertEqual(len(df), 3)
        # Check if duplicates are dropped after merge.
        hparque.list_and_merge_pq_files(self.bucket_name, aws_profile=s3fs_)
        df = hparque.from_parquet(original_sample_path, aws_profile=s3fs_)
        self.assertEqual(len(df), 1)


# #############################################################################


class TestListAndMergePqFilesMixedUnits(hunitest.TestCase):
    def test_parquet_files_with_mixed_time_units_1(self) -> None:
        """
        Test merging Parquet files with the `ns` and `us`.
        """
        first_unit = "ns"
        second_unit = "us"
        self._list_and_merge_mixed_units_pq_files(first_unit, second_unit)

    def test_parquet_files_with_mixed_time_units_2(self) -> None:
        """
        Test merging Parquet files with the `ms` and `ns`.

        It should raise an error. See CmampTask7331 for details.

        The test will not raise an asserion when the time units is `ms` and
        `us`. The reason is that we do not lose data when converting from
        the first time unit, which is `ms`, to the second time unit, which
        is `us`, transitioning from low resolution to high resolution.
        """
        first_unit = "us"
        second_unit = "ms"
        with self.assertRaises(pyarrow.lib.ArrowInvalid):
            self._list_and_merge_mixed_units_pq_files(first_unit, second_unit)

    def _list_and_merge_mixed_units_pq_files(
        self, first_unit: str, second_unit: str
    ) -> None:
        """
        Run `list_and_merge_pq_files` with different time units in the same
        column and index.

        :param first_unit: first time unit.
        :param second_unit: second time unit.
        """
        # Prepare test data.
        dst_dir = os.path.join(self.get_scratch_space(), "tmp.list_and_merge")
        first_file_name = os.path.join(dst_dir, "tmp.1first.parquet")
        second_file_name = os.path.join(dst_dir, "tmp.2second.parquet")
        merged_file_name = os.path.join(dst_dir, "tmp.merged.parquet")
        # Write first DF with the `first_unit`.
        initial_df = _get_test_df_with_timestamps()
        first_df = initial_df.copy()
        first_df.index = first_df.index.as_unit(first_unit)
        first_df["knowledge_timestamp"] = first_df["knowledge_timestamp"].astype(
            f"datetime64[{first_unit}, UTC]"
        )
        hparque.to_parquet(first_df, first_file_name)
        # Write second DF with the `second_unit`.
        second_df = initial_df.copy()
        second_df.index = second_df.index.as_unit(second_unit)
        second_df["knowledge_timestamp"] = second_df[
            "knowledge_timestamp"
        ].astype(f"datetime64[{second_unit}, UTC]")
        hparque.to_parquet(second_df, second_file_name)
        # List and merge.
        hparque.list_and_merge_pq_files(dst_dir, file_name="tmp.merged.parquet")
        # Read it back.
        _ = hparque.from_parquet(merged_file_name)


# #############################################################################


class TestYieldParquetTiles(hunitest.TestCase):
    def generate_test_data(self) -> None:
        """
        Generate test data and write it to a scratch dir.

        Data has the following structure:

        ```
                    asset_id  ...  year  month
        end_ts
        2021-11-01       100       2021     11
        2021-11-01       200       2021     11
        2021-11-01       300       2021     11
        ...
        2022-02-01       200       2022      2
        2022-02-01       300       2022      2
        2022-02-01       400       2022      2
        ```
        """
        # Generate synthetic data.
        asset_ids = [100, 200, 300, 400]
        prices = list(range(1, 17))
        volatility = list(range(17, 33))
        dates = ["2021-11-01", "2021-12-01", "2022-01-01", "2022-02-01"]
        dates = map(pd.Timestamp, dates)
        index_ = [dates, asset_ids]
        multi_index = pd.MultiIndex.from_product(
            index_, names=["end_ts", "asset_id"]
        )
        df = pd.DataFrame(
            {"price": prices, "volatility": volatility}, index=multi_index
        )
        df["year"] = df.index.get_level_values(0).year
        df["month"] = df.index.get_level_values(0).month
        df = df.reset_index(level=1)
        _LOG.debug("Test data: df=\n%s", hpandas.df_to_str(df))
        # Write the data to a scratch dir.
        partition_columns = ["asset_id", "year", "month"]
        dst_dir = self.get_scratch_space()
        hparque.to_partitioned_parquet(df, partition_columns, dst_dir)

    def test_yield_tiles_by_asset(self) -> None:
        """
        Test reading only certain asset ids.
        """
        self.generate_test_data()
        # Read data.
        file_name = self.get_scratch_space()
        asset_ids = [100, 200]
        asset_id_col = "asset_id"
        asset_batch_size = 1
        columns = [asset_id_col, "price"]
        generator_ = hparque.yield_parquet_tiles_by_assets(
            file_name, asset_ids, asset_id_col, asset_batch_size, columns
        )
        df = pd.concat(generator_)
        _LOG.debug("Filtered data: df=\n%s", hpandas.df_to_str(df))
        # Check asset ids filtering.
        actual = str(asset_ids)
        expected = str(df[asset_id_col].unique().tolist())
        self.assert_equal(actual, expected)

    def test_yield_tiles_by_year(self) -> None:
        """
        Test reading only certain asset ids and dates.
        """
        self.generate_test_data()
        # Read data.
        file_name = self.get_scratch_space()
        start_year = 2021
        start_month = 12
        start_date = datetime.date(start_year, start_month, 1)
        end_year = 2022
        end_month = 1
        end_date = datetime.date(end_year, end_month, 2)
        asset_ids = [300, 400]
        asset_id_col = "asset_id"
        columns = [asset_id_col, "price"]
        generator_ = hparque.yield_parquet_tiles_by_year(
            file_name,
            start_date,
            end_date,
            columns,
            asset_ids=asset_ids,
            asset_id_col=asset_id_col,
        )
        df = pd.concat(generator_)
        _LOG.debug("Filtered data: df=\n%s", hpandas.df_to_str(df))
        # Check asset ids filtering.
        actual = str(asset_ids)
        expected = str(df[asset_id_col].unique().tolist())
        self.assert_equal(actual, expected)
        # Check start date filtering.
        min_date = df.index.min()
        self.assertEqual(min_date.month, start_month)
        self.assertEqual(min_date.year, start_year)
        # Check end date filtering.
        max_date = df.index.max()
        self.assertEqual(max_date.month, end_month)
        self.assertEqual(max_date.year, end_year)


# #############################################################################


class TestBuildFilterWithOnlyEqualities(hunitest.TestCase):
    def test_year_month_day_equality(self) -> None:
        """
        Test interval with same year, month and day.
        """
        start_ts = pd.Timestamp("2022-12-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2022-12-02 21:31:00+00:00")
        filters = hparque.build_filter_with_only_equalities(start_ts, end_ts)
        actual = str(filters)
        expected = (
            r"[('year', '==', 2022), ('month', '==', 12), ('day', '==', 2)]"
        )
        self.assert_equal(actual, expected)

    def test_year_month_equality(self) -> None:
        """
        Test interval with same year and month.
        """
        start_ts = pd.Timestamp("2022-12-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2022-12-28 21:31:00+00:00")
        filters = hparque.build_filter_with_only_equalities(start_ts, end_ts)
        actual = str(filters)
        expected = r"[('year', '==', 2022), ('month', '==', 12)]"
        self.assert_equal(actual, expected)

    def test_year_equality(self) -> None:
        """
        Test interval with same year.
        """
        start_ts = pd.Timestamp("2022-10-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2022-12-02 21:31:00+00:00")
        filters = hparque.build_filter_with_only_equalities(start_ts, end_ts)
        actual = str(filters)
        expected = r"[('year', '==', 2022)]"
        self.assert_equal(actual, expected)

    def test_no_equality(self) -> None:
        """
        Test interval with different start and end years.
        """
        start_ts = pd.Timestamp("2021-10-02 09:31:00+00:00")
        end_ts = pd.Timestamp("2022-10-02 21:31:00+00:00")
        filters = hparque.build_filter_with_only_equalities(start_ts, end_ts)
        actual = str(filters)
        expected = r"[]"
        self.assert_equal(actual, expected)
