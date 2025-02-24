# TODO(gp): @Nikola adapt and get these tests to work.
# import datetime
# import logging
# import os
# from typing import List, Optional
#
# import pandas as pd
#
# import helpers.hdbg as hdbg
# import helpers.hintrospection as hintros
# import helpers.hjoblib as hjoblib
# import helpers.hpandas as hpandas
# import helpers.hparquet as hparque
# import helpers.hprint as hprint
# import helpers.hunit_test as hunitest
# import im_lime.eg.eg_transform_pq_by_date_to_by_asset as imleetpbdtba
# import research.universe as reuniver
# import vendors_lime.taq_bars as vltb
#
# _LOG = logging.getLogger(__name__)
#
#
# class TestTransformByDateToByAsset1(hunitest.TestCase):
#    @staticmethod
#    def transform_helper(
#        asset_ids: List[int],
#        dates: List[str],
#        columns: Optional[List[str]],
#        args_num_threads: str,
#        log_file: str,
#        dst_dir: str,
#    ) -> None:
#        """
#        Transform by-date Parquet data from S3 into by-asset using weekly chunks.
#        """
#        hprint.log_frame(_LOG, "transform_helper")
#        _LOG.info("Processing %s asset_ids: %s", len(asset_ids), str(asset_ids))
#        # Get the input files to process.
#        dates = [pd.Timestamp(d).date() for d in dates]
#        src_file_names = [vltb.date_to_file_path(date) for date in dates]
#        _LOG.info("Processing %s Parquet files", len(src_file_names))
#        # Prepare the tasks.
#        chunk_mode = "by_year_week"
#        tasks = imleetpbdtba._prepare_tasks(
#            src_file_names, asset_ids, columns, chunk_mode, args_num_threads, dst_dir
#        )
#        # Prepare the workload.
#        func = imleetpbdtba._execute_task
#        func_name = func.__name__
#        workload = (func, func_name, tasks)
#        hjoblib.validate_workload(workload)
#        # Execute the workload.
#        dry_run = False
#        incremental = False
#        abort_on_error = True
#        num_attempts = 1
#        hjoblib.parallel_execute(
#            workload,
#            dry_run,
#            args_num_threads,
#            incremental,
#            abort_on_error,
#            num_attempts,
#            log_file,
#        )
#
#    # ///////////////////////////////////////////////////////////////////////
#
#    # TODO(gp): This is a common idiom to check that a df has a certain
#    #  signature. We could factor it out and generalize it a bit.
#    def check_df(
#        self,
#        df: pd.DataFrame,
#        func_name: str,
#        exp_str: str,
#        exp_index_dates: List[datetime.date],
#        exp_columns: List[str],
#        exp_asset_ids: List[int],
#        exp_weekofyear: List[int],
#    ) -> None:
#        _LOG.debug("df=%s", df.head())
#        _LOG.debug(hprint.to_str("exp_columns exp_asset_ids exp_weekofyear"))
#        #
#        hdbg.dassert_set_eq(exp_columns, df.columns)
#        df.sort_values(by=exp_columns, inplace=True)
#        act_str = hpandas.df_to_str(df, tag=func_name, print_shape_info=True)
#        self.assert_equal(act_str, exp_str, fuzzy_match=True)
#        #
#        act_index_dates = str(sorted(list(set(df.index.date))))
#        exp_index_dates = str(sorted(exp_index_dates))
#        self.assert_equal(act_index_dates, exp_index_dates)
#        #
#        act_columns = str(sorted(df.columns))
#        exp_columns = str(sorted(exp_columns))
#        self.assert_equal(act_columns, exp_columns)
#        #
#        act_asset_ids = str(sorted(df["asset_id"].unique()))
#        exp_asset_ids = str(sorted(exp_asset_ids))
#        self.assert_equal(act_asset_ids, exp_asset_ids)
#        #
#        act_weekofyear = str(sorted(df["weekofyear"].unique()))
#        exp_weekofyear = str(sorted(exp_weekofyear))
#        self.assert_equal(act_weekofyear, exp_weekofyear)
#
#    def check_parquet1(self, file_name: str) -> None:
#        """
#        Read:
#        - all columns
#        - all EG ids
#        - all timestamps
#        of a Parquet file and compare it to the expected values.
#        """
#        hprint.log_frame(_LOG, "check_parquet1")
#        columns_to_read = None
#        filters = None
#        #
#        df = hparque.from_parquet(
#            file_name,
#            columns=columns_to_read,
#            filters=filters,
#            log_level=logging.INFO,
#        )
#        # Check.
#        func_name = hintros.get_function_name()
#        exp_str = r"""# check_parquet1=
#        index=[2022-01-03 09:01:00-05:00, 2022-01-10 16:59:00-05:00]
#        columns=start_time,close,asset_id,year,weekofyear
#        shape=(2874, 5)
#                                                 start_time  close   asset_id  year weekofyear
#        end_time
#        2022-01-03 09:01:00-05:00 2022-01-03 09:00:00-05:00    NaN  10253  2022          1
#        2022-01-03 09:01:00-05:00 2022-01-03 09:00:00-05:00    NaN  10971  2022          1
#        2022-01-03 09:01:00-05:00 2022-01-03 09:00:00-05:00    NaN  13684  2022          1
#        ...
#        2022-01-10 16:59:00-05:00 2022-01-10 16:58:00-05:00    NaN  10253  2022          2
#        2022-01-10 16:59:00-05:00 2022-01-10 16:58:00-05:00    NaN  10971  2022          2
#        2022-01-10 16:59:00-05:00 2022-01-10 16:58:00-05:00    NaN  13684  2022          2"""
#        exp_index_dates = ["2022-01-03", "2022-01-10"]
#        exp_index_dates = [pd.Timestamp(d).date() for d in exp_index_dates]
#        exp_columns = "start_time close asset_id year weekofyear".split()
#        exp_asset_ids = [10253, 10971, 13684]
#        exp_weekofyear = [1, 2]
#        self.check_df(
#            df,
#            func_name,
#            exp_str,
#            exp_index_dates,
#            exp_columns,
#            exp_asset_ids,
#            exp_weekofyear,
#        )
#
#    def check_parquet2(self, file_name: str) -> None:
#        """
#        Read:
#        - a subset of columns
#        - all EG ids
#        - all timestamps
#        of a Parquet file and compare it to the expected values.
#        """
#        hprint.log_frame(_LOG, "check_parquet2")
#        #
#        columns_to_read = ["asset_id", "weekofyear"]
#        filters = None
#        #
#        df = hparque.from_parquet(
#            file_name,
#            columns=columns_to_read,
#            filters=filters,
#            log_level=logging.INFO,
#        )
#        # Check.
#        func_name = hintros.get_function_name()
#        exp_str = r"""# check_parquet2=
#        index=[2022-01-03 09:01:00-05:00, 2022-01-10 16:59:00-05:00]
#        columns=asset_id,weekofyear
#        shape=(2874, 2)
#                                    asset_id weekofyear
#        end_time
#        2022-01-03 09:01:00-05:00  10253          1
#        2022-01-03 09:02:00-05:00  10253          1
#        2022-01-03 09:03:00-05:00  10253          1
#        ...
#        2022-01-10 16:57:00-05:00  13684          2
#        2022-01-10 16:58:00-05:00  13684          2
#        2022-01-10 16:59:00-05:00  13684          2"""
#        exp_index_dates = ["2022-01-03", "2022-01-10"]
#        exp_index_dates = [pd.Timestamp(d).date() for d in exp_index_dates]
#        exp_columns = columns_to_read
#        exp_asset_ids = [10253, 10971, 13684]
#        exp_weekofyear = [1, 2]
#        self.check_df(
#            df,
#            func_name,
#            exp_str,
#            exp_index_dates,
#            exp_columns,
#            exp_asset_ids,
#            exp_weekofyear,
#        )
#
#    def check_parquet3(self, file_name: str) -> None:
#        """
#        Read:
#        - all columns
#        - a subset of EG ids
#        - all timestamps
#        of a Parquet file and compare it to the expected values.
#        """
#        hprint.log_frame(_LOG, "check_parquet3")
#        #
#        columns_to_read = None
#        filters = []
#        # OR of conditions.
#        filters.append([("asset_id", "=", 13684)])
#        filters.append([("asset_id", "=", 10971)])
#        #
#        df = hparque.from_parquet(
#            file_name,
#            columns=columns_to_read,
#            filters=filters,
#            log_level=logging.INFO,
#        )
#        # Check.
#        func_name = hintros.get_function_name()
#        exp_str = r"""# check_parquet3=
#        index=[2022-01-03 09:01:00-05:00, 2022-01-10 16:59:00-05:00]
#        columns=start_time,close,asset_id,year,weekofyear
#        shape=(1916, 5)
#                                                 start_time  close   asset_id  year weekofyear
#        end_time
#        2022-01-03 09:01:00-05:00 2022-01-03 09:00:00-05:00    NaN  10971  2022          1
#        2022-01-03 09:01:00-05:00 2022-01-03 09:00:00-05:00    NaN  13684  2022          1
#        2022-01-03 09:02:00-05:00 2022-01-03 09:01:00-05:00    NaN  10971  2022          1
#        ...
#        2022-01-10 16:58:00-05:00 2022-01-10 16:57:00-05:00    NaN  13684  2022          2
#        2022-01-10 16:59:00-05:00 2022-01-10 16:58:00-05:00    NaN  10971  2022          2
#        2022-01-10 16:59:00-05:00 2022-01-10 16:58:00-05:00    NaN  13684  2022          2"""
#        exp_index_dates = ["2022-01-03", "2022-01-10"]
#        exp_index_dates = [pd.Timestamp(d).date() for d in exp_index_dates]
#        exp_columns = "start_time close asset_id year weekofyear".split()
#        exp_asset_ids = [10971, 13684]
#        exp_weekofyear = [1, 2]
#        self.check_df(
#            df,
#            func_name,
#            exp_str,
#            exp_index_dates,
#            exp_columns,
#            exp_asset_ids,
#            exp_weekofyear,
#        )
#
#    def check_parquet4(self, file_name: str) -> None:
#        """
#        Read:
#        - a subset of columns
#        - one EG id
#        - a subset of time
#        of a Parquet file and compare it to the expected values.
#        """
#        hprint.log_frame(_LOG, "check_parquet3")
#        #
#        columns_to_read = ["asset_id", "year", "weekofyear"]
#        filters = []
#        # OR of AND of conditions.
#        filters.append(
#            [
#                ("asset_id", "=", 13684),
#                ("end_time", ">", pd.Timestamp("2022-01-10 09:01:00-05:00")),
#            ]
#        )
#        #
#        df = hparque.from_parquet(
#            file_name,
#            columns=columns_to_read,
#            filters=filters,
#            log_level=logging.INFO,
#        )
#        # Check.
#        func_name = hintros.get_function_name()
#        exp_str = r"""# check_parquet4=
#        index=[2022-01-10 09:02:00-05:00, 2022-01-10 16:59:00-05:00]
#        columns=asset_id,year,weekofyear
#        shape=(478, 3)
#                                    asset_id  year weekofyear
#        end_time
#        2022-01-10 09:02:00-05:00  13684  2022          2
#        2022-01-10 09:03:00-05:00  13684  2022          2
#        2022-01-10 09:04:00-05:00  13684  2022          2
#        ...
#        2022-01-10 16:57:00-05:00  13684  2022          2
#        2022-01-10 16:58:00-05:00  13684  2022          2
#        2022-01-10 16:59:00-05:00  13684  2022          2"""
#        exp_index_dates = ["2022-01-10"]
#        exp_index_dates = [pd.Timestamp(d).date() for d in exp_index_dates]
#        exp_columns = columns_to_read
#        exp_asset_ids = [13684]
#        exp_weekofyear = [2]
#        self.check_df(
#            df,
#            func_name,
#            exp_str,
#            exp_index_dates,
#            exp_columns,
#            exp_asset_ids,
#            exp_weekofyear,
#        )
#
#    # ////////////////////////////////////////////////////////////////////////
#
#    def test_transform1(self) -> None:
#        """
#        Transform original by-date S3 data:
#        - for 3 EG ids
#        - for 2 dates in 2 different weeks
#        - with a set of columns
#        - serially
#
#        Check that the output Parquet file is what is expected.
#        """
#        scratch_dir = self.get_scratch_space()
#        dst_dir = os.path.join(scratch_dir, "parquet_out")
#        log_file = os.path.join(scratch_dir, "log.txt")
#        # Read the EG ids.
#        asset_ids = sorted(reuniver.get_eg_universe_tiny())[:3]
#        # Get the input files to process.
#        dates = ["20220103", "20220110"]
#        columns = "start_time end_time asset_id close".split()
#        args_num_threads = "serial"
#        self.transform_helper(
#            asset_ids, dates, columns, args_num_threads, log_file, dst_dir
#        )
#        # Compute signature.
#        include_file_content = False
#        remove_dir_name = True
#        act = hunitest.get_dir_signature(
#            dst_dir, include_file_content, remove_dir_name=remove_dir_name
#        )
#        exp = r"""# Dir structure
#        .
#        asset_id=10253
#        asset_id=10253/year=2022
#        asset_id=10253/year=2022/weekofyear=1
#        asset_id=10253/year=2022/weekofyear=1/data.parquet
#        asset_id=10253/year=2022/weekofyear=2
#        asset_id=10253/year=2022/weekofyear=2/data.parquet
#        asset_id=10971
#        asset_id=10971/year=2022
#        asset_id=10971/year=2022/weekofyear=1
#        asset_id=10971/year=2022/weekofyear=1/data.parquet
#        asset_id=10971/year=2022/weekofyear=2
#        asset_id=10971/year=2022/weekofyear=2/data.parquet
#        asset_id=13684
#        asset_id=13684/year=2022
#        asset_id=13684/year=2022/weekofyear=1
#        asset_id=13684/year=2022/weekofyear=1/data.parquet
#        asset_id=13684/year=2022/weekofyear=2
#        asset_id=13684/year=2022/weekofyear=2/data.parquet
#        """
#        self.assert_equal(act, exp, fuzzy_match=True)
#        # Read back and check content.
#        self.check_parquet1(dst_dir)
#        #
#        self.check_parquet2(dst_dir)
#        #
#        self.check_parquet3(dst_dir)
#        #
#        self.check_parquet4(dst_dir)
