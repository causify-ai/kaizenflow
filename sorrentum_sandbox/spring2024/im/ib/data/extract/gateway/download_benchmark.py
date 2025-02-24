#!/usr/bin/env python
"""
Benchmark different approaches to download IB data.

Import as:

import im.ib.data.extract.gateway.download_benchmark as imidegdobe
"""

import argparse
import logging

import ib_insync
import joblib
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.htimer as htimer
import im.ib.data.extract.gateway.download_data_ib_loop as imidegddil
import im.ib.data.extract.gateway.save_historical_data_with_IB_loop as imidegshdwil
import im.ib.data.extract.gateway.unrolling_download_data_ib_loop as imideguddil
import im.ib.data.extract.gateway.utils as imidegaut

_LOG = logging.getLogger(__name__)

SETUP = dict(
    contract=ib_insync.ContFuture(symbol="ES", exchange="GLOBEX", currency="USD"),
    start_ts=pd.Timestamp(year=2021, month=3, day=10),
    end_ts=pd.Timestamp(year=2021, month=3, day=15),
    duration_str="1 D",
    bar_size_setting="1 min",
    what_to_show="TRADES",
    use_rth=False,
)


def _run_req_wrapper() -> None:
    """
    Run direct IB request.
    """
    args = SETUP.copy()
    ib = imidegaut.ib_connect(200, False)
    contract = ib.qualifyContracts(args.pop("contract"))[0]
    ib.disconnect()
    args.pop("start_ts")
    args.update(
        dict(
            ib=ib,
            contract=contract,
        )
    )
    for dur, times in [("10 D", 1), ("1 M", 1), ("10 D", 3)]:
        _LOG.info("Running request wrapper code %s %s times...", dur, times)
        timer = htimer.Timer()
        args.update(dict(duration_str=dur))
        for i in range(times):
            ib = imidegaut.ib_connect(201 + i, False)
            args["ib"] = ib
            df = imidegaut.req_historical_data(**args)
            ib.disconnect()
        _LOG.info(
            "Finished. Time: %s seconds. Dataframe: %s",
            timer.get_elapsed(),
            imidegaut.get_df_signature(df),
        )


def _run_unrolling_download_data_ib_loop() -> None:
    """
    Run latest code.
    """
    _LOG.info("Running unrolling_download_data_ib_loop code...")
    for mode, num_threads, dst_dir in [
        ("in_memory", "serial", "./in_memory"),
        ("on_disk", "serial", "./on_disk_serial"),
        ("on_disk", 4, "./on_disk_4_cores"),
    ]:
        hio.create_dir(dst_dir, incremental=True)
        args = SETUP.copy()
        args.update(
            dict(
                client_id=300,
                mode=mode,
                num_threads=num_threads,
                incremental=False,
                dst_dir=dst_dir,
            )
        )
        args.pop("duration_str")
        _LOG.info(
            "Starting data extraction. Mode: %s. Threads: %s.", mode, num_threads
        )
        timer = htimer.Timer()
        df = imideguddil.get_historical_data(**args)
        _LOG.info(
            "Finished. Time: %s seconds. Dataframe: %s",
            timer.get_elapsed(),
            imidegaut.get_df_signature(df),
        )
        hio.delete_dir(dst_dir)


def _run_save_historical_data_with_IB_loop() -> None:
    """
    Run saving to separate files.
    """
    _LOG.info("Running save_historical_data_with_IB_loop code...")
    file_name = "./save_ib_loop/experiment.csv"
    hio.create_enclosing_dir(file_name, incremental=True)
    _LOG.info("Starting data extraction.")
    args = SETUP.copy()
    args.update(
        dict(file_name=file_name, ib=imidegaut.ib_connect(400, is_notebook=False))
    )
    timer = htimer.Timer()
    df = imidegshdwil.save_historical_data_with_IB_loop(**args)
    args["ib"].disconnect()
    _LOG.info(
        "Finished. Time: %s seconds. Dataframe: %s",
        timer.get_elapsed(),
        imidegaut.get_df_signature(df),
    )
    hio.delete_file(file_name)


def _run_download_data_IB_loop() -> None:
    """
    Run loading by chunks different symbol sequentially.
    """
    symbols = ["DA", "ES", "NQ"]
    _LOG.info("Running sequential downloading of %s", symbols)
    timer = htimer.Timer()
    for symbol in symbols:
        _run_download_data_IB_loop_by_symbol(500, symbol)
    _LOG.info(
        "Finished %s sequential extracting. Time: %s",
        symbols,
        timer.get_elapsed(),
    )
    # Run loading by chunks different symbols in parallel.
    _LOG.info("Running parallel downloading of %s", symbols)
    timer.resume()
    joblib.Parallel(n_jobs=4)(
        joblib.delayed(_run_download_data_IB_loop_by_symbol)(600, symbol)
        for symbol in symbols
    )
    _LOG.info(
        "Finished %s parallel extracting. Time: %s", symbols, timer.get_elapsed()
    )


def _run_download_data_IB_loop_by_symbol(
    base_client_id: int, symbol: str
) -> None:
    """
    Run loading by chunks.
    """
    _LOG.info("Running download_data_IB_loop code for %s symbol...", symbol)
    file_name = "./simple_ib_loop/experiment.csv"
    hio.create_enclosing_dir(file_name, incremental=True)
    _LOG.info("Starting in memory data extraction.")
    args = SETUP.copy()
    args.update(
        dict(
            ib=imidegaut.ib_connect(
                base_client_id + sum(bytes(symbol, encoding="UTF-8")),
                is_notebook=False,
            )
        )
    )
    args.update(
        dict(
            contract=args["ib"].qualifyContracts(
                ib_insync.ContFuture(symbol, exchange="GLOBEX", currency="USD")
            )[0],
        )
    )
    for duration_str in ["1 D", "2 D"]:
        args.update(dict(duration_str=duration_str))
        _LOG.info("Run for %s duration", duration_str)
        timer = htimer.Timer()
        df = imidegddil.get_historical_data_with_IB_loop(**args)
        _LOG.info(
            "Finished. Time: %s seconds. Dataframe: %s",
            timer.get_elapsed(),
            imidegaut.get_df_signature(df),
        )
    args["ib"].disconnect()
    hio.delete_file(file_name)


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _run_unrolling_download_data_ib_loop()
    _run_save_historical_data_with_IB_loop()
    _run_download_data_IB_loop()
    _run_req_wrapper()


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    hparser.add_verbosity_arg(parser)
    return parser


if __name__ == "__main__":
    _main(_parse())
