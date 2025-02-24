#!/usr/bin/env python

"""
Process a result directory in place.

Import as:

import dataflow.scripts.process_experiment_result as dtfsprexre
"""

import argparse
import glob
import logging

from tqdm.auto import tqdm

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hpickle as hpickle

_LOG = logging.getLogger(__name__)

# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dst_dir", action="store", help="Destination dir")
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    dst_dir = args.dst_dir
    dst_dir = "/cache/experiments/oos_experiment.RH2Eg.v2_0-all.5T.run2.hacked"
    hdbg.dassert_dir_exists(dst_dir)
    # Look for files like `.../result_0/result_bundle.v2_0.pkl`
    glob_exp = dst_dir + "/**/result_bundle.v2_0.pkl"
    _LOG.info("glob_exp=%s", glob_exp)
    files = glob.glob(glob_exp, recursive=True)
    _LOG.info("Found %d files", len(files))
    # Process files.
    for file_name in tqdm(files):
        obj = hpickle.from_pickle(file_name)
        obj.payload = None
        hpickle.to_pickle(obj, file_name)


if __name__ == "__main__":
    _main(_parse())
