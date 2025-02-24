"""
Invokes in the file are runnable from a Docker container only.

E.g., to run for certain date from a Docker container:
```
docker> invoke reconcile_data_run_notebook  \
   --db-stage 'dev' \
   --start-timestamp '2022-11-01T00:00:00+00:00' \
   --end-timestamp '2022-11-01T02:00:00+00:00' \
   --exchange-id 'binance' \
   --data-type 'bid_ask' \
   --contract-type 'futures' \
   --db-table 'ccxt_bid_ask_futures_resampled_1min_preprod' \
   --aws-profile 'ck' \
   --s3-vendor 'crypto_chassis' \
   --s3-path 's3://cryptokaizen-data.preprod/reorg/daily_staged.airflow.pq' \
   --base-dst-dir '/shared_data/ecs/preprod/data_reconciliation' \
   --bid-ask-accuracy 1 \
   --resample-mode 'resample_1min'

to run outside a Docker container:
```
> invoke docker_cmd --cmd 'invoke reconcile_data_run_notebook ...'
```

Import as:

import dev_scripts.lib_tasks_data_reconcile as dsltdare
"""

import logging
import os
import re

from invoke import task

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.hio as hio
import oms.lib_tasks_reconcile as olitarec

_LOG = logging.getLogger(__name__)


def _reconcile_data_create_dirs(
    base_dst_dir: str,
    start_timestamp: str,
    end_timestamp: str,
    db_table: str,
    abort_if_exists=True,
) -> str:
    """
    Create dirs for storing data reconciliation results.

    Final dirs layout is:
    ```
    {base_dst_dir}/
        {timestamp_dst_dir}/
            {db_table}/
                result_0/
            ...
    ```

    i.e.
    ```
    shared_data/ecs/preprod/data_reconciliation/
         20221021_000000.20221021_210000 \
             ccxt_ohlcv_futures_preprod/
                result_0
            ...
    ```

    :param base_dst_dir: base directory (most likely shared) to store data
     reconciliation
    :param start_timestamp: start of the reconciled time interval
    :param end_timestamp: end of the reconciled time interval
    :param db_table: DB table the reconciliation is done for, at the moment assuming
     there is only a single reconcilation done on a particular table and particular
     time range.
    :param abort_if_exists: see `hio.create_dir()`
    :return: path to the created target dir
    """
    # Transform the timestamp arguments to avoid special characters
    #  i.e. 2022-11-01T00:02:00+00:00 -> 20221101_000200
    #  the context isn't lost since the raw args are present in the saved notebook
    #  and also chances of using anything else as UTC are low.
    start_timestamp = start_timestamp.replace("+00:00", "")
    end_timestamp = end_timestamp.replace("+00:00", "")
    start_timestamp = re.sub(r"[^A-Za-z0-9 ]+", "", start_timestamp)
    end_timestamp = re.sub(r"[^A-Za-z0-9 ]+", "", end_timestamp)
    start_timestamp = start_timestamp.replace("T", "_")
    end_timestamp = end_timestamp.replace("T", "_")
    timestamp_dst_dir = f"{start_timestamp}.{end_timestamp}"
    target_dir = os.path.join(base_dst_dir, timestamp_dst_dir, db_table)
    # Create a dir for reconcilation results.
    hio.create_dir(target_dir, incremental=True, abort_if_exists=abort_if_exists)
    # Sanity check the created dirs.
    cmd = f"ls -lh {target_dir}"
    olitarec._system(cmd)
    return target_dir


# TODO(Juraj): this flow is very similiar to omlitare.reconcile_run_notebook
#  it might be good to define common behavior.
# TODO(Juraj): divide into smaller invokes and then run in a single
#  reconcile_data_run_all.
# TODO(Juraj): add prevent_overwriting option.
@task
def reconcile_data_run_notebook(
    ctx,
    db_stage,
    start_timestamp,
    end_timestamp,
    exchange_id,
    data_type,
    contract_type,
    db_table,
    aws_profile,
    s3_vendor,
    s3_path,
    base_dst_dir,
    bid_ask_accuracy=None,
    bid_ask_depth=10,
    resample_mode=None,
):  # type: ignore
    """
    Run data reconciliation notebook and store in in a stored location.

    See `im_v2.ccxt.data.extract.compare_realtime_and_historical` for
    reconcilation params description.

    :param base_dst_dir: dir to store data reconciliation
    """
    # TODO(Juraj): this does not work in the cmamp prod container when ran
    #  via AWS ECS.
    # hdbg.dassert(
    #    hserver.is_inside_docker(), "This is runnable only inside Docker."
    # )
    config_dict = {
        "db_stage": db_stage,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "exchange_id": exchange_id,
        "data_type": data_type,
        "contract_type": contract_type,
        "db_table": db_table,
        "aws_profile": aws_profile,
        "s3_vendor": s3_vendor,
        "s3_path": s3_path,
        "bid_ask_accuracy": bid_ask_accuracy,
        "bid_ask_depth": bid_ask_depth,
        "resample_mode": resample_mode,
    }
    config = cconfig.Config.from_dict(config_dict)
    os.environ["CK_DATA_RECONCILIATION_CONFIG"] = config.to_python()
    _ = ctx
    # Set directory to store results locally
    results_dir = "."
    # Add the command to run the notebook.
    notebook_path = "amp/im_v2/ccxt/notebooks/Data_reconciliation.ipynb"
    cmd_txt = []
    config_builder = (
        "amp.im_v2.ccxt.data.extract.compare_realtime_and_historical."
        + "build_dummy_data_reconciliation_config()"
    )
    opts = (
        "--num_threads 'serial' --allow_errors --publish_notebook -v DEBUG 2>&1"
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
    # Make the script executable and run it.
    _LOG.info("Running the notebook=%s", notebook_path)
    olitarec._system(script_name)
    # Assert directory generated by `run_notebook` was created.`
    results_dir = os.path.join(results_dir, "result_0")
    # hdbg.dassert_dir_exists(results_dir)
    # Copy the published notebook to the specified folder.
    target_dir = _reconcile_data_create_dirs(
        base_dst_dir, start_timestamp, end_timestamp, db_table
    )
    hdbg.dassert_dir_exists(target_dir)
    _LOG.info("Copying results from '%s' to '%s'", results_dir, target_dir)
    cmd = f"cp -vr {results_dir} {target_dir}"
    olitarec._system(cmd)
    # This is a workaround to get outcome of the data reconciliation from the notebook.
    reconc_outcome = hio.from_file("/app/ck_data_reconciliation_outcome.txt")
    if reconc_outcome.strip() == "SUCCESS":
        _LOG.info(
            "Data reconciliation was successful, results stored in '%s'",
            target_dir,
        )
    else:
        hdbg.dfatal(
            message=f"Data reconciliation failed:\n {reconc_outcome} \n"
            + f"Results stored in '{target_dir}'"
        )


# TODO(Juraj): temporary solution, the refactoring will be completed to use
#  dataset signatures for all datasets
@task
def reconcile_data_run_notebook(
    ctx,
    db_stage,
    start_timestamp,
    end_timestamp,
    db_table,
    aws_profile,
    s3_path,
    base_dst_dir,
    s3_dataset_signature,
    bid_ask_accuracy=None,
):  # type: ignore
    """
    Run data reconciliation notebook and store it in a specified location.

    See `im_v2.ccxt.data.extract.compare_realtime_and_historical` for
    reconcilation params description.

    :param base_dst_dir: dir to store data reconciliation
    """
    # TODO(Juraj): this does not work in the cmamp prod container when ran
    #  via AWS ECS.
    # hdbg.dassert(
    #    hserver.is_inside_docker(), "This is runnable only inside Docker."
    # )
    config_dict = {
        "db_stage": db_stage,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "db_table": db_table,
        "aws_profile": aws_profile,
        "s3_dataset_signature": s3_dataset_signature,
        "s3_path": s3_path,
        "bid_ask_accuracy": bid_ask_accuracy,
    }
    config = cconfig.Config.from_dict(config_dict)
    os.environ["CK_DATA_RECONCILIATION_CONFIG"] = config.to_python()
    _ = ctx
    # Set directory to store results locally
    results_dir = "."
    # Add the command to run the notebook.
    notebook_path = "amp/im_v2/ccxt/notebooks/Data_reconciliation.ipynb"
    cmd_txt = []
    config_builder = (
        "amp.im_v2.ccxt.data.extract.compare_realtime_and_historical."
        + "build_dummy_data_reconciliation_config()"
    )
    opts = (
        "--num_threads 'serial' --allow_errors --publish_notebook -v DEBUG 2>&1"
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
    # Make the script executable and run it.
    _LOG.info("Running the notebook=%s", notebook_path)
    olitarec._system(script_name)
    # Assert directory generated by `run_notebook` was created.`
    results_dir = os.path.join(results_dir, "result_0")
    # hdbg.dassert_dir_exists(results_dir)
    # Copy the published notebook to the specified folder.
    target_dir = _reconcile_data_create_dirs(
        base_dst_dir, start_timestamp, end_timestamp, db_table
    )
    hdbg.dassert_dir_exists(target_dir)
    _LOG.info("Copying results from '%s' to '%s'", results_dir, target_dir)
    cmd = f"cp -vr {results_dir} {target_dir}"
    olitarec._system(cmd)
    # This is a workaround to get outcome of the data reconciliation from the notebook.
    reconc_outcome = hio.from_file("/app/ck_data_reconciliation_outcome.txt")
    if reconc_outcome.strip() == "SUCCESS":
        _LOG.info(
            "Data reconciliation was successful, results stored in '%s'",
            target_dir,
        )
    else:
        hdbg.dfatal(
            message=f"Data reconciliation failed:\n {reconc_outcome} \n"
            + f"Results stored in '{target_dir}'"
        )
