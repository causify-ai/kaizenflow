#!/usr/bin/env python
import argparse

import pandas as pd

import core.config as cconfig
import dataflow.system as dtfsys
import dataflow_amp.system.mock2.mock2_forecast_system as dtasmmfosy
import helpers.hdbg as hdbg
import helpers.hparser as hparser


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("positional", nargs="*", help="...")
    parser.add_argument("--dst_dir", action="store", help="Destination dir")
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    # report_memory_usage = True,
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # 1) Build the System.
    system = dtasmmfosy.Mock2_Time_ForecastSystem_with_DataFramePortfolio()
    # 2) Configure the System.
    system.config["system_log_dir"] = "/app/system_log_dir"
    # 2a) Configure the input data.
    # Bar duration in seconds, e.g., 60 * 60 is 1 hour bar.
    system.config["bar_duration_in_seconds"] = 60 * 60
    # Number of assets.
    system.config["market_data_config", "number_of_assets"] = 10
    # History amount, e.g., 10 days worth of data.
    system.config["market_data_config", "history_lookback"] = pd.Timedelta(
        days=10
    )
    # 2b) Configure Portfolio.
    # Maximum Portfolio notional.
    system.config[
        "process_forecasts_node_dict",
        "process_forecasts_dict",
        "optimizer_config",
        "params",
        "kwargs",
    ] = cconfig.Config.from_dict({"target_gmv": 1e7})
    # 2c) Configure `DagRunner`.
    # Propagate bar duration to `DagRunner`.
    system.config["dag_runner_config", "bar_duration_in_secs"] = system.config[
        "bar_duration_in_seconds"
    ]
    # Specify for how long to run.
    system.config["dag_runner_config", "rt_timeout_in_secs_or_time"] = (
        system.config["bar_duration_in_seconds"] * 2
    )
    # 3) Run the replayed time simulation.
    self = None
    config_tag = "mock2"
    use_unit_test_log_dir = False
    check_config = False
    _ = dtfsys.run_Time_ForecastSystem(
        self,
        system,
        config_tag,
        use_unit_test_log_dir,
        check_config=check_config,
    )


if __name__ == "__main__":
    _main(_parse())
