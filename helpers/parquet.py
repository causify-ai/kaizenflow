#!/usr/bin/env python

# TODO(gp): Remove this since it is obsolete.

"""
Add a description of what the script does and examples of command lines.

Check dev_scripts/linter.py to see an example of a script using this
template.
"""

import argparse
import datetime
import logging
import random

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds

import helpers.dbg as dbg
import helpers.io_ as hio
import helpers.parser as prsr
import helpers.printing as hprint

# import helpers.system_interaction as si

_LOG = logging.getLogger(__name__)

# #############################################################################


def _get_df(date) -> pd.DataFrame:
    """
    Create pandas random data, like:

                idx instr  val1  val2
    2000-01-01    0     A    99    30
    2000-01-02    0     A    54    46
    2000-01-03    0     A    85    86
    """
    instruments = "A B C D E".split()
    date = pd.Timestamp(date, tz="America/New_York")
    start_date = date.replace(hour=9, minute=30)
    end_date = date.replace(hour=16, minute=0)
    df_idx = pd.date_range(start_date, end_date, freq="5T")
    _LOG.debug("df_idx=[%s, %s]", min(df_idx), max(df_idx))
    _LOG.debug("len(df_idx)=%s", len(df_idx))
    random.seed(1000)
    # For each instruments generate random data.
    df = []
    for idx, inst in enumerate(instruments):
        df_tmp = pd.DataFrame({"idx": idx,
                               "instr": inst,
                               "val1": [random.randint(0, 100) for k in range(len(df_idx))],
                               "val2": [random.randint(0, 100) for k in range(len(df_idx))],
                               }, index=df_idx)
        _LOG.debug(hprint.df_to_short_str("df_tmp", df_tmp))
        df.append(df_tmp)
    # Create a single df for all the instruments.
    df = pd.concat(df)
    _LOG.debug(hprint.df_to_short_str("df", df))
    return df


def get_available_dates():
    """
    Return list of all available dates.
    """
    dates = pd.date_range(pd.Timestamp("2000-01-01"), pd.Timestamp("2000-01-15"), freq="1D")
    dates = sorted(dates)
    return dates


def _save_data_as_pq(df, dst_dir):
    # Append year and month.
    df["year"] = df.index.year
    df["month"] = df.index.month
    # Save.
    table = pa.Table.from_pandas(df)
    partition_cols = ["idx", "year", "month"]
    pq.write_to_dataset(table,
                        dst_dir,
                        partition_cols=partition_cols)


def _save_data_as_pq_without_extra_cols(df, dst_dir):
    # Scan and save.
    # Save.
    pass


def _date_exists(date: datetime.datetime, dst_dir: str) -> bool:
    """
    Check if the data corresponding to `date` under `dst_dir` already exists.
    """
    # /app/data/idx=0/year=2000/month=1/02e3265d515e4fb88ebe1a72a405fc05.parquet
    subdirs = glob.glob(f"{dst_dir}/idx=*")
    suffix = os.path.join("year=%s" % date.year, "month=%s" % date.month)
    _LOG.debug("suffix=%s", suffix)
    found = False
    for subdir in sorted(subdirs):
        file_name = os.path.join(subdir, suffix)
        exists = os.path.exists(file_name)
        _LOG.debug("file_name=%s -> exists=%s", file_name, exists)
        if exists:
            found = True
            break
    return found


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--start_date", action="store", help="Start date, e.g., 2010-01-01")
    parser.add_argument("--end_date", action="store", help="End date, e.g., 2010-01-01")
    parser.add_argument("--incremental", action="store_true", help="")
    parser.add_argument("--dst_dir", action="store", help="Destination dir")
    prsr.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    dbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Insert your code here.
    # - Use _LOG.info(), _LOG.debug() instead of printing.
    # - Use dbg.dassert_*() for assertion.
    # - Use si.system() and si.system_to_string() to issue commands.
    dst_dir = args.dst_dir
    #
    hio.create_dir(dst_dir, incremental=args.incremental)
    # Get all the dates with s3.list
    dates = get_available_dates()
    #dbg.dassert_strictly_increasing_index(dates)
    _LOG.info("dates=%s [%s, %s]", len(dates), min(dates), max(dates))
    # Scan the dates.
    for date in dates:
        if args.incremental and _date_exists(date, dst_dir):
            _LOG.info("Skipping processing of date '%s since incremental mode'", date)
            continue
        # Read data.
        df = _get_df(date)
        _LOG.debug("date=%s\ndf=\n%s", date, str(df.head(3)))
        _save_data_as_pq(df, dst_dir)


if __name__ == "__main__":
    _main(_parse())
