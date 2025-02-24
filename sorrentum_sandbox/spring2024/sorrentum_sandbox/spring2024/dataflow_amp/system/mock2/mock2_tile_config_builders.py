"""
Import as:

import dataflow_amp.system.mock2.mock2_tile_config_builders as dtasmmtcbu
"""

import dataflow.system as dtfsys
import dataflow_amp.system.mock2.mock2_forecast_system_example as dtasmmfsex


def build_Mock2_tile_config_list(
    backtest_config: str,
) -> dtfsys.SystemConfigList:
    """
    Build a `ConfigList` object from a backtest config for running simulations.
    """
    system = dtasmmfsex.get_Mock2_NonTime_ForecastSystem_example1(backtest_config)
    system_config_list = dtfsys.build_tile_config_list(system)
    return system_config_list


def build_Mock2_tile_config_list_for_unit_test(
    backtest_config: str,
) -> dtfsys.SystemConfigList:
    """
    Build a `ConfigList` object from a backtest config for unit testing.
    """
    system = dtasmmfsex.get_Mock2_NonTime_ForecastSystem_example2(backtest_config)
    system_config_list = dtfsys.build_tile_config_list(system)
    return system_config_list
