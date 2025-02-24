"""
Generate configs for execution analysis.

Import as:

import oms.execution_analysis_configs as oexancon
"""

import logging
import os

import core.config as cconfig
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import reconciliation as reconcil

_LOG = logging.getLogger(__name__)


# #############################################################################
# Master_execution_analysis
# #############################################################################


def get_execution_analysis_configs_Cmtask4881(
    system_log_dir: str,
    bar_duration: str,
    universe_version: str,
    child_order_execution_freq: str,
    price_col: str,
    table_name: str,
    *,
    test_asset_id: int = 1464553467,
) -> cconfig.ConfigList:
    """
    Build execution analysis config with default values and provided system log
    dir.

    :param system_log_dir: dir where run logs are saved,
      e.g., ../system_log_dir.manual/process_forecasts
    :param bar_duration: length of bar in time, e.g., `5T`
    :param universe_version: version of the universe, e.g., `v7.4`
    :param child_order_execution_freq: execution frequency of child order, e.g. `1T`
    :param price_col: name of the price column, e.g., `close`
    :param table_name: name of the DB table to connect to
    :param test_asset_id: asset id to use as example
    """
    #
    id_col = "asset_id"
    vendor = "CCXT"
    mode = "trade"
    use_historical = True
    config_list = build_execution_analysis_configs(
        system_log_dir,
        id_col,
        price_col,
        table_name,
        universe_version,
        vendor,
        mode,
        test_asset_id,
        bar_duration,
        child_order_execution_freq,
        use_historical,
    )
    return config_list


def build_execution_analysis_configs(
    system_log_dir: str,
    id_col: str,
    price_col: str,
    table_name: str,
    universe_version: str,
    vendor: str,
    mode: str,
    test_asset_id: int,
    bar_duration: str,
    child_order_execution_freq: str,
    use_historical: bool,
) -> cconfig.ConfigList:
    """
    Build configs for `Master_execution_analysis` notebook.

    :param system_log_dir: path to execution logs
    :param id_col: name of asset_id column, e.g. 'asset_id'
    :param price_col: name of price column, e.g., 'close'
    :param table_name: name of the DB table to connect to
    :param universe_version: e.g. 'v7.4'
    :param vendor: vendor to load data for (e.g., CCXT)
    :param mode: download or trade universe
    :param test_asset_id: asset id to use as example, e.g. '1467591036'
    :param bar_duration: as pd.Timedelta-compatible string, e.g. '5T'
        for 5 minutes
    :param child_order_execution_freq: execution frequency of child
        orders, e.g. 1T or 30s
    :param use_historical: to use real-time or archived OHLCV data. Use
        'True' for experiments older than 3 days, 'False' otherwise.
    :return: list of configs with a single resulting config
    """
    hdbg.dassert_path_exists(system_log_dir)
    # Build the config.
    config_dict = {
        "meta": {
            "id_col": id_col,
            "use_historical": use_historical,
            "price_col": price_col,
        },
        "system_log_dir": system_log_dir,
        "market_data": {
            "vendor": vendor,
            "mode": mode,
            "universe": {
                "universe_version": universe_version,
                "test_asset_id": test_asset_id,
            },
            "im_client_config": {"table_name": table_name},
        },
        "execution_parameters": {
            "bar_duration": bar_duration,
            "execution_freq": child_order_execution_freq,
        },
    }
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list


# #############################################################################
# Master_bid_ask_execution_analysis
# #############################################################################


def get_bid_ask_execution_analysis_configs(
    system_log_dir: str,
    bar_duration: str,
    bid_ask_data_source: str,
    *,
    test_asset_id: int = 1464553467,
    use_historical: bool = False,
) -> cconfig.ConfigList:
    """
    Build default config for `Master_bid_ask_execution_analysis` using real-
    time data with provided system log dir.

    :param system_log_dir: directory of the experiment
    :param bar_duration: as pd.Timedelta-compatible string, e.g. '5T'
        for 5 minutes
    :param bid_ask_data_source: source of bid-ask data
    :param test_asset_id: asset id to use as example
    :param use_historical: to use real-time or archived OHLCV data. Use
        'True' for experiments older than 3 days, 'False' otherwise.
    """
    hdbg.dassert_path_exists(system_log_dir)
    hdbg.dassert_in(
        bid_ask_data_source,
        ["S3", "logged_during_experiment", "logged_after_experiment"],
    )
    config_dict = {
        "meta": {
            "bid_ask_data_source": bid_ask_data_source,
            "use_historical": use_historical,
        },
        "universe": {"test_asset_id": test_asset_id},
        "execution_parameters": {"bar_duration": bar_duration},
        "system_log_dir": system_log_dir,
    }
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list


# #############################################################################
# Master_broker_debugging
# #############################################################################


def get_broker_debugging_configs_Cmtask4881(
    system_log_dir: str,
) -> cconfig.ConfigList:
    """
    Build default config for `Master_broker_debugging` using real-time data
    with provided system log dir.
    """
    # TODO(Danya): Add new parameters to the config.
    hdbg.dassert_path_exists(system_log_dir)
    config_dict = {"system_log_dir": system_log_dir}
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list


# #############################################################################
# Master_broker_portfolio_reconciliation
# #############################################################################


def build_broker_portfolio_reconciliation_configs(
    system_log_dir: str,
    id_col: str,
    universe_version: str,
    price_column_name: str,
    vendor: str,
    mode: str,
    bar_duration: str,
    table_name: str,
) -> cconfig.ConfigList:
    """
    Build configs for `Master_broker_portfolio_reconciliation` notebook.

    :param system_log_dir: path to execution logs
    :param id_col: name of asset_id column, e.g. "asset_id"
    :param universe_version: e.g. "v7.4"
    :param price_column_name: name of price column, e.g., "close"
    :param vendor: vendor to load data for (e.g., CCXT)
    :param mode: download or trade universe
    :param bar_duration: as pd.Timedelta-compatible string, e.g. "5T"
        for 5 minutes
    :param table_name: name of the DB table to connect to
    :return: list of configs with a single resulting config
    """
    hdbg.dassert_path_exists(system_log_dir)
    # Build the config.
    config_dict = {
        "id_col": id_col,
        "system_log_dir": system_log_dir,
        "market_data": {
            "vendor": vendor,
            "mode": mode,
            "universe_version": universe_version,
            "im_client_config": {
                "table_name": table_name,
            },
        },
        # TODO(Nina): extract from `SystemConfig`.
        "price_column_name": price_column_name,
        "bar_duration": bar_duration,
        "share_asset_ids_with_no_fills": 0.3,
        "n_index_elements_to_ignore": 2,
        "target_positions_columns_to_compare": [
            "price",
            "holdings_shares",
            "holdings_notional",
            "target_holdings_shares",
            "target_holdings_notional",
            "target_trades_shares",
            "target_trades_notional",
        ],
        "compare_dfs_kwargs": {
            "row_mode": "inner",
            "column_mode": "inner",
            "diff_mode": "pct_change",
            "assert_diff_threshold": 1e-3,
            "log_level": logging.INFO,
        },
    }
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list


# TODO(Grisha): Consider moving universe version and bar duration extraction
# to `build_broker_portfolio_reconciliation_configs()` and killing
# the current function.
def get_broker_portfolio_reconciliation_configs_Cmtask5690(
    system_log_dir: str,
) -> cconfig.ConfigList:
    """
    Build default config for `Master_broker_portfolio_reconciliation` using
    real-time data with provided system log dir.

    :param system_log_dir: dir where run logs are saved, e.g.,
        ../system_log_dir.manual/process_forecasts
    """
    id_col = "asset_id"
    # TODO(Sameep): Repeated code. Pass it using an argument to the function.
    system_config_dir = system_log_dir.rstrip("/process_forecasts")
    # Load pickled SystemConfig.
    config_file_name = "system_config.output.values_as_strings.pkl"
    system_config_path = os.path.join(system_config_dir, config_file_name)
    system_config = cconfig.load_config_from_pickle(system_config_path)
    # Get param values from SystemConfig.
    bar_duration_in_secs = reconcil.get_bar_duration_from_config(system_config)
    bar_duration = hdateti.convert_seconds_to_pandas_minutes(bar_duration_in_secs)
    universe_version = system_config["market_data_config", "universe_version"]
    price_column_name = system_config["portfolio_config", "mark_to_market_col"]
    table_name = system_config[
        "market_data_config", "im_client_config", "table_name"
    ]
    vendor = "CCXT"
    mode = "trade"
    #
    config_list = build_broker_portfolio_reconciliation_configs(
        system_log_dir,
        id_col,
        universe_version,
        price_column_name,
        vendor,
        mode,
        bar_duration,
        table_name,
    )
    return config_list


def get_master_trading_system_report_notebook_config(
    timestamp_dir: str,
    analysis_notebooks_file_path: str,
) -> cconfig.ConfigList:
    """
    Build config for `Master_trading_system_report` notebook.

    :param timestamp_dir: path to the directory with balance data
    :param analysis_notebooks_file_path: path to the analysis notebooks
        file
    :return: list of configs with a single resulting config
    """
    hdbg.dassert_path_exists(analysis_notebooks_file_path)
    # Build the config.
    config_dict = {
        "timestamp_dir": timestamp_dir,
        "analysis_notebooks_file_path": analysis_notebooks_file_path,
    }
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list
