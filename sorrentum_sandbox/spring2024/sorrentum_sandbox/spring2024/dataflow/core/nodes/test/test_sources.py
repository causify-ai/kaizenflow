import logging
import os
from typing import Any, Optional

import pandas as pd

import dataflow.core.nodes.sources as dtfconosou
import helpers.hpandas as hpandas  # pylint: disable=no-name-in-module
import helpers.hunit_test as hunitest  # pylint: disable=no-name-in-module

_LOG = logging.getLogger(__name__)


# #############################################################################


class TestDiskDataSource(hunitest.TestCase):
    def test_datetime_index_csv1(self) -> None:
        """
        Test CSV file using timestamps in the index.
        """
        df = TestDiskDataSource._generate_df()
        #
        ext = ".csv"
        timestamp_col = None
        self._helper(df, ext, timestamp_col)

    def test_datetime_col_csv1(self) -> None:
        """
        Test CSV file using timestamps in a column.
        """
        df = TestDiskDataSource._generate_df()
        df = df.reset_index()
        #
        ext = ".csv"
        timestamp_col = "timestamp"
        self._helper(df, ext, timestamp_col)

    def test_datetime_index_parquet1(self) -> None:
        """
        Test Parquet file using timestamps in the index.
        """
        df = TestDiskDataSource._generate_df()
        #
        ext = ".pq"
        timestamp_col = None
        self._helper(df, ext, timestamp_col)

    def test_datetime_col_parquet1(self) -> None:
        """
        Test Parquet file using timestamps in a column.
        """
        df = TestDiskDataSource._generate_df()
        df = df.reset_index()
        #
        ext = ".pq"
        timestamp_col = "timestamp"
        self._helper(df, ext, timestamp_col)

    def test_filter_dates1(self) -> None:
        """
        Test date filtering with both boundaries specified for CSV file using
        timestamps in the index.
        """
        df = TestDiskDataSource._generate_df()
        #
        ext = ".csv"
        timestamp_col = None
        dds_kwargs = {"start_date": "2010-01-02", "end_date": "2010-01-05"}
        self._helper(df, ext, timestamp_col, **dds_kwargs)

    def test_filter_dates_open_boundary1(self) -> None:
        """
        Test date filtering with one boundary specified for CSV file using
        timestamps in the index.
        """
        df = TestDiskDataSource._generate_df()
        #
        ext = ".csv"
        timestamp_col = None
        dds_kwargs = {"start_date": "2010-01-02"}
        self._helper(df, ext, timestamp_col, **dds_kwargs)

    @staticmethod
    def _generate_df(num_periods: int = 10) -> pd.DataFrame:
        """
        Generate a df with a format like:
        ```
                    0
        timestamp
        2010-01-02  1
        2010-01-03  2
        2010-01-04  3
        2010-01-05  4
        ```
        """
        idx = pd.date_range("2010-01-01", periods=num_periods, name="timestamp")
        df = pd.DataFrame(range(num_periods), index=idx, columns=["0"])
        return df

    def _save_df(self, df: pd.DataFrame, ext: str) -> str:
        scratch_space = self.get_scratch_space()
        file_path = os.path.join(scratch_space, f"df{ext}")
        if ext == ".csv":
            df.to_csv(file_path)
        elif ext == ".pq":
            df.to_parquet(file_path)
        else:
            raise ValueError("Invalid extension='%s'" % ext)
        return file_path

    def _helper(
        self,
        df: pd.DataFrame,
        ext: str,
        timestamp_col: Optional[str],
        **dds_kwargs: Any,
    ) -> None:
        """
        Instantiate a `DiskDataSource` with the passed parameter, run it and
        check.
        """
        # Save the data with the proper extension.
        file_path = self._save_df(df, ext)
        # Instantiate node.
        dds = dtfconosou.DiskDataSource(
            "read_data",
            file_path=file_path,
            timestamp_col=timestamp_col,
            **dds_kwargs,
        )
        # Run node.
        loaded_df = dds.fit()["df_out"]
        # Check output.
        act_result = loaded_df.to_string()
        self.check_string(act_result)


# #############################################################################


class TestArmaDataSource(hunitest.TestCase):
    def test1(self) -> None:
        node = dtfconosou.ArmaDataSource(  # pylint: disable=no-member
            nid="source",
            frequency="30T",
            start_date="2010-01-04 09:00",
            end_date="2010-01-04 17:00",
            ar_coeffs=[0],
            ma_coeffs=[0],
            scale=0.1,
            burnin=0,
            seed=0,
        )
        df = node.fit()["df_out"]
        act = hpandas.df_to_str(df, num_rows=None, precision=2)
        self.check_string(act)


# #############################################################################


class TestMultivariateNormalDataSource(hunitest.TestCase):
    def test1(self) -> None:
        node = (
            dtfconosou.MultivariateNormalDataSource(  # pylint: disable=no-member
                nid="source",
                frequency="30T",
                start_date="2010-01-04 09:00",
                end_date="2010-01-04 17:00",
                dim=4,
                target_volatility=10,
                seed=1,
            )
        )
        df = node.fit()["df_out"]
        act = hpandas.df_to_str(df, num_rows=None, precision=2)
        self.check_string(act)
