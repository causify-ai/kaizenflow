#!/usr/bin/env python
r"""
Create the new revision of ECS task definition and point image URL to the new
candidate image.

Use as:

# To create the new revision of `cmamp-test` task definition with `13538588e` image tag:
> aws_update_task_definition.py \
    --task_definition "cmamp-test" \
    --image_tag "13538588e"

Import as:

import im_v2.aws.aws_update_task_definition as iaautd
"""

import argparse
import logging
import re

import helpers.haws as haws
import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


def _update_task_definition(
    task_definition: str, image_tag: str, region: str
) -> None:
    """
    Create the new revision of specified ECS task definition and point Image
    URL specified to the new candidate image.

    :param task_definition: the name of the ECS task definition for
        which an update to container image URL is made, e.g. cmamp-test
    :param image_tag: the hash of the new candidate image, e.g.
        13538588e
    """
    old_image_url = haws.get_task_definition_image_url(
        task_definition, region=region
    )
    # Edit container version, e.g. cmamp:prod-12a45 - > cmamp:prod-12b46`
    new_image_url = re.sub("prod-(.+)$", f"prod-{image_tag}", old_image_url)
    haws.update_task_definition(task_definition, new_image_url, region=region)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-t",
        "--task_definition",
        type=str,
        help="the name of the ECS task definition to update",
    )
    parser.add_argument(
        "-i",
        "--image_tag",
        type=str,
        help="the hash of the new candidate image",
    )
    parser.add_argument(
        "-r",
        "--region",
        type=str,
        help="aws region",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _update_task_definition(args.task_definition, args.image_tag, args.region)


if __name__ == "__main__":
    _main(_parse())
