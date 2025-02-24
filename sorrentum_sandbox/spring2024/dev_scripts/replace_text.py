#!/usr/bin/env python

"""
Instructions at docs/work_tools/all.replace_text.how_to_guide.md.
"""

import argparse
import logging
import os
import pprint
import re
import sys
from typing import Dict, List, Optional, Tuple

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

# TODO(gp):
#  - allow to read a cfile with a subset of files / points to replace
#  - allow to work with no filter
#  - fix the help
#  - figure out the issue with encoding

_LOG = logging.getLogger(__name__)

_ENCODING = "ISO-8859-1"


def _get_all_files(dirs: List[str], extensions: Optional[List[str]]) -> List[str]:
    """
    Find all the files with the given extensions in files under `dirs`.

    :param extensions: if None, no filtering by extensions
    """
    if extensions is not None:
        # Extensions are specified.
        hdbg.dassert_isinstance(extensions, list)
        hdbg.dassert_lte(1, len(extensions))
        for extension in extensions:
            hdbg.dassert(
                not extension.startswith("."), "Invalid ext='%s'", extension
            )
    # Get files.
    _LOG.debug("extensions=%s", extensions)
    file_names = []
    for d in dirs:
        _LOG.debug("Processing dir '%s'", d)
        only_files = False
        use_relative_paths = False
        if extensions is not None:
            # Extensions are specified: find all the files with the given
            # extensions.
            for extension in extensions:
                pattern = "*." + extension
                file_names_tmp = hio.listdir(
                    d, pattern, only_files, use_relative_paths
                )
                _LOG.debug(
                    "extension=%s -> found %s files",
                    extension,
                    len(file_names_tmp),
                )
                file_names.extend(file_names_tmp)
        else:
            # No extension: find all files.
            pattern = "*"
            file_names_tmp = hio.listdir(
                d, pattern, only_files, use_relative_paths
            )
            _LOG.debug(
                "extensions=%s -> found %s files", extensions,
                len(file_names_tmp)
            )
            file_names.extend(file_names_tmp)
    # Exclude some files.
    file_names_to_remove = [
        ".ipynb_checkpoints",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "replace_text.py",
        ".git/",
    ]
    for file_name_to_remove in file_names_to_remove:
        file_names = [f for f in file_names if file_name_to_remove not in f]
    file_names = [f for f in file_names if os.path.basename(f) != "cfile"]
    _LOG.info(
        "Found %s target files with extensions '%s'",
        len(file_names),
        str(extensions),
    )
    return file_names


# #############################################################################
# Replace strings inside file.
# #############################################################################


def _look_for(file_name: str, filter_by: str) -> Tuple[bool, List[str]]:
    """
    Search for the regex string in a file.

    :param file_name: the name of the file to search in
    :param filter_by: the regex to search for in the file content
    :return: whether the regex was found in a file; the corresponding
        cfile entry
    """
    txt = hio.from_file(file_name, encoding=_ENCODING)
    txt = txt.split("\n")
    res = []
    found = False
    for i, line in enumerate(txt):
        # TODO(Vlad): It filters files based on content, but it should filter
        # based on a name.
        m = re.search(filter_by, line)
        if m:
            # ./install/create_conda.py:21:import helpers.helper_io as hio
            res.append("%s:%s:%s" % (file_name, i + 1, line))
            found = True
    return found, res


def _get_files_to_replace(
    file_names: List[str],
    filter_by: str,
) -> Tuple[List[str], str]:
    """
    Get the list of the files that contain the `filter_by` regex.

    :param file_names: names of the files to check
    :param filter_by: the regex to look for in the files
    :return: names of the files that contain the `filter_by` regex and the
        corresponding cfile
    """
    # Look for files with values.
    res = []
    file_names_to_process = []
    for f in file_names:
        found, res_tmp = _look_for(f, filter_by)
        _LOG.debug("File='%s', found=%s, res_tmp=\n%s", f, found, res_tmp)
        res.extend(res_tmp)
        if found:
            file_names_to_process.append(f)
    #
    txt = "\n".join(res)
    _LOG.info("Found %s occurrences to replace\n%s", len(res), hprint.indent(txt))
    _LOG.info("Found %s files to replace", len(file_names_to_process))
    return file_names_to_process, txt


# #############################################################################


def _replace_with_perl(
    file_name: str, old_regex: str, new_regex: str, backup: bool
) -> None:
    perl_opts = []
    perl_opts.append("-p")
    if backup:
        perl_opts.append("-i.bak")
    else:
        perl_opts.append("-i")
    if "/" in old_regex or "/" in new_regex:
        sep = "|"
    else:
        sep = "/"
    # s|\\balphamatic/kibot/All_Futures|alphamatic/kibot/All_Futures|g
    regex = ""
    regex += "s" + sep
    # regex += "\\b"
    regex += old_regex
    regex += sep
    regex += new_regex
    regex += sep
    regex += "g"
    # regex = r"s%s\\b%s%s%s%sg" % (sep, args.old, sep, args.new, sep)
    if True:
        perl_opts.append("-e '%s'" % regex)
    else:
        perl_opts.append(r"-e '%s unless /^\s*#/'" % regex)
    cmd = "perl %s %s" % (" ".join(perl_opts), file_name)
    hsystem.system(cmd, suppress_output=False)


def _replace_with_python(
    file_name: str, old_regex: str, new_regex: str, backup: bool
) -> None:
    if backup:
        cmd = "cp %s %s.bak" % (file_name, file_name)
        hsystem.system(cmd)
    #
    lines = hio.from_file(file_name, encoding=_ENCODING).split("\n")
    lines_out = []
    for line in lines:
        _LOG.debug("line='%s'", line)
        line_new = re.sub(old_regex, new_regex, line)
        if line_new != line:
            _LOG.debug("    -> line_new='%s'", line_new)
        lines_out.append(line_new)
    lines_out = "\n".join(lines_out)
    hio.to_file(file_name, lines_out)


def _replace(
    file_names_to_process: List[str],
    old_regex: str,
    new_regex: str,
    backup: bool,
    mode: str,
) -> None:
    """
    Replace `old_regex` with `new_regex` in the given files using perl or
    Python.

    :param backup: make a backup of the file before the replacement
    :param mode: `replace_with_perl` or `replace_with_python`
    """
    hdbg.dassert_ne(old_regex, new_regex)
    _LOG.info(
        "Found %s files:\n%s",
        len(file_names_to_process),
        hprint.indent("\n".join(file_names_to_process)),
    )
    for file_name in file_names_to_process:
        _LOG.info("* _replace %s", file_name)
        if mode == "replace_with_perl":
            _replace_with_perl(file_name, old_regex, new_regex, backup)
        elif mode == "replace_with_python":
            _replace_with_python(file_name, old_regex, new_regex, backup)
        else:
            raise ValueError("Invalid mode='%s'" % mode)


def _replace_repeated_lines(file_name: str, new_regex: str) -> None:
    """
    Remove consecutive lines in `file_name` that are equal and contain
    `new_regex`.

    This is equivalent to Linux `uniq`.
    """
    _LOG.info("* _replace_repeated_lines %s", file_name)
    lines = hio.from_file(file_name, encoding=_ENCODING).split("\n")
    lines_out = []
    prev_line = None
    for line in lines:
        _LOG.debug("line='%s'", line)
        if new_regex not in line:
            # Emit.
            lines_out.append(line)
        else:
            if line != prev_line:
                # Emit.
                lines_out.append(line)
            else:
                _LOG.debug("    -> skipped line")
        prev_line = line
    lines_out = "\n".join(lines_out)
    hio.to_file(file_name, lines_out)


# #############################################################################
# Custom flows.
# #############################################################################


def _custom1(args: argparse.Namespace) -> None:
    to_replace = [
        # ("import helpers.printing as hprint", "import helpers.printing as
        # pri"),
        # (r"printing\.", "hprint."),
        ("import helpers.config", "import core.config")
    ]
    dirs = ["."]
    exts = ["py", "ipynb"]
    backup = args.backup
    preview = args.preview
    mode = "replace_with_python"
    #
    file_names = _get_all_files(dirs, exts)
    txt = ""
    for old_regex, new_regex in to_replace:
        print(hprint.frame("%s -> %s" % (old_regex, new_regex)))
        file_names_to_process, txt_tmp = _get_files_to_replace(
            file_names, old_regex
        )
        hdbg.dassert_lte(1, len(file_names_to_process))
        # Replace.
        if preview:
            txt += txt_tmp
        else:
            _replace(file_names_to_process, old_regex, new_regex, backup, mode)
    hio.to_file("./cfile", txt)
    if preview:
        _LOG.warning("Preview only as required. Results saved in ./cfile")
        sys.exit(0)


def _fix_AmpTask1403_helper(
    args: argparse.Namespace, to_replace: List[Tuple[str, str]]
) -> None:
    dirs = ["."]
    exts = ["py", "ipynb"]
    backup = args.backup
    preview = args.preview
    mode = "replace_with_python"
    #
    file_names = _get_all_files(dirs, exts)
    # file_names = ["amp/core/dataflow/nodes/test/test_volatility_models.py"]
    # Store the replacement points.
    txt = ""
    for old_regex, new_regex in to_replace:
        print(hprint.frame("%s -> %s" % (old_regex, new_regex)))
        file_names_to_process, txt_tmp = _get_files_to_replace(
            file_names, old_regex
        )
        # hdbg.dassert_lte(1, len(file_names_to_process))
        if len(file_names_to_process) < 1:
            _LOG.warning("Didn't find files to replace")
        # Replace.
        if preview:
            txt += txt_tmp
        else:
            _replace(file_names_to_process, old_regex, new_regex, backup, mode)
            for file_name in file_names_to_process:
                _replace_repeated_lines(file_name, new_regex)
    hio.to_file("./cfile", txt)
    if preview:
        _LOG.warning("Preview only as required. Results saved in ./cfile")
        sys.exit(0)


def _fix_AmpTask1403(args: argparse.Namespace) -> None:
    """
    Implement AmpTask1403.
    """
    # From longest to shortest to avoid nested replacements.
    to_replace = [
        "import core.config as cfg",
        "import core.config as ccfg",
        # "import core.config as cconfi",
        "import core.config as cconfig",
        "import core.config_builders as ccbuild",
        "import core.config_builders as cfgb",
    ]
    # to_replace = [(f"^{s}$", "import core.config as cconfig") for s in to_replace]
    to_replace = [(f"{s}", "import core.config as cconfig") for s in to_replace]
    _fix_AmpTask1403_helper(args, to_replace)
    #
    to_replace = [
        # (r"printing\.", "hprint."),
        # ("import helpers.config", "import core.config")
        "ccfg",
        # "cconfi",
        "cconfig",
        "cfg",
        "ccbuild",
        "cfgb",
    ]
    to_replace = [(rf"{s}\.", "cconfig.") for s in to_replace]
    _fix_AmpTask1403_helper(args, to_replace)


def _prerelease_cleanup(args: argparse.Namespace) -> None:
    """
    Implement AmpTask1403.
    """
    # From longest to shortest to avoid nested replacements.
    to_replace = [("instrument_master", "im"), ("order_management_system", "oms")]
    dirs = ["."]
    # exts = ["py", "ipynb", "md", "txt"]
    exts = None
    backup = args.backup
    preview = args.preview
    mode = "replace_with_python"
    #
    file_names = _get_all_files(dirs, exts)
    # file_names = ["amp/core/dataflow/nodes/test/test_volatility_models.py"]
    # Store the replacement points.
    txt = ""
    for old_regex, new_regex in to_replace:
        print(hprint.frame("%s -> %s" % (old_regex, new_regex)))
        file_names_to_process, txt_tmp = _get_files_to_replace(
            file_names, old_regex
        )
        # hdbg.dassert_lte(1, len(file_names_to_process))
        if len(file_names_to_process) < 1:
            _LOG.warning("Didn't find files to replace")
        # Replace.
        if preview:
            txt += txt_tmp
        else:
            _replace(file_names_to_process, old_regex, new_regex, backup, mode)
    hio.to_file("./cfile", txt)
    if preview:
        _LOG.warning("Preview only as required. Results saved in ./cfile")
        sys.exit(0)


# #############################################################################
# Rename files.
# #############################################################################


def _get_files_to_rename(
    file_names: List[str],
    old_regex: str,
    new_regex: str,
    replace_in: str,
    filter_by: str,
    filter_on: str,
) -> Tuple[List[str], Dict[str, str]]:
    """
    Get names of the files to be renamed and a mapping for renaming.

    :param file_names: all file names to check
    :param old_regex: regex of the string to be replaced in the file names
    :param new_regex: regex of the string that `old_regex` will be replaced with
    :param replace_in: part of the name to replace `old_regex` with `new_regex` in
        - "basename": `file.py` for `dir/subdir/file.py`
        - "dirname": `dir/subdir` for `dir/subdir/file.py`
        - "filename": `dir/subdir/file.py` for `dir/subdir/file.py`
    :param filter_by: only replace `old_regex` with `new_regex` if the `filter_by`
        regex is found in the file name
    :param filter_on: part of the file name to look for the `filter_by` regex in;
        same possible options as in `replace_in`
    :return: file names to rename; a mapping for renaming
    """
    file_map: Dict[str, str] = {}
    file_names_to_process = []
    for filename in file_names:
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        # Check if the file matches the filter.
        if filter_on == "basename":
            filter_name_part = basename
        elif filter_on == "dirname":
            filter_name_part = dirname
        elif filter_on == "filename":
            filter_name_part = filename
        else:
            raise ValueError(f"Unsupported 'filter_on'={filter_on}")
        found = bool(re.findall(filter_by, filter_name_part))
        if found:
            # Update the name.
            if replace_in == "basename":
                new_basename = re.sub(old_regex, new_regex, basename)
                new_filename = os.path.join(dirname, new_basename)
            elif replace_in == "dirname":
                new_dirname = re.sub(old_regex, new_regex, dirname)
                new_filename = os.path.join(new_dirname, basename)
            elif replace_in == "filename":
                new_filename = re.sub(old_regex, new_regex, filename)
            else:
                raise ValueError(f"Unsupported 'replace_in'={replace_in}")
            # Store the new file name.
            _LOG.debug(hprint.to_str("filename found new_filename"))
            if filename != new_filename:
                file_names_to_process.append(filename)
                hdbg.dassert_ne(filename, new_filename)
                file_map[filename] = new_filename
    _LOG.info("Found %s files to rename", len(file_names_to_process))
    if file_map:
        _LOG.info("Replacing:\n%s", pprint.pformat(file_map))
    return file_names_to_process, file_map


def _rename(file_names_to_process: List[str], file_map: Dict[str, str]) -> None:
    for f in file_names_to_process:
        new_name = file_map[f]
        dirname = os.path.dirname(new_name)
        if not os.path.isdir(dirname):
            # Create a dir if the new file name presupposes a new dir.
            cmd = "mkdir -p %s" % dirname
            hsystem.system(cmd)
        # Rename the file.
        cmd = "git mv %s %s" % (f, new_name)
        hsystem.system(cmd)


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dst_dir",
        action="store",
        default=None,
        help="Change dir before replacing",
    )
    parser.add_argument(
        "--revert_all",
        action="store_true",
        help="Revert all the files (excluding this one) before processing",
    )
    parser.add_argument("--custom_flow", action="store", type=str)
    parser.add_argument(
        "--filter_by",
        action="store",
        default=None,
        type=str,
        help="Regex to filter file names by",
    )
    parser.add_argument(
        "--filter_on",
        action="store",
        default="basename",
        choices=["basename", "dirname", "filename"],
        help="Which part of the file name to filter on",
    )
    parser.add_argument(
        "--old",
        action="store",
        type=str,
        help="Regex of text to replace",
    )
    parser.add_argument(
        "--new", action="store", type=str, help="New string to replace with"
    )
    parser.add_argument(
        "--replace_in",
        action="store",
        default="basename",
        choices=["basename", "dirname", "filename"],
        help="Which part of the file name to replace the string in",
    )
    parser.add_argument(
        "--preview", action="store_true", help="Preview only the replacement"
    )
    parser.add_argument(
        "--mode",
        action="store",
        default="replace_with_python",
        choices=["replace_with_python", "replace_with_perl"],
    )
    parser.add_argument(
        "--action",
        action="store",
        default="replace",
        choices=["replace", "rename", "replace_rename"],
    )
    parser.add_argument(
        "--ext",
        action="store",
        type=str,
        default="py,ipynb,txt,md,sh",
        help="Extensions to process. `_all_` for all files",
    )
    parser.add_argument(
        "--backup", action="store_true", help="Keep backups of files"
    )
    parser.add_argument(
        "--only_dirs",
        action="append",
        default=None,
        help="Space-separated list of directories to process",
    )
    parser.add_argument(
        "--only_files",
        action="store",
        default=None,
        help="Space-separated list of files to process",
    )
    parser.add_argument(
        "--exclude_files",
        action="store",
        default=None,
        help="Space-separated list of files to exclude from replacements",
    )
    parser.add_argument(
        "--exclude_dirs",
        action="store",
        default=None,
        help="Space-separated dir to exclude from replacements",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(args.log_level)
    if args.dst_dir:
        print("pwd=", os.getcwd())
        hdbg.dassert_dir_exists(args.dst_dir)
        os.chdir(args.dst_dir)
    if args.revert_all:
        # Revert all the files but this one. Use at your own risk.
        _LOG.warning("Reverting all files but this one")
        cmd = [
            r"git status -s",
            r"grep -v dev_scripts/replace_text.py",
            r'grep -v "\?"',
            r"awk '{print $2}'",
            r"xargs git checkout --",
        ]
        cmd = " | ".join(cmd)
        print(f"> {cmd}")
        hsystem.system(cmd)
    if args.custom_flow:
        eval("%s(args)" % args.custom_flow)
    else:
        # Use command line params.
        dirs = args.only_dirs
        if dirs is None:
            dirs = ["."]
        _LOG.info("dirs=%s", dirs)
        # Parse the extensions.
        if args.ext == "_all_":
            exts = None
        else:
            exts = args.ext
            # exts = "py,ipynb,txt"
            exts = exts.split(",")
        _LOG.info("extensions=%s", exts)
        # Find all the files with the correct extension.
        file_names = _get_all_files(dirs, exts)
        # Use only specific files.
        if args.only_files:
            only_files_list = args.only_files.split(" ")
            num_files_before = len(file_names)
            _LOG.info("Using only_files=%s", only_files_list)
            file_names = [
                file_name
                for file_name in file_names
                # Remove current directory to match only_files format.
                if os.path.normpath(file_name) in only_files_list
            ]
            num_files_after = len(file_names)
            _LOG.info(
                "num_files_before=%s num_files_after=%s",
                num_files_before,
                num_files_after,
            )
        # Exclude files.
        if args.exclude_files:
            exclude_files_list = args.exclude_files.split(" ")
            num_files_before = len(file_names)
            _LOG.info("Excluding files=%s", exclude_files_list)
            file_names = [
                file_name
                for file_name in file_names
                if os.path.normpath(file_name) not in exclude_files_list
            ]
            num_files_after = len(file_names)
            _LOG.info(
                "num_files_before=%s num_files_after=%s",
                num_files_before,
                num_files_after,
            )
        # Exclude dirs.
        if args.exclude_dirs:
            exclude_dirs_list = args.exclude_dirs.split(" ")
            num_files_before = len(file_names)
            _LOG.info("Excluding dirs=%s", exclude_dirs_list)
            file_names = [
                file_name
                for file_name in file_names
                if os.path.normpath(os.path.dirname(file_name))
                not in exclude_dirs_list
            ]
            num_files_after = len(file_names)
            _LOG.info(
                "num_files_before=%s num_files_after=%s",
                num_files_before,
                num_files_after,
            )
        # Process the actions.
        _LOG.info("Found %s target files to process", len(file_names))
        if args.filter_by is None:
            # Filter the files by the string that is going to be replaced.
            filter_by = args.old
        else:
            # Filter the files by the supplied regex.
            filter_by = args.filter_by
        action_processed = False
        if args.action in ("replace", "replace_rename"):
            # Get the files to replace the string in. The files are selected
            # if the `filter_by` regex is found in their content.
            file_names_to_process, txt = _get_files_to_replace(
                file_names, filter_by
            )
            if args.preview:
                hio.to_file("./cfile", txt)
                _LOG.warning("Preview only as required. Results saved in ./cfile")
            else:
                # Replace the string inside the files. The `args.old` regex is
                # replaced with the `args.new` regex in the whole files' contents.
                _replace(
                    file_names_to_process,
                    args.old,
                    args.new,
                    args.backup,
                    args.mode,
                )
            action_processed = True
        if args.action in ("rename", "replace_rename"):
            # Get the files to rename. The files are selected if the `filter_by`
            # regex is found in a part of their name determined by
            # `args.filter_on`. Then the `args.old` regex is replaced with the
            # `args.new` regex in the part of their name determined by
            # `args.replace_in`.
            file_names_to_process, file_map = _get_files_to_rename(
                file_names,
                args.old,
                args.new,
                args.replace_in,
                filter_by,
                args.filter_on,
            )
            if args.preview:
                _LOG.warning("Preview only as required.")
            else:
                # Rename the files.
                _rename(file_names_to_process, file_map)
            action_processed = True
        if not action_processed:
            raise ValueError("Invalid action='%s'" % args.action)
        if args.preview:
            sys.exit(0)


if __name__ == "__main__":
    _main(_parse())
