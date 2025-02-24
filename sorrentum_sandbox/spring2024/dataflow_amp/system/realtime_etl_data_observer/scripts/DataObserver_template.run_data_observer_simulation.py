#!/usr/bin/env python
import logging

import pandas as pd

import core.finance as cofinanc
import dataflow.system as dtfsys
import dataflow_amp.system.realtime_etl_data_observer.realtime_etl_data_observer_system_example as dtfasredoredose
import helpers.hdbg as hdbg

if __name__ == "__main__":
    # Set logger.
    hdbg.init_logger(
        verbosity=logging.DEBUG,
        use_exec_path=True,
        report_memory_usage=True,
    )
    # 1) Generate synthetic data.
    tz = "America/New_York"
    start_datetime = pd.Timestamp("2023-01-03 09:35:00", tz=tz)
    end_datetime = pd.Timestamp("2023-01-03 09:37:00", tz=tz)
    asset_ids = [101, 201, 301]
    columns = ["open", "high", "low", "close", "volume"]
    freq = "1S"
    df = cofinanc.generate_random_price_data(
        start_datetime, end_datetime, columns, asset_ids, freq=freq
    )
    # The param defines for how long to run the System in seconds.
    rt_timeout_in_secs_or_time = 10
    # 2) Build the System.
    system = dtfasredoredose.get_RealTime_etl_DataObserver_System_example1(
        df, rt_timeout_in_secs_or_time
    )
    system.config["system_log_dir"] = "/app/system_log_dir"
    # 3) Run the simulation.
    self = None
    config_tag = "data_observer"
    use_unit_test_log_dir = False
    check_config = False
    # TODO(Grisha): call the `dataflow_amp.system.common.system_simulation_utils.run_simulation()`
    # API instead of using the function from the TestCase. The issue is that
    # the general API has Cx config hard-wired inside.
    _ = dtfsys.run_Time_ForecastSystem(
        self,
        system,
        config_tag,
        use_unit_test_log_dir,
        check_config=check_config,
    )
