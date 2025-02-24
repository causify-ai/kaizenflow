"""
Import as:

import dataflow_amp.system.common.replayed_time_simulation_test_case as dtfascrtstc
"""

import os

import dataflow.system as dtfsys
import dataflow_amp.system.common.system_simulation_utils as dtfascssiut

# TODO(Grisha): `dataflow_amp/system/common` should not depend on
# `dataflow_amp/system/Cx`.
import dataflow_amp.system.Cx as dtfamsysc
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest


# TODO(Grisha): can we re-use `Test_Time_ForecastSystem_TestCase1` somehow?
# The functionality looks similar to what the current test case does,
# we need to understand the differences and unify the test cases.
class Test_Replayed_Time_Simulation_TestCase(hunitest.TestCase):
    """
    Test case for replayed time simulation.
    """

    def _test_save_market_data(
        self, start_timestamp_as_str: str, end_timestamp_as_str: str
    ) -> None:
        """
        Save market data for unit testing.
        """
        scratch_dir = self.get_scratch_space()
        # TODO(Grisha): rename `test_data.csv.gz` -> `market_data.csv.gz`.
        market_data_file_path = os.path.join(scratch_dir, "test_data.csv.gz")
        # Dump market data for a given interval.
        db_stage = "preprod"
        # TODO(Grisha): this is overfit for OHLCV models, expose to the interface.
        table_name = "ccxt_ohlcv_futures"
        universe_version = "v7.4"
        dtfamsysc.dump_market_data_from_db(
            market_data_file_path,
            start_timestamp_as_str,
            end_timestamp_as_str,
            db_stage,
            table_name,
            universe_version,
        )
        # Copy data to the test S3 input dir.
        s3_input_dir = self.get_s3_input_dir()
        aws_profile = "ck"
        hs3.copy_file_to_s3(market_data_file_path, s3_input_dir, aws_profile)

    def _test_run_simulation(
        self,
        system: dtfsys.System,
        start_timestamp_as_str: str,
        end_timestamp_as_str: str,
        incremental: bool,
    ) -> None:
        """
        Run simulation.
        """
        # Check if the market data file exists in the test dir on S3.
        s3_input_dir = self.get_s3_input_dir()
        aws_profile = "ck"
        s3fs_ = hs3.get_s3fs(aws_profile)
        path_exists = s3fs_.exists(s3_input_dir)
        #
        scratch_dir = self.get_scratch_space()
        # Test a case when `incremental = False` or path doesn't exist, then
        # `run_simulation()` will dump market data if either condition is false.
        if incremental and path_exists:
            # Copy market data file from S3 to a scratch dir.
            hs3.copy_data_from_s3_to_local_dir(
                s3_input_dir, scratch_dir, aws_profile
            )
        # Define params for the simulation run.
        dst_system_log_dir = os.path.join(scratch_dir, "system_log_dir")
        market_data_file_name = "test_data.csv.gz"
        market_data_file_path = os.path.join(scratch_dir, market_data_file_name)
        config_tag = "prod_system"
        check_config = True
        # Run simulation.
        result_bundle = dtfascssiut.run_simulation(
            system,
            start_timestamp_as_str,
            end_timestamp_as_str,
            market_data_file_path,
            dst_system_log_dir,
            incremental=incremental,
            config_tag=config_tag,
            self_=self,
            check_config=check_config,
        )
        # Check the run signature.
        output_col_name = "vwap.ret_0.vol_adj.shift_-2_hat"
        result_bundle = result_bundle[-1]
        # TODO(Nina): freeze log dir structure. It requires to propagate
        # `get_wall_clock_time()` to a DAG. See CmTask5927 for reference.
        actual = dtfsys.get_signature(
            system.config, result_bundle, output_col_name
        )
        self.check_string(actual, fuzzy_match=True, purify_text=True)
