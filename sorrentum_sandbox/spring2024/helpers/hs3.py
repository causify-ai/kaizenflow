"""
Import as:

import helpers.hs3 as hs3
"""

import argparse
import configparser
import copy
import functools
import gzip
import logging
import os
import pathlib
import pprint
from typing import Any, Dict, List, Optional, Tuple, Union

_WARNING = "\033[33mWARNING\033[0m"

try:
    import s3fs
except ModuleNotFoundError:
    _module = "s3fs"
    print(_WARNING + f": Can't find {_module}: continuing")

# Avoid the following dependency from other `helpers` modules to prevent import cycles.
# import helpers.hpandas as hpandas
# import helpers.hsql as hsql
# import helpers.hunit_test as hunitest

# To enforce this order of the imports we use the directive for the linter below.
import helpers.hdbg as hdbg  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position
import helpers.hintrospection as hintros  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position
import helpers.hio as hio  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position
import helpers.hprint as hprint  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position
import helpers.hserver as hserver  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position
import helpers.hsystem as hsystem  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position
import helpers.htimer as htimer  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position

_LOG = logging.getLogger(__name__)

# TODO(gp): @all separate S3 code in `helpers/hs3.py` from authentication and
#  AWS profile code in `helpers/aws_authentication.py`.

# #############################################################################
# Basic utils.
# #############################################################################

AwsProfile = Optional[Union[str, s3fs.core.S3FileSystem]]


def is_s3_path(s3_path: str) -> bool:
    """
    Return whether a path is on an S3 bucket, i.e., if it starts with `s3://`.
    """
    hdbg.dassert_isinstance(s3_path, str)
    valid = s3_path.startswith("s3://")
    if s3_path.startswith("s3://s3://"):
        valid = False
    return valid


def dassert_is_s3_path(s3_path: str) -> None:
    """
    Assert if a file is not a S3 path.
    """
    hdbg.dassert(
        is_s3_path(s3_path),
        "Invalid S3 file='%s'",
        s3_path,
    )


def dassert_is_not_s3_path(s3_path: str) -> None:
    """
    Assert if a file is a S3 path.
    """
    hdbg.dassert(
        not is_s3_path(s3_path),
        "Passed an S3 file='%s' when it was not expected",
        s3_path,
    )


def dassert_is_valid_aws_profile(path: str, aws_profile: AwsProfile) -> None:
    """
    Check that the value of `aws_profile` is compatible with the S3 or local
    file `path`.

    :param path: S3 or local path
    :param aws_profile: AWS profile to use if and only if using an S3 path,
        otherwise `None` for local path
    """
    if is_s3_path(path):
        hdbg.dassert_is_not(
            aws_profile, None, "path=%s aws_profile=%s", path, aws_profile
        )
    else:
        hdbg.dassert_is(
            aws_profile, None, "path=%s aws_profile=%s", path, aws_profile
        )


def dassert_path_exists(
    path: str, aws_profile: Optional[AwsProfile] = None
) -> None:
    """
    Assert if S3 or local path doesn't exist. `aws_profile` is specified if and
    only if path is an S3 path.

    :param path: S3 or local path
    :param aws_profile: the name of an AWS profile or a s3fs filesystem
    """
    dassert_is_valid_aws_profile(path, aws_profile)
    if is_s3_path(path):
        s3fs_ = get_s3fs(aws_profile)
        hdbg.dassert(s3fs_.exists(path), f"S3 path '{path}' doesn't exist!")
    else:
        hdbg.dassert_path_exists(path)


def dassert_path_not_exists(
    path: str, aws_profile: Optional[AwsProfile] = None
) -> None:
    """
    Assert if S3 or local path exist. `aws_profile` is specified if and only if
    path is an S3 path.

    :param path: S3 or local path
    :param aws_profile: the name of an AWS profile or a s3fs filesystem
    """
    dassert_is_valid_aws_profile(path, aws_profile)
    if is_s3_path(path):
        s3fs_ = get_s3fs(aws_profile)
        hdbg.dassert(not s3fs_.exists(path), f"S3 path '{path}' already exist!")
    else:
        hdbg.dassert_path_not_exists(path)


# TODO(gp): Consider using `s3fs.split_path`.
def split_path(s3_path: str) -> Tuple[str, str]:
    """
    Separate an S3 path in the bucket and the rest of the path as absolute from
    the root.

    E.g., for `s3://alphamatic-data/tmp/hello` returns (`alphamatic-
    data`, /tmp/hello`)
    """
    dassert_is_s3_path(s3_path)
    # Remove the s3 prefix.
    prefix = "s3://"
    hdbg.dassert(s3_path.startswith(prefix))
    s3_path = s3_path[len(prefix) :]
    # Break the path into dirs.
    dirs = s3_path.split("/")
    bucket = dirs[0]
    abs_path = os.path.join("/", *dirs[1:])
    hdbg.dassert(
        abs_path.startswith("/"),
        "The path should be absolute instead of %s",
        abs_path,
    )
    return bucket, abs_path


def listdir(
    dir_name: str,
    pattern: str,
    only_files: bool,
    use_relative_paths: bool,
    *,
    exclude_git_dirs: bool = True,
    aws_profile: Optional[AwsProfile] = None,
    maxdepth: Optional[int] = None,
) -> List[str]:
    """
    Counterpart to `hio.listdir` with S3 support.

    :param dir_name: S3 or local path
    :param aws_profile: AWS profile to use if and only if using an S3 path,
        otherwise `None` for local path
    :param maxdepth: limit the depth of directory traversal
    """
    dassert_is_valid_aws_profile(dir_name, aws_profile)
    if is_s3_path(dir_name):
        s3fs_ = get_s3fs(aws_profile)
        dassert_path_exists(dir_name, s3fs_)
        # Ensure that there are no multiple stars in pattern.
        hdbg.dassert_not_in("**", pattern)
        # `hio.listdir` is using `find` which looks for files and directories
        # descending recursively in the directory.
        # One star in glob will use `maxdepth=1`.
        pattern = pattern.replace("*", "**")
        # Detailed S3 objects in dict form with metadata.
        path_objects = s3fs_.glob(
            f"{dir_name}/{pattern}", detail=True, maxdepth=maxdepth
        )
        if only_files:
            # Original `path_objects` must not be changed during loop.
            temp_path_objects = copy.deepcopy(list(path_objects.values()))
            # Use metadata to distinguish files from directories without
            # calling `s3fs_.isdir/isfile`.
            for path_object in temp_path_objects:
                if path_object["type"] != "file":
                    path_objects.pop(path_object["Key"])
        paths = list(path_objects.keys())
        if exclude_git_dirs:
            paths = [
                path for path in paths if ".git" not in pathlib.Path(path).parts
            ]
        bucket, absolute_path = split_path(dir_name)
        # Basically the goal is to remove `s3://` from the full S3 path.
        root_path = f"{bucket}{absolute_path}"
        # Remove redundant separators.
        paths = set([os.path.normpath(path) for path in paths])
        # Remove special entries such as `.` (`root_path` in this case) and
        # bucket name to keep the same return format as in `hio.listdir()`.
        paths_to_exclude = [bucket, root_path]
        paths = [path for path in paths if path not in paths_to_exclude]
        if use_relative_paths:
            paths = [os.path.relpath(path, start=root_path) for path in paths]
    else:
        paths = hio.listdir(
            dir_name,
            pattern,
            only_files,
            use_relative_paths,
            exclude_git_dirs=exclude_git_dirs,
            maxdepth=maxdepth,
        )
    return paths


def du(
    path: str,
    *,
    human_format: bool = False,
    aws_profile: Optional[AwsProfile] = None,
) -> Union[int, str]:
    """
    Counterpart to `hsystem.du` with S3 support.

    If and only if `aws_profile` is specified, S3 is used instead of
    local filesystem.
    """
    dassert_is_valid_aws_profile(path, aws_profile)
    if is_s3_path(path):
        s3fs_ = get_s3fs(aws_profile)
        dassert_path_exists(path, s3fs_)
        size: Union[int, str] = s3fs_.du(path)
        if human_format:
            size = hintros.format_size(size)
    else:
        size = hsystem.du(path, human_format=human_format)
    return size


def to_file(
    lines: str,
    file_name: str,
    *,
    mode: Optional[str] = None,
    force_flush: bool = False,
    aws_profile: Optional[AwsProfile] = None,
) -> None:
    """
    Counterpart to `hio.to_file` with S3 support.

    If and only if `aws_profile` is specified, S3 is used instead of
    local filesystem.
    """
    dassert_is_valid_aws_profile(file_name, aws_profile)
    if is_s3_path(file_name):
        # Ensure that `bytes` is used.
        if mode is not None and "b" not in mode:
            raise ValueError("S3 only allows binary mode!")
        hdbg.dassert_isinstance(lines, str)
        # Convert lines to bytes, only supported mode for S3.
        # Also create a list of new lines as raw bytes is not supported.
        os_sep = os.linesep
        lines_lst = [f"{line}{os_sep}".encode() for line in lines.split(os_sep)]
        # Inspect file name and path.
        hio.dassert_is_valid_file_name(file_name)
        s3fs_ = get_s3fs(aws_profile)
        mode = "wb" if mode is None else mode
        # Open S3 file. `rb` is the default mode for S3.
        with s3fs_.open(file_name, mode) as s3_file:
            if file_name.endswith((".gz", ".gzip")):
                # Open and decompress gzipped file.
                with gzip.GzipFile(fileobj=s3_file) as gzip_file:
                    gzip_file.writelines(lines_lst)
            else:
                # Any other file.
                s3_file.writelines(lines_lst)
            if force_flush:
                # TODO(Nikola): Investigate S3 alternative for `os.fsync(f.fileno())`.
                s3_file.flush()
    else:
        use_gzip = file_name.endswith((".gz", ".gzip"))
        hio.to_file(
            file_name,
            lines,
            mode=mode,
            use_gzip=use_gzip,
            force_flush=force_flush,
        )


def from_file(
    file_name: str,
    encoding: Optional[Any] = None,
    aws_profile: Optional[AwsProfile] = None,
) -> str:
    """
    Counterpart to `hio.from_file` with S3 support.

    If and only if `aws_profile` is specified, S3 is used instead of
    local filesystem.
    """
    dassert_is_valid_aws_profile(file_name, aws_profile)
    if is_s3_path(file_name):
        if encoding:
            raise ValueError("Encoding is not supported when reading from S3!")
        # Inspect file name and path.
        hio.dassert_is_valid_file_name(file_name)
        s3fs_ = get_s3fs(aws_profile)
        dassert_path_exists(file_name, s3fs_)
        # Open s3 file.
        with s3fs_.open(file_name) as s3_file:
            if file_name.endswith((".gz", ".gzip")):
                # Open and decompress gzipped file.
                with gzip.GzipFile(fileobj=s3_file) as gzip_file:
                    data = gzip_file.read().decode()
            else:
                # Any other file.
                data = s3_file.read().decode()
    else:
        data = hio.from_file(file_name, encoding=encoding)
    return data


# TODO(Nina): consider adding support for handling dirs.
# TODO(Grisha): consider extending for the regular file system.
def copy_file_to_s3(
    file_path: str,
    s3_dst_file_path: str,
    aws_profile: str,
) -> None:
    """
    Copy a local file to S3.

    :param file_path: path to a file to copy
    :param s3_dst_file_path: S3 path to copy to
    :param aws_profile: aws profile
    """
    hdbg.dassert_file_exists(file_path)
    dassert_is_s3_path(s3_dst_file_path)
    dassert_is_valid_aws_profile(s3_dst_file_path, aws_profile)
    aws_s3_cp_cmd = f"aws s3 cp {file_path} {s3_dst_file_path}"
    if not hserver.is_inside_ecs_container():
        # There is no `~/.aws/credentials` file inside an ECS container
        # but the AWS credentials are received via a task role. So
        # no need to pass the profile option.
        aws_s3_cp_cmd += f" --profile {aws_profile}"
    _LOG.info("Copying from %s to %s", file_path, s3_dst_file_path)
    hsystem.system(aws_s3_cp_cmd, suppress_output=False)


def get_local_or_s3_stream(
    file_name: str, **kwargs: Any
) -> Tuple[Union[s3fs.core.S3FileSystem, str], Any]:
    """
    Get S3 stream for desired file or simply returns file name.

    :param file_name: file name or full path to file
    """
    _LOG.debug(hprint.to_str("file_name kwargs"))
    # Handle the s3fs param, if needed.
    if is_s3_path(file_name):
        # For S3 files we need to have an `s3fs` parameter.
        hdbg.dassert_in(
            "s3fs",
            kwargs,
            "Credentials through s3fs are needed to access an S3 path",
        )
        s3fs_ = kwargs.pop("s3fs")
        hdbg.dassert_isinstance(s3fs_, s3fs.core.S3FileSystem)
        dassert_path_exists(file_name, s3fs_)
        stream = s3fs_.open(file_name)
    else:
        if "s3fs" in kwargs:
            _LOG.warning("Passed `s3fs` without an S3 file: ignoring it")
            _ = kwargs.pop("s3fs")
        hdbg.dassert_file_exists(file_name)
        stream = file_name
    return stream, kwargs


# #############################################################################
# Bucket
# #############################################################################


# TODO(Nikola): CmTask #1810 "Increase test coverage in helpers/hs3.py"
def get_s3_bucket_path(aws_profile: str, add_s3_prefix: bool = True) -> str:
    """
    Return the S3 bucket from environment variable corresponding to a given
    `aws_profile`.

    E.g., `aws_profile="am"` uses the value in `AM_AWS_S3_BUCKET` which
    is usually set to `s3://alphamatic-data`.
    """
    hdbg.dassert_type_is(aws_profile, str)
    prefix = aws_profile.upper()
    env_var = f"{prefix}_AWS_S3_BUCKET"
    if env_var in os.environ:
        _LOG.debug("No env var '%s'", env_var)
        s3_bucket = os.environ[env_var]
    else:
        # Fall-back to local credentials.
        _LOG.debug("Checking credentials")
        aws_credentials = get_aws_credentials(aws_profile)
        _LOG.debug("%s", aws_credentials)
        s3_bucket = aws_credentials.get("aws_s3_bucket", "")
    hdbg.dassert_ne(s3_bucket, "")
    hdbg.dassert(
        not s3_bucket.startswith("s3://"),
        "Invalid %s value '%s'",
        env_var,
        s3_bucket,
    )
    if add_s3_prefix:
        s3_bucket = "s3://" + s3_bucket
    return s3_bucket


# TODO(sonaal): Do we really need aws profile as argument or
# we can use default? Ref. https://github.com/cryptokaizen/cmamp/pull/6045#discussion_r1380392748
def get_s3_bucket_path_unit_test(
    aws_profile: str, *, add_s3_prefix: bool = True
) -> str:
    if aws_profile == "ck":
        s3_bucket = "cryptokaizen-unit-test"
    else:
        hdbg.dfatal(f"Invalid aws_profile={aws_profile}")
    if add_s3_prefix:
        s3_bucket = "s3://" + s3_bucket
    return s3_bucket


def get_latest_pq_in_s3_dir(s3_path: str, aws_profile: str) -> str:
    """
    Get the latest parquet file in the specified directory.

    :param s3_path: the path to s3 directory, e.g.
      `cryptokaizen-data/reorg/daily_staged.airflow.pq/bid_ask/crypto_chassis.downloaded_1sec/binance`
    :param aws_profile: AWS profile to use
    :return: the path to the latest parquet file in the directory,
      e.g. `cryptokaizen-data/reorg/daily_staged.airflow.pq/bid_ask/crypto_chassis.downloaded_1sec/binance/
       currency_pair=ETH_USDT/year=2022/month=12/data.parquet`
    """
    hdbg.dassert_type_is(aws_profile, str)
    s3fs_ = get_s3fs(aws_profile)
    pq_files = s3fs_.glob(f"{s3_path}/**.parquet", detail=True)
    # Sort the files by the date they were modified for the last time.
    sorted_files = sorted(
        pq_files.items(), key=lambda t: t[1]["LastModified"], reverse=True
    )
    # Get the path to the latest file.
    latest_file_path = sorted_files[0][0]
    return latest_file_path


# #############################################################################
# Parser.
# #############################################################################


def add_s3_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add the command line options for the AWS credentials.
    """
    parser.add_argument(
        "--aws_profile",
        action="store",
        type=str,
        help="The AWS profile to use for `.aws/credentials` or for env vars",
    )
    parser.add_argument(
        "--s3_path",
        action="store",
        type=str,
        default=None,
        help="Full S3 dir path to use (e.g., `s3://alphamatic-data/foobar/`), "
        "overriding any other setting",
    )
    return parser


def get_aws_profile(aws_profile: str) -> str:
    """
    Return the AWS profile to access S3, based on:

    - argument passed
    - command line option (i.e., `args.aws_profile`)
    - env vars (i.e., `AM_AWS_PROFILE`)
    """
    hdbg.dassert_type_is(aws_profile, str)
    prefix = aws_profile.upper()
    env_var = f"{prefix}_AWS_PROFILE"
    hdbg.dassert_in(env_var, os.environ)
    return os.environ[env_var]


def _get_aws_config(file_name: str) -> configparser.RawConfigParser:
    """
    Return a parser to the config in `~/.aws/{file_name]}`.
    """
    file_name = os.path.join(os.path.expanduser("~"), ".aws", file_name)
    hdbg.dassert_file_exists(file_name)
    # Read the config.
    config = configparser.RawConfigParser()
    config.read(file_name)
    _LOG.debug("config.sections=%s", config.sections())
    return config


def _dassert_all_env_vars_set(key_to_env_var: Dict[str, str]) -> None:
    """
    Check that the required AWS env vars are set and are not empty strings.
    """
    for v in key_to_env_var.values():
        hdbg.dassert_in(v, os.environ)
        hdbg.dassert_ne(v, "")


def _get_aws_file_text(key_to_env_var: Dict[str, str]) -> List[str]:
    """
    Generate text from env vars for AWS files.

    E.g.:
    ```
    aws_access_key_id=***
    aws_secret_access_key=***
    aws_s3_bucket=***
    ```

    :param key_to_env_var: aws settings names to the corresponding env
        var names mapping
    :return: AWS file text
    """
    txt = []
    for k, v in key_to_env_var.items():
        line = f"{k}={os.environ[v]}"
        txt.append(line)
    return txt


def _get_aws_config_text(aws_profile: str) -> str:
    """
    Generate text for the AWS config file, i.e. ".aws/config".
    """
    # Set which env vars we need to get.
    profile_prefix = aws_profile.upper()
    region_env_var = f"{profile_prefix}_AWS_DEFAULT_REGION"
    key_to_env_var = {"region": region_env_var}
    # Check that env vars are set.
    _dassert_all_env_vars_set(key_to_env_var)
    text = _get_aws_file_text(key_to_env_var)
    text.insert(0, f"[profile {aws_profile}]")
    text = "\n".join(text)
    return text


def _get_aws_credentials_text(aws_profile: str) -> str:
    """
    Generate text for the AWS credentials file, i.e. ".aws/credentials".
    """
    # Set which env vars we need to get.
    profile_prefix = aws_profile.upper()
    key_to_env_var = {
        "aws_access_key_id": f"{profile_prefix}_AWS_ACCESS_KEY_ID",
        "aws_secret_access_key": f"{profile_prefix}_AWS_SECRET_ACCESS_KEY",
        "aws_s3_bucket": f"{profile_prefix}_AWS_S3_BUCKET",
    }
    # Check that env vars are set.
    _dassert_all_env_vars_set(key_to_env_var)
    text = _get_aws_file_text(key_to_env_var)
    text.insert(0, f"[{aws_profile}]")
    text = "\n".join(text)
    return text


def generate_aws_files(
    home_dir: str = "~",
    aws_profiles: Optional[List[str]] = None,
) -> None:
    """
    Generate AWS configuration files.
    """
    if home_dir == "~":
        home_dir = os.path.expanduser(home_dir)
    config_file_name = os.path.join(home_dir, ".aws", "config")
    credentials_file_name = os.path.join(home_dir, ".aws", "credentials")
    if os.path.exists(credentials_file_name) and os.path.exists(config_file_name):
        # Ensure that both files exist.
        _LOG.info(
            "Both files exist: %s and %s; exiting",
            credentials_file_name,
            config_file_name,
        )
        return
    if aws_profiles is None:
        aws_profiles = ["am", "ck"]
    config_file_text = []
    credentials_file_text = []
    # Get text with settings for both files.
    for profile in aws_profiles:
        current_config_text = _get_aws_config_text(profile)
        config_file_text.append(current_config_text)
        current_credentials_text = _get_aws_credentials_text(profile)
        credentials_file_text.append(current_credentials_text)
    # Create both files.
    config_file_text = "\n\n".join(config_file_text)
    hio.to_file(config_file_name, config_file_text)
    _LOG.debug("Saved AWS config to %s", config_file_name)
    #
    credentials_file_text = "\n\n".join(credentials_file_text)
    hio.to_file(credentials_file_name, credentials_file_text)
    _LOG.debug("Saved AWS credentials to %s", credentials_file_name)


# #############################################################################
# Authentication.
# #############################################################################

# Architecture of the AWS authentication
#
# - There can be two or more AWS S3 systems with different credentials, paths to
#   bucket, and other properties
# - Some code needs to refer always and only to a specific S3 bucket
#   - E.g., AM S3 bucket for Kibot data
# - Other code needs to work with different AWS S3 systems
#   - E.g., `publish_notebooks`, saving / retrieving experiments, caching
#
# - The desired AWS S3 systems are selected through an `aws_profile` parameter
#   (e.g., `am`)
# - The value of AWS profile is obtained from
#   - the `--aws_profile` command line option; or
#   - a client specifying the needed `aws_profile`
#
# - The AWS profile is then used to access the `~/.aws` files and extract:
#   - the credentials (e.g., `aws_access_key_id`, `aws_secret_access_key`,
#     `aws_region`)
#   - other variables (e.g., `aws_s3_bucket`)
# - The variables that are extracted from the files are passed through env vars
#   directly for GitHub Actions CI
#   - One can specify env vars conditioned to different profiles using the AWS
#     profile
#   - E.g., `am` profile for `AWS_ACCESS_KEY_ID` corresponds to
#     `AM_AWS_ACCESS_KEY_ID`


@functools.lru_cache()
def get_aws_credentials(
    aws_profile: str,
) -> Dict[str, Optional[str]]:
    """
    Read the AWS credentials for a given profile from `~/.aws` or from env
    vars.

    :return: a dictionary with `access_key_id`, `aws_secret_access_key`,
        `aws_region` and optionally `aws_session_token`
    """
    _LOG.debug("Getting credentials for aws_profile='%s'", aws_profile)
    if aws_profile == "__mock__":
        # `mock` profile is artificial construct used only in tests.
        aws_profile = aws_profile.strip("__")
    profile_prefix = aws_profile.upper()
    result: Dict[str, Optional[str]] = {}
    key_to_env_var: Dict[str, str] = {
        "aws_access_key_id": f"{profile_prefix}_AWS_ACCESS_KEY_ID",
        "aws_secret_access_key": f"{profile_prefix}_AWS_SECRET_ACCESS_KEY",
        # TODO(gp): AWS_DEFAULT_REGION -> AWS_REGION so we can use the invariant
        #  that the var is simply the capitalized version of the key.
        "aws_region": f"{profile_prefix}_AWS_DEFAULT_REGION",
    }
    # If all the AWS credentials are passed through env vars, they override the
    # config file.
    env_var_override = False
    set_env_vars = [
        (env_var in os.environ and os.environ[env_var] != "")
        for env_var in sorted(key_to_env_var.values())
    ]
    if any(set_env_vars):
        if not all(set_env_vars):
            _LOG.warning(
                "Some but not all AWS env vars are set (%s): ignoring",
                str(set_env_vars),
            )
        else:
            env_var_override = True
    if env_var_override:
        _LOG.debug("Using AWS credentials from env vars")
        # If one variable is defined all should be defined.
        for key, env_var in key_to_env_var.items():
            _LOG.debug("'%s' in env vars=%s", env_var, env_var in os.environ)
            _LOG.debug(
                "'%s' != ''=%s", env_var, os.environ.get(env_var, None) != ""
            )
            hdbg.dassert_in(env_var, os.environ)
            result[key] = os.environ[env_var]
        # TODO(gp): We don't pass this through env var for now.
        result["aws_session_token"] = None
    else:
        _LOG.debug("Using AWS credentials from files")
        # > more ~/.aws/credentials
        # [am]
        # aws_access_key_id=AKI...
        # aws_secret_access_key=mhg..
        # aws_session_token = Fwo...
        file_name = "credentials"
        config = _get_aws_config(file_name)
        #
        key = "aws_access_key_id"
        result[key] = config.get(aws_profile, key)
        #
        key = "aws_secret_access_key"
        result[key] = config.get(aws_profile, key)
        #
        key = "aws_session_token"
        if config.has_option(aws_profile, key):
            result[key] = config.get(aws_profile, key)
        else:
            result[key] = None
        #
        key = "aws_s3_bucket"
        if config.has_option(aws_profile, key):
            result[key] = config.get(aws_profile, key)
        else:
            result[key] = None
        # > more ~/.aws/config
        # [am]
        # region = us-east-1
        file_name = "config"
        config = _get_aws_config(file_name)
        key = "aws_region"
        # For ~/.aws/config the tag is `profile am` instead of `am`.
        result[key] = config.get(f"profile {aws_profile}", "region")
    #
    hdbg.dassert_is_subset(key_to_env_var.keys(), result.keys())
    return result


# ///////////////////////////////////////////////////////////////////////////////


def get_s3fs(aws_profile: AwsProfile) -> s3fs.core.S3FileSystem:
    """
    Return a `s3fs` object from a given AWS profile.

    :param aws_profile: the name of an AWS profile or a s3fs filesystem
    """
    if hserver.is_ig_prod():
        # On IG prod machines we let the Docker container infer the right AWS
        # account.
        _LOG.warning("Not using AWS profile='%s'", aws_profile)
        s3fs_ = s3fs.core.S3FileSystem()
    else:
        if isinstance(aws_profile, str):
            # When deploying jobs via ECS the container obtains credentials
            # based on passed task role specified in the ECS task-definition,
            # refer to:
            # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html
            if aws_profile == "ck" and hserver.is_inside_ecs_container():
                _LOG.info("Fetching credentials from task IAM role")
                s3fs_ = s3fs.core.S3FileSystem()
            else:
                # From https://stackoverflow.com/questions/62562945
                aws_credentials = get_aws_credentials(aws_profile)
                _LOG.debug("%s", pprint.pformat(aws_credentials))
                s3fs_ = s3fs.core.S3FileSystem(
                    anon=False,
                    key=aws_credentials["aws_access_key_id"],
                    secret=aws_credentials["aws_secret_access_key"],
                    token=aws_credentials["aws_session_token"],
                    client_kwargs={"region_name": aws_credentials["aws_region"]},
                )
        elif isinstance(aws_profile, s3fs.core.S3FileSystem):
            s3fs_ = aws_profile
        else:
            raise ValueError(f"Invalid aws_profile='{aws_profile}'")
    return s3fs_


# #############################################################################
# Archive and retrieve data from S3.
# #############################################################################


# TODO(gp): -> helpers/aws_utils.py


def archive_data_on_s3(
    src_dir: str, s3_path: str, aws_profile: Optional[str], tag: str = ""
) -> str:
    """
    Compress dir `src_dir` and save it on AWS S3 under `s3_path`.

    A timestamp and a tag is added to make the name more informative.
    The tgz is created so that when expanded a dir with the name `src_dir` is
    created.

    :param src_dir: directory that will be compressed
    :param s3_path: full S3 path starting with `s3://`
    :param aws_profile: the profile to use. We use a string and not an
        `AwsProfile` since this is typically the outermost caller in the stack,
        and it doesn't reuse an S3 fs object
    :param tag: a tag to add to the name of the file
    """
    aws_profile = get_aws_profile(aws_profile)
    _LOG.info(
        "# Archiving '%s' to '%s' with aws_profile='%s'",
        src_dir,
        s3_path,
        aws_profile,
    )
    hdbg.dassert_dir_exists(src_dir)
    dassert_is_s3_path(s3_path)
    _LOG.info(
        "The size of '%s' is %s", src_dir, hsystem.du(src_dir, human_format=True)
    )
    # Add a timestamp if needed.
    dst_path = hsystem.append_timestamp_tag(src_dir, tag) + ".tgz"
    # Compress the dir.
    # > (cd .../TestRunExperimentArchiveOnS3.test_serial1; \
    #    tar cvzf /app/.../TestRunExperimentArchiveOnS3.test_serial1.tgz experiment.RH1E)
    # experiment.RH1E/
    # experiment.RH1E/log.20210802-123758.txt
    # experiment.RH1E/output_metadata.json
    # ...
    _LOG.debug("Destination path is '%s'", dst_path)
    with htimer.TimedScope(logging.INFO, "Compressing"):
        dir_name = os.path.dirname(src_dir)
        base_name = os.path.basename(src_dir)
        hdbg.dassert_ne(base_name, "", "src_dir=%s", src_dir)
        cmd = ""
        if dir_name != "":
            cmd += f"cd {dir_name} && "
        cmd += f"tar czf {dst_path} {base_name}"
        hsystem.system(cmd)
    _LOG.info(
        "The size of '%s' is %s",
        dst_path,
        hsystem.du(dst_path, human_format=True),
    )
    # Test expanding the tgz. The package should expand to the original dir.
    # > tar tf /app/.../TestRunExperimentArchiveOnS3.test_serial1.tgz
    # experiment.RH1E/
    # experiment.RH1E/log.20210802-123758.txt
    # experiment.RH1E/output_metadata.json
    _LOG.info("Testing archive")
    cmd = f"tar tvf {dst_path}"
    hsystem.system(cmd, log_level=logging.INFO, suppress_output=False)
    # Copy to S3.
    s3_file_path = os.path.join(s3_path, os.path.basename(dst_path))
    _LOG.info("Copying '%s' to '%s'", dst_path, s3_file_path)
    hdbg.dassert_file_exists(dst_path)
    s3fs_ = get_s3fs(aws_profile)
    # TODO(gp): Make sure the S3 dir exists.
    s3fs_.put(dst_path, s3_file_path)
    _LOG.info("Data archived on S3 to '%s'", s3_file_path)
    return s3_file_path


def copy_data_from_s3_to_local_dir(
    src_s3_dir: str, dst_local_dir: str, aws_profile: str
) -> None:
    """
    Copy data from S3 to a local dir.

    :param src_s3_dir: path on S3 storing the data to copy
    :param scratch_space_path: local path on scratch space
    :param aws_profile: AWS profile to use
    """
    _LOG.debug(
        "Copying input data from %s to %s",
        src_s3_dir,
        dst_local_dir,
    )
    cmd = f"aws s3 sync {src_s3_dir} {dst_local_dir} --profile {aws_profile}"
    hsystem.system(cmd, suppress_output=False, log_level="echo")


def retrieve_archived_data_from_s3(
    s3_file_path: str,
    dst_dir: str,
    aws_profile: Optional[str] = None,
    incremental: bool = True,
) -> str:
    """
    Retrieve tgz file from S3, unless it's already present (incremental mode).

    :param s3_file_path: path to the S3 file with the archived data. E.g.,
       `s3://.../experiment.20210802-121908.tgz`
    :param dst_dir: destination directory where to save the data
    :param aws_profile: the profile to use. We use a string and not an
        `AwsProfile` since this is typically the outermost caller in the stack,
        and it doesn't reuse an S3 fs object
    :param incremental: skip if the tgz file is already present locally
    :return: path with the local tgz file
    """
    aws_profile = get_aws_profile(aws_profile)
    _LOG.info(
        "# Retrieving archive from '%s' to '%s' with aws_profile='%s'",
        s3_file_path,
        dst_dir,
        aws_profile,
    )
    dassert_is_s3_path(s3_file_path)
    # Download the tgz file.
    hio.create_dir(dst_dir, incremental=True)
    dst_file = os.path.join(dst_dir, os.path.basename(s3_file_path))
    _LOG.debug(hprint.to_str("s3_file_path dst_dir dst_file"))
    if incremental and os.path.exists(dst_file):
        _LOG.warning("Found '%s': skipping downloading", dst_file)
    else:
        # Download.
        s3fs_ = get_s3fs(aws_profile)
        dassert_path_exists(s3_file_path, s3fs_)
        _LOG.debug("Getting from s3: '%s' -> '%s", s3_file_path, dst_file)
        s3fs_.get(s3_file_path, dst_file)
        _LOG.info("Saved to '%s'", dst_file)
    return dst_file


def expand_archived_data(src_tgz_file: str, dst_dir: str) -> str:
    """
    Expand an S3 tarball storing results of an experiment.

    E.g.,
    - given a tgz file like `s3://.../experiment.20210802-121908.tgz` (which is the
      result of compressing a dir like `/app/.../experiment.RH1E`)
    - expand it into a dir `{dst_dir}/experiment.RH1E`

    :param src_tgz_file: path to the local file with the archived data. E.g.,
       `/.../experiment.20210802-121908.tgz`
    :param dst_dir: directory where expand the archive tarball
    :return: dir with the expanded data (e.g., `{dst_dir/experiment.RH1E`)
    """
    _LOG.debug("Expanding '%s'", src_tgz_file)
    # Get the name of the including dir, e.g., `experiment.RH1E`.
    cmd = f"cd {dst_dir} && tar tzf {src_tgz_file} | head -1"
    rc, enclosing_tgz_dir_name = hsystem.system_to_one_line(cmd)
    _ = rc
    _LOG.debug(hprint.to_str("enclosing_tgz_dir_name"))
    tgz_dst_dir = os.path.join(dst_dir, enclosing_tgz_dir_name)

    if os.path.exists(tgz_dst_dir):
        hdbg.dassert_dir_exists(dst_dir)
        _LOG.info(
            "While expanding '%s' dst dir '%s' already exists: skipping",
            src_tgz_file,
            tgz_dst_dir,
        )
    else:
        # Expand the tgz file.
        # The output should be the original compressed dir under `{dst_dir}`.
        # E.g.,
        # > tar tzf /app/.../experiment.20210802-133901.tgz
        # experiment.RH1E/
        # experiment.RH1E/log.20210802-133859.txt
        # experiment.RH1E/result_0/
        with htimer.TimedScope(logging.INFO, "Decompressing"):
            hdbg.dassert_file_exists(src_tgz_file)
            cmd = f"cd {dst_dir} && tar xzf {src_tgz_file}"
            hsystem.system(cmd)
    hdbg.dassert_dir_exists(tgz_dst_dir)
    # Return `{dst_dir}/experiment.RH1E`.
    return tgz_dst_dir
