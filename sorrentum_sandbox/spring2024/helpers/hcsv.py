"""
Import as:

import helpers.hcsv as hcsv
"""

import ast
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hs3 as hs3

_LOG = logging.getLogger(__name__)


def _append_csv(
    df: pd.DataFrame, path: str, *, index: bool = False, **kwargs: Any
) -> None:
    """
    Append a df to the CSV file `path` without header.
    """
    with open(path, "a") as f:
        df.to_csv(f, header=False, index=index, **kwargs)


def _read_csv_range(
    csv_path: str, from_: int, to: int, **kwargs: Any
) -> pd.DataFrame:
    """
    Read a specified row range of a CSV file and convert to a DataFrame.

    This function:
    - assumes the CSV file to have header, considered to be row 0.
    - reads [from_, to), e.g., (to - from_) lines following list slicing semantics.

    :param csv_path: location of CSV file
    :param from_: first line to read (header is row 0 and is always read)
    :param to: last line to read, not inclusive
    :return: DataFrame with columns from CSV line 0 (header)
    """
    hdbg.dassert_lt(0, from_, msg="Row 0 assumed to be header row")
    hdbg.dassert_lt(from_, to, msg="Empty range requested!")
    skiprows = range(1, from_)
    nrows = to - from_
    df = pd.read_csv(csv_path, skiprows=skiprows, nrows=nrows, **kwargs)
    if df.shape[0] < to:
        _LOG.warning("Number of df rows = %i vs requested = %i", df.shape[0], to)
    return df


# TODO(gp): There is no use of this function.
def build_chunk(
    csv_path: str,
    col_name: str,
    start: int,
    *,
    nrows_at_a_time: int = 1000,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Build a DataFrame from a CSV subset as follows:

      - Names the columns using the header line (row 0)
      - Reads the value in (row, col) coordinates (`start`, `col_name`) (if it
          exists) as `value`
      - Adds row `start` and all subsequent contiguous rows with `value` in
          column `col_name`

    For memory efficiency, the CSV is processed in chunks of size `nrows_at_a_time`.

    :param csv_path: location of CSV file
    :param col_name: name of column whose values define chunks
    :param start: first row to process
    :param nrows_at_a_time: size of chunks to process
    :return: DataFrame with columns from CSV line 0
    """
    hdbg.dassert_lt(0, start)
    stop = False
    dfs: List[pd.DataFrame] = []
    init_df = _read_csv_range(csv_path, start, start + 1, **kwargs)
    if init_df.shape[0] < 1:
        return init_df
    val = init_df[col_name].iloc[0]
    _LOG.debug("Building chunk for %s", val)
    counter = 0
    while not stop:
        from_ = start + counter * nrows_at_a_time
        df = _read_csv_range(csv_path, from_, from_ + nrows_at_a_time)
        # Break if there are no matches.
        if df.shape[0] == 0:
            break
        if not (df[col_name] == val).any():
            break
        # Stop if we have run out of rows to read.
        if df.shape[0] < nrows_at_a_time:
            stop = True
        idx_max = (df[col_name] == val)[::-1].idxmax()
        # Stop if we have reached a new value.
        if idx_max < (df.shape[0] - 1):
            stop = True
        dfs.append(df.iloc[0 : idx_max + 1])
        counter += 1
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, axis=0).reset_index(drop=True)


# TODO(gp): There is no use of this function.
def find_first_matching_row(
    csv_path: str,
    col_name: str,
    val: str,
    *,
    start: int = 1,
    nrows_at_a_time: int = 1000000,
    **kwargs: Any,
) -> Optional[int]:
    """
    Find first row in CSV where value in column `col_name` equals `val`.

    :param csv_path: location of CSV file
    :param col_name: name of column whose values define chunks
    :param val: value to match on
    :param start: first row (inclusive) to start search on
    :param nrows_at_a_time: size of chunks to process
    :return: line in CSV of first matching row at or past start
    """
    curr = start
    while True:
        _LOG.debug("Start of current chunk = line %i", curr)
        df = _read_csv_range(csv_path, curr, curr + nrows_at_a_time, **kwargs)
        if df.shape[0] < 1:
            _LOG.info("Value %s not found", val)
            break
        matches = df[col_name] == val
        if matches.any():
            idx_max = matches.idxmax()
            return int(curr + idx_max)
        curr += nrows_at_a_time
    return None


# #############################################################################
# CSV to PQ conversion
# #############################################################################


def _csv_mapreduce(
    csv_path: str,
    out_dir: str,
    key_func: Callable,
    chunk_preprocessor: Optional[Callable],
    *,
    chunk_size: int = 1000000,
) -> None:
    """
    Map-reduce-type processing of CSV.

    The phases are:
      - Read the CSV in chunks as DataFrame
      - Key each row of the DataFrame using a `groupby`
      - "Reduce" keyed groups by writing and appending to a CSV

    :param csv_path: input CSV path
    :param out_dir: output dir for CSV with filenames corresponding to keys
    :param key_func: function to apply to each chunk DataFrame to key rows
        Should return an iterable with elements like (key, df)
    :param chunk_preprocessor: function to apply to each chunk DataFrame before
        applying key_func
    :param chunk_size: chunk_size of input to process
    """
    # Read CSV data in chunks.
    chunks = pd.read_csv(csv_path, chunksize=chunk_size)
    # Preprocess chunk, if needed.
    if chunk_preprocessor is not None:
        chunks = map(chunk_preprocessor, chunks)
    # Apply key_func to each chunk.
    keyed_group_blocks = map(key_func, chunks)
    # Append results.
    for block in keyed_group_blocks:
        for idx, df in block:
            file_name = os.path.join(out_dir, idx + ".csv")
            _append_csv(df, file_name)


def convert_csv_to_pq(
    csv_path: str,
    pq_path: str,
    *,
    normalizer: Optional[Callable] = None,
    header: Optional[int] = 0,
    compression: Optional[str] = "gzip",
) -> None:
    """
    Convert CSV file to Parquet file.

    Output of `csv_map_reduce()` is typically header-less to support append mode,
    and so `normalizer` may be used to add appropriate headers. Note that Parquet
    requires string column names, whereas Pandas by default uses integer column
    names.

    :param csv_path: full path of CSV
    :param pq_path: full path of parquet
    :param header: header specification of CSV
    :param normalizer: function to apply to df before writing to PQ
    """
    df = pd.read_csv(csv_path, header=header)
    # TODO(Paul): Ensure that one of header, normalizer is not None.
    if normalizer is not None:
        df = normalizer(df)
    df.to_parquet(pq_path, compression=compression)


# TODO(gp): Promote to hio.
def _maybe_remove_extension(filename: str, extension: str) -> Optional[str]:
    """
    Attempt to remove `extension` from `filename`.

    :param filename: str filename
    :param extension: file extension starting with a dot. E.g., ".csv"
    :return: filename without `extension`, if applicable, else returns `None`.
    """
    hdbg.dassert_isinstance(filename, str)
    hdbg.dassert(filename)
    hdbg.dassert_file_exists(filename)
    #
    hdbg.dassert_isinstance(extension, str)
    hdbg.dassert(
        extension.startswith("."),
        "filename extension=`%s` expected to start with `.`",
        extension,
    )
    #
    ret: Optional[str] = None
    if filename.endswith(extension):
        ret = filename[: -len(extension)]
    return ret


def convert_csv_dir_to_pq_dir(
    csv_dir: str,
    pq_dir: str,
    *,
    normalizer: Optional[Callable] = None,
    header: Optional[int] = None,
) -> None:
    """
    Apply `convert_csv_to_pq()` to all files in `csv_dir`.

    :param csv_dir: directory storing CSV files on S3 or local
    :param pq_dir: target directory to save PQ files (only local
        filesystem)
    :param header: header specification of CSV
    :param normalizer: function to apply to df before writing to PQ
    """
    # Get the filenames in `csv_dir`.
    if hs3.is_s3_path(csv_dir):
        # TODO(gp): Pass aws_profile.
        s3fs = hs3.get_s3fs("am")
        filenames = s3fs.ls(csv_dir)
    else:
        # Local filesystem.
        hdbg.dassert_dir_exists(csv_dir)
        # TODO(Paul): check .endswith(".csv") or do glob(csv_dir + "/*.csv")
        filenames = os.listdir(csv_dir)
    hdbg.dassert(filenames, "No files in the directory '%s'", csv_dir)
    # Process all the filenames.
    # TODO(gp): Add tqdm.
    # TODO(gp): Consider parallelizing.
    for filename in filenames:
        # Remove .csv/.csv.gz.
        csv_stem = _maybe_remove_extension(filename, ".csv")
        if csv_stem is None:
            csv_stem = _maybe_remove_extension(filename, ".csv.gz")
        if csv_stem is None:
            _LOG.warning(
                "Skipping filename=%s since it has invalid extension", csv_stem
            )
            continue
        # Convert file to PQ.
        pq_filename = csv_stem + ".pq"
        convert_csv_to_pq(
            os.path.join(csv_dir, filename),
            os.path.join(pq_dir, pq_filename),
            normalizer=normalizer,
            header=header,
        )


# #############################################################################
# CSV-JSON dict conversion
# #############################################################################


# TODO(gp): convert_csv_to_json_dict?
# TODO(gp): path_to_csv -> file_name
def convert_csv_to_dict(path_to_csv: str, remove_nans: bool) -> Dict[Any, Any]:
    """
    Convert a CSV file storing a dataframe into a JSON-compatible dict.

    :param path_to_csv: path to the CSV file
    :param remove_nans: whether to remove NaNs from the dictionary
    :return: a JSON-compatible dict with the dataframe data
    """
    hdbg.dassert_file_exists(path_to_csv)
    # Load the dataframe from a CSV file.
    df = pd.read_csv(path_to_csv)
    # Transform the dataframe into a dict.
    dict_df = df.to_dict(orient="list")
    if remove_nans:
        # Remove NaNs from the dict.
        for key in dict_df:
            dict_df[key] = [x for x in dict_df[key] if not pd.isnull(x)]
    return dict_df  # type: ignore


# TODO(gp): path_to_csv -> file_name
def save_csv_as_json(
    path_to_csv: str, remove_nans: bool, path_to_json: Optional[str] = None
) -> None:
    """
    Convert the df from a CSV into a dict and save it into a JSON file.

    If the `path_to_json` is not provided, the JSON is saved in the folder where
    the CSV file is located.

    :param path_to_csv: path to the CSV file
    :param remove_nans: whether to remove NaNs from the dictionary
    :param path_to_json: path to save the JSON file
    """
    # Convert the df from the CSV into a JSON-compatible dict.
    dict_df = convert_csv_to_dict(path_to_csv, remove_nans)
    # Determine the JSON destination path.
    if path_to_json is None:
        path_to_json = hio.change_filename_extension(path_to_csv, ".csv", ".json")
    # Save the dict into a JSON file.
    hio.to_json(path_to_json, dict_df)


# #############################################################################
# CSV files with types
# #############################################################################


def to_typed_csv(df: pd.DataFrame, file_name: str) -> str:
    """
    Convert df into CSV and creates a file with the dtypes of columns.

    This function creates a file containing the types with the same name
    and suffix e.g., `foobar.csv.types`.
    """
    # Save the types.
    dtypes_filename = file_name + ".types"
    hio.create_enclosing_dir(dtypes_filename, incremental=True)
    dtypes_dict = str(df.dtypes.apply(lambda x: x.name).to_dict())
    # Save the data.
    df.to_csv(file_name, index=False)
    with open(dtypes_filename, "w") as dtypes_file:
        dtypes_file.write(dtypes_dict)
    return dtypes_filename


def from_typed_csv(file_name: str) -> pd.DataFrame:
    """
    Load CSV file as df applying the original types of columns.

    This function uses a file with name `file_name.types` to load
    information about the column types.
    """
    # Load the types.
    dtypes_filename = file_name + ".types"
    hdbg.dassert_path_exists(dtypes_filename)
    with open(dtypes_filename) as dtypes_file:
        dtypes_dict = ast.literal_eval(list(dtypes_file)[0])
    # Load the data, applying the types.
    df = pd.read_csv(file_name, dtype=dtypes_dict)
    return df
