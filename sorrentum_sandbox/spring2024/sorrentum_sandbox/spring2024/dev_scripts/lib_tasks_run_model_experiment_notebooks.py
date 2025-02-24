"""
Invokes in the file are runnable from a Docker container only.

Examples:
```
docker> invoke run_notebooks \
        --system-log-dir "/shared_data/ecs/test/twap_experiment/20230814_1" \
        --base-dst-dir "s3://cryptokaizen-html/notebooks" \
        --system-log-dir-recon "/shared_data/ecs/preprod/prod_reconciliation/"

to run outside a Docker container:
```
> invoke docker_cmd --cmd 'invoke run_notebooks ...'
```

Import as:

import dev_scripts.lib_tasks_run_model_experiment_notebooks as dsltrmeno
"""

import logging
import os
from typing import Optional

import pandas as pd
from invoke import task

import core.config as cconfig
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hsystem as hsystem
import im_v2.common.universe as ivcu
import reconciliation.sim_prod_reconciliation as rsiprrec

_LOG = logging.getLogger(__name__)


def _run_notebook(
    config_builder: str,
    base_dst_dir: str,
    notebook_path: str,
    analysis_notebooks_results_dir: str,
    *,
    abort_on_error: bool = False,
) -> None:
    """
    Run analysis notebooks and store it in a specified location.

    :param config_builder: config builder to build the notebook config
    :param base_dst_dir: top most directory to store data into
    :param notebook_path: relative path to the notebook to execute,
        assuming amp is a submodule.
    :param analysis_notebooks_results_dir: root dir to store analysis
        notebooks results
    :param abort_on_error: if True, abort the execution if an error is
        encountered during the notebook execution
    """
    # TODO(Juraj): this does not work in the cmamp prod container when ran
    #  via AWS ECS.
    # hdbg.dassert(
    #    hserver.is_inside_docker(), "This is runnable only inside Docker."
    # )
    # Create dir for the particular notebook to store the results.
    # Example of the dir: `../system_log_dir.manual/analysis_notebooks/Master_broker_debugging/`
    notebook_file_name = os.path.basename(notebook_path)
    notebook_file_name = notebook_file_name.split(".")[0]
    results_dir = os.path.join(analysis_notebooks_results_dir, notebook_file_name)
    cmd_txt = []
    opts = "--tee --no_suppress_output --num_threads 'serial' "
    if abort_on_error:
        opts += " --allow_errors"
    opts += (
        " --publish_notebook -v DEBUG 2>&1 | tee log.txt; exit ${PIPESTATUS[0]}"
    )
    cmd_run_txt = [
        "amp/dev_scripts/notebooks/run_notebook.py",
        f"--notebook {notebook_path}",
        f"--config_builder '{config_builder}'",
        f"--dst_dir '{results_dir}'",
        f"{opts}",
    ]
    cmd_run_txt = " ".join(cmd_run_txt)
    cmd_txt.append(cmd_run_txt)
    cmd_txt = "\n".join(cmd_txt)
    # Save the commands as a script.
    script_name = "tmp.publish_notebook.sh"
    hio.create_executable_script(script_name, cmd_txt)
    # Delete the temp dir before execution.
    results_dir = os.path.join(results_dir, "result_0")
    hio.delete_dir(results_dir)
    # Make the script executable and run it.
    _LOG.info("Running the notebook=%s", notebook_path)
    # if allow_errors is True and we still encounter error then abort to prevent infinite loop.
    rc = hsystem.system(
        script_name,
        suppress_output=False,
        log_level="echo",
        abort_on_error=abort_on_error,
    )
    if rc != 0:
        _LOG.info(
            "Failed running notebook=%s, Trying again with --allow-errors",
            notebook_path,
        )
        _run_notebook(
            config_builder,
            base_dst_dir,
            notebook_path,
            analysis_notebooks_results_dir,
            abort_on_error=True,
        )
        return
    # Move the ipynb.html file to s3.
    if hs3.is_s3_path(base_dst_dir):
        notebook_name = os.path.basename(notebook_path)
        notebook_name = os.path.splitext(notebook_name)[0]
        find_and_move_html_file_to_s3(
            notebook_name,
            results_dir,
            base_dst_dir,
            analysis_notebooks_results_dir=analysis_notebooks_results_dir,
        )
    else:
        hio.create_dir(base_dst_dir, incremental=True)
        hdbg.dassert_dir_exists(base_dst_dir)
        _LOG.info("Copying results from '%s' to '%s'", results_dir, base_dst_dir)
        hsystem.system(script_name, suppress_output=False, log_level="echo")


def _get_analysis_notebooks_file_path(analysis_notebooks_results_dir) -> str:
    """
    Get path to the CSV file storing links to the published notebooks.

    :param analysis_notebooks_results_dir: root dir to store analysis
        notebooks results
    """
    hdbg.dassert_dir_exists(analysis_notebooks_results_dir)
    analysis_notebooks_file_path = os.path.join(
        analysis_notebooks_results_dir, "analysis_notebooks_links.csv"
    )
    return analysis_notebooks_file_path


def find_and_move_html_file_to_s3(
    notebook_name: str,
    results_dir: str,
    base_dst_dir: str,
    *,
    analysis_notebooks_results_dir: Optional[str] = None,
) -> None:
    """
    Find the notebook_name.*.html file in results_dir and move to s3.

    :param notebook_name: html notebook name which needs to be publish
    :param results_dir: dir where html notebook is saved
    :param base_dst_dir: s3 dst path to publish
    :param analysis_notebooks_results_dir: if present, it is used as the
        root directory to store analysis notebook results
    """
    html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
    cmd = f"find {results_dir} -type f -name '{notebook_name}.*.html'"
    _, html_notebook_path = hsystem.system_to_string(cmd)
    html_notebook_name = os.path.basename(html_notebook_path)
    #
    s3_dst_path = os.path.join(base_dst_dir, html_notebook_name)
    aws_profile = "ck"
    hs3.copy_file_to_s3(html_notebook_path, s3_dst_path, aws_profile)
    if base_dst_dir.startswith(html_bucket_path):
        dir_to_url = henv.execute_repo_config_code(
            "get_html_dir_to_url_mapping()"
        )
        url_bucket_path = dir_to_url[html_bucket_path]
        url = s3_dst_path.replace(html_bucket_path, url_bucket_path)
        if analysis_notebooks_results_dir is not None:
            analysis_notebooks_file_path = _get_analysis_notebooks_file_path(
                analysis_notebooks_results_dir
            )
            # Add url to the csv file along with notebook name.
            notebook_info = pd.DataFrame(
                [[notebook_name, url]], columns=["Notebook Name", "URL"]
            )
            # Set header to False if the file already exists to avoid repeating the
            # header in the output.
            header = (
                False if os.path.exists(analysis_notebooks_file_path) else True
            )
            notebook_info.to_csv(
                analysis_notebooks_file_path, mode="a", index=False, header=header
            )
            _LOG.info(f"URL - {url} added to {analysis_notebooks_file_path}")
        cmd = f"""
        # To open the notebook from a web-browser open a link:
        {url}
        """
        print(hprint.dedent(cmd))


def publish_system_reconciliation_notebook(
    system_log_dir: str, base_dst_dir: str, analysis_notebooks_results_dir: str
) -> None:
    """
    system_reconciliation notebook is already created with `reconcile_run_all`
    just need to publish it.

    :param system_log_dir: refer `run_notebooks()` for param description
    :param base_dst_dir: refer `run_notebooks()` for param description
    :param analysis_notebooks_results_dir: root dir to store analysis
        notebooks results
    """
    reconciliation_notebook_path = system_log_dir.replace(
        "system_reconciliation", "prod_reconciliation"
    )
    # Filter out path , eg.: */prod_reconciliation/C5b/prod/20240108_170500.20240108_173000/system_log_dir.manual/process_forecasts
    # -> */prod_reconciliation/C5b/prod/20240108_170500.20240108_173000
    reconciliation_notebook_path = "/".join(
        reconciliation_notebook_path.split("/")[:-2]
    )
    reconciliation_notebook_path = os.path.join(
        reconciliation_notebook_path, "reconciliation_notebook/fast/result_0"
    )
    notebook_name = "Master_system_reconciliation_fast"
    find_and_move_html_file_to_s3(
        notebook_name,
        reconciliation_notebook_path,
        base_dst_dir,
        analysis_notebooks_results_dir=analysis_notebooks_results_dir,
    )


def _publish_master_trading_notebook(
    timestamp_dir: str,
    analysis_notebooks_results_dir: str,
    *,
    mark_as_latest: bool = True,
    cleanup: bool = True,
):
    """
    Run the trading system report notebook and publish it to S3.

    :param timestamp_dir: a dir where results for a specific run are stored
    :param analysis_notebooks_results_dir: root dir to store analysis notebooks
        results
    :param mark_as_latest: if True, mark the dashboard as `latest`, otherwise
        just publish a timestamped copy
    :param cleanup: if True, cleanup the temporary directory after the
        notebook is published. This is useful for local runs intended for
        debugging purposes
    """
    # TODO(Vlad): Factor out common code with the
    # `helpers.lib_tasks_gh.publish_buildmeister_dashboard_to_s3()`.
    amp_abs_path = hgit.get_amp_abs_path()
    run_notebook_script_path = os.path.join(
        amp_abs_path, "dev_scripts/notebooks/run_notebook.py"
    )
    notebook_path = os.path.join(
        amp_abs_path, "oms/notebooks/Master_trading_system_report.ipynb"
    )
    # Publish the notebook.
    # Do not pass S3 path to `run_notebook.py` with `--publish` flag to preserve
    # an access to the notebook via a stable link. So publish it to a temporary
    # local directory and then copy to S3 without timestamp in the name.
    dst_local_dir = os.path.join(amp_abs_path, "tmp.notebooks")
    analysis_notebooks_file_path = _get_analysis_notebooks_file_path(
        analysis_notebooks_results_dir
    )
    config_builder = (
        "oms.execution_analysis_configs."
        f'get_master_trading_system_report_notebook_config("{timestamp_dir}", "{analysis_notebooks_file_path}")'
    )
    cmd_run_txt = [
        run_notebook_script_path,
        f"--notebook {notebook_path}",
        f"--config_builder '{config_builder}'",
        f"--dst_dir '{dst_local_dir}'",
        "--publish",
        "--num_threads serial",
    ]
    cmd_run_txt = " ".join(cmd_run_txt)
    hsystem.system(cmd_run_txt)
    # Get HTML file name.
    tmp_local_dir_name = os.path.join(amp_abs_path, "tmp.notebooks")
    pattern = "Master_trading_system_report.0*.html"
    only_files = True
    use_relative_paths = False
    local_html_files = hio.listdir(
        tmp_local_dir_name,
        pattern,
        only_files=only_files,
        use_relative_paths=use_relative_paths,
    )
    # Assert if more than 1 file is returned.
    hdbg.dassert_eq(
        len(local_html_files),
        1,
        f"Found more than one file in {tmp_local_dir_name} - {local_html_files}",
    )
    local_html_file_path = local_html_files[0]
    html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
    s3_build_path = os.path.join(html_bucket_path, "notebooks", "Master_Analysis")
    aws_profile = "ck"
    if mark_as_latest:
        # Copy the dashboard notebook to S3 as latest build.
        s3_latest_build_path = os.path.join(
            s3_build_path, "Master_trading_system_report.latest.html"
        )
        hs3.copy_file_to_s3(
            local_html_file_path, s3_latest_build_path, aws_profile
        )
        _print_html_url_by_s3_path(s3_latest_build_path)
    # Copy the timestamped version of the dashboard notebook to S3.
    local_html_file_name = os.path.basename(local_html_file_path)
    s3_timestamped_build_path = os.path.join(s3_build_path, local_html_file_name)
    hs3.copy_file_to_s3(
        local_html_file_path, s3_timestamped_build_path, aws_profile
    )
    _print_html_url_by_s3_path(s3_timestamped_build_path)
    if cleanup:
        hio.delete_dir(tmp_local_dir_name)


def _print_html_url_by_s3_path(s3_file_name: str) -> None:
    """
    Print the URL of the HTML file stored in S3.

    :param s3_file_name: S3 path to the HTML file
    """
    # TODO(Vlad): Factor out common code with the
    # `dev_scripts.notebooks.publish_notebook.py`.
    html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
    dir_to_url = henv.execute_repo_config_code("get_html_dir_to_url_mapping()")
    url_bucket_path = dir_to_url[html_bucket_path]
    url = s3_file_name.replace(html_bucket_path, url_bucket_path)
    cmd = f"""
    # To open the notebook from a web-browser open a link:
    {url}
    """
    print(hprint.dedent(cmd))


# TODO(Grisha): Consider to move the script to `oms.`
# TODO(Grisha): running analysis notebooks, publishing the reconciliation
# notebook and running the trading report notebook should become separate
# functions. Otherwise, all the `if-else` inside the function is hard to follow.
@task
def run_notebooks(
    ctx, system_log_dir: str, base_dst_dir: str, run_mode: str = "all_notebooks"
):  # type: ignore
    """
    Run cross dataset reconciliation notebook and store it in a specified
    location.

    :param system_log_dir: dir where run logs are saved
        Eg.:
        ```
        Broker only :
            /shared_data/ecs/test/20240110_experiment1
        Full System run:
            /shared_data/ecs/test/system_reconciliation/C5b/prod/20240108_170500.20240108_173000/system_log_dir.manual/process_forecasts
        ```

    :param base_dst_dir: dir to store ipython notebooks
    :param run_mode: detetermine set of notebooks to run, only relevant for full system runs,
        broker only runs run all notebooks by default
        all_notebooks: default option, run all notebooks
            - for full system experiments assumes that reconciliation flow has been run
        skip_reconciliation: skip `Master_system_reconciliation_fast` notebook
        reconciliation_only: only publish `Master_system_reconciliation_fast`
            - only applicable for full system run, assumes that reconciliation flow has been run
        trading_report_only: only publish `Master_trading_system_report`
            - assumes that reconciliation flow has been run
    """
    hdbg.dassert_in(
        run_mode,
        [
            "all_notebooks",
            "skip_reconciliation",
            "reconciliation_only",
            "trading_report_only",
        ],
    )
    _ = ctx
    # `system_log_dir` is in a form `.../system_log_dir/process_forecasts` and
    # we want to extract `.../system_log_dir` to find SystemConfig.
    full_system_log_dir, _ = os.path.split(system_log_dir)
    # Create dir to store analysis notebooks results.
    # TODO(Grisha): consider moving the analysis notebooks data outside of the
    # system_log_dir since they are not a part of the system run.
    analysis_notebooks_results_dir = os.path.join(
        full_system_log_dir, "analysis_notebooks"
    )
    hio.create_dir(analysis_notebooks_results_dir, incremental=True)
    # TODO(Sonaal): get the `system_config.output.values_as_strings.pkl` from
    # some constant.
    config_path = os.path.join(
        full_system_log_dir, "system_config.output.values_as_strings.pkl"
    )
    # The assumption is that a full System run saves SystemConfig which is not
    # the case for broker-only runs.
    is_full_system_run = os.path.exists(config_path)
    if not is_full_system_run:
        # For broker-only run, only "all_notebooks" is valid.
        hdbg.dassert_eq(run_mode, "all_notebooks")
    # For broker only runs we are guaranteed to capture all bid/ask data
    # during experiment itself.
    bid_ask_data_source = "logged_during_experiment"
    if is_full_system_run:
        # Load pickled SystemConfig.
        system_config = cconfig.load_config_from_pickle(config_path)
        # Get param values from SystemConfig.
        bar_duration_in_secs = rsiprrec.get_bar_duration_from_config(
            system_config
        )
        bar_duration = hdateti.convert_seconds_to_pandas_minutes(
            bar_duration_in_secs
        )
        universe_version = system_config["market_data_config", "universe_version"]
        child_order_execution_freq = system_config[
            "process_forecasts_node_dict",
            "process_forecasts_dict",
            "order_config",
            "execution_frequency",
        ]
        price_col = system_config["portfolio_config", "mark_to_market_col"]
        table_name = system_config[
            "market_data_config", "im_client_config", "table_name"
        ]
        #
        _LOG.debug("Using bar_duration=%s from SystemConfig", bar_duration)
        _LOG.debug(
            "Using universe_version=%s from SystemConfig", universe_version
        )
        _LOG.debug(
            "Using child_order_execution_freq=%s from SystemConfig",
            child_order_execution_freq,
        )
        _LOG.debug(
            "Using price_col=%s from SystemConfig",
            price_col,
        )
        _LOG.debug(
            "Using table_name=%s from SystemConfig",
            table_name,
        )
        # For full system runs, the default method is to use bid/ask data
        # Logged after the experiment to avoid potential gaps.
        bid_ask_data_source = "logged_after_experiment"
    else:
        # Setting default values for `table_name` and `price_col`.
        # These initializations are essential for the execution analysis notebook to run smoothly.
        table_name = "ccxt_ohlcv_futures"
        price_col = "close"
        args_logfile = os.path.join(system_log_dir, "args.json")
        hdbg.dassert_file_exists(args_logfile)
        args_dict = hio.from_json(args_logfile)
        hdbg.dassert_in("parent_order_duration_in_min", args_dict.keys())
        bar_duration = str(args_dict["parent_order_duration_in_min"]) + "T"
        _LOG.debug("Using bar_duration from Broker only args")
        hdbg.dassert_in("universe", args_dict.keys())
        universe_version = args_dict["universe"]
        _LOG.debug("Using universe_version from Broker only args")
        hdbg.dassert_in("child_order_execution_freq", args_dict.keys())
        child_order_execution_freq = args_dict["child_order_execution_freq"]
        _LOG.debug("Using child_order_execution_freq from Broker only args")
    _LOG.info("bar_duration=%s", bar_duration)
    _LOG.info("universe_version=%s", universe_version)
    _LOG.info("child_order_execution_freq=%s", child_order_execution_freq)
    _LOG.info("price_col=%s", price_col)
    _LOG.info("table_name=%s", table_name)
    # Get a random `test_asset_id` from the universe.
    vendor = "CCXT"
    mode = "trade"
    asset_ids = sorted(
        ivcu.get_vendor_universe_as_asset_ids(universe_version, vendor, mode)
    )
    test_asset_id = asset_ids[0]
    bid_ask = (
        "amp/oms/notebooks/Master_bid_ask_execution_analysis.ipynb",
        "amp.oms.execution_analysis_configs."
        + f'get_bid_ask_execution_analysis_configs("{system_log_dir}", "{bar_duration}", "{bid_ask_data_source}", test_asset_id={test_asset_id})',
    )
    master_exec = (
        "amp/oms/notebooks/Master_execution_analysis.ipynb",
        "amp.oms.execution_analysis_configs."
        + f'get_execution_analysis_configs_Cmtask4881("{system_log_dir}", \
            "{bar_duration}", \
            "{universe_version}", \
            "{child_order_execution_freq}", \
            "{price_col}", \
            "{table_name}", \
            test_asset_id={test_asset_id})',
    )
    broker_debug = (
        "amp/oms/notebooks/Master_broker_debugging.ipynb",
        "amp.oms.execution_analysis_configs."
        + f'get_broker_debugging_configs_Cmtask4881("{system_log_dir}")',
    )
    portfolio_recon = (
        "amp/oms/notebooks/Master_broker_portfolio_reconciliation.ipynb",
        "amp.oms.execution_analysis_configs."
        + f'get_broker_portfolio_reconciliation_configs_Cmtask5690("{system_log_dir}")',
    )
    # create list of notebooks to run.
    notebooks = []
    if run_mode in ["all_notebooks", "skip_reconciliation"]:
        if is_full_system_run:
            notebooks.append(portfolio_recon)
        # Sometimes the bid/ask notebook fails for long runs. It's the last one
        # so that we run the rest before failing on the bid/ask notebook.
        notebooks.extend([broker_debug, master_exec, bid_ask])
    if is_full_system_run and run_mode in [
        "all_notebooks",
        "reconciliation_only",
    ]:
        publish_system_reconciliation_notebook(
            system_log_dir, base_dst_dir, analysis_notebooks_results_dir
        )
    for notebook, config in notebooks:
        _run_notebook(
            config, base_dst_dir, notebook, analysis_notebooks_results_dir
        )
    # Publish master trading report notebook.
    # The trading report notebook requires all the analysis notebooks to be finished.
    # TODO(Grisha): move the trading report piece into a separate function.
    if is_full_system_run and run_mode == "trading_report_only":
        _LOG.debug("Running only Master_trading_system_report notebook")
        timestamp_dir = os.path.split(full_system_log_dir)[0]
        _publish_master_trading_notebook(
            timestamp_dir, analysis_notebooks_results_dir, mark_as_latest=True
        )
