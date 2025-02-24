#!/usr/bin/env python
"""
Script to set batch of GitHub secrets from `.json` file in one go.

Simple usage:

> ./dev_scripts/github/set_secrets.py \
     --file 'dev_scripts/github/secrets.json' \
     --repo 'cryptomtc/cmamp_test'

The json file looks like:
```
{
    "GH_ACTION_ACCESS_TOKEN": "***",
    "AM_AWS_ACCESS_KEY_ID": "***",
    "AM_AWS_SECRET_ACCESS_KEY": "***",
    "AM_AWS_DEFAULT_REGION": "us-east-1",
    "AM_ECR_BASE_PATH": "***",
    "AM_AWS_S3_BUCKET": "alphamatic-data",
    "AM_TELEGRAM_TOKEN": "***",
    "CK_AWS_ACCESS_KEY_ID": "***",
    "CK_AWS_SECRET_ACCESS_KEY": "***",
    "CK_AWS_DEFAULT_REGION": "eu-north-1",
    "CK_AWS_S3_BUCKET": "ck-data",
    "CK_TELEGRAM_TOKEN": "***",
}
```
"""

import argparse
import logging
import pprint
import sys

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_verbosity_arg(parser)
    parser.add_argument(
        "--file",
        action="store",
        required=True,
        type=str,
        help="Location of `.json` file with desired secrets.",
    )
    parser.add_argument(
        "--repo",
        action="store",
        required=True,
        type=str,
        help="On which repository command will be applied.",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove batch of secrets from GitHub.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Print out the secrets and exits immediately.",
    )
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    secrets = hio.from_json(args.file)
    # Sort secrets.
    secrets = dict(sorted(secrets.items())).items()
    if args.dry_run:
        print(pprint.pformat(secrets))
        sys.exit(0)
    operation = "set" if not args.remove else "remove"
    for secret_key, secret_value in secrets:
        # GitHub does not accept empty strings.
        hdbg.dassert_ne(secret_value, "")
        cmd = [
            f"gh secret {operation} {secret_key}",
            f"--repo {args.repo}",
        ]
        if not args.remove:
            cmd.insert(1, f'--body "{secret_value}"')
        cmd = " ".join(cmd)
        rc = hsystem.system(cmd, abort_on_error=False)
        if rc != 0:
            _LOG.warning("cmd='%s' failed: continuing", cmd)
        else:
            _LOG.info("%s %s!", operation, secret_key)
    _LOG.info("All secrets are processed!")


if __name__ == "__main__":
    _main(_parse())
