#!/usr/bin/env python
"""
Convert a directory storing Parquet files organized by dates into a Parquet
dataset organized by assets.

A parquet file organized by dates looks like:

```
src_dir/
    date1/
        data.parquet
    date2/
        data.parquet
```

A parquet file organized by assets looks like:

```
dst_dir/
    year1/
        month1/
            day1/
                asset1/
                    data.parquet
                asset2/
                    data.parquet
    year2/
        month2/
            day2/
                asset1/
                    data.parquet
                asset2/
                    data.parquet
```

# Example:
> im_v2/common/data/transform/convert_pq_by_date_to_by_asset.py \
    --src_dir im_v2/common/data/transform/test_data_by_date \
    --dst_dir im_v2/common/data/transform/test_data_by_asset \
    --num_threads 2

Import as:

import im_v2.common.data.transform.convert_pq_by_date_to_by_asset as imvcdtcpbdtba
"""

import argparse
import logging
import os
from typing import Any, Dict, List

import numpy as np

import helpers.datetime_ as hdateti
import helpers.dbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.io_ as hio
import helpers.joblib_helpers as hjoblib
import helpers.parser as hparser
import helpers.printing as hprint

_LOG = logging.getLogger(__name__)


def _source_pq_files(src_dir: str) -> List[str]:
    """
    Generator for all the Parquet files in a given dir.
    """
    hdbg.dassert_dir_exists(src_dir)
    # Find all the files with extension `.parquet` or `.pq`.
    src_pq_files = hio.find_files(src_dir, "*.parquet")
    if not src_pq_files:
        src_pq_files = hio.find_files(src_dir, "*.pq")
    _LOG.debug("Found %s pq files in '%s'", len(src_pq_files), src_dir)
    hdbg.dassert_lte(1, len(src_pq_files))
    return src_pq_files


def _save_chunk(config: Dict[str, str], **kwargs: Dict[str, Any]):
    """
    Smaller part of daily data that will be decoupled to asset format for
    certain period of time.

    Chunk is executed as small task.
    """
    # TODO(Nikola): Use incremental and repeat from kwargs.
    # TODO(Nikola): Check config.
    for daily_pq in config["chunk"]:
        df = hparque.from_parquet(daily_pq)
        _LOG.debug("before df=\n%s", hprint.dataframe_to_str(df.head(3)))
        # Transform.
        # TODO(gp): Use eval or a more general mechanism.
        transform_func = config["transform_func"]
        if not transform_func:
            pass
        elif transform_func == "reindex_on_unix_epoch":
            in_col_name = "start_time"
            df = hpandas.reindex_on_unix_epoch(df, in_col_name)
            _LOG.debug("after df=\n%s", hprint.dataframe_to_str(df.head(3)))
        else:
            hdbg.dfatal(f"Invalid transform_func='{transform_func}'")
        hparque.save_pq_by_asset(config["asset_col_name"], df, config["dst_dir"])


# TODO(gp): We might want to use a config to pass a set of params related to each
#  other (e.g., transform_func, asset_col_name, ...)
def _run(args: argparse.Namespace) -> None:
    # We assume that the destination dir doesn't exist, so we don't override data.
    dst_dir = args.dst_dir
    # TODO(Nikola): Conflict with parallel incremental. Use one for all?
    if not args.no_incremental:
        # In not incremental mode the dir should already be there.
        hdbg.dassert_not_exists(dst_dir)
    hio.create_dir(dst_dir, incremental=False)

    tasks = []
    # Convert the files one at the time.
    # TODO(Nikola): Pick chunk by chunk, not all files.
    source_pq_files = _source_pq_files(args.src_dir)
    # TODO(Nikola): Remove, quick testing. Currently splitting by week.
    chunks = np.array_split(source_pq_files, len(source_pq_files) // 7 or 1)
    for chunk in chunks:
        # TODO(Nikola): Make this config as subconfig for script args?
        config = {
            "src_dir": args.src_dir,
            "chunk": chunk,
            "dst_dir": args.dst_dir,
            "transform_func": args.transform_func,
            "asset_col_name": args.asset_col_name,
        }
        task: hjoblib.Task = (
            # args.
            (config,),
            # kwargs.
            {},
        )
        tasks.append(task)

    func_name = "_save_chunk"
    workload = (_save_chunk, func_name, tasks)
    hjoblib.validate_workload(workload)

    # Parse command-line options.
    dry_run = args.dry_run
    num_threads = args.num_threads
    incremental = not args.no_incremental
    abort_on_error = not args.skip_on_error
    num_attempts = args.num_attempts

    # Prepare the log file.
    timestamp = hdateti.get_timestamp("naive_ET")
    # TODO(Nikola): Change directory.
    log_dir = os.getcwd()
    log_file = os.path.join(log_dir, f"log.{timestamp}.txt")
    _LOG.info("log_file='%s'", log_file)
    hjoblib.parallel_execute(
        workload,
        dry_run,
        num_threads,
        incremental,
        abort_on_error,
        num_attempts,
        log_file,
    )


# TODO(Nikola): Add support for reading (not writing) to S3. #697


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--src_dir",
        action="store",
        type=str,
        required=True,
        help="Source directory where original PQ files are stored",
    )
    parser.add_argument(
        "--dst_dir",
        action="store",
        type=str,
        required=True,
        help="Destination directory where transformed PQ files will be stored",
    )
    parser.add_argument(
        "--transform_func",
        action="store",
        type=str,
        default="",
        help="Function that will be used for transforming the df",
    )
    parser.add_argument(
        "--asset_col_name",
        action="store",
        type=str,
        default="asset",
        help="Asset column may not be necessarily called asset",
    )
    hparser.add_parallel_processing_arg(parser)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _run(args)


if __name__ == "__main__":
    _main(_parse())
