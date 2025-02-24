#!/usr/bin/env python

"""
Diff content of two directories using vimdiff, by transform the output of `diff -r
--brief dir1 dir2` into a script using vimdiff.

# To clean up the crap in the dirs:
> git status --ignored
> git clean -fdx --dry-run

# Diff content of dirs using vimdiff:
> diff_to_vimdiff.py \
    --dir1 /Users/saggese/src/...2/amp \
    --dir2 /Users/saggese/src/...3/amp

# Diff only files that are present in both dirs but have different content:
> diff_to_vimdiff.py \
    --dir1 ... --dir2 ... \
    --only_different_file_content

# Diff only files that are not present in both dirs
> diff_to_vimdiff.py \
    --dir1 ... --dir2 ... \
    --only_different_files

# Compare the list of files in the two dirs, instead of the content of the files:
> diff_to_vimdiff.py \
    --dir1 ... --dir2 ... \
    --compare_file_list

Import as:

import dev_scripts.diff_to_vimdiff as dsditovi
"""

import argparse
import logging
import os
import re
import sys
from typing import Any, Match, Optional

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def _remove_files(file_name: str, to_ignore_regex: Optional[str]) -> None:
    """
    Remove certain files (e.g., `.git`, `tmp.`, ...) from the content of a file.

    - Read the file name which has one file per line
    - Remove certain files
    - Write the file back
    """
    print(f"# Removing files from '{file_name}'")
    txt = hio.from_file(file_name)
    files = txt.split("\n")
    removed_files = []
    kept_files = []
    vals = ["\.git\/", "\.git:", "\.idea", "[\/ ]tmp\."]
    if to_ignore_regex:
        vals.append(to_ignore_regex)
    regex = "|".join(vals)
    print(f"regex={regex}")
    # remove_cmd = "| grep -v \"\.git/\" | grep -v \.idea | grep -v '[/ ]tmp.'"
    for file in files:
        keep = not bool(re.search(regex, file))
        if keep:
            kept_files.append(file)
        else:
            removed_files.append(file)
        _LOG.debug("file='%s': -> kept=%s", file, keep)
    #
    hio.to_file(file_name + ".orig", "\n".join(files))
    hio.to_file(file_name + ".removed", "\n".join(removed_files))
    hio.to_file(file_name, "\n".join(kept_files))
    hdbg.dassert_eq(len(files), len(removed_files) + len(kept_files))
    # assert 0, (len(files), len(removed_files), len(kept_files))
    # print(len(files), len(removed_files), len(kept_files))


# ###############################################################################


def _compare_file_list(
    dir1: str, dir2: str, to_ignore_regex: Optional[str]
) -> None:
    """
    Extract the file list from two dirs and run `sdiff` on the two file lists.

    The output looks like:
    ```
    > sdiff --suppress-common-lines --expand-tabs /tmp/dir1 /tmp/dir2                                                                                                            [244/93661]
                                                                    > ./.dockerignore
                                                                    > ./.github.OLD
                                                                    > ./.github.OLD/gh_requirements.txt

      ./.github/workflows/build_image.cmamp.yml                     <
      ./.github/workflows/build_image.dev.yml                       <
      ./.github/workflows/ib_connector.build_image.yml.DISABLED     <
      ./.github/workflows/import_cycles_detector.yml                <
      ./dev_scripts/notebooks/test/outcomes/Test_publish_notebook1. | ./dev_scripts/notebooks/test/simple_notebook.ipynb
      ./dev_scripts/notebooks/test/outcomes/Test_publish_notebook1. | ./dev_scripts/notebooks/test/simple_notebook.py
    ```

    :param dir1: first dir
    :param dir2: second dir
    :param to_ignore_regex: regex for files to remove
    """
    print(hprint.frame("Compare file list in dirs '%s' vs '%s'" % (dir1, dir2)))
    hdbg.dassert_path_exists(dir1)
    hdbg.dassert_path_exists(dir2)
    # Find all the files in both dirs.
    cmd = ""
    # remove_cmd = "| grep -v \"\.git/\" | grep -v \.idea | grep -v '[/ ]tmp.'"
    cmd += '(cd %s && find . -name "*" | sort >/tmp/dir1) && ' % (
        # os.path.dirname(dir1),
        # os.path.basename(dir1),
        dir1,
    )
    cmd += '(cd %s && find . -name "*" | sort >/tmp/dir2)' % (
        # os.path.dirname(dir2),
        # os.path.basename(dir2),
        dir2,
    )
    print(cmd)
    hsystem.system(cmd, abort_on_error=True)
    # Remove files.
    _remove_files("/tmp/dir1", to_ignore_regex)
    _remove_files("/tmp/dir2", to_ignore_regex)
    # Compare the file listings.
    opts = []
    opts.append("--suppress-common-lines")
    opts.append("--expand-tabs")
    opts = " ".join(opts)
    cmd = f"sdiff {opts} /tmp/dir1 /tmp/dir2"
    print("# Diff file listing with:\n> " + cmd)
    hsystem.system(cmd, abort_on_error=False, suppress_output=False)


# ###############################################################################


def _find_files_to_diff(
    dir1: str, dir2: str, to_ignore_regex: Optional[str]
) -> str:
    """
    Diff the dirs with `diff -r --brief`, and save the output in a file.

    :return: path of the file with the output of `diff -r --brief`
    """
    print(hprint.frame("Diff dirs '%s' vs '%s'" % (dir1, dir2)))
    dst_file = "./tmp.diff_file_listings.txt"
    cmd = f"diff --brief -r {dir1} {dir2} >{dst_file}"
    # We don't abort since rc != 0 in case of differences, which is a valid outcome.
    hsystem.system(cmd, abort_on_error=False)
    # Remove files.
    _remove_files(dst_file, to_ignore_regex)
    #
    cmd = f"cat {dst_file}"
    print(f"# To see diff of the dirs:\n> {cmd}")
    hsystem.system(cmd, abort_on_error=False, suppress_output=False)
    return dst_file


def _get_symbolic_filepath(dir1: str, dir2: str, file_name: str) -> str:
    """
    Transform a path like:

        /Users/saggese/src/...2/amp/vendors/first_rate/utils.py
    into:
        $DIR1/amp/vendors/first_rate/utils.py
    """
    file_name = file_name.replace(dir1, "$DIR1")
    file_name = file_name.replace(dir2, "$DIR2")
    return file_name


# TODO(gp): We should use the `sdiff` between files, instead of the output of
#  `diff -r --brief` to compare, since the second doesn't work for dirs that are
#  present only on one side.
def _parse_diff_output(
    input_file: str, dir1: str, dir2: str, args: argparse.Namespace
) -> None:
    """
    Process the output of diff and create a script to diff the different files.

    :param input_file: the output of `diff -r --brief`, e.g.,
        ```
        Only in /Users/saggese/src/amp1/dataflow_amp: features
        Only in /Users/saggese/src/amp1/dataflow_amp/real_time/test: TestRealTimeReturnPipeline1.test1
        ```
    """
    print(
        hprint.frame("Compare file content in dirs '%s' vs '%s'" % (dir1, dir2))
    )
    # Read the output from `diff -r --brief`.
    hdbg.dassert_path_exists(input_file)
    _LOG.info("Reading '%s'", input_file)
    txt = hio.from_file(input_file)
    txt = txt.split("\n")
    # Process the output.
    out = []
    for line in txt:
        _LOG.debug("# line='%s'", line)
        if line == "":
            continue
        comment = None
        out_line = None
        skip = False
        if line.startswith("Only in "):
            # Only in /data/gp_wd/src/deploy_...1/: cfile
            m = re.match(r"^Only in (\S+): (\S+)$", line)
            hdbg.dassert(m, "Invalid line='%s'", line)
            m: Match[Any]
            file_name = "%s/%s" % (m.group(1), m.group(2))
            # hdbg.dassert_path_exists(file_name)
            dir_ = _get_symbolic_filepath(dir1, dir2, m.group(1))
            dirs = dir_.split("/")
            dir_ = dirs[0]
            file_ = os.path.join(
                *dirs[1:], _get_symbolic_filepath(dir1, dir2, m.group(2))
            )
            # Determine the direction.
            if "$DIR1" in dir_:
                sign = "<"
            elif "$DIR2" in dir_:
                sign = ">"
            else:
                hdbg.dfatal("Invalid dir_='%s'" % dir_)
            if args.dir1_name is not None:
                dir_ = dir_.replace("$DIR1", args.dir1_name)
            if args.dir2_name is not None:
                dir_ = dir_.replace("$DIR2", args.dir2_name)
            comment = line + "\n"
            comment += "%s: ONLY: %s in '%s'\n" % (sign, file_, dir_)
            # Diff command.
            if args.dir1 in file_name:
                out_line = "vimdiff %s %s" % (
                    file_name,
                    file_name.replace(args.dir1, args.dir2),
                )
            else:
                hdbg.dassert_in(args.dir2, file_name)
                out_line = "vimdiff %s %s" % (
                    file_name.replace(args.dir2, args.dir1),
                    file_name,
                )
            # Skip directory.
            if os.path.isdir(file_name):
                _LOG.debug("Skipping dir '%s'", file_name)
                skip = True
            if args.only_different_file_content:
                # We want to see only files with diff content, so skip this.
                _LOG.debug("  -> Skipping line")
                skip = True
        elif line.startswith("Files "):
            # Files
            #   /data/gp_wd/src/deploy_...1/compustat/fiscal_calendar.py and
            #   /data/gp_wd/src/...1/compustat/fiscal_calendar.py differ
            m = re.match(r"^Files (\S+) and (\S+) differ$", line)
            hdbg.dassert(m, "Invalid line='%s'", line)
            m: Match[Any]
            # Check.
            hdbg.dassert_path_exists(m.group(1))
            hdbg.dassert_path_exists(m.group(2))
            # Comment.
            file1 = _get_symbolic_filepath(dir1, dir2, m.group(1))
            file1 = file1.replace("$DIR1/", "")
            file2 = _get_symbolic_filepath(dir1, dir2, m.group(2))
            file2 = file2.replace("$DIR2/", "")
            hdbg.dassert_eq(file1, file2)
            sign = "-"
            comment = "\n" + line + "\n"
            comment += "%s: DIFF: %s" % (sign, file1)
            # Diff command.
            out_line = "vimdiff %s %s" % (m.group(1), m.group(2))
            if args.only_different_files:
                _LOG.debug("  -> Skipping line")
                skip = True
        elif line.startswith("File "):
            # File
            #   /wd/saggese/src/...1/amp/devops/docker_build/fstab
            # is a regular file while file
            #   /wd/saggese/src/dev_tools/devops/docker_build/fstab
            # is a directory
            _LOG.warning(line)
            continue
        else:
            hdbg.dfatal("Invalid line='%s'" % line)
        #
        if not args.skip_comments:
            if comment:
                out.append(hprint.prepend(comment, "#       "))
        if not args.skip_vim:
            if out_line:
                _LOG.debug("    -> out='%s'", out_line)
                if skip:
                    out_line = "# " + out_line
                out.append(out_line)
    # Write the output.
    out = "\n".join(out)
    output_file = args.output_file
    if output_file is None:
        # Print to screen.
        print(out)
    else:
        # Prepare the diff script.
        _LOG.info("Writing '%s'", output_file)
        hio.to_file(output_file, out)
        cmd = "chmod +x %s" % output_file
        hsystem.system(cmd)
        # Press enter to continue.
        hsystem.press_enter_to_continue()
        # Run the diff script.
        cmd = "./%s" % output_file
        print("Run script with:\n> " + cmd)
        #
        # Start the script automatically.
        if args.run_diff_script:
            os.system(cmd)
        else:
            _LOG.warning("Skipping running script: %s", cmd)
        # cmd = "kill -kill $(ps -ef | grep %s | awk '{print $2 }')" % output_file
        # print("# To kill the script run:\n> " + cmd)


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Specify dirs.
    parser.add_argument(
        "--dir1", action="store", required=True, help="First dir to compare"
    )
    parser.add_argument(
        "--dir2", action="store", required=True, help="Second dir to compare"
    )
    parser.add_argument("--subdir", action="store", help="subdir to compare")
    # Name dir.
    parser.add_argument(
        "--dir1_name",
        action="store",
        help="A symbolic name for the dir1, e.g., branch_ABC",
    )
    parser.add_argument(
        "--dir2_name",
        action="store",
        help="A symbolic name for the dir2, e.g., branch_XYZ",
    )
    #
    parser.add_argument(
        "-o",
        "--output_file",
        action="store",
        default="tmp.diff_to_vimdiff.sh",
        help="Output script file. Don't specify anything for stdout",
    )
    parser.add_argument(
        "--compare_file_list",
        action="store_true",
        help="Diff the list of files between the dirs and exit",
    )
    parser.add_argument(
        "--only_different_file_content",
        action="store_true",
        help="Diff content of only files that are present in both dirs but have "
             "different content",
    )
    parser.add_argument(
        "--only_different_files",
        action="store_true",
        help="Diff content of only files that are not present in both dirs",
    )
    parser.add_argument(
        "--select_files",
        action="store",
        default=None,
        help="Specify a file that contains the files to actually consider "
             "for the diff",
    )
    parser.add_argument(
        "--ignore_files",
        action="store",
        default=None,
        help="Regex to skip certain files",
    )
    hparser.add_bool_arg(
        parser,
        "run_diff_script",
        default_value=True,
        help_="Run automatically the diffing script or not",
    )
    parser.add_argument(
        "--skip_comments", action="store_true",
        help="Do not print comments in the diff script"
    )
    parser.add_argument(
        "--skip_vim", action="store_true",
        help="Do not print vim commands in the diff script"
    )
    hparser.add_verbosity_arg(parser)
    return parser


# ###############################################################################


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=False)
    # Compute the target dirs.
    dir1 = os.path.abspath(args.dir1)
    dir2 = os.path.abspath(args.dir2)
    if args.subdir:
        dir1 = os.path.join(dir1, args.subdir)
        dir2 = os.path.join(dir2, args.subdir)
    if args.compare_file_list:
        # Compare the file list and exit.
        _compare_file_list(dir1, dir2, args.ignore_files)
        sys.exit(0)
    # Find the files to diff.
    diff_file = _find_files_to_diff(dir1, dir2, args.ignore_files)
    # Diff the files.
    _parse_diff_output(diff_file, dir1, dir2, args)


if __name__ == "__main__":
    _main(_parse())
