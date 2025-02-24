"""
Functions to handle filesystem operations.

Import as:

import helpers.hio as hio
"""

import datetime
import gzip
import json
import logging
import os
import re
import shutil
import time
import uuid
from typing import Any, Dict, List, Optional, Union

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hsystem as hsystem

# This module can depend only on:
# - Python standard modules
# - a few helpers as described in `helpers/dependencies.txt`


_LOG = logging.getLogger(__name__)

# Set logging level of this file.
_LOG.setLevel(logging.INFO)

# #############################################################################
# Glob.
# #############################################################################


def purify_file_name(file_name: str) -> str:
    """
    Remove non-Linux friendly characters from the basename.
    """
    basename = os.path.basename(file_name)
    for char in (" ", "_", "'", '"', "`", "/"):
        basename = basename.replace(char, "_")
    #
    dir_name = os.path.dirname(file_name)
    file_name_out = os.path.join(dir_name, basename)
    file_name_out: str = os.path.normpath(file_name_out)
    return file_name_out


def listdir(
    dir_name: str,
    pattern: str,
    only_files: bool,
    use_relative_paths: bool,
    *,
    exclude_git_dirs: bool = True,
    maxdepth: Optional[int] = None,
) -> List[str]:
    """
    Find all files and subdirectories under `directory` that match `pattern`.

    :param dir_name: path to the directory where to look for files
    :param pattern: pattern to match a filename against (e.g., `*.py`)
    :param only_files: look for only files instead of both files and directories
    :param use_relative_paths: remove `dir_name` from path
    :param exclude_git_dirs: skip `.git` dirs
    :param maxdepth: limit the depth of directory traversal
    """
    hdbg.dassert_dir_exists(dir_name)
    cmd = [f"find {dir_name}", f'-name "{pattern}"']
    if maxdepth is not None:
        cmd.append(f'-maxdepth "{maxdepth}"')
    if only_files:
        cmd.append("-type f")
    if exclude_git_dirs:
        cmd.append(r'-not -path "*/\.git/*"')
    cmd = " ".join(cmd)
    _, output = hsystem.system_to_string(cmd)
    # TODO(gp): -> system_to_files
    paths = [path for path in output.split("\n") if path != ""]
    _LOG.debug("Found %s paths in %s", len(paths), dir_name)
    _LOG.debug("\n".join(paths))
    if use_relative_paths:
        paths = [os.path.relpath(path, start=dir_name) for path in paths]
    return paths


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
    cmd = f"ln -s {src} {dst}"
    hsystem.system(cmd)


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
        hsystem.system(cmd)
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
                        f"Couldn't delete {dir_} after {num_retries} attempts ({str(e)})"
                    )
                else:
                    time.sleep(num_secs_retry)
            else:
                # Unforeseen error: just propagate it.
                raise e


def create_dir(
    dir_name: str,
    incremental: bool,
    *,
    abort_if_exists: bool = False,
    ask_to_delete: bool = False,
    backup_dir_if_exists: bool = False,
) -> None:
    """
    Create a directory.

    :param incremental: if False then the directory is deleted and re-
        created, otherwise the same directory is reused as it is
    :param abort_if_exists: abort if the target directory already exists
    :param ask_to_delete: if it is not incremental and the dir exists,
        asks before deleting. This option is used when we want to start
        with a clean dir (i.e., incremental=False) but, at the same
        time, we want to make sure that the user doesn't want to delete
        the content of the dir. Another approach is to automatically
        rename the old dir with backup_dir_if_exists.
    :param backup_dir_if_exists: if the target dir already exists, then
        rename it using a timestamp (e.g., dir_20231003_080000) and
        create a new target dir
    """
    if backup_dir_if_exists:
        if not os.path.exists(dir_name):
            # Create new dir.
            _LOG.debug("Creating dir '%s'", dir_name)
            _create_dir(dir_name, incremental=True)
        else:
            _LOG.debug("Dir '%s' already exists", dir_name)
            # Get dir timestamp.
            dir_timestamp = os.path.getmtime(dir_name)
            dir_datetime = datetime.datetime.fromtimestamp(dir_timestamp)
            # Build new dir name with timestamp.
            dir_name_new = dir_name + "." + dir_datetime.strftime("%Y%m%d_%H%M%S")
            # Rename dir.
            if not os.path.exists(dir_name_new):
                _LOG.warning("Renaming dir '%s' -> '%s'", dir_name, dir_name_new)
                os.rename(dir_name, dir_name_new)
            else:
                _LOG.warning("Dir '%s' already exists", dir_name_new)
            # Create new dir.
            _LOG.debug("Creating dir '%s'", dir_name)
            _create_dir(dir_name, incremental=True)
    else:
        _create_dir(
            dir_name,
            incremental,
            abort_if_exists=abort_if_exists,
            ask_to_delete=ask_to_delete,
        )


def _create_dir(
    dir_name: str,
    incremental: bool,
    abort_if_exists: bool = False,
    ask_to_delete: bool = False,
) -> None:
    """
    Create a directory `dir_name` if it doesn't exist.

    Same interface as `create_dir()` but without handling
    `backup_dir_if_exists`.
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
        hdbg.dassert_path_not_exists(dir_name)
    #                   dir exists / dir does not exist
    # incremental       no-op        mkdir
    # not incremental   rm+mkdir     mkdir
    if exists:
        if incremental and is_dir:
            # The dir exists and we want to keep it (i.e., incremental), so we
            # are done.
            # os.chmod(dir_name, 0755)
            _LOG.debug(
                "The dir '%s' exists and incremental=True: exiting", dir_name
            )
            return
        if ask_to_delete:
            hsystem.query_yes_no(
                f"Do you really want to delete dir '{dir_name}'?",
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


def dassert_is_valid_file_name(file_name: str) -> None:
    hdbg.dassert_isinstance(file_name, str)
    hdbg.dassert_ne(file_name, "")


# TODO(gp): Don't use default incremental.
def create_enclosing_dir(file_name: str, incremental: bool = False) -> str:
    """
    Create the dir enclosing file_name, if needed.

    :param incremental: same meaning as in `create_dir()`
    """
    _LOG.debug(hprint.to_str("file_name incremental"))
    dassert_is_valid_file_name(file_name)
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
# TODO(Nikola): Remove `use_gzip` and use `file_name` extension instead.
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
    dassert_is_valid_file_name(file_name)
    # Choose default writing mode based on compression.
    if mode is None:
        if use_gzip:
            # Override default binary mode for `gzip`.
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
    msg.append(f"error={error}")
    msg.append(f"file_name='{file_name}'")
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
    dassert_is_valid_file_name(file_name)
    hdbg.dassert_path_exists(file_name)
    data: str = ""
    if file_name.endswith((".gz", ".gzip")):
        # Open gzipped file.
        f = gzip.open(file_name, "rt", encoding=encoding)
    # TODO(Nikola): CmTask1305: This function should only read the data without
    #  any transformation. Furthermore we can't use hpandas and hparquet in
    #  this file since it creates circular imports.
    # elif file_name.endswith((".pq", ".parquet")):
    #   df = hparque.from_parquet(file_name)
    #   data = hpandas.convert_df_to_json_string(df, n_head=3, n_tail=3)
    # return data
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
        if size_in_bytes < (1024**2):
            size_in_kb = size_in_bytes / 1024.0
            res = "%.1f KB" % size_in_kb
        elif size_in_bytes < (1024**3):
            size_in_mb = size_in_bytes / (1024.0**2)
            res = "%.1f MB" % size_in_mb
        else:
            size_in_gb = size_in_bytes / (1024.0**3)
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


# TODO(gp): @all Use msg in all uses of this script `jackpyc "create_executable"`
def create_executable_script(
    file_name: str, content: str, *, msg: str = ""
) -> None:
    # Write the file.
    hdbg.dassert_isinstance(content, str)
    to_file(file_name, content)
    # Make it executable.
    cmd = "chmod +x " + file_name
    hsystem.system(cmd)
    if msg:
        print(f"# {msg}:\n> {file_name}")


def add_suffix_to_filename(
    file_name: str,
    suffix: Union[int, str],
    *,
    before_extension: bool = True,
    with_underscore: bool = True,
) -> str:
    """
    Add a suffix to a file name, with or without changing the extension.

    E.g., {base_name}.{ext} -> {file_name}.{suffix}.{ext}

    :param file_name: file name to modify
    :param suffix: index to add to the file name
    :param before_extension: whether to insert the index before the file
        extension
    :param with_underscore: whether to separate the index with an
        underscore
    :return: modified file name with an index
    """
    suffix = str(suffix)
    if with_underscore:
        suffix = "_" + suffix
    _LOG.debug(hprint.to_str("suffix"))
    #
    if before_extension:
        # Add the suffix to the file name before the extension.
        data = file_name.rsplit(".", 1)
        if len(data) == 1:
            # E.g., `system_log_dir` -> `system_log_dir_1`
            ret = file_name + suffix
        else:
            # E.g., `dir/file.txt` -> `dir/file_1.txt`.
            hdbg.dassert_eq(len(data), 2, "Invalid file_name='%s'", file_name)
            file_name_no_ext, ext = data
            ret = file_name_no_ext + suffix + "." + ext
    else:
        # Add the suffix after the name of the file.
        # E.g., `dir/file.txt` -> `dir/file.txt_1`.
        ret = file_name + suffix
    _LOG.debug(hprint.to_str("ret"))
    return ret


def rename_file_if_exists(
    file_path: str,
    suffix: str,
    *,
    before_extension: bool = True,
) -> None:
    """
    Rename a file if it exists using provided suffix.

    Used to avoid overwriting if writing multiple files with the same name.

    :param file_path: a file path to modify
    :param suffix: index to add to the file name
    :param before_extension: whether to insert the suffix before the file extension
        - if True, {file_path}.{ext} -> {file_path}.{suffix}.{ext}
        - if False, {file_path}.{ext} -> {file_path}.{ext}.{suffix}
    """
    if os.path.exists(file_path):
        # Add a suffix to a file name.
        if before_extension:
            # Add a suffix before an extension, e.g., `file.suffix.csv`.
            dir_path, file_name = os.path.split(file_path)
            file_name, ext = os.path.splitext(file_name)
            hdbg.dassert(ext.startswith("."))
            new_file_path = f"{file_name}.{suffix}{ext}"
            new_file_path = os.path.join(dir_path, new_file_path)
        else:
            # Add a suffix after an extension, e.g., `file.csv.suffix`.
            new_file_path = f"{file_path}.{suffix}"
        hdbg.dassert_path_not_exists(new_file_path)
        _LOG.debug("renaming %s to %s", file_path, new_file_path)
        os.rename(file_path, new_file_path)


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
        raise TypeError(f"Can not serialize {obj} of type {type(obj)}")
    return result


def to_json(file_name: str, obj: dict, *, use_types: bool = False) -> None:
    """
    Write an object into a JSON file.

    :param obj: data for writing
    :param file_name: name of file
    :param use_types: whether to use jsonpickle to save the file
    """
    if not file_name.endswith(".json"):
        _LOG.warning("The file '%s' doesn't end in .json", file_name)
    # Create dir.
    dir_name = os.path.dirname(file_name)
    if dir_name != "" and not os.path.isdir(dir_name):
        create_dir(dir_name, incremental=True)
    # Write data as JSON.
    with open(file_name, "w") as outfile:
        if use_types:
            # Use jsonpickle to save types.
            import jsonpickle

            txt = jsonpickle.encode(obj, indent=4)
            outfile.write(txt)
        else:
            json.dump(
                obj,
                outfile,
                indent=4,
                default=serialize_custom_types_for_json_encoder,
            )


def from_json(file_name: str, *, use_types: bool = False) -> Dict:
    """
    Read object from JSON file.

    :param file_name: name of file
    :param use_types: whether to use jsonpickle to load the file
    :return: dict with data
    """
    hdbg.dassert(file_name)
    if not file_name.endswith(".json"):
        _LOG.warning("The file '%s' doesn't end in .json", file_name)
    # Read file as text.
    hdbg.dassert_file_exists(file_name)
    txt = from_file(file_name)
    # Remove comments (which are not supported natively by JSON).
    txt_tmp = []
    for line in txt.split("\n"):
        if re.match(r"^\s*#", line):
            continue
        txt_tmp.append(line)
    txt_tmp = "\n".join(txt_tmp)
    _LOG.debug("txt_tmp=\n%s", txt_tmp)
    # Convert text into Python data structures.
    if use_types:
        import jsonpickle

        data: Dict = jsonpickle.decode(txt_tmp)
    else:
        data: Dict = json.loads(txt_tmp)
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
