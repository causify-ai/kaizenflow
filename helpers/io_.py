"""
Functions to handle filesystem operations.

Import as:

import helpers.io_ as hio
"""

# TODO(gp): -> hio

import datetime
import fnmatch
import gzip
import json
import logging
import os
import shutil
import time
import uuid
from typing import Any, List, Optional, cast

import helpers.dbg as hdbg
import helpers.printing as hprint

# TODO(gp): Enable this after the linter has been updated.
# import helpers.s3 as hs3
import helpers.system_interaction as hsysinte

_LOG = logging.getLogger(__name__)

# Set logging level of this file.
# _LOG.setLevel(logging.INFO)


# #############################################################################
# Glob.
# #############################################################################


def find_files(directory: str, pattern: str) -> List[str]:
    """
    Find all files under `directory` that match a certain `pattern`.

    :param pattern: pattern to match a filename against
    """
    file_names = []
    for root, _, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                file_name = os.path.join(root, basename)
                file_names.append(file_name)
    return file_names


# TODO(gp): Seems equivalent to `find_files`. Let's keep this.
def find_regex_files(src_dir: str, regex: str) -> List[str]:
    cmd = 'find %s -name "%s"' % (src_dir, regex)
    _, output = hsysinte.system_to_string(cmd)
    # TODO(gp): -> system_to_files
    file_names = [f for f in output.split("\n") if f != ""]
    _LOG.debug("Found %s files in %s", len(file_names), src_dir)
    _LOG.debug("\n".join(file_names))
    return file_names


# TODO(gp): Redundant with `find_files()`.
def find_all_files(dir_name: str) -> List[str]:
    """
    Find all files (not directory) under `dir_name`, skipping `.git`.
    """
    cmd = fr'''cd {dir_name} && find . -type f -name "*" -not -path "*/\.git/*"'''
    file_names = hsysinte.system_to_files(cmd)
    file_names = cast(List[str], file_names)
    _LOG.debug("Found %s files", len(file_names))
    return file_names


def is_paired_jupytext_python_file(py_filename: str) -> bool:
    """
    Return if a Python file has a paired Jupyter notebook.
    """
    hdbg.dassert(
        py_filename.endswith("py"), "Invalid python filename='%s'", py_filename
    )
    hdbg.dassert_file_exists(py_filename)
    # Check if a corresponding ipynb file exists.
    ipynb_filename = change_filename_extension(py_filename, "py", "ipynb")
    is_paired = os.path.exists(ipynb_filename)
    _LOG.debug(
        "Checking ipynb file='%s' for py file='%s': is_paired=%s",
        py_filename,
        ipynb_filename,
        is_paired,
    )
    return is_paired


def keep_python_files(
    file_names: List[str], exclude_paired_jupytext: bool
) -> List[str]:
    """
    Return a list with all Python file names (i.e., with the `py` extension).

    :param exclude_paired_jupytext: exclude Python file that are associated to
        notebooks (i.e., that have a corresponding `.ipynb` file)
    """
    hdbg.dassert_isinstance(file_names, list)
    # Check all the files.
    py_file_names = []
    for file_name in file_names:
        if file_name.endswith(".py"):
            if exclude_paired_jupytext:
                # Include only the non-paired Python files.
                is_paired = is_paired_jupytext_python_file(file_name)
                add = not is_paired
            else:
                # Include all the Python files.
                add = True
        else:
            add = False
        _LOG.debug("file_name='%s' -> add='%s'", file_name, add)
        if add:
            py_file_names.append(file_name)
    _LOG.debug("Found %s python files", len(py_file_names))
    return py_file_names


# #############################################################################
# Filesystem.
# #############################################################################


def create_soft_link(src: str, dst: str) -> None:
    """
    Create a soft-link to <src> called <dst> (where <src> and <dst> are files
    or directories as in a Linux ln command).

    This is equivalent to a command like "cp <src> <dst>" but creating a
    soft link.
    """
    _LOG.debug("# CreateSoftLink")
    # hs3.dassert_is_not_s3_path(src)
    # hs3.dassert_is_not_s3_path(dst)
    # Create the enclosing directory, if needed.
    enclosing_dir = os.path.dirname(dst)
    _LOG.debug("enclosing_dir=%s", enclosing_dir)
    create_dir(enclosing_dir, incremental=True)
    # Create the link. Note that the link source needs to be an absolute path.
    src = os.path.abspath(src)
    cmd = "ln -s %s %s" % (src, dst)
    hsysinte.system(cmd)


def delete_file(file_name: str) -> None:
    _LOG.debug("Deleting file '%s'", file_name)
    # hs3.dassert_is_not_s3_path(file_name)
    if not os.path.exists(file_name) or file_name == "/dev/null":
        # Nothing to delete.
        return
    try:
        os.unlink(file_name)
    except OSError as e:
        # It can happen that we try to delete the file, while somebody already
        # deleted it, so we neutralize the corresponding exception.
        if e.errno == 2:
            # OSError: [Errno 2] No such file or directory.
            pass
        else:
            raise e


def delete_dir(
    dir_: str,
    change_perms: bool = False,
    errnum_to_retry_on: int = 16,
    num_retries: int = 1,
    num_secs_retry: int = 1,
) -> None:
    """
    Delete a directory.

    :param change_perms: change permissions to -R rwx before deleting to deal with
      incorrect permissions left over
    :param errnum_to_retry_on: specify the error to retry on, e.g.,
        ```
        OSError: [Errno 16] Device or resource busy:
          'gridTmp/.nfs0000000002c8c10b00056e57'
        ```
    """
    _LOG.debug("Deleting dir '%s'", dir_)
    # hs3.dassert_is_not_s3_path(dir_)
    if not os.path.isdir(dir_):
        # No directory so nothing to do.
        return
    if change_perms and os.path.isdir(dir_):
        cmd = "chmod -R +rwx " + dir_
        hsysinte.system(cmd)
    i = 1
    while True:
        try:
            shutil.rmtree(dir_)
            # Command succeeded: exit.
            break
        except OSError as e:
            if errnum_to_retry_on is not None and e.errno == errnum_to_retry_on:
                # TODO(saggese): Make it less verbose once we know it's working
                # properly.
                _LOG.warning(
                    "Couldn't delete %s: attempt=%s / %s", dir_, i, num_retries
                )
                i += 1
                if i > num_retries:
                    hdbg.dfatal(
                        "Couldn't delete %s after %s attempts (%s)"
                        % (dir_, num_retries, str(e))
                    )
                else:
                    time.sleep(num_secs_retry)
            else:
                # Unforeseen error: just propagate it.
                raise e


def create_dir(
    dir_name: str,
    incremental: bool,
    abort_if_exists: bool = False,
    ask_to_delete: bool = False,
) -> None:
    """
    Create a directory `dir_name` if it doesn't exist.

    :param incremental: if False then the directory is deleted and
        re-created, otherwise it skips
    :param abort_if_exists:
    :param ask_to_delete: if it is not incremental and the dir exists,
        asks before deleting
    """
    _LOG.debug(
        hprint.to_str("dir_name incremental abort_if_exists ask_to_delete")
    )
    hdbg.dassert_is_not(dir_name, None)
    dir_name = os.path.normpath(dir_name)
    if os.path.normpath(dir_name) == ".":
        _LOG.debug("Can't create dir '%s'", dir_name)
    exists = os.path.exists(dir_name)
    is_dir = os.path.isdir(dir_name)
    _LOG.debug(hprint.to_str("dir_name exists is_dir"))
    if abort_if_exists:
        hdbg.dassert_not_exists(dir_name)
    #                   dir exists / dir does not exist
    # incremental       no-op        mkdir
    # not incremental   rm+mkdir     mkdir
    if exists:
        if incremental and is_dir:
            # The dir exists and we want to keep it it exists (i.e.,
            # incremental), so we are done.
            # os.chmod(dir_name, 0755)
            _LOG.debug(
                "The dir '%s' exists and incremental=True: exiting", dir_name
            )
            return
        if ask_to_delete:
            hsysinte.query_yes_no(
                "Do you really want to delete dir '%s'?" % dir_name,
                abort_on_no=True,
            )
        # The dir exists and we want to create it from scratch (i.e., not
        # incremental), so we need to delete the dir.
        _LOG.debug("Deleting dir '%s'", dir_name)
        if os.path.islink(dir_name):
            delete_file(dir_name)
        else:
            shutil.rmtree(dir_name)
    _LOG.debug("Creating directory '%s'", dir_name)
    # NOTE: `os.makedirs` raises `OSError` if the target directory already exists.
    # A race condition can happen when another process creates our target
    # directory, while we have just found that it doesn't exist, so we need to
    # handle this situation gracefully.
    try:
        os.makedirs(dir_name)
    except OSError as e:
        _LOG.error(str(e))
        # It can happen that we try to create the directory while somebody else
        # created it, so we neutralize the corresponding exception.
        if e.errno == 17:
            # OSError: [Errno 17] File exists.
            pass
        else:
            raise e


def _dassert_is_valid_file_name(file_name: str) -> None:
    # hdbg.dassert_in(type(file_name), (str, unicode))
    hdbg.dassert_in(type(file_name), [str])
    hdbg.dassert_is_not(file_name, None)
    hdbg.dassert_ne(file_name, "")


# TODO(gp): Don't use default incremental.
def create_enclosing_dir(file_name: str, incremental: bool = False) -> str:
    """
    Create the dir enclosing file_name, if needed.

    :param incremental: same meaning as in `create_dir()`
    """
    _LOG.debug(hprint.to_str("file_name incremental"))
    _dassert_is_valid_file_name(file_name)
    # hs3.dassert_is_not_s3_path(file_name)
    #
    dir_name = os.path.dirname(file_name)
    _LOG.debug(hprint.to_str("dir_name"))
    if dir_name != "":
        _LOG.debug(
            "Creating dir_name='%s' for file_name='%s'", dir_name, file_name
        )
        create_dir(dir_name, incremental=incremental)
    hdbg.dassert_dir_exists(dir_name, "file_name='%s'", file_name)
    return dir_name


# #############################################################################
# File.
# #############################################################################


# TODO(saggese): We should have `lines` first since it is an input param.
def to_file(
    file_name: str,
    lines: str,
    use_gzip: bool = False,
    mode: Optional[str] = None,
    force_flush: bool = False,
) -> None:
    """
    Write the content of lines into file_name, creating the enclosing directory
    if needed.

    :param file_name: name of written file
    :param lines: content of the file
    :param use_gzip: whether the file should be compressed as gzip
    :param mode: file writing mode
    :param force_flush: whether to forcibly clear the file buffer
    """
    _LOG.debug(hprint.to_str("file_name use_gzip mode force_flush"))
    _dassert_is_valid_file_name(file_name)
    # Choose default writing mode based on compression.
    if mode is None:
        if use_gzip:
            mode = "wt"
        else:
            mode = "w"
    # Create the enclosing dir, if needed.
    create_enclosing_dir(file_name, incremental=True)
    if use_gzip:
        # Check if user provided correct file name.
        if not file_name.endswith(("gz", "gzip")):
            _LOG.warning("The provided file extension is not for a gzip file.")
        # Open gzipped file.
        f = gzip.open(file_name, mode)
    else:
        # Open regular text file.
        # buffering = 0 if mode == "a" else -1
        buffering = 0 if force_flush else -1
        f = open(  # pylint: disable=consider-using-with
            file_name, mode, buffering=buffering
        )
    # Write file contents.
    f.writelines(lines)
    f.close()
    # Clear internal buffer of the file.
    if force_flush:
        f.flush()
        os.fsync(f.fileno())


def _raise_file_decode_error(error: Exception, file_name: str) -> None:
    """
    Raise UnicodeDecodeError with detailed error message.

    :param error: raised UnicodeDecodeError
    :param file_name: name of read file that raised the exception
    """
    msg = []
    msg.append("error=%s" % error)
    msg.append("file_name='%s'" % file_name)
    msg_as_str = "\n".join(msg)
    _LOG.error(msg_as_str)
    raise RuntimeError(msg_as_str)


def from_file(
    file_name: str,
    encoding: Optional[Any] = None,
) -> str:
    """
    Read contents of a file as string.

    :param file_name: path to .txt,.gz or .pq file
    :param encoding: encoding to use when reading the string
    :return: contents of file as string
    """
    hdbg.dassert_ne(file_name, "")
    _dassert_is_valid_file_name(file_name)
    hdbg.dassert_exists(file_name)
    data: str = ""
    if file_name.endswith((".gz", ".gzip")):
        # Open gzipped file.
        f = gzip.open(file_name, "rt", encoding=encoding)
    elif file_name.endswith((".pq", ".parquet")):
        # TODO(Nikola): Temporary workaround. Definitely revisit.
        import helpers.hparquet as hparque
        import helpers.unit_test as hunitest

        # Open pq file.
        df = hparque.from_parquet(file_name)
        data = hunitest.convert_df_to_json_string(df, n_head=3, n_tail=3)
        # Already a proper string.
        return data
    else:
        # Open regular text file.
        f = open(  # pylint: disable=consider-using-with
            file_name, "r", encoding=encoding
        )
    try:
        # Read data.
        data = f.read()
    except UnicodeDecodeError as e:
        # Raise unicode decode error message.
        _raise_file_decode_error(e, file_name)
    finally:
        f.close()
    hdbg.dassert_isinstance(data, str)
    return data


# TODO(gp): Use hintro.format_size
def get_size_as_str(file_name: str) -> str:
    if os.path.exists(file_name):
        size_in_bytes = os.path.getsize(file_name)
        if size_in_bytes < (1024 ** 2):
            size_in_kb = size_in_bytes / 1024.0
            res = "%.1f KB" % size_in_kb
        elif size_in_bytes < (1024 ** 3):
            size_in_mb = size_in_bytes / (1024.0 ** 2)
            res = "%.1f MB" % size_in_mb
        else:
            size_in_gb = size_in_bytes / (1024.0 ** 3)
            res = "%.1f GB" % size_in_gb
    else:
        res = "nan"
    return res


def is_valid_filename_extension(ext: str) -> bool:
    """
    By convention extensions are the initial `.`.

    E.g., "tgz" is valid, but not ".tgz".
    """
    valid = not ext.startswith(".")
    return valid


def change_filename_extension(filename: str, old_ext: str, new_ext: str) -> str:
    """
    Change extension of a filename (e.g. "data.csv" to "data.json").

    :param filename: the old filename (including extension)
    :param old_ext: the extension of the old filename
    :param new_ext: the extension to replace the old extension
    :return: a filename with the new extension
    """
    hdbg.dassert(
        is_valid_filename_extension(old_ext), "Invalid extension '%s'", old_ext
    )
    hdbg.dassert(
        is_valid_filename_extension(new_ext), "Invalid extension '%s'", new_ext
    )
    hdbg.dassert(
        filename.endswith(old_ext),
        "Extension '%s' doesn't match file '%s'",
        old_ext,
        filename,
    )
    # Remove the old extension.
    len_ext = len(old_ext)
    new_filename = filename[:-len_ext]
    hdbg.dassert(new_filename.endswith("."), "new_filename='%s'", new_filename)
    # Add the new extension.
    new_filename += new_ext
    return new_filename


# #############################################################################
# JSON
# #############################################################################


def serialize_custom_types_for_json_encoder(obj: Any) -> Any:
    """
    Serialize DataFrame and other objects for JSON.

    E.g. dataframe {"A": [0, 1], "B": [0, 1]} will go to a list of dictionaries:
    [{"A": 0, "B": 0}, {"A": 1, "B": 1}] - each dictionary is for one row.
    """
    import numpy as np
    import pandas as pd

    result = None
    if isinstance(obj, pd.DataFrame):
        result = obj.to_dict("records")
    elif isinstance(obj, pd.Series):
        result = obj.to_dict()
    elif isinstance(obj, np.int64):
        result = int(obj)
    elif isinstance(obj, np.float64):
        result = float(obj)
    elif isinstance(obj, uuid.UUID):
        result = str(obj)
    elif isinstance(obj, datetime.date):
        result = obj.isoformat()
    elif isinstance(obj, type(pd.NaT)):
        result = None
    elif isinstance(obj, type(pd.NA)):
        result = None
    else:
        raise TypeError("Can not serialize %s of type %s" % (obj, type(obj)))
    return result


def to_json(file_name: str, obj: dict) -> None:
    """
    Write an object into a JSON file.

    :param obj: data for writing
    :param file_name: name of file
    :return:
    """
    if not file_name.endswith(".json"):
        _LOG.warning("The file '%s' doesn't end in .json", file_name)
    dir_name = os.path.dirname(file_name)
    if dir_name != "" and not os.path.isdir(dir_name):
        create_dir(dir_name, incremental=True)
    with open(file_name, "w") as outfile:
        json.dump(
            obj,
            outfile,
            indent=4,
            default=serialize_custom_types_for_json_encoder,
        )


def from_json(file_name: str) -> dict:
    """
    Read object from JSON file.

    :param file_name: name of file
    :return: dict with data
    """
    if not file_name.endswith(".json"):
        _LOG.warning("The file '%s' doesn't end in .json", file_name)
    hdbg.dassert_file_exists(file_name)
    with open(file_name, "r") as f:
        data: dict = json.loads(f.read())
    return data


# TODO(gp): -> pandas_helpers.py
def load_df_from_json(path_to_json: str) -> "pd.DataFrame":
    """
    Load a dataframe from a json file.

    :param path_to_json: path to the json file
    :return:
    """
    import pandas as pd

    # Load the dict with the data.
    data = from_json(path_to_json)
    # Preprocess the dict to handle arrays with different length.
    data = {k: pd.Series(v) for k, v in data.items()}
    # Package into a dataframe.
    df = pd.DataFrame(data)
    return df
