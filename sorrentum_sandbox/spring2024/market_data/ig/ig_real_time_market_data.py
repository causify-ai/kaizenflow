# """
# Import as:
#
# import market_data_lime.ig_real_time_market_data as mdlertmda
# """
#
# import datetime
# import logging
# from typing import List
#
# import pandas as pd
#
# import helpers.hdatetime as hdateti
# import market_data as mdata
#
# _LOG = logging.getLogger(__name__)
#
#
## #############################################################################
#
#
# def ig_db_should_be_online(current_time: pd.Timestamp) -> bool:
#    """
#    The IG RT system is on-line between 9:00 ET and 16:38 ET when the US market
#    is open.
#    """
#    # TODO(gp): We should add a trading calendar. For now we use business days
#    #  as proxy.
#    hdateti.dassert_has_ET_tz(current_time)
#    _LOG.info("current_time_ET=%s", current_time)
#    is_business_day = bool(
#        len(pd.bdate_range(current_time.date(), current_time.date()))
#    )
#    is_online_ = is_business_day and (
#        datetime.time(9, 0) <= current_time.time() <= datetime.time(16, 38)
#    )
#    return is_online_
#
#
## #############################################################################
## IgRealTimeMarketData
## #############################################################################
#
#
# class IgRealTimeMarketData(mdata.RealTimeMarketData):
#    """
#    Connect to the actual IG RT DB.
#    """
#
#    def __init__(
#        self,
#        db_connection,
#        asset_ids: List[int],
#    ):
#        table_name = "bars_qa"
#        where_clause = "interval=60 AND region='AM'"
#        # SPY.
#        valid_id = 17085
#        asset_id_col = "asset_id"
#        start_time_col_name = "start_time"
#        end_time_col_name = "end_time"
#        # Real-time columns.
#        columns = [
#            start_time_col_name,
#            end_time_col_name,
#            asset_id_col,
#            "close",
#            "volume",
#            "timestamp_db",
#            "bid_price",
#            "ask_price",
#            "bid_num_trade",
#            "ask_num_trade",
#            "day_spread",
#            "day_num_spread",
#        ]
#        # Rename columns from real-time fields to historical fields.
#        column_remap = {
#            # TODO(gp): Some pipelines call volume "vol", which could be
#            # confused with volatility. We should be explicit and call it
#            # "volume".
#            # "volume": "vol",
#            "ask_price": "good_ask",
#            "bid_price": "good_bid",
#            "bid_num_trade": "sided_bid_count",
#            "ask_num_trade": "sided_ask_count",
#        }
#        event_loop = None
#        get_wall_clock_time = lambda: hdateti.get_current_time(
#            tz="ET", event_loop=event_loop
#        )
#        super().__init__(
#            db_connection,
#            table_name,
#            where_clause,
#            valid_id,
#            #
#            asset_id_col,
#            asset_ids,
#            start_time_col_name,
#            end_time_col_name,
#            columns,
#            get_wall_clock_time,
#            column_remap=column_remap,
#        )
#
#    def should_be_online(self, current_time: pd.Timestamp) -> bool:
#        _ = self
#        return ig_db_should_be_online(current_time)
