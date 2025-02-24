# """
# Import as:
#
# import market_data_lime.ig_market_data_example as mdlemdaex
# """
#
# import asyncio
# import logging
# from typing import List, Optional, Union
#
# import helpers.hdatetime as hdateti
# import helpers.hpandas as hpandas
# import helpers.hs3 as hs3
# import im_lime.eg as imlimeg
# import market_data as mdata
# import market_data_lime.ig_real_time_market_data as mdlertmda
# import market_data_lime.ig_replayed_market_data as mdlermada
# import market_data_lime.ig_stitched_market_data as mdlesmada
# import vendors_lime.ig_credentials as vliegcre
#
# _LOG = logging.getLogger(__name__)
#
#
## #############################################################################
#
#
## TODO(gp): Add types.
# def get_IgRealTimeMarketData_example1(
#    asset_ids: List[int],
# ):
#    """
#    Build a `IgRealTimeMarketData` object using the RT market data DB.
#    """
#    # Build the RT market data interface.
#    account_type = "candidate"
#    db_connection = vliegcre.get_rt_db_connection(account_type)
#    market_data = mdlertmda.IgRealTimeMarketData(
#        db_connection,
#        asset_ids,
#    )
#    return market_data
#
#
## #############################################################################
#
#
# def get_IgReplayedMarketData_example1(
#    event_loop: Optional[asyncio.AbstractEventLoop],
#    *,
#    replayed_delay_in_mins_or_timestamp: Union[int, str] = 0,
# ) -> mdlermada.IgReplayedMarketData:
#    """
#    Build a `IgReplayedMarketData` using an S3 file with 10 stocks.
#    """
#    # This file was generated with:
#    # > pytest market_data_lime/test/test_ig_market_data.py::TestIgReplayedMarketData1::test_save_market_data1
#    # > aws s3 cp market_data.20220104-183252.csv.gz s3://
#    file_name = "s3://sasm/data/market_data.20220104-183252.csv.gz"
#    s3fs_ = hs3.get_s3fs(aws_profile="sasm")
#    # Load data
#    data = mdata.load_market_data(file_name, s3fs=s3fs_)
#    _LOG.debug("\n%s", hpandas.df_to_str(data.head()))
#    knowledge_datetime_col_name = "timestamp_db"
#    delay_in_secs = 0
#    asset_ids = [
#        17085,
#        13684,
#    ]
#    columns = "asset_id close start_time end_time timestamp_db volume".split()
#    market_data = mdlermada.IgReplayedMarketData(
#        file_name,
#        knowledge_datetime_col_name,
#        event_loop,
#        delay_in_secs,
#        replayed_delay_in_mins_or_timestamp,
#        asset_ids=asset_ids,
#        columns=columns,
#        s3fs=s3fs_,
#    )
#    return market_data
#
#
## #############################################################################
#
#
# def get_IgStitchedMarketData_example1(
#    asset_ids: List[int],
# ) -> mdlesmada.IgStitchedMarketData:
#    """
#    Build a `IgStitchedMarketData` object using:
#
#    - a RT market data DB
#    - an `ImClient` reading data from historical TAQ bar data in the native IG
#      format
#    """
#    # Build the RT market data interface.
#    ig_rt_market_data = get_IgRealTimeMarketData_example1(asset_ids)
#    # Build the historical IM client.
#    im_client = imlimeg.IgHistoricalPqByDateTaqBarClient()
#    # Stitch it together.
#    # We use a real time clock since there is RT market data.
#    event_loop = None
#    get_wall_clock_time = lambda: hdateti.get_current_time(
#        tz="ET", event_loop=event_loop
#    )
#    market_data = mdlesmada.IgStitchedMarketData(
#        asset_ids,
#        get_wall_clock_time,
#        ig_rt_market_data,
#        im_client,
#    )
#    return market_data
#
#
## #############################################################################
#
#
# def get_IgHistoricalMarketData_example1(
#    asset_ids: List[int],
#    *,
#    root_dir_name: str = "/cache/tiled.bar_data.all.2010_2022.20220204",
#    aws_profile: Optional[str] = None,
#    partition_mode: str = "by_year_month",
#    columns: Optional[List[str]] = None,
# ) -> mdata.ImClientMarketData:
#    """
#    Build a `ImClientMarketData` object using
#    `IgHistoricalPqByTileTaqBarClient` to read data from the tiled Parquet
#    data.
#    """
#    # /local/home/share/cache/tiled.bar_data.all.2010_2022.20220204
#    # - partitioned by month
#    # /local/home/share/cache/tiled.bar_data.top100.2010_2020
#    # - partitioned by month
#    # /local/home/share/cache/tiled.bar_data.all.2010.weekofyear
#    # - partitioned by week
#    # Build the historical IM client by-asset.
#    # root_dir_name = "/cache/tiled.bar_data.all.2010_2022.20220204"
#    # root_dir_name = None
#    im_client = imlimeg.IgHistoricalPqByTileTaqBarClient(
#        root_dir_name, aws_profile, partition_mode
#    )
#    # Build a `MarketData` with the IM client inside.
#    asset_id_col = "asset_id"
#    start_time_col_name = "start_ts"
#    end_time_col_name = "end_ts"
#    # TODO(gp): Pass a clock.
#    event_loop = None
#    get_wall_clock_time = lambda: hdateti.get_current_time(
#        tz="ET", event_loop=event_loop
#    )
#    # columns = None
#    # vendor_date  interval start_time ticker currency  open  close
#    # low  high  volume  notional  last_trade_time  all_day_volume
#    # all_day_notional  day_volume  day_notional  day_vol_prc_sqr  day_num_trade
#    # bid   ask  bid_size  ask_size  good_bid  good_ask  good_bid_size
#    # good_ask_size  day_spread  day_num_spread  day_low  day_high  last_trade
#    # last_trade_volume  bid_high  ask_high  bid_low  ask_low  sided_bid_count
#    # sided_bid_shares  sided_bid_notional  day_sided_bid_count
#    # day_sided_bid_shares  day_sided_bid_notional  sided_ask_count
#    # sided_ask_shares  sided_ask_notional  day_sided_ask_count
#    # day_sided_ask_shares  day_sided_ask_notional   asset_id  year month
#    # timestamp_db
#    if columns is None:
#        columns = "asset_id start_time close volume day_spread day_num_spread sided_bid_count sided_ask_count".split()
#    column_remap = None
#    market_data = mdata.ImClientMarketData(
#        asset_id_col,
#        asset_ids,
#        start_time_col_name,
#        end_time_col_name,
#        columns,
#        get_wall_clock_time,
#        im_client=im_client,
#        column_remap=column_remap,
#    )
#    return market_data
#
#
## TODO(gp): Add a test for each of these classes.
## TODO(gp): Add an example for IgHistoricalPqByDate
## TODO(gp): Can we move them to amp?
