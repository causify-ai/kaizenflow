# #############################################################################
# Reconciliation
# #############################################################################

# 1. Run production system (done by a separate AirFlow task)
# 2. Create reconciliation target directories
# 3. Copy production data to a system reconciliation folder
# 4. Dump market data for replayed time simulation
# 5. Run replayed time simulation
# 6. Run the reconciliation notebook and publish it
"""
Invokes in the file are runnable from a Docker container only.

E.g., to run for certain date from a Docker container:
```
> invoke reconcile_run_all \
    --dag-builder-ctor-as-str "dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder" \
    --run-mode paper_trading \
    --start-timestamp-as-str "20230828_130500" \
    --end-timestamp-as-str "20230829_131000" \
    --mode "scheduled" \
    --prod-data-source-dir ".../system_reconciliation" \
    --dst-root-dir ".../prod_reconciliation" \
    --no-prevent-overwriting \
    --run-notebook \
    --mark-as-last-24-hour-run
```

Import as:

import oms.lib_tasks_reconcile as olitarec
"""

import datetime
import logging
import os
import sys
from typing import Optional

import pandas as pd
from invoke import task

import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.system.common as dtfasc
import dataflow_amp.system.Cx as dtfasysc
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hserver as hserver
import helpers.hsystem as hsystem
import im_v2.common.universe as ivcu
import reconciliation.sim_prod_reconciliation as rsiprrec

_LOG = logging.getLogger(__name__)


def _system(cmd: str) -> int:
    return hsystem.system(cmd, suppress_output=False, log_level="echo")


def _allow_update(
    dag_builder_ctor_as_str: str,
    run_mode: str,
    start_timestamp_as_str: str,
    end_timestamp_as_str: str,
    dst_root_dir: str,
    *,
    tag: str = "",
) -> None:
    """
    Allow to overwrite reconciliation outcomes in the date-specific target dir.

    See `reconcile_run_all()` for params description.
    """
    # Get date-specific target dir.
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    target_dir = rsiprrec.get_target_dir(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
    )
    hdbg.dassert_path_exists(target_dir)
    # Allow overwritting.
    _LOG.info("Allow to overwrite files at: %s", target_dir)
    cmd = f"chmod -R +w {target_dir}"
    _system(cmd)


def _prevent_overwriting(path: str) -> None:
    """
    Remove write permissions.

    :param path: path to a file or to a dir
    """
    hdbg.dassert_path_exists(path)
    _LOG.info("Removing the write permissions for: %s", path)
    if os.path.isdir(path):
        opt = "-R"
    else:
        opt = ""
    cmd = f"chmod {opt} -w {path}"
    _system(cmd)


# TODO(Nina): extend to handle S3 files.
def _sanity_check_data(file_path: str) -> None:
    """
    Check that data at the specified file path is correct.
    """
    cmd = f"gzip -cd {file_path} | head -3"
    _system(cmd)
    cmd = f"gzip -cd {file_path} | tail -3"
    _system(cmd)
    cmd = f"gzip -cd {file_path} | wc -l"
    _system(cmd)
    cmd = f"ls -lh {file_path}"
    _system(cmd)


# TODO(Grisha): seems more general than this file.
# TODO(Grisha): extend to handle dirs.
def _copy_result_file(
    file_path: str, dst_dir: str, aws_profile: Optional[str]
) -> None:
    """
    Copy a file to a specified dir.

    :param file_path: a path to copy data from
    :param dst_dir: a dir to copy data to
    """
    if hs3.is_s3_path(file_path):
        hs3.dassert_path_exists(file_path, aws_profile)
        cmd = f"aws s3 cp {file_path} {dst_dir} --profile {aws_profile}"
    else:
        hdbg.dassert_file_exists(file_path)
        hdbg.dassert_dir_exists(dst_dir)
        cmd = f"cp {file_path} {dst_dir}"
    _LOG.info("Copying from %s to %s", file_path, dst_dir)
    _system(cmd)


# TODO(Nina): Consider killing the function as it is not used.
@task
def reconcile_dump_market_data(
    ctx,
    dag_builder_ctor_as_str,
    run_mode,
    start_timestamp_as_str,
    end_timestamp_as_str,
    dst_root_dir,
    db_stage,
    universe_version,
    source_dir=None,
    incremental=False,
    interactive=False,
    prevent_overwriting=True,
    aws_profile=None,
):  # type: ignore
    # pylint: disable=line-too-long
    """
    Dump the market data image and copy it to the specified folder.

    The output df looks like:
    ```
                               asset_id              knowledge_timestamp     open     high      low    close     volume            end_download_timestamp       id        full_symbol            start_timestamp
    end_timestamp
    2022-09-27 10:35:00-04:00  1030828978 2022-09-27 14:36:12.230330+00:00   0.7233   0.7247   0.7215   0.7241  3291381.0  2022-09-27 14:36:11.727196+00:00  3409049  binance::GMT_USDT  2022-09-27 10:34:00-04:00
    2022-09-27 10:35:00-04:00  1464553467 2022-09-27 14:36:05.788923+00:00  1384.23  1386.24  1383.19  1385.63   5282.272  2022-09-27 14:36:05.284506+00:00  3409043  binance::ETH_USDT  2022-09-27 10:34:00-04:00
    ```

    See `reconcile_run_all()` for params description.

    :param incremental: see `hio.create_dir()`
    :param interactive: if True ask user to visually inspect data snippet and
        confirm the dumping otherwise just save
    """
    # pylint: enable=line-too-long
    hdbg.dassert(
        hserver.is_inside_docker(), "This is runnable only inside Docker."
    )
    hdbg.dassert_in(db_stage, ("local", "test", "preprod", "prod"))
    hdbg.dassert_is_not(universe_version, None)
    _ = ctx
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    target_dir = rsiprrec.get_target_dir(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
    )
    sim_target_dir = rsiprrec.get_simulation_dir(target_dir)
    if source_dir is None:
        source_dir = "."
    # TODO(Grisha): rename `test_data.csv.gz` -> `market_data.csv.gz`.
    market_data_file = "test_data.csv.gz"
    market_data_file_path = os.path.join(source_dir, market_data_file)
    if hs3.is_s3_path(source_dir):
        aws_profile = "ck"
        s3fs_ = hs3.get_s3fs(aws_profile)
        path_exists = s3fs_.exists(market_data_file_path)
    else:
        path_exists = os.path.exists(market_data_file)
    # TODO(Grisha): @Dan Reconsider clause logic (compare with `reconcile_run_notebook`).
    if incremental and path_exists:
        # Copy market data file to the target dir.
        _copy_result_file(market_data_file_path, sim_target_dir, aws_profile)
        _LOG.warning("Skipping generating %s", market_data_file_path)
    else:
        market_data_file_path = os.path.join(sim_target_dir, market_data_file)
        dtfasysc.dump_market_data_from_db(
            market_data_file_path,
            start_timestamp_as_str,
            end_timestamp_as_str,
            db_stage,
            universe_version,
        )
    # Check the market data file.
    # TODO(Nina): enable once the function is extended to handle S3 files.
    # _sanity_check_data(market_data_file_path)
    if interactive:
        question = "Is the file ok?"
        hsystem.query_yes_no(question)
    # Sanity check result data.
    market_data_file_target = os.path.join(sim_target_dir, market_data_file_path)
    # _sanity_check_data(market_data_file_target)
    #
    if prevent_overwriting:
        _prevent_overwriting(market_data_file_target)


@task
def reconcile_run_sim(
    ctx,
    dag_builder_ctor_as_str,
    run_mode,
    start_timestamp_as_str,
    end_timestamp_as_str,
    mode,
    dst_root_dir,
    stage,
    tag="",
    market_data_source_dir=None,
    incremental=False,
    set_config_values=None,
):  # type: ignore
    """
    Run the simulation given an interval [start_timestamp, end_timestamp].

    See `reconcile_run_all()` for params description.
    """
    hdbg.dassert(
        hserver.is_inside_docker(), "This is runnable only inside Docker."
    )
    _ = ctx
    #
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    target_dir = rsiprrec.get_target_dir(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
    )
    sim_target_dir = rsiprrec.get_simulation_dir(target_dir)
    system_log_dir = rsiprrec.get_prod_system_log_dir(mode)
    dst_result_dir = os.path.join(sim_target_dir, system_log_dir)
    # Build the system.
    system = dtfasysc.Cx_ProdSystem_v1_20220727(
        dag_builder_ctor_as_str,
        run_mode="simulation",
    )
    #
    system.config["trading_period"] = "5T"
    system.config["market_data_config", "days"] = None
    # Set the latest universe version.
    universe_version = ivcu.get_latest_universe_version()
    system.config["market_data_config", "universe_version"] = universe_version
    system.config[
        "market_data_config", "im_client_config", "table_name"
    ] = "ccxt_ohlcv_futures"
    system = dtfsys.apply_Portfolio_config(system)
    order_config = dtfasysc.get_Cx_order_config_instance1()
    optimizer_config = dtfasysc.get_Cx_optimizer_config_instance1()
    process_forecasts_dir = rsiprrec.get_process_forecasts_dir(dst_result_dir)
    system = dtfasysc.apply_ProcessForecastsNode_config(
        system, order_config, optimizer_config, process_forecasts_dir
    )
    # Build paths to a market data file and a result dir.
    file_name = "test_data.csv.gz"
    market_data_file_path = os.path.join(sim_target_dir, file_name)
    if market_data_source_dir is not None:
        market_data_file_path = os.path.join(market_data_source_dir, file_name)
    # Run simulation.
    _ = dtfasc.run_simulation(
        system,
        start_timestamp_as_str,
        end_timestamp_as_str,
        market_data_file_path,
        dst_result_dir,
        set_config_values=set_config_values,
        incremental=incremental,
        db_stage=stage,
    )
    # Check that the required dirs were created.
    hdbg.dassert_dir_exists(os.path.join(dst_result_dir, "dag"))
    hdbg.dassert_dir_exists(os.path.join(dst_result_dir, "process_forecasts"))
    # TODO(Grisha): @Dan Add asserts on the latest files so we confirm that simulation was completed.


@task
def reconcile_copy_prod_data(
    ctx,
    dag_builder_ctor_as_str,
    run_mode,
    start_timestamp_as_str,
    end_timestamp_as_str,
    dst_root_dir,
    # TODO(Nina): -> "prod_data_source_root_dir".
    prod_data_source_dir,
    mode,
    tag="",
    prevent_overwriting=True,
    aws_profile=None,
):  # type: ignore
    """
    Copy the output of the prod run to the specified folder.

    See `reconcile_run_all()` for params description.
    """
    hdbg.dassert_in(mode, ("scheduled", "manual"))
    hs3.dassert_path_exists(prod_data_source_dir, aws_profile)
    _ = ctx
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    # `target_dir` is the local dir path where we copy results to.
    target_dir = rsiprrec.get_target_dir(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
        aws_profile=None,
    )
    # Set source log dir.
    prod_data_source_dir = rsiprrec.get_target_dir(
        prod_data_source_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
        aws_profile=aws_profile,
    )
    system_log_subdir = rsiprrec.get_prod_system_log_dir(mode)
    system_log_dir = os.path.join(prod_data_source_dir, system_log_subdir)
    hs3.dassert_path_exists(system_log_dir, aws_profile)
    # Set target dirs.
    prod_target_dir = rsiprrec.get_prod_dir(target_dir)
    prod_results_target_dir = os.path.join(prod_target_dir, system_log_subdir)
    _LOG.info("Copying prod results to '%s'", prod_results_target_dir)
    # Copy prod run results to the target dir.
    if hs3.is_s3_path(system_log_dir):
        cmd = f"aws s3 cp {system_log_dir} {prod_results_target_dir} --recursive --profile {aws_profile}"
    else:
        cmd = f"cp -vr {system_log_dir} {prod_results_target_dir}"
    _system(cmd)
    # Copy prod run logs to the specified folder.
    log_file_name = f"log.{mode}.txt"
    log_file_path = os.path.join(prod_data_source_dir, "logs", log_file_name)
    #
    _copy_result_file(log_file_path, prod_target_dir, aws_profile)
    #
    if prevent_overwriting:
        _prevent_overwriting(prod_target_dir)


@task
def reconcile_run_multiday_notebook(
    ctx,
    dst_root_dir,
    dag_builder_ctor_as_str,
    run_mode,
    start_timestamp_as_str,
    end_timestamp_as_str,
    html_notebook_tag,
):  # type: ignore
    """
    Run the reconciliation notebook for multiple days (e.g., one week, one
    month), publish it locally and copy the results to the specified folder.

    See `reconcile_run_all()` for params description.

    :param html_notebook_tag: a tag for a notebook run period, e.g.,
        "last_week"
    """
    hdbg.dassert(
        hserver.is_inside_docker(), "This is runnable only inside Docker."
    )
    _LOG.info(
        hprint.to_str(
            "dst_root_dir dag_builder_name run_mode start_timestamp_as_str end_timestamp_as_str html_notebook_tag"
        )
    )
    _ = ctx
    amp_dir = hgit.get_amp_abs_path()
    script_path = os.path.join(
        amp_dir, "dev_scripts", "notebooks", "run_notebook.py"
    )
    # Retrieve the notebook path.
    notebook_path = rsiprrec.get_multiday_system_reconciliation_notebook_path()
    # Prepare the config and the notebook params.
    config_builder = (
        f"amp.reconcil.build_multiday_system_reconciliation_config"
        + f'("{dst_root_dir}", "{dag_builder_ctor_as_str}", "{run_mode}", "{start_timestamp_as_str}", "{end_timestamp_as_str}")'
    )
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    notebook_dir = rsiprrec.get_multiday_reconciliation_dir(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
    )
    # Build a cmd to run the notebook.
    cmd = [
        script_path,
        f"--notebook {notebook_path}",
        f"--config_builder '{config_builder}'",
        f"--dst_dir {notebook_dir}",
        "--tee",
        "--no_suppress_output",
        "--num_threads 'serial'",
        "--publish_notebook",
        "-v DEBUG 2>&1 | tee log.txt;",
        "exit ${PIPESTATUS[0]}",
    ]
    cmd = " ".join(cmd)
    # Run the notebook.
    _system(cmd)
    # Copy the notebook to S3 HTML bucket so that it is accessible via
    # a web-browser.
    notebook_name = os.path.basename(notebook_path)
    notebook_name = os.path.splitext(notebook_name)[0]
    pattern = f"{notebook_name}.*.html"
    only_files = True
    use_relative_paths = False
    html_notebook_path = hs3.listdir(
        notebook_dir,
        pattern,
        only_files,
        use_relative_paths,
    )
    notebooks_cnt = len(html_notebook_path)
    msg = f"{notebooks_cnt} html-notebooks were found while should be only one."
    hdbg.dassert_eq(1, notebooks_cnt, msg=msg)
    #
    html_notebook_path = html_notebook_path[0]
    html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
    s3_dst_dir = os.path.join(html_bucket_path, "system_reconciliation")
    html_file_name = f"{dag_builder_name}.{html_notebook_tag}.html"
    s3_dst_path = os.path.join(s3_dst_dir, html_file_name)
    aws_profile = "ck"
    hs3.copy_file_to_s3(html_notebook_path, s3_dst_path, aws_profile)


@task
def reconcile_run_notebook(
    ctx,
    notebook_run_mode,
    dag_builder_ctor_as_str,
    run_mode,
    start_timestamp_as_str,
    end_timestamp_as_str,
    dst_root_dir,
    mode,
    tag="",
    incremental=False,
    mark_as_last_24_hour_run=False,
    prevent_overwriting=True,
    set_config_values=None,
):  # type: ignore
    """
    Run the reconciliation notebook, publish it locally and copy the results to
    the specified folder.

    See `reconcile_run_all()` for params description.

    :param notebook_run_mode: same as in
        `get_system_reconciliation_notebook_path()`
    :param incremetal: see `hio.create_dir()`
    """
    hdbg.dassert(
        hserver.is_inside_docker(), "This is runnable only inside Docker."
    )
    hdbg.dassert_in(mode, ("scheduled", "manual"))
    if notebook_run_mode == "slow":
        # The slow version of the notebook does not compute research portfolio,
        # thus does not require any overrides to the research portfolio config.
        hdbg.dassert_is(set_config_values, None)
    _ = ctx
    # Set results destination dir and clear it if is already filled.
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    target_dir = rsiprrec.get_target_dir(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
    )
    hdbg.dassert_dir_exists(target_dir)
    # The common pattern is to save an output locally and copy to the specified
    # folder. However, if a notebook run fails then the copying piece of the
    # code is not executed so saving the output directly to the specified folder.
    notebook_root_dir = rsiprrec.get_reconciliation_notebook_dir(target_dir)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("notebook_root_dir"))
    # Store the "fast" and the "slow" notebook results separately.
    notebook_dir = os.path.join(notebook_root_dir, notebook_run_mode)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(hprint.to_str("notebook_dir"))
    if os.path.exists(notebook_dir):
        if incremental:
            _LOG.warning(
                "Notebook run results are already stored at %s", notebook_dir
            )
            sys.exit(-1)
        else:
            rm_cmd = f"rm -rf {notebook_dir}"
            _LOG.warning(
                "The results_dir=%s already exists, removing it.", notebook_dir
            )
            _system(rm_cmd)
    # TODO(Grisha): pass `asset_class` as a param.
    asset_class = "crypto"
    #
    cmd_txt = []
    cmd_txt.append(f"export AM_ASSET_CLASS={asset_class}")
    # Add the command to run the notebook.
    amp_dir = hgit.get_amp_abs_path()
    script_path = os.path.join(
        amp_dir, "dev_scripts", "notebooks", "run_notebook.py"
    )
    notebook_path = rsiprrec.get_system_reconciliation_notebook_path(
        notebook_run_mode
    )
    if set_config_values is None:
        # Get a string representation of config builder.
        config_builder = (
            f"amp.reconciliation.sim_prod_reconciliation.build_reconciliation_configs"
            + f'("{dst_root_dir}", "{dag_builder_ctor_as_str}", "{start_timestamp_as_str}", "{end_timestamp_as_str}", "{run_mode}", "{mode}", tag="{tag}")'
        )
    else:
        # Append config values to override to a string representation of config
        # builder.
        config_builder = (
            f"amp.reconciliation.sim_prod_reconciliation.build_reconciliation_configs"
            + f'("{dst_root_dir}", "{dag_builder_ctor_as_str}", "{start_timestamp_as_str}", "{end_timestamp_as_str}", "{run_mode}", "{mode}", tag="{tag}", set_config_values="""{set_config_values}""")'
        )
    opts = "--tee --no_suppress_output --num_threads 'serial' --publish_notebook -v DEBUG 2>&1 | tee log.txt; exit ${PIPESTATUS[0]}"
    cmd_run_txt = [
        script_path,
        f"--notebook {notebook_path}",
        f"--config_builder '{config_builder}'",
        f"--dst_dir {notebook_dir}",
        f"{opts}",
    ]
    cmd_run_txt = " ".join(cmd_run_txt)
    cmd_txt.append(cmd_run_txt)
    cmd_txt = "\n".join(cmd_txt)
    # Save the commands as a script.
    script_name = "tmp.publish_notebook.sh"
    hio.create_executable_script(script_name, cmd_txt)
    # Make the script executable and run it.
    _LOG.info("Running the notebook=%s", notebook_path)
    _system(script_name)
    # Copy the notebook on S3 HTML bucket so that it is accessible via
    # a web-browser.
    html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
    s3_dst_dir = os.path.join(html_bucket_path, "system_reconciliation")
    #
    notebook_name = os.path.basename(notebook_path)
    notebook_name = os.path.splitext(notebook_name)[0]
    cmd = f"find {notebook_dir} -type f -name '{notebook_name}.*.html'"
    _, html_notebook_path = hsystem.system_to_string(cmd)
    html_notebook_name = os.path.basename(html_notebook_path)
    #
    s3_dst_path = os.path.join(s3_dst_dir, html_notebook_name)
    aws_profile = "ck"
    hs3.copy_file_to_s3(html_notebook_path, s3_dst_path, aws_profile)
    if mark_as_last_24_hour_run:
        # Copy the reconciliation notebook to S3 HTML bucket so that it becomes
        # available via the static link, e.g.,
        # `https://***/system_reconciliation/C3a.last_24hours.html`.
        html_file_name = (
            f"{dag_builder_name}.{notebook_run_mode}.last_24hours.html"
        )
        s3_dst_path = os.path.join(s3_dst_dir, html_file_name)
        hs3.copy_file_to_s3(html_notebook_path, s3_dst_path, aws_profile)
    if prevent_overwriting:
        _prevent_overwriting(notebook_dir)
    if s3_dst_dir.startswith(html_bucket_path):
        dir_to_url = henv.execute_repo_config_code(
            "get_html_dir_to_url_mapping()"
        )
        url_bucket_path = dir_to_url[html_bucket_path]
        url = s3_dst_path.replace(html_bucket_path, url_bucket_path)
        cmd = f"""
        # To open the notebook from a web-browser open a link:
        {url}
        """
        print(hprint.dedent(cmd))


# TODO(Grisha): consider moving to a different file.
@task
def run_master_pnl_real_time_observer_notebook(
    ctx,
    prod_data_root_dir,
    dag_builder_ctor_as_str,
    run_mode,
    tag="",
    start_timestamp_as_str=None,
    end_timestamp_as_str=None,
    mode=None,
    burn_in_bars=3,
    mark_as_last_5minute_run=False,
    save_plots_for_investors=True,
):  # type: ignore
    """
    Run the PnL real time observer notebook and copy the results to the S3 HTML
    bucket.

    If `start_timestamp_as_str`, `end_timestamp_as_str`, `mode`, use the results
    that correspond to the latest prod system run for a given model, system run
    mode.

    :param prod_data_root_dir: a dir that stores the production system output,
        e.g., "/shared_data/ecs/preprod/system_reconciliation/"
    :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
        e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
    :param start_timestamp_as_str: string representation of timestamp
        at which a production run started
    :param end_timestamp_as_str: string representation of timestamp
        at which a production run ended
    :param mode: the prod system run mode which defines a prod system log dir name
        - "scheduled": the system is run at predefined time automatically
        - "manual": the system run is triggered manually
    :param burn_in_bars: a minimum amount of bars that is needed for calculations
    :param mark_as_last_5minute_run: mark the production run as latest so
        that the latest PnL real-time observer notebook becomes available via
        a static link, e.g., `https://***/system_reconciliation/C3a.last_5minutes.html`
    :param save_plots_for_investors: if plots should be saved for investors
    """
    hdbg.dassert(
        hserver.is_inside_docker(), "This is runnable only inside Docker."
    )
    if mode is not None:
        hdbg.dassert_in(mode, ("scheduled", "manual"))
    hdbg.dassert_dir_exists(prod_data_root_dir)
    hdbg.dassert_all_defined_or_all_None(
        [start_timestamp_as_str, end_timestamp_as_str, mode]
    )
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    # Check if at least `burn_in_bars` bars are computed, otherwise exit.
    # TODO(Grisha): consider passing the system_log_dir path directly to the
    # config building function.
    vals = [start_timestamp_as_str, end_timestamp_as_str, mode]
    if all(val is None for val in vals):
        # Filter system run params by current time to exclude the future
        # timestamps when then both runs exists at the same time. E.g.,
        # current timestamp is "20230802_130000", run from the previous day,
        # "20230801_131000.20230802_130500", is still on going; while a dir
        # for the next run has been already created, "20230802_131000.20230803_130500".
        # So technically "20230802_131000.20230803_130500" is the latest timestamp
        # but prod system run has not been started yet.
        tz = "UTC"
        end_timestamp = hdateti.get_current_time(tz)
        start_timestamp = end_timestamp - pd.Timedelta(days=1)
        system_run_params = rsiprrec.get_system_run_parameters(
            prod_data_root_dir,
            dag_builder_name,
            tag,
            run_mode,
            start_timestamp,
            end_timestamp,
        )
        hdbg.dassert_lte(1, len(system_run_params))
        # Get the latest system run parameters. Using `max()` to check that all
        # values in tuple are the latest.
        # TODO(Grisha): do not use `max()` for strings.
        start_timestamp_as_str, end_timestamp_as_str, mode = max(
            system_run_params
        )
        _LOG.info(
            hprint.to_str("start_timestamp_as_str, end_timestamp_as_str, mode")
        )
    target_dir = rsiprrec.get_target_dir(
        prod_data_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
    )
    system_log_dir = rsiprrec.get_prod_system_log_dir(mode)
    system_log_dir = os.path.join(target_dir, system_log_dir)
    data_type = "orders"
    orders_dir = rsiprrec.get_data_type_system_log_path(system_log_dir, data_type)
    # TODO(Grisha): create a separate function to get orders files.
    order_files = dtfcore.get_dag_node_csv_file_names(orders_dir)
    # There is a separate order file for each bar. Assumption: a bar is computed
    # when a corresponding order file exists. We use the number of order files as
    # a proxy for the number of computed bars.
    n_bars = len(order_files)
    if n_bars < burn_in_bars:
        _LOG.warn(
            "Not enough data to run the notebook, should be at least %s bars computed, received %s bars, exiting",
            burn_in_bars,
            n_bars,
        )
        return None
    _ = ctx
    # Add the command to run the notebook.
    amp_dir = hgit.get_amp_abs_path()
    notebook_name = "Master_PnL_real_time_observer"
    script_path = os.path.join(
        amp_dir, "dev_scripts", "notebooks", "run_notebook.py"
    )
    notebook_path = os.path.join(
        amp_dir, "oms", "notebooks", f"{notebook_name}.ipynb"
    )
    html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
    s3_dst_dir = os.path.join(html_bucket_path, "pnl_for_investors")
    config_builder = (
        f"amp.reconciliation.sim_prod_reconciliation.build_prod_pnl_real_time_observer_configs"
        + f'("{prod_data_root_dir}", "{dag_builder_ctor_as_str}", "{run_mode}", "{start_timestamp_as_str}", "{end_timestamp_as_str}",  "{mode}", {save_plots_for_investors}, s3_dst_dir="{s3_dst_dir}", tag="{tag}")'
    )
    # Since the invoke is run multiple times per day create a subdir for every
    # run and mark it with the current UTC timestamp, e.g.,
    # `.../C3a/20230411/pnl_realtime_observer_notebook/20230411_130510`.
    notebook_dir = "pnl_realtime_observer_notebook"
    shared_notebook_dir = os.path.join(target_dir, notebook_dir)
    hio.create_dir(shared_notebook_dir, incremental=True)
    #
    tz = "UTC"
    current_time = hdateti.get_current_timestamp_as_string(tz)
    current_time = current_time.replace("-", "_")
    # E.g., `.../C3a/20230411/pnl_realtime_observer_notebook/20230411_130510`.
    shared_nootebook_timestamp_dir = os.path.join(
        shared_notebook_dir, current_time
    )
    hio.create_dir(shared_nootebook_timestamp_dir, incremental=True)
    opts = "--tee --no_suppress_output --num_threads 'serial' --publish_notebook -v DEBUG 2>&1 | tee log.txt; exit ${PIPESTATUS[0]}"
    cmd_run_txt = [
        script_path,
        f"--notebook {notebook_path}",
        f"--config_builder '{config_builder}'",
        f"--dst_dir {shared_nootebook_timestamp_dir}",
        f"{opts}",
    ]
    cmd_txt = " ".join(cmd_run_txt)
    # Save the commands as a script.
    script_name = "tmp.publish_notebook.sh"
    hio.create_executable_script(script_name, cmd_txt)
    # Run the notebook.
    _LOG.info("Running the notebook=%s", notebook_path)
    _system(script_name)
    # Remove the tmp script.
    rm_cmd = f"rm {script_name}"
    _system(rm_cmd)
    if mark_as_last_5minute_run:
        # Search for the published notebook.
        cmd = f"find {shared_nootebook_timestamp_dir} -type f -name '{notebook_name}.*.html'"
        _, html_notebook_path = hsystem.system_to_string(cmd)
        # Copy the notebook to the S3 HTML bucket so that
        # it becomes available via the static link, e.g.,
        # `https://***/system_reconciliation/C3a.last_5minutes.html`.
        html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
        html_file_name = (
            f"{dag_builder_name}.{tag}.last_5minutes.html"
        )
        s3_dst_path = os.path.join(
            html_bucket_path, "system_reconciliation", html_file_name
        )
        aws_profile = "ck"
        hs3.copy_file_to_s3(html_notebook_path, s3_dst_path, aws_profile)


@task
def reconcile_ls(
    ctx,
    dag_builder_ctor_as_str,
    run_mode,
    start_timestamp_as_str,
    end_timestamp_as_str,
    dst_root_dir,
    tag="",
):  # type: ignore
    """
    Run `ls` on the dir containing the reconciliation data.

    See `reconcile_run_all()` for params description.
    """
    _ = ctx
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    target_dir = rsiprrec.get_target_dir(
        dst_root_dir,
        dag_builder_name,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        tag=tag,
    )
    _LOG.info(hprint.to_str("target_dir"))
    hdbg.dassert_dir_exists(target_dir)
    #
    cmd = f"ls -lh {target_dir}"
    _system(cmd)
    cmd = f"du -d 1 -h {target_dir}"
    _system(cmd)


@task
def reconcile_dump_tca_data(
    ctx,
    dag_builder_ctor_as_str,
    start_timestamp_as_str,
    dst_root_dir,
    stage,
    tag="",
    incremental=False,
    prevent_overwriting=True,
):  # type: ignore
    """
    Retrieve and save the TCA data.

    See `reconcile_run_all()` for params description.

    :param incremetal: see `hio.create_dir()`
    """
    hdbg.dassert(
        hserver.is_inside_docker(), "This is runnable only inside Docker."
    )
    _ = ctx
    # TCA is being dumped only for prod run mode.
    dag_builder_name = dtfcore.get_DagBuilder_name_from_string(
        dag_builder_ctor_as_str
    )
    run_mode = "prod"
    # TODO(Nina): `get_target_dir()` requires end timestamp to build the path.
    target_dir = rsiprrec.get_target_dir(
        dst_root_dir,
        dag_builder_name,
        start_timestamp_as_str,
        run_mode,
        tag=tag,
    )
    run_date = rsiprrec.get_run_date(start_timestamp_as_str)
    run_date = datetime.datetime.strptime(run_date, "%Y%m%d")
    # TODO(Grisha): add as params to the interface.
    end_timestamp = run_date
    start_timestamp = (end_timestamp - datetime.timedelta(days=1)).strftime(
        "%Y%m%d"
    )
    local_results_dir = "./tca"
    if os.path.exists(local_results_dir):
        if incremental:
            _LOG.warning("TCA data is already stored at %s", local_results_dir)
            sys.exit(-1)
        else:
            _LOG.warning(
                "The local_results_dir=%s already exists, re-creating it.",
                local_results_dir,
            )
    hio.create_dir(local_results_dir, incremental=incremental)
    exchange_id = "binance"
    contract_type = "futures"
    account_type = "trading"
    secrets_id = "3"
    # See the TODO comment in `obrbrexa.get_DataFrameBroker_example1()`.
    universe = ivcu.get_latest_universe_version()
    opts = [
        f"--exchange_id {exchange_id}",
        f"--contract_type {contract_type}",
        f"--stage {stage}",
        f"--account_type {account_type}",
        f"--secrets_id {secrets_id}",
        f"--universe {universe}",
    ]
    opts = " ".join(opts)
    log_file = os.path.join(local_results_dir, "log.txt")
    opts += f" --incremental -v DEBUG 2>&1 | tee {log_file}"
    opts += "; exit ${PIPESTATUS[0]}"
    cmd_run_txt = [
        "amp/oms/broker/ccxt/scripts/get_ccxt_trades.py",
        f"--start_timestamp '{start_timestamp}'",
        f"--end_timestamp '{end_timestamp}'",
        f"--dst_dir {local_results_dir}",
        f"{opts}",
    ]
    cmd_run_txt = " ".join(cmd_run_txt)
    # Save the command as a script.
    script_name = "tmp.dump_tca_data.sh"
    hio.create_executable_script(script_name, cmd_run_txt)
    # Make the script executable and run it.
    _system(script_name)
    # Copy dumped data to the specified folder.
    hdbg.dassert_dir_exists(target_dir)
    _LOG.info("Copying results from '%s' to '%s'", local_results_dir, target_dir)
    cmd = f"cp -vr {local_results_dir} {target_dir}"
    _system(cmd)
    #
    if prevent_overwriting:
        tca_dir = rsiprrec.get_tca_dir(target_dir)
        _prevent_overwriting(tca_dir)


@task
def reconcile_run_all(
    ctx,
    dag_builder_ctor_as_str,
    run_mode,
    start_timestamp_as_str,
    end_timestamp_as_str,
    dst_root_dir,
    prod_data_source_dir,
    mode,
    stage,
    tag="",
    market_data_source_dir=None,
    mark_as_last_24_hour_run=False,
    # TODO(Grisha): propagate everywhere below.
    incremental=False,
    prevent_overwriting=True,
    abort_if_exists=True,
    backup_dir_if_exists=False,
    run_notebook=False,
    allow_update=False,
    aws_profile=None,
    # TODO(Grisha): Consider using iterable values instead of passing a single
    #  string separated by `;`, see
    #  https://docs.pyinvoke.org/en/stable/concepts/invoking-tasks.html#iterable-flag-values.
    set_config_values=None,
):  # type: ignore
    """
    Run all phases of prod vs simulation reconciliation.

    :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
        e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
    :param run_mode: prod run mode, e.g. "prod" or "paper_trading"
    :param start_timestamp_as_str: string representation of timestamp
        at which to start reconcile run
    :param end_timestamp_as_str: string representation of timestamp
        at which to end reconcile run
    :param dst_root_dir: dir to store reconcilation results in
    :param prod_data_source_dir: path to the prod run outcomes
        (i.e. system log dir, logs)
    :param stage: development stage, e.g., `preprod`. Also applies to a database
        stage
    :param tag: config tag, e.g., "config1"
    :param mark_as_last_24_hour_run: mark the reconciliation run as latest so
        that the latest reconciliation notebook becomes available via a static
        link, e.g., `https://***/system_reconciliation/C3a.last_24hours.html`
    :param mode: the prod system run mode which defines a prod system log dir name
        - "scheduled": the system is run at predefined time automatically
        - "manual": the system run is triggered manually
    :param incremental:
        - if `True` use the data located at `market_data_file_path`
            in case the file path exists
        - if `False` dump market data
    :param prevent_overwriting: if True write permissions are removed otherwise
        a permissions remain as they are
    :param abort_if_exists: see `hio.create_dir()`
    :param backup_dir_if_exists: see `hio.create_dir()`
    :param run_notebook: if True run the reconcilation notebook otherwise do not run
    :param allow_update: if True allow to overwrite reconcilation outcomes
        otherwise retain permissions as they are
    :param set_config_values: string representations of config values used
        to override simulation params and update research portoflio config when
        running the system reconciliation notebook. Config values are separated
        with ';' in order to be processed by invoke. E.g.,
        '("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","style"),(str("longitudinal")); \n
        ("process_forecasts_node_dict","process_forecasts_dict","optimizer_config","params","kwargs"),({"target_dollar_risk_per_name": float(0.1), "prediction_abs_threshold": float(0.35)})'
    :param aws_profile: AWS profile, e.g., "ck"
    """
    hdbg.dassert(
        hserver.is_inside_docker(), "This is runnable only inside Docker."
    )
    #
    rsiprrec.reconcile_create_dirs(
        dag_builder_ctor_as_str,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        dst_root_dir,
        abort_if_exists,
        backup_dir_if_exists,
        tag=tag,
    )
    #
    reconcile_copy_prod_data(
        ctx,
        dag_builder_ctor_as_str,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        dst_root_dir,
        prod_data_source_dir,
        mode,
        tag=tag,
        prevent_overwriting=prevent_overwriting,
        aws_profile=aws_profile,
    )
    #
    reconcile_run_sim(
        ctx,
        dag_builder_ctor_as_str,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        mode,
        dst_root_dir,
        stage,
        tag=tag,
        market_data_source_dir=market_data_source_dir,
        incremental=incremental,
        set_config_values=set_config_values,
    )
    # TODO(Grisha): decide do we need to run TCA given that `CcxtBroker` logs
    # the fills.
    # if run_mode == "prod":
    #     reconcile_dump_tca_data(
    #         ctx,
    #         dag_builder_name,
    #         start_timestamp_as_str,
    #         dst_root_dir,
    #         prevent_overwriting=prevent_overwriting,
    #     )
    if run_notebook:
        notebook_run_mode = "fast"
        reconcile_run_notebook(
            ctx,
            notebook_run_mode,
            dag_builder_ctor_as_str,
            run_mode,
            start_timestamp_as_str,
            end_timestamp_as_str,
            dst_root_dir,
            mode,
            tag=tag,
            mark_as_last_24_hour_run=mark_as_last_24_hour_run,
            prevent_overwriting=prevent_overwriting,
            set_config_values=set_config_values,
        )
        notebook_run_mode = "slow"
        reconcile_run_notebook(
            ctx,
            notebook_run_mode,
            dag_builder_ctor_as_str,
            run_mode,
            start_timestamp_as_str,
            end_timestamp_as_str,
            dst_root_dir,
            mode,
            tag=tag,
            mark_as_last_24_hour_run=mark_as_last_24_hour_run,
            prevent_overwriting=prevent_overwriting,
            # The slow version of the notebook does not compute research
            # portfolio, thus does not require any overrides to the research
            # portfolio config.
            set_config_values=None,
        )
    reconcile_ls(
        ctx,
        dag_builder_ctor_as_str,
        run_mode,
        start_timestamp_as_str,
        end_timestamp_as_str,
        dst_root_dir,
        tag=tag,
    )
    if allow_update:
        _allow_update(
            dag_builder_ctor_as_str,
            run_mode,
            start_timestamp_as_str,
            end_timestamp_as_str,
            dst_root_dir,
            tag=tag,
        )
