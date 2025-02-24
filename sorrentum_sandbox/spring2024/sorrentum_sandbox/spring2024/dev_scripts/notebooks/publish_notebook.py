#!/usr/bin/env python
r"""
This script performs several actions on a Jupyter notebook, such as:

- opening a notebook in the browser
- publishing a notebook locally or remotely on an HTML server

# Open a notebook in the browser

- The following command opens an archived notebook as HTML into the browser:
  ```
  > publish_notebook.py \
      --file s3://.../notebooks/PTask768_event_filtering.html \
      --action open \
      --aws_profile 'am'
  ```

# Publish a notebook

  ```
  > publish_notebook.py \
      --file nlp/notebooks/PTask768_event_filtering.ipynb \
      --action publish \
      --aws_profile 'am'
  ```

# Detailed instructions at:
https://docs.google.com/document/d/1b3RptKVK6vFUc8upcz3n0nTZhTO0ZQ-Ay5I01nCp5WM/edit#heading=h.prfy6fm6muxp

Import as:

import dev_scripts.notebooks.publish_notebook as dsnopuno
"""

import argparse
import logging
import os
import sys
import tempfile
from typing import BinaryIO, List, Tuple

import requests

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hio as hio
import helpers.hopen as hopen
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hs3 as hs3
import helpers.hserver as hserver
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


# TODO(gp): Reuse url.py code.
def _get_path(path_or_url: str) -> str:
    """
    Get path from file, local link, or GitHub link.

    :param path_or_url: URL to notebook/github, local path,
        E.g., `https://github.com/...ipynb`
    :return: path to file
        E.g., `UnderstandingAnalysts.ipynb`
    """
    if "https://github" in path_or_url:
        ret = "/".join(path_or_url.split("/")[7:])
    elif "http://" in path_or_url:
        ret = "/".join(path_or_url.split("/")[4:])
        hdbg.dassert_path_exists(ret)
        if not os.path.exists(path_or_url):
            # Try to find the file with find basename in the current client.
            pass
    elif path_or_url.endswith(".ipynb") and os.path.exists(path_or_url):
        ret = path_or_url
    else:
        raise ValueError(f"Incorrect file '{path_or_url}'")
    return ret


# TODO(gp): This can go in `git.py`.
def _get_file_from_git_branch(git_branch: str, git_path: str) -> str:
    """
    Checkout a file from a git branch and store it in a temporary location.

    :param git_branch: the branch name e.g.,
        `origin/PTask302_download_eurostat_data`
    :param git_path: the relative path to the file E.g.,
        `core/notebooks/gallery_signal_processing.ipynb`
    :return: the path to the file retrieved E.g.,
        `/tmp/gallery_signal_processing.ipynb`
    """
    dst_file_name = os.path.join(
        tempfile.gettempdir(), os.path.basename(git_path)
    )
    _LOG.debug("Check out '%s/%s' to '%s'.", git_branch, git_path, dst_file_name)
    hsystem.system(f"git show {git_branch}:{git_path} > {dst_file_name}")
    return dst_file_name


def _export_notebook_to_html(ipynb_file_name: str, tag: str) -> str:
    """
    Export a notebook as HTML in the same location, adding a timestamp to file
    name.

    :param ipynb_file_name: path to the notebook file
        E.g., `.../event_relevance_exploration.ipynb`
    :return: path to the HTML file with a timestamp
        E.g., `event_relevance_exploration.20180802_162438.html`
    """
    # Extract file name and dir for the ipynb file.
    dir_path = os.path.dirname(os.path.realpath(ipynb_file_name))
    file_name = os.path.splitext(os.path.basename(ipynb_file_name))[0]
    # Create dst file name including timestamp.
    html_file_name = file_name + ".html"
    html_file_name = hsystem.append_timestamp_tag(html_file_name, tag)
    dst_file_name = os.path.join(dir_path, html_file_name)
    # Export notebook file to HTML format.
    cmd = (
        f"jupyter nbconvert {ipynb_file_name} --to html --output {dst_file_name}"
    )
    hsystem.system(cmd)
    _LOG.debug("Export notebook '%s' to HTML '%s'", file_name, dst_file_name)
    return dst_file_name


def _export_notebook_to_dir(ipynb_file_name: str, tag: str, dst_dir: str) -> str:
    """
    Export a notebook as HTML to a dst dir.

    :param ipynb_file_name: path to the notebook file
        E.g., `.../event_relevance_exploration.ipynb`
    :param dst_dir: destination folder
    """
    # Convert to HTML in the same location.
    html_src_path = _export_notebook_to_html(ipynb_file_name, tag)
    #
    html_file_name = os.path.basename(html_src_path)
    html_dst_path = os.path.join(dst_dir, html_file_name)
    # Normalize paths so that they are comparable. E.g., `./file_name.py`
    # and `/app/file_name.py` are the same when the script is run from
    # `root`, so they are converted to `/app/file_name.py`.
    norm_html_src_path = os.path.abspath(html_src_path)
    norm_html_dst_path = os.path.abspath(html_dst_path)
    if norm_html_src_path != norm_html_dst_path:
        # Move the HTML file to the `dst_dir`.
        _LOG.debug("Export '%s' to '%s'", norm_html_src_path, norm_html_dst_path)
        hio.create_dir(dst_dir, incremental=True)
        cmd = f"mv {norm_html_src_path} {norm_html_dst_path}"
        hsystem.system(cmd)
    # Print info.
    _LOG.info("Generated HTML file '%s'", norm_html_dst_path)
    cmd = f"""
        # To open the notebook run:
        > publish_notebook.py --file {norm_html_dst_path} --action open
        """
    print(hprint.dedent(cmd))
    return norm_html_dst_path


def _post_to_s3(
    local_src_path: str, s3_path: str, aws_profile: hs3.AwsProfile
) -> str:
    """
    Export a notebook as HTML to S3.

    :param local_src_path: the path of the local ipynb to export
    :param s3_path: full S3 path starting with `s3://`
    :param local_src_path: the path of the local ipynb to export
    :param s3_path: full S3 path starting with `s3://`
    :param aws_profile: the name of an AWS profile or a s3fs filesystem
    """
    hdbg.dassert_file_exists(local_src_path)
    # TODO(gp): Pass s3_path through the credentials.
    hs3.dassert_is_s3_path(s3_path)
    # Compute the full S3 path.
    remote_path = os.path.join(s3_path, os.path.basename(local_src_path))
    # TODO(gp): Make sure the S3 dir exists.
    _LOG.info("Copying '%s' to '%s'", local_src_path, remote_path)
    # For some reason when using `s3fs` a web-browser downloads an HTML file instead
    # of just displaying it. See CmTask #4027 "Cosmetic change in serving notebooks
    # via S3".
    hs3.copy_file_to_s3(local_src_path, remote_path, aws_profile)
    # s3fs = hs3.get_s3fs(aws_profile)
    # s3fs.put(local_src_path, remote_path)
    return remote_path


# TODO(gp): This can be more general than this file.
def _post_to_webserver(local_src_path: str, remote_dst_path: str) -> None:
    """
    Copy file to a directory on the remote server using HTTP post.

    :param local_src_path: path to the local file
        E.g.: `.../relevance_and_event_relevance_exploration.html`
    :param remote_dst_path: folder in which the file will be copied
        E.g.: `user@server_ip:/http/notebook_publisher`
    """
    _NOTEBOOK_KEEPER_SRV = "http://notebook-keeper"
    _NOTEBOOK_KEEPER_ENTRY_POINT = f"{_NOTEBOOK_KEEPER_SRV}/save-file"
    # File copying.
    payload: dict = {"dst_path": remote_dst_path}
    files: List[Tuple[str, BinaryIO]] = [("file", open(local_src_path, "rb"))]
    response = requests.request(
        "POST", _NOTEBOOK_KEEPER_ENTRY_POINT, data=payload, files=files
    )
    _LOG.debug("Response: %s", response.text.encode("utf8"))


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--file",
        action="store",
        required=True,
        type=str,
        help="The path to the ipynb file, a Jupyter URL, or a GitHub URL",
    )
    parser.add_argument(
        "--branch",
        action="store",
        type=str,
        help="The Git branch containing the notebook, if different than `master`",
    )
    parser.add_argument(
        "--target_dir",
        action="store",
        type=str,
        default=None,
        help="Dir where to save the HTML file",
    )
    parser.add_argument(
        "--tag",
        action="store",
        default="",
        type=str,
        help="A tag that is added to the file (e.g., `RH1E_with_magic_parameters`)",
    )
    parser.add_argument(
        "--action",
        action="store",
        default=["convert"],
        choices=[
            "convert",
            "open",
            "publish",
            # TODO(Grisha): consider discontinuing if not used.
            "publish_on_webserver",
        ],
        help="""
        - convert: convert notebook to HTML in the current dir
        - open: open an existing notebook
        - publish: publish notebook to a specified directory
        - publish_on_webserver: publish notebook through a webservice
        """,
    )
    parser = hs3.add_s3_args(parser)
    parser = hparser.add_verbosity_arg(parser)
    return parser  # type: ignore[no-any-return]


def _main(parser: argparse.ArgumentParser) -> None:
    # Check that we are running inside the Docker dev container.
    if False:
        hdbg.dassert(
            hserver.is_inside_docker(),
            "This can be run only inside the Docker dev container",
        )
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    if args.action == "open":
        # Open an existing HTML notebook.
        src_file_name = args.file
        if hs3.is_s3_path(src_file_name):
            # We use AWS CLI to minimize the dependencies from Python packages.
            aws_profile = hs3.get_aws_profile(args.aws_profile)
            # Check that the file exists.
            cmd = f"aws s3 ls --profile {aws_profile} {src_file_name}"
            hsystem.system(cmd)
            # Copy.
            local_file_name = os.path.basename(src_file_name)
            cmd = f"aws s3 cp --profile {aws_profile} {src_file_name} {local_file_name}"
            hsystem.system(cmd)
            _LOG.info("Copied remote url to '%s'", local_file_name)
        else:
            local_file_name = src_file_name
        #
        hopen.open_file(local_file_name)
        sys.exit(0)
    # Compute the path of the src file.
    if args.branch:
        src_file_name = _get_file_from_git_branch(args.branch, args.file)
    else:
        src_file_name = _get_path(args.file)
    # Process the action.
    if args.action == "convert":
        # Convert to HTML.
        dst_dir = "."
        html_file_name = _export_notebook_to_dir(src_file_name, args.tag, dst_dir)
        # Try to open.
        hopen.open_file(html_file_name)
        # Exit the `convert` action.
        sys.exit(0)
    if args.action == "publish":
        target_dir = args.target_dir
        _LOG.debug("target_dir='%s'", target_dir)
        aws_profile = args.aws_profile
        _LOG.debug("aws_profile='%s'", aws_profile)
        html_bucket_path = henv.execute_repo_config_code("get_html_bucket_path()")
        if target_dir is None:
            # Set defait tatget dir for the notebook publishing.
            target_dir = os.path.join(html_bucket_path, "notebooks")
            # TODO(Grisha): we should infer the profile from the HTML bucket or extend `get_html_bucket_path()`
            # so that it also returns the `aws_profile`.
            aws_profile = "ck"
            _LOG.info(
                "`target_dir` was not provided, using the default one='%s', aws_profile='%s'",
                target_dir,
                aws_profile,
            )
        if hs3.is_s3_path(target_dir):
            # Convert to HTML.
            dst_dir = "."
            # TODO(Grisha): @Dan Consider posting an HTML to s3 without postig it locally.
            html_file_name = _export_notebook_to_dir(
                src_file_name, args.tag, dst_dir
            )
            # Copy to S3.
            s3_file_name = _post_to_s3(html_file_name, target_dir, aws_profile)
            # TODO(gp): Remove the file or save it directly in a temp dir.
            cmd = f"""
            # To open the notebook from S3 run:
            > publish_notebook.py --file {s3_file_name} --action open --aws_profile {aws_profile}
            """
            print(hprint.dedent(cmd))
            #
            if target_dir.startswith(html_bucket_path):
                dir_to_url = henv.execute_repo_config_code(
                    "get_html_dir_to_url_mapping()"
                )
                url_bucket_path = dir_to_url[html_bucket_path]
                url = s3_file_name.replace(html_bucket_path, url_bucket_path)
                cmd = f"""
                # To open the notebook from a web-browser open a link:
                {url}
                """
                print(hprint.dedent(cmd))
        else:
            hdbg.dassert_dir_exists(target_dir)
            _export_notebook_to_dir(src_file_name, args.tag, target_dir)
    elif args.action == "publish_on_webserver":
        remote_dst_path = os.path.basename(html_file_name)
        _post_to_webserver(html_file_name, remote_dst_path)
    else:
        hdbg.dfatal(f"Invalid action='{args.action}'")


if __name__ == "__main__":
    _main(_parse())
