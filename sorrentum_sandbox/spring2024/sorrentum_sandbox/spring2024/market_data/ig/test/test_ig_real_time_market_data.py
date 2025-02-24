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
# class TestIgRealTimeMarketData1(hunitest.TestCase):
#    def test_should_be_online1(self) -> None:
#        """
#        Check that the IG RT DB is on-line when it should be.
#
#        This can have false positives.
#        """
#        asset_ids = [17085]
#        market_data = mdlemdaex.get_IgRealTimeMarketData_example1(asset_ids)
#        #
#        current_time = hdateti.get_current_time(tz="ET")
#        should_be_online = market_data.should_be_online(current_time)
#        is_online = market_data.is_online()
#        _LOG.debug(hprint.to_str("current_time should_be_online is_online"))
#        self.assertEqual(is_online, should_be_online)
#
#
## #############################################################################
#
#
# class TestIgRealTimeMarketData2(hunitest.TestCase):
#    def test_sql_get_query1(self) -> None:
#        """
#        Check the SQL query to get data.
#        """
#        asset_ids = [17085]
#        market_data = mdlemdaex.get_IgRealTimeMarketData_example1(asset_ids)
#        #
#        columns = "asset_id last_price start_time end_time timestamp_db".split()
#        start_ts = pd.Timestamp("2021-09-24 19:42:49-05:00")
#        end_ts = None
#        ts_col_name = "start_datetime"
#        left_close = True
#        right_close = False
#        sort_time = True
#        limit = None
#        query = market_data._get_sql_query(
#            columns,
#            start_ts,
#            end_ts,
#            ts_col_name,
#            asset_ids,
#            left_close,
#            right_close,
#            sort_time,
#            limit,
#        )
#        # expected = ("SELECT asset_id,last_price,start_time,end_time,timestamp_db " +
#        #    "FROM bars_qa WHERE interval=60 AND region='AM' AND asset_id=17085 AND " +
#        #    "start_time >= '2021-09-24 19:42:49' ORDER BY end_time DESC LIMIT 5")
#        _LOG.info("-> query=%s", query)
#        # TODO(gp): Enable this.
#        if False:
#            regex = (
#                "SELECT asset_id,last_price,start_time,end_time,timestamp_db "
#                + "FROM bars_qa WHERE interval=60 AND region='AM' AND asset_id=17085 AND "
#                + "start_time >= '.*' AND start_time < '.*' "
#                "ORDER BY end_time DESC LIMIT 5"
#            )
#            self.assertRegex(query, regex)
#
#    def get_data_helper(
#        self,
#        timedelta: pd.Timedelta,
#    ) -> None:
#        asset_ids = [17085]
#        market_data = mdlemdaex.get_IgRealTimeMarketData_example1(asset_ids)
#        limit = None
#        df = market_data.get_data_for_last_period(timedelta, limit=limit)
#        _LOG.info("-> " + hpandas.df_to_str(df, print_shape_info=True, tag="df"))
#        # Check: if the DB is online then we should get back some data.
#        if self._should_skip_check(market_data):
#            return
#        self.assertGreaterEqual(df.shape[0], 1)
#
#    def test_get_data1(self) -> None:
#        """
#        Get the last 5 minutes of data with dataflow processing.
#        """
#        timedelta = pd.Timedelta("5T")
#        self.get_data_helper(timedelta)
#
#    def test_get_data3(self) -> None:
#        """
#        Get the last day of data with dataflow processing.
#        """
#        timedelta = pd.Timedelta("1D")
#        self.get_data_helper(timedelta)
#
#    # ////////////////////////////////////////////////////////////////////////
#
#    def test_is_online1(self) -> None:
#        asset_ids = [17085]
#        market_data = mdlemdaex.get_IgRealTimeMarketData_example1(asset_ids)
#        current_time = hdateti.get_current_time(tz="ET")
#        is_online = market_data.is_online()
#        _LOG.info("-> current_time=%s is_online=%s", current_time, is_online)
#
#    def test_get_last_end_time1(self) -> None:
#        asset_ids = [17085]
#        market_data = mdlemdaex.get_IgRealTimeMarketData_example1(asset_ids)
#        last_end_time = market_data.get_last_end_time()
#        _LOG.info("-> last_end_time=%s", last_end_time)
#
#    @pytest.mark.slow("Up to a minute")
#    def test_get_last_end_time2(self) -> None:
#        asset_ids = [17085]
#        market_data = mdlemdaex.get_IgRealTimeMarketData_example1(asset_ids)
#        if self._should_skip_check(market_data):
#            return
#        get_current_time = lambda: hdateti.get_current_time(tz="ET")
#        current_time = get_current_time()
#        _LOG.debug("current_time=%s", current_time)
#        start_time, end_time, num_iter = asyncio.run(
#            market_data.wait_for_latest_data()
#        )
#        _LOG.info(hprint.to_str("start_time end_time num_iter"))
#        _ = start_time, end_time, num_iter
#
#    # ////////////////////////////////////////////////////////////////////////
#
#    @staticmethod
#    def _should_skip_check(
#        market_data: mdlertmda.IgRealTimeMarketData,
#    ) -> bool:
#        """
#        Check that if the DB is online then we get back some data.
#        """
#        current_time = hdateti.get_current_time(tz="ET")
#        if not market_data.should_be_online(current_time):
#            _LOG.warning("The DB should not be online: skipping check")
#            return True
#        if not market_data.is_online():
#            _LOG.warning("The DB is not online: skipping check")
#            return True
#        return False
