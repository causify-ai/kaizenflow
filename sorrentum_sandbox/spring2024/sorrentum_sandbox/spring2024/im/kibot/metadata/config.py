"""
Import as:

import im.kibot.metadata.config as imkimecon
"""


import helpers.hs3 as hs3

_AWS_PROFILE = "ck"
# TODO(gp): Merge / reconcile S3_PREFIX in with im.kibot/data/config.py.
S3_BUCKET = hs3.get_s3_bucket_path_unit_test(_AWS_PROFILE, add_s3_prefix=False)
S3_PREFIX = f"s3://{S3_BUCKET}/alphamatic-data/data/kibot/metadata"

# TODO(amr): move common configs between data & metadata to
# `im.kibot.config`
ENDPOINT = "http://www.kibot.com/"
API_ENDPOINT = "http://api.kibot.com/"

TICKER_LISTS_SUB_DIR = "raw/ticker_lists"
ADJUSTMENTS_SUB_DIR = "raw/adjustments"
