import pandas as pd
import pytest 

import core.finance as cofinanc
import dataflow.system as dtfsys
import dataflow_amp.system.realtime_etl_data_observer.realtime_etl_data_observer_system_example as dtfasredoredose
import helpers.hunit_test as hunitest


class Test_run_RealTime_etl_DataObserver_System_simulation(hunitest.TestCase):
    @pytest.mark.slow("~5 seconds.")
    def test1(self) -> None:
        # Generate synthetic data.
        tz = "America/New_York"
        start_datetime = pd.Timestamp("2023-01-03 09:35:00", tz=tz)
        end_datetime = pd.Timestamp("2023-01-03 09:37:00", tz=tz)
        asset_ids = [101, 201, 301]
        columns = ["open", "high", "low", "close", "volume"]
        freq = "1S"
        df = cofinanc.generate_random_price_data(
            start_datetime, end_datetime, columns, asset_ids, freq=freq
        )
        # Build the system.
        rt_timeout_in_secs_or_time = 10
        system = dtfasredoredose.get_RealTime_etl_DataObserver_System_example1(
            df, rt_timeout_in_secs_or_time
        )
        # Run simulation.
        config_tag = "data_observer"
        check_config = True
        use_unit_test_log_dir = True
        # Use `run_Time_ForecastSystem()` to run a simulation since
        # `run_simulation()` is applicable only for Cx System for now.
        result_bundle = dtfsys.run_Time_ForecastSystem(
            self,
            system,
            config_tag,
            use_unit_test_log_dir,
            check_config=check_config,
        )
        # Check the run signature.
        output_col_name = "feature"
        result_bundle = result_bundle[-1]
        actual = dtfsys.get_signature(
            system.config, result_bundle, output_col_name
        )
        self.check_string(actual, fuzzy_match=True, purify_text=True)
