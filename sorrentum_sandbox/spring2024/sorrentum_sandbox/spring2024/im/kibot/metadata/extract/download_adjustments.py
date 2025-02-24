#!/usr/bin/env python

"""
Download all adjustments from kibot.

> download_adjustments.py -u kibot_username -p kibot_password

# Download serially
> download_adjustments.py -u kibot_username -p kibot_password --serial

Import as:

import im.kibot.metadata.extract.download_adjustments as imkmedoad
"""
import argparse
import logging
import os
from typing import Callable, Iterable, List

import joblib
import requests
import tqdm

import helpers.hio as hio
import helpers.hs3 as hs3
import helpers.hsystem as hsystem
import im.kibot.base.command as imkibacom
import im.kibot.metadata.config as imkimecon

# #############################################################################

_JOBLIB_NUM_CPUS = 10
_JOBLIB_VERBOSITY = 1


# TODO(amr): make more general and provide as helper.
# TODO(gp): Replace this with helpers/parallel.py
def _execute_loop(
    func: Callable,
    kwargs_list: Iterable[dict],
    total: int,
    serial: bool = True,
) -> None:
    """
    Execute a function with a list of kwargs serially or in parallel.
    """
    tqdm_ = tqdm.tqdm(kwargs_list, total=total, desc="Executing loop")

    if not serial:
        joblib.Parallel(n_jobs=_JOBLIB_NUM_CPUS, verbose=_JOBLIB_VERBOSITY)(
            joblib.delayed(func)(**row) for row in tqdm_
        )
    else:
        for row in tqdm_:
            func(**row)


_LOG = logging.getLogger(__name__)


# #############################################################################


def _get_symbols_list() -> List[str]:
    """
    Get a list of symbols that have adjustments from Kibot.
    """
    response = requests.get(
        url=imkimecon.API_ENDPOINT,
        params=dict(action="adjustments", symbolsonly="1"),
    )

    symbols = response.text.splitlines()

    _LOG.info("Found %s symbols", len(symbols))
    return symbols


def _download_adjustments_data_for_symbol(symbol: str, tmp_dir: str) -> None:
    """
    Download adjustments file for a symbol and save to s3.
    """
    response = requests.get(
        url=imkimecon.API_ENDPOINT,
        params=dict(action="adjustments", symbol=symbol),
    )

    file_name = f"{symbol}.txt"
    file_path = os.path.join(tmp_dir, imkimecon.ADJUSTMENTS_SUB_DIR, file_name)
    hio.to_file(file_name=file_path, lines=str(response.content, "utf-8"))

    # Save to S3.
    aws_path = os.path.join(
        imkimecon.S3_PREFIX, imkimecon.ADJUSTMENTS_SUB_DIR, file_name
    )
    hs3.dassert_is_s3_path(aws_path)

    # TODO(amr): create hs3.copy() helper.
    cmd = "aws s3 cp %s %s" % (file_path, aws_path)
    hsystem.system(cmd)


# #############################################################################


class DownloadAdjustmentsCommand(imkibacom.KibotCommand):
    def __init__(self) -> None:
        super().__init__(
            docstring=__doc__,
            supports_tmp_dir=True,
            requires_auth=True,
            requires_api_login=True,
        )

    @staticmethod
    def customize_parser(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--serial", action="store_true", help="Download data serially"
        )

    def customize_run(self) -> int:
        symbols = _get_symbols_list()

        _execute_loop(
            func=_download_adjustments_data_for_symbol,
            kwargs_list=(
                dict(symbol=symbol, tmp_dir=self.args.tmp_dir)
                for symbol in symbols
            ),
            total=len(symbols),
            serial=self.args.serial,
        )

        return 0


if __name__ == "__main__":
    DownloadAdjustmentsCommand().run()
