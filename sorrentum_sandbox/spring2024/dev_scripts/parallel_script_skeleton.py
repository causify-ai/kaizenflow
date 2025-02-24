#!/usr/bin/env python

"""
This is an example of script using the `joblib_helpers` API to run jobs in
parallel.

# Run with:
> clear; parallel_script_skeleton.py --workload success --num_threads serial
> clear; parallel_script_skeleton.py --workload success --num_threads 2
> clear; parallel_script_skeleton.py --workload failure --num_threads serial
> clear; parallel_script_skeleton.py --workload failure --num_threads 3

Add a description of what the script does and examples of command lines.
Check dev_scripts/linter.py to see an example of a script using this
template.

Import as:

import dev_scripts.parallel_script_skeleton as dspascsk
"""

# TODO(gp): We should test this, although the library is already tested.

import argparse
import logging
import os

import helpers.hdbg as hdbg
import helpers.hjoblib as hjoblib
import helpers.hparser as hparser

# This module contains example workloads.
import helpers.test.test_joblib_helpers

# import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--workload",
        action="store",
        type=str,
        choices=["success", "failure"],
        help="Worklod to execute",
    )
    parser.add_argument(
        "--randomize",
        action="store_true",
    )
    parser.add_argument(
        "--seed",
        action="store",
        default=1,
        type=int,
    )
    # parser = hparser.add_dst_dir_arg(parser, dst_dir_required=True)
    parser = hparser.add_parallel_processing_arg(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser  # type: ignore


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Prepare the workload.
    randomize = args.randomize
    # randomize = False
    seed = args.seed
    if args.workload == "success":
        workload = helpers.test.test_joblib_helpers.get_workload1(
            randomize, seed=seed
        )
    elif args.workload == "failure":
        workload = helpers.test.test_joblib_helpers.get_workload2()
    else:
        hdbg.dfatal("Invalid workload='%s'" % args.workload)
    # Handle the dst dir.
    # dst_dir, clean_dst_dir = hparser.parse_dst_dir_arg(args)
    # _ = clean_dst_dir
    # Parse command-line options.
    dry_run = args.dry_run
    num_threads = args.num_threads
    incremental = not args.no_incremental
    abort_on_error = not args.skip_on_error
    num_attempts = args.num_attempts
    dst_dir = "."
    log_file = os.path.join(dst_dir, "parallel_execute.log")
    # Execute.
    res = hjoblib.parallel_execute(
        workload,
        #
        dry_run,
        num_threads,
        incremental,
        abort_on_error,
        num_attempts,
        log_file,
    )
    if res is None:
        print("res=%s" % res)
    else:
        print("res=\n%s" % "\n".join(map(str, res)))


if __name__ == "__main__":
    _main(_parse())
