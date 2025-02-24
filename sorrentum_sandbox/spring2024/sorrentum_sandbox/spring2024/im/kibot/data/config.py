"""
Import as:

import im.kibot.data.config as imkidacon
"""


import helpers.hs3 as hs3

ENDPOINT = "http://www.kibot.com/"

API_ENDPOINT = "http://api.kibot.com/"

AM_AWS_PROFILE = "am"
CK_AWS_PROFILE = "ck"


def get_s3_prefix(aws_profile: str):
    """
    Generate an S3 prefix based on an aws profile.

    Acceptable values: 'am', 'ck'.
    """
    try:
        if aws_profile == CK_AWS_PROFILE:
            s3_bucket = hs3.get_s3_bucket_path(
                CK_AWS_PROFILE, add_s3_prefix=False
            )
        elif aws_profile == AM_AWS_PROFILE:
            s3_bucket = hs3.get_s3_bucket_path(
                AM_AWS_PROFILE, add_s3_prefix=False
            )
        else:
            raise ValueError(f"Incorrect aws_profile={aws_profile}")
        s3_prefix = f"s3://{s3_bucket}/data/kibot"
    except AssertionError as e:
        import helpers.hserver as hserver

        # if hserver.is_dev4() or hserver.is_ig_prod():
        if hserver.is_ig_prod():
            # In IG prod we let the outside system control S3 and don't need Kibot,
            # so we ignore the assertion about S3 bucket being empty.
            pass
        else:
            raise e
    return s3_prefix


# This is needed only for some old lemonade tests.
S3_PREFIX = get_s3_prefix(AM_AWS_PROFILE)


DATASETS = [
    "adjustments",
    "all_stocks_1min",
    "all_stocks_unadjusted_1min",
    "all_stocks_daily",
    "all_stocks_unadjusted_daily",
    #
    "all_etfs_1min",
    "all_etfs_unadjusted_1min",
    "all_etfs_daily",
    "all_etfs_unadjusted_daily",
    #
    "all_forex_pairs_1min",
    "all_forex_pairs_daily",
    #
    "all_futures_contracts_1min",
    "all_futures_contracts_daily",
    # TODO(gp): -> tickbidask?
    "all_futures_continuous_contracts_tick",
    "all_futures_continuous_contracts_1min",
    "all_futures_continuous_contracts_daily",
    #
    "sp_500_tickbidask",
    "sp_500_unadjusted_tickbidask",
    "sp_500_1min",
    "sp_500_unadjusted_1min",
    "sp_500_daily",
    "sp_500_unadjusted_daily",
]
