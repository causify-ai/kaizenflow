"""
Import as:

import reconciliation.sim_prod_reconciliation as rsiprrec
"""

import datetime
import itertools
import logging
import os
import pprint
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.model as dtfmod
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hsystem as hsystem
import oms.broker.ccxt.ccxt_utils as obccccut
import oms.order_processing.target_position_and_order_generator as ooptpaoge
import oms.portfolio.portfolio as oporport
import optimizer.forecast_evaluator_with_optimizer as ofevwiop

_LOG = logging.getLogger(__name__)

# Each function should accept a `log_level` parameter that controls at which
# level output summarizing the results. By default it is set by function to
# logging.DEBUG (since we don't want to print anything).
# The internal debugging info is printed as usual at level `logging.DEBUG`.


def _get_config_from_signature(signature: str) -> Dict[str, str]:
    """
    Parse signature string into key-value mapping according to the
    config_schema.

    :param signature: config signature to parse,
        eg: /shared_data/ecs/test/prod_reconciliation.C5b.20230829_165500.20230829_175000.prod.manual
    """
    # TODO(sonaal): We can move this to separate function just like dataset_schema_util.
    config_schema = "dag_builder_name.start_timestamp_as_str.end_timestamp_as_str.run_mode.mode"
    keys = config_schema.split(".")
    values = signature.split(".")
    hdbg.dassert_eq(len(keys), len(values))
    config = {keys[i]: values[i] for i in range(len(keys))}
    return config


# #############################################################################
# Config
# #############################################################################


def build_reconciliation_configs_instance1(
    dst_root_dir: str,
    signature: str,
    dag_builder_ctor_as_str: str,
) -> cconfig.ConfigList:
    """
    Build reconciliation config with signature.

    :param dst_root_dir: dir to store the reconciliation results in
    :param signature: string representation of configs as signature
    :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
        e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
    """
    config_dict = _get_config_from_signature(signature)
    config_dict["dag_builder_name"]
    start_timestamp_as_str = config_dict["start_timestamp_as_str"]
    end_timestamp_as_str = config_dict["end_timestamp_as_str"]
    run_mode = config_dict["run_mode"]
    mode = config_dict["mode"]
    config_list = build_reconciliation_configs(
        dst_root_dir,
        dag_builder_ctor_as_str,
        start_timestamp_as_str,
        end_timestamp_as_str,
        run_mode,
        mode,
    )
    return config_list


# TODO(Grisha): separate crypto and equities (e.g., create 2 functions).
# TODO(Grisha): add a separate config for the slow version of the
# Master system reconciliation notebook.
def build_reconciliation_configs(
    dst_root_dir: str,
    dag_builder_ctor_as_str: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    run_mode: str,
    mode: str,
    *,
    tag: str = "",
    set_config_values: Optional[str] = None,
) -> cconfig.ConfigList:
    """
    Build reconciliation configs that are specific of an asset class.

    Note: the function returns list of configs because the function is used
    as a config builder function for the run notebook script.

    :param dst_root_dir: dir to store the reconciliation results in, e.g.,
        "/shared_data/prod_reconciliation/"
    :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
        e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
    :param start_timestamp_as_str: string representation of timestamp
        at which to start reconcile run, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp
        at which to end reconcile run, e.g. "20221010_080000"
    :param run_mode: prod run mode, e.g. "prod" or "paper_trading"
    :param mode: reconciliation run mode, i.e., "scheduled" and "manual"
    param tag: config tag, e.g., "config1"
    :param set_config_values: see `reconcile_run_all` for detailed description
    :return: list of reconciliation configs
    """
    run_date = get_run_date(start_timestamp_as_str)
    _LOG.info("Using run_date=%s", run_date)
    #
    asset_key = "AM_ASSET_CLASS"
    if asset_key in os.environ:
        asset_class = os.environ[asset_key]
    else:
        asset_class = "crypto"
    # Set values for variables that are specific of an asset class.
    if asset_class == "crypto":
        dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
            dag_builder_ctor_as_str
        )
        # For crypto the TCA part is not implemented yet.
        run_tca = False
        target_dir = get_target_dir(
            dst_root_dir,
            dag_builder_name,
            run_mode,
            start_timestamp_as_str,
            end_timestamp_as_str,
            tag=tag,
        )
        system_log_path_dict = get_system_log_dir_paths(target_dir, mode)
        system_log_dir = system_log_path_dict["prod"]
        config_file_name = "system_config.output.values_as_strings.pkl"
        config_path = os.path.join(system_log_dir, config_file_name)
        system_config = cconfig.load_config_from_pickle(config_path)
        # Get bar duration from config.
        bar_duration_in_secs = get_bar_duration_from_config(system_config)
        bar_duration = hdateti.convert_seconds_to_pandas_minutes(
            bar_duration_in_secs
        )
        # Get column names from `DagBuilder`.
        dag_builder = dtfcore.get_DagBuilder_from_string(dag_builder_ctor_as_str)
        fep_init_dict = {
            "price_col": dag_builder.get_column_name("price"),
            "prediction_col": dag_builder.get_column_name("prediction"),
            "volatility_col": dag_builder.get_column_name("volatility"),
        }
        quantization = None
        # TODO(Grisha): consider exposing file path to config instead of
        # storing the whole mapping in the config.
        asset_id_to_share_decimals = obccccut.get_asset_id_to_share_decimals()
        gmv = 3000.0
        liquidate_at_end_of_day = False
        initialize_beginning_of_day_trades_to_zero = False
    elif asset_class == "equities":
        run_tca = True
        #
        bar_duration = "15T"
        #
        root_dir = ""
        search_str = ""
        prod_dir_cmd = f"find {root_dir}/{run_date}/prod -name '{search_str}'"
        _, prod_dir = hsystem.system_to_string(prod_dir_cmd)
        cand_cmd = (
            f"find {root_dir}/{run_date}/job.candidate.* -name '{search_str}'"
        )
        _, cand_dir = hsystem.system_to_string(cand_cmd)
        system_log_path_dict = {
            "prod": prod_dir,
            "cand": cand_dir,
            "sim": os.path.join(root_dir, run_date, "system_log_dir"),
        }
        #
        fep_init_dict = {
            "price_col": "twap",
            "prediction_col": "prediction",
            "volatility_col": "garman_klass_vol",
        }
        quantization = 0
        asset_id_to_share_decimals = None
        gmv = 20000.0
        liquidate_at_end_of_day = True
        initialize_beginning_of_day_trades_to_zero = True
    else:
        raise ValueError(f"Unsupported asset class={asset_class}")
    # Sanity check dirs.
    for dir_name in system_log_path_dict.values():
        hdbg.dassert_dir_exists(dir_name)
    # Build config.
    config_dict = {
        "meta": {
            "date_str": run_date,
            "asset_class": asset_class,
            "run_tca": run_tca,
            "bar_duration": bar_duration,
            "compute_research_portfolio_mode": "automatic",
            "get_dag_output_mode": "automatic",
        },
        "system_log_path": system_log_path_dict,
        "dag_builder_ctor_as_str": dag_builder_ctor_as_str,
        "forecast_evaluator_config": {
            "forecast_evaluator_type": "ForecastEvaluatorFromPrices",
            "init": fep_init_dict,
            "annotate_forecasts_kwargs": {
                "quantization": quantization,
                "liquidate_at_end_of_day": liquidate_at_end_of_day,
                "initialize_beginning_of_day_trades_to_zero": initialize_beginning_of_day_trades_to_zero,
                "burn_in_bars": 3,
                "asset_id_to_share_decimals": asset_id_to_share_decimals,
            },
        },
    }
    # Set the default optimizer config values.
    style = "cross_sectional"
    optimizer_config_kwargs = {
        "bulk_frac_to_remove": 0.0,
        "target_gmv": gmv,
    }
    #
    optimizer_dict = {
        "forecast_evaluator_config": {
            "annotate_forecasts_kwargs": {
                "style": style,
                **optimizer_config_kwargs,
            }
        }
    }
    # Create default optimizer config.
    config = cconfig.Config.from_dict(config_dict)
    optimizer_config = cconfig.Config.from_dict(optimizer_dict)
    config.update(optimizer_config)
    #
    if set_config_values is not None and "optimizer_config" in set_config_values:
        # Update optimizer config for a `ForecastEvaluator` using the
        # SystemConfig overrides.
        config = build_optimizer_config_from_config_overrides(
            config_dict, set_config_values
        )
    else:
        _LOG.debug("No optimzer config overrides found, using the default config")
    # Put config in a config list for compatability with the `run_notebook.py`
    # script.
    config_list = cconfig.ConfigList([config])
    return config_list


# TODO(Grisha): read optimizer parameters from SystemConfig instead of
# inferring them from `set_config_values`. See CmTask7725 for details.
def build_optimizer_config_from_config_overrides(
    config_dict: Dict[str, Any],
    set_config_values: str,
) -> cconfig.Config:
    """
    Create a config with optimizer overrides using the values passed from the
    cmd line.

    :param config_dict: config params
    :param set_config_values: values to override in the config
    :return: reconciliation notebook config with optimizer overrides
    """
    set_config_values_list = set_config_values.split(";")
    override_config = cconfig.Config()
    override_config = cconfig.apply_config(
        override_config, set_config_values_list
    )
    # Get optimizer config params from config overrides.
    optimizer_config = override_config["process_forecasts_node_dict"][
        "process_forecasts_dict"
    ]["optimizer_config"]
    optimizer_config_params = optimizer_config["params"]
    #
    if "batch_optimizer" in set_config_values:
        # Set `batch_optimizer` config params in the config.
        config_dict["forecast_evaluator_config"][
            "forecast_evaluator_type"
        ] = "ForecastEvaluatorWithOptimizer"
        optimizer_config_params["verbose"] = False
        optimizer_config_dict = {"optimizer_config_dict": optimizer_config_params}
        config_dict["forecast_evaluator_config"]["init"].update(
            optimizer_config_dict
        )
        # Create config with `batch_optimizer`.
        config = cconfig.Config.from_dict(config_dict)
    else:
        # Set `pomo_optimizer` config params in the config.
        if "style" in optimizer_config_params:
            style = optimizer_config_params["style"]
        if "kwargs" in optimizer_config_params:
            optimizer_config_kwargs = optimizer_config_params["kwargs"]
        config_dict["forecast_evaluator_config"]["annotate_forecasts_kwargs"][
            "style"
        ] = style
        config_dict["forecast_evaluator_config"][
            "annotate_forecasts_kwargs"
        ].update(optimizer_config_kwargs)
        # Override config for `pomo` optimizer from command line.
        config = cconfig.Config.from_dict(config_dict)
    return config


def build_multiday_system_reconciliation_config(
    dst_root_dir: str,
    dag_builder_ctor_as_str: str,
    run_mode: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
) -> cconfig.ConfigList:
    """
    Build multiday system reconciliation config.

    :param dst_root_dir: dir to store the reconciliation results in, e.g.,
        "/shared_data/prod_reconciliation/"
    :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
        e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
    :param run_mode: prod run mode, e.g. "prod" or "paper_trading"
    :param start_timestamp_as_str: string representation of timestamp
        at which to start reconcile run, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp
        at which to end reconcile run, e.g. "20221010_080000"
    """
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    # We add timezone info to `start_timestamp_as_str` and `end_timestamp_as_str`
    # because they are passed in the "UTC" timezone.
    tz = "UTC"
    datetime_format = "%Y%m%d_%H%M%S"
    start_timestamp = hdateti.str_to_timestamp(
        start_timestamp_as_str, tz, datetime_format=datetime_format
    )
    end_timestamp = hdateti.str_to_timestamp(
        end_timestamp_as_str, tz, datetime_format=datetime_format
    )
    config = {
        "dst_root_dir": dst_root_dir,
        "dag_builder_ctor_as_str": dag_builder_ctor_as_str,
        "dag_builder_name": dag_builder_name,
        "run_mode": run_mode,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "pnl_resampling_frequency": "5T",
    }
    config = cconfig.Config().from_dict(config)
    config_list = cconfig.ConfigList([config])
    return config_list


# TODO(Grisha): Factor out common code with `build_reconciliation_configs()`.
def build_prod_pnl_real_time_observer_configs(
    prod_data_root_dir: str,
    dag_builder_ctor_as_str: str,
    run_mode: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    mode: str,
    save_plots_for_investors: bool,
    *,
    tag: str = "",
    s3_dst_dir: Optional[str] = None,
) -> cconfig.ConfigList:
    """
    Build prod PnL real-time observer configs.

    Note: the function returns list of configs because the function is used
    as a config builder function for the run notebook script.

    :param prod_data_root_dir: dir to store the production results in, e.g.,
        "/shared_data/ecs/preprod/system_reconciliation/"
    :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
        e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
    :param start_timestamp_as_str: string representation of timestamp
        at which a production run started, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp
        at which a production run ended, e.g. "20221010_080000"
    :param mode: prod run mode, i.e., "scheduled" and "manual"
    :param save_plots_for_investors: whether to save PnL plots for investors or not
    :param tag: config tag, e.g., "config1"
    :param s3_dst_dir: dst dir where to save plots for investors on S3
    :return: list of configs
    """
    run_date = get_run_date(start_timestamp_as_str)
    _LOG.info("Using run_date=%s", run_date)
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    prod_data_dir = get_target_dir(
        prod_data_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
    )
    #
    system_log_subdir = get_prod_system_log_dir(mode)
    system_log_dir = os.path.join(prod_data_dir, system_log_subdir)
    hdbg.dassert_dir_exists(system_log_dir)
    # Get necessary data from `DagBuilder`.
    dag_builder = dtfcore.get_DagBuilder_from_string(dag_builder_ctor_as_str)
    dag_config = dag_builder.get_config_template()
    bar_duration = dag_config["resample"]["transformer_kwargs"]["rule"]
    fep_init_dict = {
        "price_col": dag_builder.get_column_name("price"),
        "prediction_col": dag_builder.get_column_name("prediction"),
        "volatility_col": dag_builder.get_column_name("volatility"),
    }
    quantization = None
    market_info = obccccut.load_market_data_info()
    asset_id_to_share_decimals = obccccut.subset_market_info(
        market_info, "amount_precision"
    )
    gmv = 3000.0
    liquidate_at_end_of_day = False
    initialize_beginning_of_day_trades_to_zero = False
    # Build the config.
    config_dict = {
        "meta": {
            "dag_builder_name": dag_builder_name,
            "date_str": run_date,
            "bar_duration": bar_duration,
            "save_plots_for_investors": save_plots_for_investors,
        },
        "s3_dst_dir": s3_dst_dir,
        "system_log_dir": system_log_dir,
        "dag_builder_ctor_as_str": dag_builder_ctor_as_str,
        "research_forecast_evaluator_from_prices": {
            "init": fep_init_dict,
            "annotate_forecasts_kwargs": {
                "style": "cross_sectional",
                "quantization": quantization,
                "liquidate_at_end_of_day": liquidate_at_end_of_day,
                "initialize_beginning_of_day_trades_to_zero": initialize_beginning_of_day_trades_to_zero,
                # TODO(Grisha): should it be a function of a model?
                # TODO(Grisha): ideally the value should come from `run_master_pnl_real_time_observer_notebook()`
                # because some bars are burnt already there. E.g., the first 3 bars skipped by the
                # `run_master_pnl_real_time_observer_notebook()` -> no need to burn here.
                "burn_in_bars": 0,
                "asset_id_to_share_decimals": asset_id_to_share_decimals,
                "bulk_frac_to_remove": 0.0,
                "target_gmv": gmv,
            },
        },
    }
    config = cconfig.Config.from_dict(config_dict)
    config_list = cconfig.ConfigList([config])
    return config_list


# /////////////////////////////////////////////////////////////////////////////


def load_config_dict_from_pickle(
    system_log_path_dict: Dict[str, str]
) -> Dict[str, cconfig.Config]:
    """
    Load output (i.e. after the system is fully built) configs from pickle
    files given a dict of paths.
    """
    config_dict = {}
    file_name = "system_config.output.values_as_strings.pkl"
    for stage, path in system_log_path_dict.items():
        path = os.path.join(path, file_name)
        config = cconfig.load_config_from_pickle(path)
        config_dict[stage] = config
    return config_dict


def get_bar_duration_from_config(config: cconfig.Config) -> int:
    """
    Get bar duration value from Config.
    """
    val = config["dag_runner_config", "bar_duration_in_secs"]
    if isinstance(val, str):
        _LOG.warning("Found Config v2 flow, converting value to int.")
        val = int(val)
    else:
        # Bar duration is stored as int for Config v3 version and higher.
        hdbg.dassert_type_is(val, int)
    return val


def get_universe_version_from_config_overrides(
    set_config_values: Optional[str],
) -> Optional[str]:
    """
    Retrieve the specified universe version if available from passed values;
    otherwise, return `None`.

    See `reconcile_run_all()` for param description.
    """
    universe_version = None
    if set_config_values:
        re_pattern = r"\"universe_version\"\)\s*,\s*\(.*?\"(.*?)\"\)\)"
        match = re.search(re_pattern, set_config_values)
        if match is not None:
            universe_version = match.group(1)
    return universe_version


# /////////////////////////////////////////////////////////////////////////////


# TODO(Grisha): seems more general than this file.
def _dassert_is_date(date: str) -> None:
    """
    Check if an input string is a date.

    :param date: date as string, e.g., "20221101"
    """
    hdbg.dassert_isinstance(date, str)
    try:
        _ = datetime.datetime.strptime(date, "%Y%m%d")
    except ValueError as e:
        raise ValueError(f"date='{date}' doesn't have the right format: {e}")


# TODO(Grisha): -> `_get_run_date_from_start_timestamp`.
def get_run_date(start_timestamp_as_str: Optional[str]) -> str:
    """
    Return the run date as string from start timestamp, e.g. "20221017".

    If start timestamp is not specified by a user then return current
    date.

    E.g., "20221101_064500" -> "20221101".
    """
    if start_timestamp_as_str is None:
        # TODO(Grisha): do not use default values.
        run_date = datetime.date.today().strftime("%Y%m%d")
    else:
        # TODO(Dan): Add assert for `start_timestamp_as_str` regex.
        run_date = start_timestamp_as_str.split("_")[0]
    _LOG.info(hprint.to_str("run_date"))
    _dassert_is_date(run_date)
    return run_date


# #############################################################################
# System reconciliation flow
# #############################################################################


def reconcile_create_dirs(
    dag_builder_ctor_as_str: str,
    run_mode: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    # TODO(Grisha): should be the 1st param.
    dst_root_dir: str,
    abort_if_exists: bool,
    backup_dir_if_exists: bool,
    *,
    tag: str = "",
) -> None:
    """
    Create dirs for storing reconciliation data.

    Final dirs layout is:
    ```
    {dst_root_dir}/
        {dag_builder_name}/
            {run_mode}/
                {start_timestamp_as_str}.{end_timestamp_as_str}/
                    prod/
                    simulation/
                    tca/
                    reconciliation_notebook/
                    ...
    ```

    See `reconcile_run_all()` for params description.

    :param abort_if_exists: see `hio.create_dir()`
    :param backup_dir_if_exists: see `hio.create_dir()`
    """
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    target_dir = get_target_dir(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
    )
    # Create a dir for reconcilation results.
    hio.create_dir(
        target_dir,
        incremental=True,
        abort_if_exists=abort_if_exists,
        backup_dir_if_exists=backup_dir_if_exists,
    )
    # Create dirs for storing prod and simulation results.
    prod_target_dir = get_prod_dir(target_dir)
    sim_target_dir = get_simulation_dir(target_dir)
    hio.create_dir(
        prod_target_dir, incremental=True, abort_if_exists=abort_if_exists
    )
    hio.create_dir(
        sim_target_dir, incremental=True, abort_if_exists=abort_if_exists
    )
    # Create dir for publishing reconciliation notebook.
    notebook_target_dir = get_reconciliation_notebook_dir(target_dir)
    hio.create_dir(
        notebook_target_dir, incremental=True, abort_if_exists=abort_if_exists
    )
    # Create dir for dumped TCA data.
    if run_mode == "prod":
        # Transaction costs analysis is not applicable when running with a mocked
        # broker.
        tca_target_dir = get_tca_dir(target_dir)
        hio.create_dir(
            tca_target_dir, incremental=True, abort_if_exists=abort_if_exists
        )
    # Sanity check the created dirs.
    cmd = f"ls -lh {target_dir}"
    hsystem.system(cmd, suppress_output=False, log_level="echo")


# #############################################################################


def get_system_reconciliation_notebook_path(notebook_run_mode: str) -> str:
    """
    Get a system reconciliation notebook path.

    :param notebook_run_mode: version of the notebook to run
        - "fast": run fast checks only, i.e. compare DAG output for the last
            node / last bar timestamp
        - "slow": run slow checks only,  i.e. compare DAG output for all nodes / all
            bar timestamps
    :return: path to a system reconciliation notebook, e.g.,
        ".../.../Master_system_reconciliation.slow.ipynb"
    """
    hdbg.dassert_in(notebook_run_mode, ["fast", "slow"])
    amp_dir = hgit.get_amp_abs_path()
    base_name = "Master_system_reconciliation"
    notebook_path = os.path.join(
        amp_dir, "oms", "notebooks", f"{base_name}_{notebook_run_mode}.ipynb"
    )
    hdbg.dassert_file_exists(notebook_path)
    return notebook_path


def get_multiday_system_reconciliation_notebook_path() -> str:
    """
    Get a multiday system reconciliation notebook path.

    :return: path to a multiday system reconciliation notebook, e.g.,
        ".../.../Master_multiday_system_reconciliation.ipynb"
    """
    amp_dir = hgit.get_amp_abs_path()
    notebook_path = os.path.join(
        amp_dir, "oms", "notebooks", "Master_multiday_system_reconciliation.ipynb"
    )
    return notebook_path


def get_multiday_reconciliation_dir(
    dst_root_dir: str,
    dag_builder_name: str,
    run_mode: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
) -> str:
    """
    Return multiday reconciliation results dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/paper_trading/multiday/20230707_101000.20230717_100500".
    """
    multiday_dir_path = os.path.join(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        "multiday",
        f"{start_timestamp_as_str}.{end_timestamp_as_str}",
    )
    return multiday_dir_path


def get_prod_dir(dst_root_dir: str) -> str:
    """
    Return prod results dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/paper_trading/20230702_100500.20230703_100000/prod".
    """
    prod_dir = os.path.join(
        dst_root_dir,
        "prod",
    )
    return prod_dir


def get_simulation_dir(dst_root_dir: str) -> str:
    """
    Return simulation results dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/paper_trading/20230702_100500.20230703_100000/simulation".
    """
    sim_dir = os.path.join(
        dst_root_dir,
        "simulation",
    )
    return sim_dir


def _get_timestamp_dirs(
    dst_root_dir: str,
    dag_builder_name: str,
    tag: str,
    run_mode: str,
) -> List[str]:
    """
    Get all timestamp dirs for the specified inputs.

    :param dst_root_dir: a root dir containing the prod system run results
    :param dag_builder_name: name of the DAG builder, e.g. "C1b"
    :param run_mode: prod system run mode, e.g. "prod" or "paper_trading"
    :return: a list of timestamp dirs, e.g.:
        ```
        [
            "20220212_101500.20220213_100500",
            "20220213_101500.20220214_100500",
            ...
        ]
        ```
    """
    dag_builder_dir = f"{dag_builder_name}.{tag}" if tag != "" else dag_builder_name
    target_dir = os.path.join(dst_root_dir, dag_builder_dir, run_mode)
    # `listdir()` utilizes `glob` which has limited functionality compared
    # to regex so other variations of the pattern might not work.
    date_pattern = "[0-9]" * 8
    time_pattern = "[0-9]" * 6
    # E.g., "20220212_101500.20220213_100500".
    pattern = f"{date_pattern}_{time_pattern}.{date_pattern}_{time_pattern}"
    only_files = False
    use_relatives_paths = True
    # Search in the given directory in order not to slow down the time
    # execution.
    maxdepth = 1
    # Get list of all timestamp dirs in the target dir.
    timestamp_dirs = hs3.listdir(
        target_dir,
        pattern,
        only_files,
        use_relatives_paths,
        maxdepth=maxdepth,
    )
    # pylint: disable=line-too-long
    # Filter timestamp dirs by regex to exclude pattern-like dirs from subdirs
    # which are returned as relative paths, e.g., "multiday/20220213_101500.20220214_100500".
    # pylint: enable=line-too-long
    # TODO(Grisha): do not search recursively. The assumption is that all the
    # timestamp dirs are under the `target_dir`.
    timestamp_dirs = [dir_ for dir_ in timestamp_dirs if re.match(pattern, dir_)]
    timestamp_dirs = sorted(timestamp_dirs)
    return timestamp_dirs


def get_system_run_timestamps(
    dst_root_dir: str,
    dag_builder_name: str,
    tag: str,
    run_mode: str,
    start_timestamp: Optional[pd.Timestamp],
    end_timestamp: Optional[pd.Timestamp],
) -> List[Tuple[str, str]]:
    """
    Get system run timestamps in between start and end dates from dir names.

    :param dst_root_dir: a root dir containing the prod system run results
    :param dag_builder_name: name of the DAG builder, e.g. "C1b"
    :param run_mode: prod system run mode, e.g. "prod" or "paper_trading"
    :param start_timestamp: a timestamp to start collect data from
    :param end_timestamp: a timestamp to collect data until to
    :return: sorted list of tuples that contains start and end timestamps
        as strings, e.g., `[("20230715_131000", "20230716_130500"), ...]`
    """
    _LOG.debug(
        hprint.to_str(
            "dst_root_dir dag_builder_name run_mode start_timestamp end_timestamp"
        )
    )
    tz = "UTC"
    if start_timestamp is not None:
        hdateti.dassert_has_specified_tz(start_timestamp, tz)
    if end_timestamp is not None:
        hdateti.dassert_has_specified_tz(end_timestamp, tz)
    # Find all availiable timestamp dirs.
    timestamp_dirs = _get_timestamp_dirs(
        dst_root_dir, dag_builder_name, tag, run_mode
    )
    # Get start and end timestamps from a timestamp dir name. E.g.,
    # `[("20230723_131000", "20230724_130500"), ...]`.
    system_run_timestamps = [tuple(ts.split(".")) for ts in timestamp_dirs]
    # Keep timestamps within the `[start_date, end_date]` range.
    datetime_format = "%Y%m%d_%H%M%S"
    # Filter by start / end timestamps using system run start timestamp.
    if start_timestamp is not None:
        system_run_timestamps = [
            (system_run_start_timestamp, system_run_end_timestamp)
            for (
                system_run_start_timestamp,
                system_run_end_timestamp,
            ) in system_run_timestamps
            if hdateti.str_to_timestamp(
                system_run_start_timestamp, tz, datetime_format=datetime_format
            )
            >= start_timestamp
        ]
        _LOG.info("Filtered by `start_timestamp`: %s.", system_run_timestamps)
    if end_timestamp is not None:
        system_run_timestamps = [
            (system_run_start_timestamp, system_run_end_timestamp)
            for (
                system_run_start_timestamp,
                system_run_end_timestamp,
            ) in system_run_timestamps
            if hdateti.str_to_timestamp(
                system_run_start_timestamp, tz, datetime_format=datetime_format
            )
            <= end_timestamp
        ]
        _LOG.info("Filtered by `end_timestamp`: %s.", system_run_timestamps)
    msg = f"No system run dir found for start_date={start_timestamp}, end_date={end_timestamp}."
    hdbg.dassert_lte(1, len(system_run_timestamps), msg=msg)
    return system_run_timestamps


def get_system_run_parameters(
    dst_root_dir: str,
    dag_builder_name: str,
    tag: str,
    run_mode: str,
    start_timestamp: Optional[pd.Timestamp],
    end_timestamp: Optional[pd.Timestamp],
) -> List[Tuple[str, str, str]]:
    """
    Get all system run parameters from dir names.

    The function can be used for the system reconciliation results also
    as long as system run and system reconciliation dir structures are
    the same.

    :param prod_data_root_dir: dir to store the production results in,
        e.g., "/shared_data/ecs/preprod/system_reconciliation/"
    :param dag_builder_name: name of the DAG builder, e.g. "C1b"
    :param tag: config tag, e.g., "config1"
    :param run_mode: prod system run mode, e.g. "prod" or
        "paper_trading"
    :param start_timestamp: a timestamp to filter out system run params
        from
    :param end_timestamp: a timestamp to filter out system run params
        until to
    :return: start and end timestamps as strings, mode of the system
        run, e.g., "20220212_101500", "20220213_100500", "scheduled"
    """
    timestamps = get_system_run_timestamps(
        dst_root_dir,
        dag_builder_name,
        tag,
        run_mode,
        start_timestamp,
        end_timestamp,
    )
    system_run_params = []
    for start_timestamp_as_str, end_timestamp_as_str in timestamps:
        # Get mode from system log dir name.
        timestamp_dir_path = get_target_dir(
            dst_root_dir,
            dag_builder_name,
            run_mode,
            start_timestamp_as_str,
            end_timestamp_as_str,
            tag=tag,
        )
        # TODO(Grisha): consider moving `mode` to timestamp dir, e.g.,
        # `20220212_101500.20220213_100500` -> `20220212_101500.20220213_100500.scheduled`.
        # Extract mode from dir name using the pattern `system_log_dir.{mode}`.
        system_log_dir_pattern = "system_log_dir.*"
        only_files = False
        use_relative_paths = True
        system_log_dirs = hs3.listdir(
            timestamp_dir_path,
            system_log_dir_pattern,
            only_files,
            use_relative_paths,
        )
        # Skip an empty prod dirs, e.g.:
        # "/shared_data/ecs/C1b/paper_trading/20220212_101500.20220213_100500/prod/".
        if len(system_log_dirs) == 0:
            _LOG.warning(
                "Empty prod dir was found: %s. Skipping.", timestamp_dir_path
            )
            continue
        hdbg.dassert_eq(1, len(system_log_dirs))
        system_log_dir = os.path.basename(system_log_dirs[0])
        # E.g., `system_log_dir.scheduled` -> `scheduled`.
        mode = system_log_dir.split(".")[-1]
        system_run_params.append(
            (start_timestamp_as_str, end_timestamp_as_str, mode)
        )
    return system_run_params


def get_target_dir(
    dst_root_dir: str,
    dag_builder_name: str,
    run_mode: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    *,
    tag: str = "",
    aws_profile: Optional[str] = None,
) -> str:
    """
    Return the target dir name to store reconcilation results.

    If a dir name is not specified by a user then use prod reconcilation
    dir on the shared disk with the corresponding `dag_builder_name`, run date,
    and `run_mode` subdirs.

    E.g., "/shared_data/prod_reconciliation/C1b/paper_trading/20230702_100500.20230703_100000".

    :param dst_root_dir: root dir of reconciliation result dirs, e.g.,
        "/shared_data/prod_reconciliation"
    :param dag_builder_name: name of the DAG builder, e.g. "C1b"
    :param tag: config tag, e.g., "config1"
    :param run_mode: prod run mode, e.g. "prod" or "paper_trading"
    :param start_timestamp_as_str: string representation of timestamp
        at which to start reconcile run, e.g. "20221010_060500"
    :param end_timestamp_as_str: string representation of timestamp
        at which to end reconcile run
    :return: a target dir to store reconcilation results
    """
    _LOG.info(
        hprint.to_str(
            "dst_root_dir dag_builder_name run_mode start_timestamp_as_str end_timestamp_as_str"
        )
    )
    hs3.dassert_path_exists(dst_root_dir, aws_profile)
    hdbg.dassert_isinstance(dag_builder_name, str)
    hdbg.dassert_isinstance(start_timestamp_as_str, str)
    hdbg.dassert_in(run_mode, ["prod", "paper_trading"])
    #
    timestamp_dir = f"{start_timestamp_as_str}.{end_timestamp_as_str}"
    dag_builder_dir = f"{dag_builder_name}.{tag}" if tag else dag_builder_name
    target_dir = os.path.join(
        dst_root_dir, dag_builder_dir, run_mode, timestamp_dir
    )
    _LOG.info(hprint.to_str("target_dir"))
    return target_dir


def get_reconciliation_notebook_dir(dst_root_dir: str) -> str:
    """
    Return reconciliation notebook dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/paper_trading/20230702_100500.20230703_100000/reconciliation_notebook".
    """
    notebook_dir = os.path.join(
        dst_root_dir,
        "reconciliation_notebook",
    )
    return notebook_dir


def get_tca_dir(dst_root_dir: str) -> str:
    """
    Return TCA results dir name.

    E.g., "/shared_data/prod_reconciliation/C1b/paper_trading/20230702_100500.20230703_100000/tca".
    """
    tca_dir = os.path.join(
        dst_root_dir,
        "tca",
    )
    return tca_dir


# TODO(Grisha): I would pass also a `root_dir` and check if
# the resulting dir exists.
# TODO(Nina): rename to `get_system_log_dir()` since it's
# common for prod and simulation.
def get_prod_system_log_dir(mode: str) -> str:
    """
    Get a prod system log dir.

    E.g.: "system_log_dir.manual".

    See `lib_tasks_reconcile.reconcile_run_all()` for params
    description.
    """
    system_log_dir = f"system_log_dir.{mode}"
    _LOG.info(hprint.to_str("system_log_dir"))
    return system_log_dir


# TODO(Grisha): support multiple experiments, not only "sim" and "prod".
def get_system_log_dir_paths(
    target_dir: str,
    mode: str,
) -> Dict[str, str]:
    """
    Get paths to system log dirs.

    :param target_dir: dir to store the reconciliation results in, e.g.,
        "/shared_data/prod_reconciliation/C3a/paper_trading/20230702_100500.20230703_100000"
    :param mode: reconciliation run mode, i.e., "scheduled" and "manual"
    :return: system log dir paths for prod and simulation, e.g.,
        ```
        {
            "prod": ".../prod/system_log_dir.manual",
            "sim": ...
        }
        ```
    """
    prod_dir = get_prod_dir(target_dir)
    prod_system_log_dir = get_prod_system_log_dir(mode)
    prod_system_log_dir = os.path.join(prod_dir, prod_system_log_dir)
    #
    sim_dir = get_simulation_dir(target_dir)
    system_log_dir = get_prod_system_log_dir(mode)
    sim_system_log_dir = os.path.join(sim_dir, system_log_dir)
    system_log_dir_paths = {
        "prod": prod_system_log_dir,
        "sim": sim_system_log_dir,
    }
    return system_log_dir_paths


def get_process_forecasts_dir(root_dir: str) -> str:
    """
    Get path to the process forecasts.

    E.g., "/shared_data/system_log_dir/process_forecasts/".
    """
    process_forecasts_dir = os.path.join(root_dir, "process_forecasts")
    _LOG.info(hprint.to_str("process_forecasts_dir"))
    return process_forecasts_dir


def get_data_type_system_log_path(system_log_path: str, data_type: str) -> str:
    """
    Get path to data inside a system log dir.

    :param system_log_path: system log dir path
    :param data_type: type of data to create paths to
        - "dag_data": DAG output
        - "dag_stats": DAG execution profiling stats
        - "portfolio": Portfolio output
        - "orders": orders info
    :return: path to the specified data type system log dir, e.g.,
        `system_log_dir/dag/node_io/node_io.data`
    """
    if data_type == "dag_data":
        dir_name = os.path.join(system_log_path, "dag/node_io/node_io.data")
    elif data_type == "dag_stats":
        dir_name = os.path.join(system_log_path, "dag/node_io/node_io.prof")
    elif data_type == "portfolio":
        dir_name = os.path.join(system_log_path, "process_forecasts/portfolio")
    elif data_type == "orders":
        dir_name = os.path.join(system_log_path, "process_forecasts/orders")
    else:
        raise ValueError(f"Unsupported data type={data_type}")
    return dir_name


# TODO(gp): -> _get_system_log_paths?
def get_system_log_paths(
    system_log_path_dict: Dict[str, str],
    data_type: str,
    *,
    log_level: int = logging.DEBUG,
    only_warning: bool = False,
) -> Dict[str, str]:
    """
    Get paths to data inside a system log dir.

    :param system_log_path_dict: system log dirs paths for different experiments, e.g.,
        ```
        {
            "prod": "/shared_data/system_log_dir",
            "sim": ...
        }
        ```
    :param data_type: type of data to create paths for, e.g., "dag" for
        DAG output, "portfolio" to load Portfolio
    :param only_warning: issue a warning instead of aborting when one of system
        log dir paths don't exist
    :return: dir paths inside system log dir for different experiments, e.g.,
        ```
        {
            "prod": "/shared_data/system_log_dir/process_forecasts/portfolio",
            "sim": ...
        }
        ```
    """
    data_path_dict = {}
    for k, v in system_log_path_dict.items():
        cur_dir = get_data_type_system_log_path(v, data_type)
        # Check provided log paths exist.
        hdbg.dassert_dir_exists(cur_dir, only_warning=only_warning)
        # Return an empty string for experiment if path doesn't exist.
        data_path_dict[k] = cur_dir if os.path.exists(cur_dir) else ""
    _LOG.log(log_level, "# %s=\n%s", data_type, pprint.pformat(data_path_dict))
    return data_path_dict


def get_path_dicts(
    config: cconfig.Config, *, log_level: int = logging.DEBUG
) -> Tuple:
    # Point to `system_log_dir` for different experiments.
    system_log_path_dict = dict(config["system_log_path"].to_dict())
    _LOG.log(
        log_level,
        "# system_log_path_dict=\n%s",
        pprint.pformat(system_log_path_dict),
    )
    # Point to `system_log_dir/process_forecasts/portfolio` for different experiments.
    data_type = "portfolio"
    portfolio_path_dict = get_system_log_paths(
        system_log_path_dict, data_type, log_level=log_level
    )
    # Point to `system_log_dir/dag/node_io/node_io.data` for different experiments.
    data_type = "dag"
    dag_path_dict = get_system_log_paths(
        system_log_path_dict, data_type, log_level=log_level
    )
    return (system_log_path_dict, portfolio_path_dict, dag_path_dict)


def get_dag_output_path(dag_path_dict: Dict[str, str], mode: str) -> str:
    """
    Choose dag data path based on the passed mode.

    :param mode: type of output dag data to get path for
        - "automatic": select prod dag data if exists otherwise sim dag data
        - "prod": select prod dag data
        - "sim": select sim dag data
    :param dag_path_dict: paths to the dag data
    :return: dag data path
    """
    hdbg.dassert_in(
        mode,
        ["automatic", "prod", "sim"],
        f"Invalid mode={mode}. The mode should be 'automatic', 'prod', 'sim'.",
    )
    prod_key = "prod"
    sim_key = "sim"
    prod_dir = dag_path_dict["prod"]
    sim_dir = dag_path_dict["sim"]
    # Check dag path dict contains `prod` and `sim` keys.
    valid_keys = [prod_key, sim_key]
    hdbg.dassert_is_subset(valid_keys, dag_path_dict.keys())
    # Check if prod and sim dag output dir exist.
    prod_dag_outputs_exist = os.path.exists(prod_dir)
    sim_dag_outputs_exist = os.path.exists(sim_dir)
    # Check if both dirs exists.
    hdbg.dassert(
        (prod_dag_outputs_exist or sim_dag_outputs_exist),
        f"Both prod dir={prod_dir} and sim dir={sim_dir} doesn't exists.",
    )
    # Dictionary to map modes to DAG paths.
    mode_to_dag_path = {
        "automatic": prod_dir if prod_dag_outputs_exist else sim_dir,
        "prod": prod_dir,
        "sim": sim_dir,
    }
    # Check if the selected DAG path exists.
    # Specifically used when mode is `prod` or `sim` and their dir doesn't exists.
    hdbg.dassert_dir_exists(
        mode_to_dag_path[mode],
        f"mode={mode} and dir {mode_to_dag_path[mode]} doesn't exist.",
    )
    hdbg.dassert_lt(
        0,
        len(os.listdir(mode_to_dag_path[mode])),
        f"Dir {mode_to_dag_path[mode]} is empty.",
    )
    return mode_to_dag_path[mode]


# #############################################################################
# DAG loader
# #############################################################################


def get_latest_output_from_last_dag_node(dag_dir: str) -> pd.DataFrame:
    """
    Retrieve the most recent output from the last DAG node.

    This function relies on our file naming conventions.
    """
    hdbg.dassert_dir_exists(dag_dir)
    parquet_files = list(
        filter(lambda x: "parquet" in x, sorted(os.listdir(dag_dir)))
    )
    _LOG.info("Tail of files found=%s", parquet_files[-3:])
    file_name = parquet_files[-1]
    dag_parquet_path = os.path.join(dag_dir, file_name)
    _LOG.info("DAG parquet path=%s", dag_parquet_path)
    dag_df = hparque.from_parquet(dag_parquet_path)
    return dag_df


# #############################################################################
# Forecast Evaluator
# #############################################################################


# TODO(Grisha): unclear where it should be, `ForecastEvaluatorFromPrices` is in
# `amp/dataflow` and `ForecastEvaluatorWithOptimizer` is in `amp/optimizer`.
def get_forecast_evaluator_instance1(
    forecast_evaluator_type: str,
    forecast_evaluator_kwargs: Dict[str, Any],
) -> Union[
    ofevwiop.ForecastEvaluatorWithOptimizer, dtfmod.ForecastEvaluatorFromPrices
]:
    """
    Instantiate forecast evaluator object from a optimizer backend.

    :param forecast_evaluator_type: type of forecast evaluator
    :param forecast_evaluator_kwargs: required arguments to pass to the
        forecast evaluator
    """
    if forecast_evaluator_type == "ForecastEvaluatorFromPrices":
        forecast_evaluator = dtfmod.ForecastEvaluatorFromPrices(
            **forecast_evaluator_kwargs
        )
    elif forecast_evaluator_type == "ForecastEvaluatorWithOptimizer":
        forecast_evaluator = ofevwiop.ForecastEvaluatorWithOptimizer(
            **forecast_evaluator_kwargs
        )
    else:
        raise ValueError(
            "forecast_evaluator_type='%s' not supported" % forecast_evaluator_type
        )
    return forecast_evaluator


# #############################################################################
# Portfolio loader
# #############################################################################


# TODO(gp): This needs to go close to Portfolio?
def load_portfolio_artifacts(
    portfolio_dir: str,
    # *,
    normalize_bar_times_freq: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load a portfolio dataframe and its associated stats dataframe.

    :return: portfolio_df, portfolio_stats_df
    """
    # Make sure the directory exists.
    hdbg.dassert_dir_exists(portfolio_dir)
    # Load the portfolio and stats dataframes.
    portfolio_df, portfolio_stats_df = oporport.Portfolio.read_state(
        portfolio_dir,
    )
    # Sanity-check the dataframes.
    hpandas.dassert_time_indexed_df(
        portfolio_df, allow_empty=False, strictly_increasing=True
    )
    hpandas.dassert_time_indexed_df(
        portfolio_stats_df, allow_empty=False, strictly_increasing=True
    )
    # Sanity-check the date ranges of the dataframes against the start and
    # end timestamps.
    first_timestamp = portfolio_df.index[0]
    _LOG.debug("First portfolio_df timestamp=%s", first_timestamp)
    last_timestamp = portfolio_df.index[-1]
    _LOG.debug("Last portfolio_df timestamp=%s", last_timestamp)
    # Maybe normalize the bar times to `freq` grid.
    if normalize_bar_times_freq is not None:
        hdbg.dassert_isinstance(normalize_bar_times_freq, str)
        _LOG.debug("Normalizing bar times to %s grid", normalize_bar_times_freq)
        portfolio_df.index = portfolio_df.index.round(normalize_bar_times_freq)
        portfolio_stats_df.index = portfolio_stats_df.index.round(
            normalize_bar_times_freq
        )
    return portfolio_df, portfolio_stats_df


def load_portfolio_dfs(
    portfolio_path_dict: Dict[str, str],
    # TODO(gp): Add *
    # *,
    normalize_bar_times_freq: Optional[str] = None,
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    """
    Load multiple portfolios and portfolio stats from disk.

    :param portfolio_path_dict: paths to portfolios for different
        experiments
    :param normalize_bar_times_freq: frequency to normalize the bar
        timestamps
    :return: portfolios and portfolio stats for different experiments
    """
    portfolio_dfs = {}
    portfolio_stats_dfs = {}
    for name, path in portfolio_path_dict.items():
        hdbg.dassert_path_exists(path)
        _LOG.info("Processing portfolio=%s path=%s", name, path)
        portfolio_df, portfolio_stats_df = load_portfolio_artifacts(
            path, normalize_bar_times_freq
        )
        portfolio_dfs[name] = portfolio_df
        portfolio_stats_dfs[name] = portfolio_stats_df
    #
    return portfolio_dfs, portfolio_stats_dfs


# TODO(gp): Merge with load_portfolio_dfs
def load_portfolio_versions(
    run_dir_dict: Dict[str, dict],
    # TODO(gp): Add *
    normalize_bar_times_freq: Optional[str] = None,
    start_timestamp: Optional[pd.Timestamp] = None,
    end_timestamp: Optional[pd.Timestamp] = None,
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    portfolio_dfs = {}
    portfolio_stats_dfs = {}
    for run, dirs in run_dir_dict.items():
        _LOG.info("Processing portfolio=%s", run)
        portfolio_df, portfolio_stats_df = load_portfolio_artifacts(
            dirs["portfolio"],
            normalize_bar_times_freq,
        )
        if start_timestamp is not None:
            portfolio_df = portfolio_df.loc[start_timestamp:]
            portfolio_stats_df = portfolio_stats_df.loc[start_timestamp:]
        if end_timestamp is not None:
            portfolio_df = portfolio_df.loc[:end_timestamp]
            portfolio_stats_df = portfolio_stats_df.loc[:end_timestamp]
        portfolio_dfs[run] = portfolio_df
        portfolio_stats_dfs[run] = portfolio_stats_df
    return portfolio_dfs, portfolio_stats_dfs


def compare_portfolios(
    portfolio_dict: Dict[str, pd.DataFrame],
    *,
    report_stats: bool = True,
    display_plot: bool = False,
    **compare_dfs_kwargs: Any,
) -> pd.DataFrame:
    """
    Compute pairwise max absolute portfolio stats differences.

    :param portfolio_dict: portfolio stats
    :param report_stats: print max abs diff for each pair if True, do
        not print otherwise
    :param display_plot: display plot for each pair if True, do not plot
        otherwise
    :param compare_dfs_kwargs: kwargs for `compare_dfs()`
    :return: pairwise max absolute portfolio stats differences
    """
    # Get a list of portfolio names.
    portfolio_names = sorted(list(portfolio_dict.keys()))
    hdbg.dassert_eq(portfolio_names, ["prod", "research", "sim"])
    # Set a list for pairwise stats data.
    portfolios_diff_dfs = []
    # Iterate over all the possible portfolio pairs.
    for name_pair in itertools.combinations(portfolio_names, 2):
        # Compute all the pairwise portfolio differences.
        name1 = name_pair[0]
        name2 = name_pair[1]
        diff_df = hpandas.compare_multiindex_dfs(
            portfolio_dict[name1],
            portfolio_dict[name2],
            compare_dfs_kwargs=compare_dfs_kwargs,
        )
        # Remove the sign.
        diff_df = diff_df.abs()
        if report_stats:
            max_diff = diff_df.max().max()
            _LOG.info(
                "Max difference between %s and %s is=%s",
                name1,
                name2,
                max_diff,
            )
        # Compute pairwise portfolio differences stats.
        portfolios_diff = diff_df.max().unstack().max(axis=1)
        portfolios_diff.name = "_".join([name1, name2, "diff"])
        if display_plot:
            _ = portfolios_diff.plot.bar()
            plt.xticks(rotation=0)
            plt.show()
        # Add stats data to the result list.
        portfolios_diff_dfs.append(portfolios_diff)
    # Combine the stats.
    res_diff_df = pd.concat(portfolios_diff_dfs, axis=1)
    return res_diff_df


def normalize_portfolio_df(df: pd.DataFrame) -> pd.DataFrame:
    normalized_df = df.copy()
    normalized_df.drop(-1, axis=1, level=1, inplace=True)
    return normalized_df


def compute_delay(df: pd.DataFrame, freq: str) -> pd.Series:
    bar_index = df.index.round(freq)
    delay_vals = df.index - bar_index
    delay = pd.Series(delay_vals, bar_index, name="delay")
    return delay


# #############################################################################
# Target position loader
# #############################################################################


def load_target_positions(
    target_position_dir: str,
    # TODO(gp): Add *
    normalize_bar_times_freq: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load a target position dataframe.
    """
    # Make sure the directory exists.
    hdbg.dassert_dir_exists(target_position_dir)
    # Load the target position dataframe.
    target_position_df = (
        ooptpaoge.TargetPositionAndOrderGenerator.load_target_positions(
            target_position_dir
        )
    )
    # Sanity-check the dataframe.
    hpandas.dassert_time_indexed_df(
        target_position_df, allow_empty=False, strictly_increasing=True
    )
    # Sanity-check the date ranges of the dataframes against the start and
    # end timestamps.
    first_timestamp = target_position_df.index[0]
    _LOG.debug("First target_position_df timestamp=%s", first_timestamp)
    last_timestamp = target_position_df.index[-1]
    _LOG.debug("Last target_position_df timestamp=%s", last_timestamp)
    # Maybe normalize the bar times to `freq` grid.
    if normalize_bar_times_freq is not None:
        hdbg.dassert_isinstance(normalize_bar_times_freq, str)
        _LOG.debug("Normalizing bar times to %s grid", normalize_bar_times_freq)
        target_position_df.index = target_position_df.index.round(
            normalize_bar_times_freq
        )
    return target_position_df


def load_target_position_versions(
    run_dir_dict: Dict[str, dict],
    normalize_bar_times_freq: Optional[str] = None,
    start_timestamp: Optional[pd.Timestamp] = None,
    end_timestamp: Optional[pd.Timestamp] = None,
) -> Dict[str, pd.DataFrame]:
    dfs = {}
    for run, dirs in run_dir_dict.items():
        _LOG.info("Processing run=%s", run)
        df = load_target_positions(
            dirs["target_positions"],
            normalize_bar_times_freq,
        )
        if start_timestamp is not None:
            df = df.loc[start_timestamp:]
        if end_timestamp is not None:
            df = df.loc[:end_timestamp]
        dfs[run] = df
    return dfs


# #############################################################################
# Log file helpers
# #############################################################################


def get_dir(root_dir: str, date_str: str, search_str: str, mode: str) -> str:
    """
    Get base log directory for a specific date.
    """
    hdbg.dassert(root_dir)
    hdbg.dassert_dir_exists(root_dir)
    if mode == "sim":
        dir_ = os.path.join(f"{root_dir}/{date_str}/system_log_dir")
    else:
        if mode == "prod":
            cmd = f"find {root_dir}/{date_str}/job.live* -name '{search_str}'"
        elif mode == "cand":
            cmd = (
                f"find {root_dir}/{date_str}/job.candidate.* -name '{search_str}'"
            )
        else:
            raise ValueError("Invalid mode %s", mode)
        rc, dir_ = hsystem.system_to_string(cmd)
    hdbg.dassert(dir_)
    hdbg.dassert_dir_exists(dir_)
    return dir_


def get_run_dirs(
    root_dir: str, date_str: str, search_str: str, modes: List[str]
) -> Dict[str, dict]:
    """
    Get a dictionary of base and derived run directories for a specific date.
    """
    run_dir_dict = {}
    for run in modes:
        dir_ = get_dir(root_dir, date_str, search_str, run)
        dict_ = {
            "base": dir_,
            "dag": os.path.join(dir_, "dag/node_io/node_io.data"),
            "portfolio": os.path.join(dir_, "process_forecasts/portfolio"),
            "target_positions": os.path.join(dir_, "process_forecasts"),
        }
        run_dir_dict[run] = dict_
    return run_dir_dict


# #############################################################################
# Multiday loader
# #############################################################################


# TODO(Grisha): Is it used? Consider deprecating.
def load_and_process_artifacts(
    root_dir: str,
    date_strs: List[str],
    search_str: str,
    mode: str,
    normalize_bar_times_freq: Optional[str] = None,
) -> Tuple[
    Dict[str, dict],
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame],
    Dict[str, pd.DataFrame],
]:
    hdbg.dassert(date_strs)
    runs = {}
    dag_dfs = {}
    portfolio_dfs = {}
    portfolio_stats_dfs = {}
    target_position_dfs = {}
    for date_str in date_strs:
        try:
            run_dir_dict = get_run_dirs(root_dir, date_str, search_str, [mode])
            runs[date_str] = run_dir_dict
        except:
            _LOG.warning("Unable to get directories for %s", date_str)
        try:

            def warn_if_duplicates_exist(df, name):
                if df.index.has_duplicates:
                    _LOG.warning(
                        "df %s has duplicates on date_str=%s", name, date_str
                    )

            # Load DAG.
            dag_df = get_latest_output_from_last_dag_node(
                run_dir_dict[mode]["dag"]
            )
            warn_if_duplicates_exist(dag_df, "dag")
            # Localize DAG to `date_str`.
            dag_df = dag_df.loc[date_str]
            dag_dfs[date_str] = dag_df
            # Load Portfolio.
            portfolio_df, portfolio_stats_df = load_portfolio_artifacts(
                run_dir_dict[mode]["portfolio"],
                normalize_bar_times_freq,
            )
            warn_if_duplicates_exist(portfolio_df, "portfolio")
            warn_if_duplicates_exist(portfolio_stats_df, "portfolio_stats")
            portfolio_dfs[date_str] = portfolio_df
            portfolio_stats_dfs[date_str] = portfolio_stats_df
            # Load target positions.
            target_position_df = load_target_positions(
                run_dir_dict[mode]["target_positions"], normalize_bar_times_freq
            )
            warn_if_duplicates_exist(target_position_df, "target_positions")
            target_position_dfs[date_str] = target_position_df
        except:
            _LOG.warning("Unable to load data for %s", date_str)
    _ = runs
    return (
        runs,
        dag_dfs,
        portfolio_dfs,
        portfolio_stats_dfs,
        target_position_dfs,
    )


# TODO(Grisha): consider removing completely, see CmTask7794.
# #############################################################################
# Extract system config param values from v1 config version
# #############################################################################


def extract_bar_duration_from_pkl_config(system_log_dir: str) -> str:
    """
    Get bar duration from pickled system config.

    :param system_log_dir: dir containing
        `system_config.output.values_as_strings.pkl` file
    :return: bar duration as a string representation, e.g., "30T"
    """
    # Extract bar duration from a pickled config as different models
    # could be run with different bar duration, e.g., `C11a`.
    config_file_name = "system_config.output.values_as_strings.pkl"
    system_config_path = os.path.join(system_log_dir, config_file_name)
    system_config_pkl = cconfig.load_config_from_pickle(system_config_path)
    # Get string representation of `DagRunner` config.
    # Bar duration should not depend on the resampling rule
    # from `dag_config` so we take its value from `DagRunner` config.
    dag_runner_config_str = str(system_config_pkl["dag_runner_config"])
    # Infer `bar_duration_in_secs`.
    # TODO(Nina): Get value from config directly instead of parsing string,
    # see CmTask6627.
    # Config from a pickle file has only string values that require
    # string processing to extract actual config values from it.
    match = re.search(r"bar_duration_in_secs:\s*(\d+)", dag_runner_config_str)
    if match is not None:
        bar_duration_in_secs = int(match.group(1))
        # Convert bar duration into minutes.
        bar_duration_in_mins = int(bar_duration_in_secs / 60)
        bar_duration_in_mins_as_str = f"{bar_duration_in_mins}T"
    else:
        raise ValueError("Cannot parse `bar_duration_in_secs` from the config")
    return bar_duration_in_mins_as_str


# TODO(Nina): consider removing once CmTask6627 is implemented.
def extract_price_column_name_from_pkl_config(system_log_dir: str) -> str:
    """
    Get price column from pickled system config.

    :param system_log_dir: dir containing
        `system_config.output.values_as_strings.pkl` file
         e.g., ".../system_log_dir.scheduled"
    :return: price column, e.g., "close"
    """
    # Get string representation of portfolio config.
    config_file_name = "system_config.output.values_as_strings.pkl"
    system_config_path = os.path.join(system_log_dir, config_file_name)
    system_config_pkl = cconfig.load_config_from_pickle(system_config_path)
    # Transform tuple into a string for regex.
    portfolio_config_str = str(system_config_pkl["portfolio_config"])
    _LOG.debug(hprint.to_str("portfolio_config_str"))
    # Get price column name.
    # TODO(Dan): Fix after CmTask6627 is implemented.
    # Config from a pickle file has only string values that require
    # string processing to extract actual config values from it.
    #
    # `mark_to_market_col` inside `portfolio_config` appears in the pickled
    # Config as: "('False', 'None', 'mark_to_market_col: close\\npricing_method:".
    #
    re_pattern = r"mark_to_market_col:\s?([^\s\\']+)"
    match = re.search(re_pattern, portfolio_config_str)
    msg = f"Cannot parse `mark_to_market_col` from the Config stored at={system_config_path}"
    hdbg.dassert_ne(match, None, msg=msg)
    # There should be exactly one match.
    hdbg.dassert_eq(1, len(match.groups()))
    price_column_name = match.group(1)
    return price_column_name


def extract_universe_version_from_pkl_config(system_log_dir: str) -> str:
    """
    Get universe version from pickled system config.

    :param system_log_dir: dir containing
        `system_config.output.values_as_strings.pkl` file
         e.g., ".../system_log_dir.scheduled"
    :return: universe version, e.g., "v7.1"
    """
    # Get string representation of market data config.
    config_file_name = "system_config.output.values_as_strings.pkl"
    system_config_path = os.path.join(system_log_dir, config_file_name)
    system_config_pkl = cconfig.load_config_from_pickle(system_config_path)
    # Transform tuple into a string for regex.
    market_data_config_str = str(system_config_pkl["market_data_config"])
    _LOG.debug(hprint.to_str("market_data_config_str"))
    # Get universe version.
    # TODO(Dan): Fix after CmTask6627 is implemented.
    # Config from a pickle file has only string values that require
    # string processing to extract actual config values from it.
    #
    # `universe_version` inside `market_data_config` appears in the pickled
    # Config as: ('False', 'None', 'sleep_in_secs: 0.1\ndays: None\n
    # universe_version:v7.4\nasset_ids: [6051632686, 8717633868,]\n
    # history_lookback: 0 days 00:15:00').
    #
    re_pattern = r"universe_version:\s?([^\s\\']+)"
    match = re.search(re_pattern, market_data_config_str)
    msg = f"Cannot parse `universe_version` from the Config stored at={system_config_path}"
    hdbg.dassert_ne(match, None, msg=msg)
    # There should be exactly one match.
    hdbg.dassert_eq(1, len(match.groups()))
    universe_version = match.group(1)
    return universe_version


# TODO(Nina): consider removing once CmTask6627 is implemented.
def extract_table_name_from_pkl_config(system_log_dir: str) -> str:
    """
    Get table name from pickled system config.

    :param system_log_dir: dir containing
        `system_config.output.values_as_strings.pkl` file
        e.g., ".../system_log_dir.scheduled"
    :return: table name, e.g., "ccxt_ohlcv_futures"
    """
    # Get string representation of market data config.
    config_file_name = "system_config.output.values_as_strings.pkl"
    system_config_path = os.path.join(system_log_dir, config_file_name)
    system_config_pkl = cconfig.load_config_from_pickle(system_config_path)
    # Transform tuple into a string for regex.
    market_data_config_str = str(system_config_pkl["market_data_config"])
    _LOG.debug(hprint.to_str("market_data_config_str"))
    # Get table name.
    re_pattern = r"table_name:\s?([^\s\\']+)"
    match = re.search(re_pattern, market_data_config_str)
    msg = f"Cannot parse `table_name` from the Config stored at={system_config_path}"
    hdbg.dassert_ne(match, None, msg=msg)
    # There should be exactly one match.
    hdbg.dassert_eq(1, len(match.groups()))
    table_name = match.group(1)
    return table_name


def extract_execution_freq_from_pkl_config(system_log_dir: str) -> str:
    """
    Get child order execution frequency from pickled system config.

    :param system_log_dir: dir containing
        `system_config.output.values_as_strings.pkl` file
         e.g., ".../system_log_dir.scheduled"
    :return: child order execution frequency, e.g., "1T"
    """
    # Get string representation of market data config.
    config_file_name = "system_config.output.values_as_strings.pkl"
    system_config_path = os.path.join(system_log_dir, config_file_name)
    system_config_pkl = cconfig.load_config_from_pickle(system_config_path)
    # Transform tuple into a string for regex.
    process_forecasts_node_dict = str(
        system_config_pkl["process_forecasts_node_dict"]
    )
    _LOG.debug(hprint.to_str("process_forecasts_node_dict"))
    re_pattern = r"execution_frequency:\s?([^\s\\']+)"
    match = re.search(re_pattern, process_forecasts_node_dict)
    msg = f"Cannot parse `execution_frequency` from the Config stored at={system_config_path}"
    hdbg.dassert_ne(match, None, msg=msg)
    # There should be exactly one match.
    hdbg.dassert_eq(1, len(match.groups()))
    execution_frequency = match.group(1)
    return execution_frequency
