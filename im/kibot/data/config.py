"""
Import as:

import im.kibot.data.config as imkidacon
"""


import helpers.hs3 as hs3

ENDPOINT = "http://www.kibot.com/"

API_ENDPOINT = "http://api.kibot.com/"

AM_AWS_PROFILE = "am"
# TODO(gp): Inline this reference everywhere, if needed.
try:
    S3_BUCKET = hs3.get_s3_bucket_path(AM_AWS_PROFILE, add_s3_prefix=False)
    S3_PREFIX = f"s3://{S3_BUCKET}/data/kibot"
except AssertionError as e:
    import helpers.hserver as hserver

    #if hserver.is_dev4() or hserver.is_ig_prod():
    if hserver.is_ig_prod():
        # In IG prod we let the outside system control S3 and don't need Kibot,
        # so we ignore the assertion about S3 bucket being empty.
        pass
    else:
        raise e


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
