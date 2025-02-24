# import asyncio
# import logging
#
# import pandas as pd
# import pytest
#
# import helpers.hdatetime as hdateti
# import helpers.hpandas as hpandas
# import helpers.hprint as hprint
# import helpers.hunit_test as hunitest
# import market_data_lime.ig_market_data_example as mdlemdaex
# import market_data_lime.ig_real_time_market_data as mdlertmda
#
# _LOG = logging.getLogger(__name__)
#
#
## #############################################################################
#
#
## TODO(gp): Use MarketDataTestCase
# class TestIgHistoricalMarketData1(hunitest.TestCase):
#    def test_should_be_online1(self) -> None:
#        asset_ids = [17085]
#        market_data = mdlemdaex.get_IgHistoricalMarketData_example1(asset_ids)
#
#    @staticmethod
#    def get_data_at_timestamp_helper(market_data, ts) -> None:
#        ts_col_name = "end_time"
#        asset_ids = None
#        hprint.log_frame(
#            _LOG,
#            "get_data_at_timestamp:" + hprint.to_str("ts ts_col_name asset_ids"),
#        )
#        df = market_data.get_data_at_timestamp(
#            ts,
#            ts_col_name,
#            asset_ids,
#        )
#        _LOG.debug("\n%s", hpandas.df_to_str(df))
#
#    # def test_get_data_at_timestamp1(self) -> None:
#    #     asset_ids = [17085]
#    #     market_data = mdlemdaex.get_IgHistoricalMarketData_example1(asset_ids)
#    #     timedelta = pd.Timedelta("1W")
#    #     df = market_data.get_data_for_last_period(timedelta)
#    #     print(df)
#
#    def test_get_data_at_timestamp1(self) -> None:
#        asset_ids = [17085]
#        root_dir_name = "/cache/tiled.bar_data.all.2010.weekofyear"
#        partition_mode = "by_year_week"
#        market_data = mdlemdaex.get_IgHistoricalMarketData_example1(
#            asset_ids, root_dir_name=root_dir_name,
#            partition_mode=partition_mode
#        )
#        start_ts = pd.Timestamp("2020-12-01 09:31:00+00:00")
#        end_ts = pd.Timestamp("2020-12-02 09:31:00+00:00")
#        # The knowledge time is the index, which is equal to `end_time`.
#        ts_col_name = "end_time"
#        df = market_data.get_data_for_interval(
#            start_ts, end_ts, ts_col_name, asset_ids
#        )
#        print(df)
