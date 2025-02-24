#!/usr/bin/env python

"""
Zip all files in a directory retaining the dir structure.

# Compress all the files in the dir `FTX` in a dir `FTX.zipped`

```
> zip_files.py --src_dir FTX --dst_dir FTX.zipped --delete_dst_dir
```

Import as:

import dev_scripts.zip_files as dsczifil
"""

import argparse
import glob
import logging
import os

from tqdm.auto import tqdm

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--src_dir", action="store", required=True, help="Source dir"
    )
    parser.add_argument(
        "--dst_dir", action="store", required=True, help="Destination dir"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Skip the files that were already processed",
    )
    parser.add_argument(
        "--delete_dst_dir",
        action="store_true",
        help="Always delete dst dir if already exists",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # `src_dir` should exist.
    src_dir = args.src_dir
    hdbg.dassert_dir_exists(src_dir)
    # Get all the files.
    files = glob.glob(f"{src_dir}/**", recursive=True)
    files = sorted(files)
    print("Found %d files" % len(files))
    # `dst_dir` should not exit, unless we want to delete it.
    dst_dir = args.dst_dir
    if not args.incremental:
        if args.delete_dst_dir:
            hdbg.dassert_eq(
                args.incremental,
                False,
                msg="You can't use --incremental and --delete_dst_dir together",
            )
            _LOG.warning("Deleting '%s' as per user request", dst_dir)
            hio.create_dir(dst_dir, incremental=False)
        else:
            hdbg.dassert_path_not_exists(dst_dir)
    #
    for file_ in tqdm(files):
        _LOG.debug("Processing '%s'", file_)
        if file_ == ".":
            _LOG.debug("Skipping '%s' since it's not a file", file_)
        # file is relative to src_dir. # E.g., file=FTX_BCHUSDT_minute.csv
        if os.path.isdir(file_):
            _LOG.debug("Skipping '%s' since it's a dir", file_)
            continue
        if not os.path.isfile(file_):
            _LOG.debug("Skipping '%s' since it's not a file", file_)
            continue
        # Convert `{src_dir}/foo/bar.csv` to `{dst_dir}/foo/bar.csv`.
        path = os.path.relpath(file_, src_dir)
        dst_path = os.path.join(dst_dir, path) + ".zip"
        enclosing_dir = os.path.dirname(dst_path)
        _LOG.debug(hprint.to_str("file_ path dst_path enclosing_dir"))
        if args.incremental and os.path.exists(dst_path):
            _LOG.debug(
                "Skipping %s -> %s since already exists", src_dir, dst_path
            )
            continue
        if not os.path.exists(enclosing_dir):
            hio.create_dir(enclosing_dir, incremental=True)
        # zip enclosing_dir/file.zip file
        cmd = f"zip '{dst_path}' '{file_}'"
        if args.dry_run:
            print(f"Dry-run: file_='{file_}' -> {cmd}")
        else:
            hsystem.system(cmd, suppress_output="ON_DEBUG_LEVEL")


if __name__ == "__main__":
    _main(_parse())
