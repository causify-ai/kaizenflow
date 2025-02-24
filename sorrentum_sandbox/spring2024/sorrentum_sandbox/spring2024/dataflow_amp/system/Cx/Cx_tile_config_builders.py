"""
Import as:

import dataflow_amp.system.Cx.Cx_tile_config_builders as dtfascctcbu
"""

from typing import Optional

import dataflow.backtest as dtfbcktst
import dataflow.system as dtfsys
import dataflow_amp.system.Cx.Cx_forecast_system_example as dtfasccfsex


# TODO(Grisha): kill once CmTask5854 "Resolve backtest memory leakage" is resolved.
def get_Cx_config_builder_for_historical_simulations(
    dag_builder_ctor_as_str: str,
    fit_at_beginning: bool,
    train_test_mode: str,
    backtest_config: str,
    universe_version: str,
    root_dir: str,
    partition_mode: str,
    dataset: str,
    contract_type: str,
    data_snapshot: str,
    aws_profile: str,
    resample_1min: bool,
    version: str,
    download_universe_version: str,
    tag: str,
    *,
    oos_start_date_as_str: Optional[str] = None,
) -> dtfsys.SystemConfigList:
    """
    Get a config builder function to run historical simulations.

    An executable from `amp/dataflow_amp/system/Cx/run_Cx_historical_simulation.sh`
        - i.e. `run_config_list.py`
    requires a config building function.

    :param dag_builder_ctor_as_str: same as in `Cx_NonTime_ForecastSystem`
    :param fit_at_beginning: force the system to fit before making predictions
    :param train_test_mode: same as in `Cx_NonTime_ForecastSystem`
    :param backtest_config: see `apply_backtest_config()`
    :param universe_version: same as in `HistoricalPqByCurrencyPairTileClient`
    :param root_dir: same as in `HistoricalPqByCurrencyPairTileClient`
    :param partition_mode: same as in `HistoricalPqByCurrencyPairTileClient`
    :param dataset: same as in `HistoricalPqByCurrencyPairTileClient`
    :param contract_type: same as in `HistoricalPqByCurrencyPairTileClient`
    :param data_snapshot: same as in `HistoricalPqByCurrencyPairTileClient`
    :param aws_profile: same as in `HistoricalPqByCurrencyPairTileClient`
    :param resample_1min: same as in `HistoricalPqByCurrencyPairTileClient`
    :param version: same as in `HistoricalPqByCurrencyPairTileClient`
    :param download_universe_version: same as in `HistoricalPqByCurrencyPairTileClient`
    :param tag: same as in `HistoricalPqByCurrencyPairTileClient`
    :param oos_start_date_as_str: used only for train_test_mode="ins_oos",
        see `dtfasccfsex.apply_ins_oos_backtest_config()`
    """
    im_client_config = {
        "universe_version": universe_version,
        "root_dir": root_dir,
        "partition_mode": partition_mode,
        "dataset": dataset,
        "contract_type": contract_type,
        "data_snapshot": data_snapshot,
        "aws_profile": aws_profile,
        "resample_1min": resample_1min,
        "version": version,
        "download_universe_version": download_universe_version,
        "tag": tag,
    }
    system = dtfasccfsex.get_Cx_NonTime_ForecastSystem_example(
        dag_builder_ctor_as_str,
        fit_at_beginning,
        train_test_mode=train_test_mode,
        backtest_config=backtest_config,
        im_client_config=im_client_config,
        oos_start_date_as_str=oos_start_date_as_str,
    )
    config_builder = dtfbcktst.build_tile_config_list(system, train_test_mode)
    return config_builder
