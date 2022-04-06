"""
Import as:

import im_v2.common.data.client.data_frame_im_clients_example as imvcdcdfimce
"""


import im_v2.common.data.client.data_frame_im_clients as imvcdcdfimc
import core.finance.market_data_example as cfmadaex


def get_DataFrameImClient_example1() -> imvcdcdfimc.DataFrameImClient:
    """
    Build a `ImClient` backed by data stored in a dataframe.
    """
    # Generate input dataframe and universe for client initialization.
    universe = ["binance::BTC_USDT", "binance::ADA_USDT"]
    df = cfmadaex.get_im_client_market_data_df1(universe)
    # Init the client for testing.
    resample_1min = False
    im_client = imvcdcdfimc.DataFrameImClient(df, universe, resample_1min)
    return im_client
