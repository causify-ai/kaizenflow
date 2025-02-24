"""
Import as:

import dataflow_amp.system.realtime_etl_data_observer.realtime_etl_data_observer_system_example as dtfasredoredose
"""

import pandas as pd

import core.config as cconfig
import dataflow.system as dtfsys
import dataflow_amp.system.realtime_etl_data_observer.realtime_etl_data_observer_system as dtfasredoredos


def get_RealTime_etl_DataObserver_System_example1(
    df: pd.DataFrame,
    rt_timeout_in_secs_or_time: int,
) -> dtfasredoredos.RealTime_etl_DataObserver_System:
    """
    Get `RealTime_etl_DataObserver_System` instance.

    :param df: a dataframe to build market data from
    :param rt_timeout_in_secs_or_time: a time for how long to execute
        the loop
    """
    system = dtfasredoredos.RealTime_etl_DataObserver_System()
    # Fill market data config.
    system.config["market_data_config", "asset_id_col_name"] = "asset_id"
    # Infer asset ids from data.
    system.config["market_data_config", "asset_ids"] = list(
        df[system.config["market_data_config", "asset_id_col_name"]].unique()
    )
    # TODO(Grisha): ideally use file paths instead of passing dfs to config.
    system.config["market_data_config", "data"] = df
    history_lookback = pd.Timedelta("1S")
    # TODO(Grisha): in `get_ReplayedTimeMarketData_from_df()` we use
    # `start_datetime` column to get a starting point which is incorrect
    # (should be `end_datetime`), that is why here we add 1 second manually as
    # a workaround.
    # Since we need some history, replay the data forward to have history available.
    system.config["market_data_config", "replayed_delay_in_mins_or_timestamp"] = (
        df["start_datetime"].min() + pd.Timedelta(seconds=1) + history_lookback
    )
    system.config["market_data_config", "delay_in_secs"] = 0
    #
    system.config[
        "dag_property_config", "debug_mode_config"
    ] = cconfig.Config.from_dict(
        {
            "save_node_io": "df_as_pq",
            "save_node_df_out_stats": False,
            "profile_execution": False,
        }
    )
    # Apply `DagRunner` config.
    system = dtfsys.apply_RealtimeDagRunner_config(
        system, rt_timeout_in_secs_or_time
    )
    # Apply history lookback.
    system = dtfsys.apply_history_lookback(system, days=history_lookback)
    return system
