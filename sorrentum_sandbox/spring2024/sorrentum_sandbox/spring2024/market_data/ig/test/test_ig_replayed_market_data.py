# import asyncio
# import logging
# import os
#
# import pandas as pd
# import pytest
#
# import helpers.hasyncio as hasynci
# import helpers.hdatetime as hdateti
# import helpers.hdbg as hdbg
# import helpers.hpandas as hpandas
# import helpers.hprint as hprint
# import helpers.hunit_test as hunitest
# import im_v2.ig.universe.ticker_igid_mapping as imviutigma
# import market_data as mdata
# import market_data_lime as mdlime
#
# _LOG = logging.getLogger(__name__)
#
#
## #############################################################################
#
#
# class TestIgReplayedMarketData1(hunitest.TestCase):
#    @pytest.mark.skip(reason="Run manually")
#    def test_save_market_data1(self) -> None:
#        """
#        Save data to disk from `IgRealTimeMarketData` for:
#
#        - 10 top IG ids
#        - a given period (e.g., `last_day`)
#        """
#        # Select the IG ids.
#        asset_ids = imviutigma.read_top_assets()[:10]
#        # asset_ids = [17085]
#        # Get the IG market data.
#        market_data = mdlime.get_IgRealTimeMarketData_example1(asset_ids)
#        hdbg.dassert(market_data.is_online())
#        # Save data.
#        timestamp = hdateti.get_current_timestamp_as_string(tz="ET")
#        file_name = f"market_data.{timestamp}.csv.gz"
#        timedelta = pd.Timedelta("1D")
#        limit = None
#        mdata.save_market_data(market_data, file_name, timedelta, limit)
#        _LOG.info("Written file '%s'", file_name)
#        # > aws s3 cp market_data.20220104-183252.csv.gz s3://data/
#
#
## #############################################################################
#
#
# class TestIgReplayedMarketData2(hunitest.TestCase):
#    """
#    - Build a `IgRealTimeMarketData`
#    - Save the data from it into a file
#    - Create a `IgReplayedMarketData` from the serialized data
#    - Run methods on the `IgReplayedMarketData` object without
#      checking the results since the values are always changing
#
#    We can run this test even if the RT DB is not on-line.
#    """
#
#    @staticmethod
#    def get_IgRealTimeMarketData() -> mdlime.IgReplayedMarketData:
#        asset_ids = [17085, 13684]
#        market_data = mdlime.get_IgRealTimeMarketData_example1(asset_ids)
#        return market_data
#
#    # //////////////////////////////////////////////////////////////////////////////
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
#    def get_IgReplayedMarketData(
#        self, market_data: mdlime.IgReplayedMarketData
#    ) -> mdlime.IgReplayedMarketData:
#        """
#        - Build a `IgRealTimeMarketData`
#        - Save the data from it into a file
#        - Create a `IgReplayedMarketData` from the serialized data
#        """
#        # - Save data from the `IgRealTimeMarketData`.
#        hprint.log_frame(_LOG, "IgRealTimeMarketData")
#        dir_name = self.get_scratch_space()
#        timestamp = hdateti.get_current_timestamp_as_string(tz="ET")
#        file_name = os.path.join(dir_name, f"market_data.{timestamp}.csv.gz")
#        timedelta = pd.Timedelta("1D")
#        limit = None
#        mdata.save_market_data(market_data, file_name, timedelta, limit)
#        _LOG.info("Written file '%s'", file_name)
#        # 3) Build a `IgReplayedMarketData`.
#        hprint.log_frame(_LOG, "IgReplayedMarketData")
#        # Read the data back.
#        # data = mdata.load_market_data(file_name)
#        # _LOG.debug("\n%s", hpandas.df_to_str(data))
#        # Build a `IgReplayedMarketData`.
#        knowledge_datetime_col_name = "timestamp_db"
#        event_loop = None
#        delay_in_secs = 0
#        replayed_delay_in_mins_or_timestamp = "last_timestamp"
#        asset_ids = market_data._asset_ids
#        columns = "asset_id close start_time end_time timestamp_db volume".split()
#        market_data = mdlime.IgReplayedMarketData(
#            file_name,
#            knowledge_datetime_col_name,
#            event_loop,
#            delay_in_secs,
#            replayed_delay_in_mins_or_timestamp,
#            asset_ids=asset_ids,
#            columns=columns,
#        )
#        return market_data
#
#    @pytest.mark.skip("Run manually")
#    def test_print_info_for_serialized_data1(self) -> None:
#        """
#        Read serialized data from `save_market_data()` and print some info.
#        """
#        file_name = "s3://data/market_data.20220104-183252.csv.gz"
#        import helpers.hs3 as hs3
#
#        s3fs_ = hs3.get_s3fs(aws_profile="sasm")
#        # Load data.
#        df = mdata.load_market_data(file_name, s3fs=s3fs_)
#        asset_ids = [17085, 13684]
#        mask = df["asset_id"].isin(asset_ids)
#        df = df[mask]
#        _LOG.debug(
#            "\n%s",
#            hpandas.df_to_str(
#                df, print_dtypes=True, print_shape_info=True, tag="df"
#            ),
#        )
#        _LOG.debug("\n%s", df.head(10).to_csv())
#
#    def test_round_trip1(self) -> None:
#        """
#        Execute the round-trip transformation.
#        """
#        market_data = self.get_IgRealTimeMarketData()
#        if mdata.skip_test_since_not_online(market_data):
#            pytest.skip("Market not on-line")
#        market_data = self.get_IgReplayedMarketData(market_data)
#        #
#        _ = market_data
#
#    def test_get_data1(self) -> None:
#        """
#        Call get_data() on the `IgReplayedMarketData`.
#        """
#        market_data = self.get_IgRealTimeMarketData()
#        if mdata.skip_test_since_not_online(market_data):
#            pytest.skip("Market not on-line")
#        market_data = self.get_IgReplayedMarketData(market_data)
#        #
#        timedelta = pd.Timedelta("10T")
#        hprint.log_frame(_LOG, "get_data:" + hprint.to_str("timedelta"))
#        df = market_data.get_data_for_last_period(
#            timedelta,
#        )
#        _LOG.debug("\n%s", hpandas.df_to_str(df))
#
#    def test_get_data_at_timestamp1(self) -> None:
#        market_data = self.get_IgRealTimeMarketData()
#        if mdata.skip_test_since_not_online(market_data):
#            pytest.skip("Market not on-line")
#        market_data = self.get_IgReplayedMarketData(market_data)
#        ts = market_data._df["end_time"].min()
#        self.get_data_at_timestamp_helper(market_data, ts)
#
#    def test_get_data_at_timestamp2(self) -> None:
#        market_data = self.get_IgRealTimeMarketData()
#        if mdata.skip_test_since_not_online(market_data):
#            pytest.skip("Market not on-line")
#        market_data = self.get_IgReplayedMarketData(market_data)
#        ts = market_data._df["end_time"].max()
#        self.get_data_at_timestamp_helper(market_data, ts)
#
#    # //////////////////////////////////////////////////////////////////////////////
#
#    def test_get_data_for_interval1(self) -> None:
#        market_data = self.get_IgRealTimeMarketData()
#        if mdata.skip_test_since_not_online(market_data):
#            pytest.skip("Market not on-line")
#        market_data = self.get_IgReplayedMarketData(market_data)
#        end_ts = market_data._df["end_time"].max()
#        start_ts = end_ts - pd.DateOffset(minutes=5)
#        # start_ts = data["end_time"].min()
#        ts_col_name = "start_time"
#        asset_ids = None
#        hprint.log_frame(
#            _LOG,
#            "get_data_for_interval:"
#            + hprint.to_str("start_ts end_ts ts_col_name asset_ids"),
#        )
#        df = market_data.get_data_for_interval(
#            start_ts,
#            end_ts,
#            ts_col_name,
#            asset_ids,
#        )
#        _LOG.debug("\n%s", hpandas.df_to_str(df))
#
#
## #############################################################################
#
#
# class TestIgReplayedMarketData3(hunitest.TestCase):
#    """
#    - Build a `IgReplayedMarketData` with data frozen on S3
#    - Test the methods
#    """
#
#    def get_data_helper(
#        self,
#        market_data,
#        get_wall_clock_time,
#        exp_wall_clock_time: str,
#        exp_get_data: str,
#    ) -> None:
#        wall_clock_time = get_wall_clock_time()
#        self.assert_equal(str(wall_clock_time), exp_wall_clock_time)
#        # - get_data(normalize=False)
#        timedelta = pd.Timedelta("10T")
#        tag = "get_data: " + hprint.to_str("wall_clock_time timedelta")
#        hprint.log_frame(_LOG, tag)
#        df = market_data.get_data_for_last_period(
#            timedelta,
#        )
#        act = hpandas.df_to_str(df, print_shape_info=True, tag=tag)
#        self.assert_equal(act, exp_get_data, dedent=True, fuzzy_match=True)
#
#    async def get_data_coroutine(self, event_loop) -> None:
#        # Build a `IgReplayedMarketData`.
#        hprint.log_frame(_LOG, "IgReplayedMarketData")
#        market_data = mdlime.get_IgReplayedMarketData_example1(event_loop)
#        if mdata.skip_test_since_not_online(market_data):
#            return
#        get_wall_clock_time = market_data.get_wall_clock_time
#        # We are at the beginning of the data.
#        exp_wall_clock_time = "2022-01-04 09:00:00-05:00"
#        # Since the clock is at the beginning of the day there is no data.
#        exp_get_data = r"""
#        # get_data: wall_clock_time=Timestamp('2022-01-04 09:00:00-0500', tz='America/New_York'), timedelta='10T', normalize_data=True=
#        shape=(0, 5)
#        Empty DataFrame
#        Columns: [asset_id, close, start_time, timestamp_db, volume]
#        Index: []"""
#        self.get_data_helper(
#            market_data,
#            get_wall_clock_time,
#            exp_wall_clock_time,
#            exp_get_data,
#        )
#        # - Wait 5 mins.
#        await asyncio.sleep(5 * 60)
#        exp_wall_clock_time = "2022-01-04 09:05:00-05:00"
#        exp_get_data = r"""
#        # get_data: wall_clock_time=Timestamp('2022-01-04 09:05:00-0500', tz='America/New_York'), timedelta='10T', normalize_data=True=
#        index=[2022-01-04 09:01:00-05:00, 2022-01-04 09:04:00-05:00]
#        columns=asset_id,close,start_time,timestamp_db,volume
#        shape=(8, 5)
#                                    asset_id  close                start_time                     timestamp_db  volume
#        end_time
#        2022-01-04 09:01:00-05:00  13684    NaN 2022-01-04 09:00:00-05:00 2022-01-04 09:01:05.142177-05:00       0
#        2022-01-04 09:01:00-05:00  17085    NaN 2022-01-04 09:00:00-05:00 2022-01-04 09:01:05.142177-05:00       0
#        2022-01-04 09:02:00-05:00  13684    NaN 2022-01-04 09:01:00-05:00 2022-01-04 09:02:02.832066-05:00       0
#        ...
#        2022-01-04 09:03:00-05:00  17085    NaN 2022-01-04 09:02:00-05:00 2022-01-04 09:03:02.977737-05:00       0
#        2022-01-04 09:04:00-05:00  13684    NaN 2022-01-04 09:03:00-05:00 2022-01-04 09:04:02.892229-05:00       0
#        2022-01-04 09:04:00-05:00  17085    NaN 2022-01-04 09:03:00-05:00 2022-01-04 09:04:02.892229-05:00       0"""
#        self.get_data_helper(
#            market_data,
#            get_wall_clock_time,
#            exp_wall_clock_time,
#            exp_get_data,
#        )
#
#        # TODO(gp): Add tests also for this.
#        # # - get_data()
#        # normalize_data = True
#        # tag = "get_data:" + hprint.to_str("period normalize_data")
#        # hprint.log_frame(_LOG, tag)
#        # df = market_data.get_data(period, normalize_data=normalize_data)
#        # act = hpandas.df_to_str(df, print_shape_info=True, tag=tag)
#        # exp = ""
#        # self.assert_equal(act, exp)
#        # #
#        # ts = data["end_time"].max()
#        # normalize_data = False
#        # hprint.log_frame(_LOG, "get_data_at_timestamp:" + hprint.to_str("ts normalize_data"))
#        # df = market_data.get_data_at_timestamp(ts, normalize_data=normalize_data)
#        # _LOG.debug("\n%s", hpandashpandashpandashpandashpandashpandashpandashpandas.df_to_str(df))
#        # #
#        # normalize_data = True
#        # hprint.log_frame(_LOG, "get_data_at_timestamp:" + hprint.to_str("ts normalize_data"))
#        # df = market_data.get_data_at_timestamp(ts, normalize_data=normalize_data)
#        # _LOG.debug("\n%s", hpandas.df_to_str(df))
#        # #
#        # ts = data["end_time"].min()
#        # normalize_data = False
#        # hprint.log_frame(_LOG, "get_data_at_timestamp:" + hprint.to_str("ts normalize_data"))
#        # df = market_data.get_data_at_timestamp(ts, normalize_data=normalize_data)
#        # _LOG.debug("\n%s", hpandas.df_to_str(df))
#        # #
#        # normalize_data = True
#        # hprint.log_frame(_LOG, "get_data_at_timestamp:" + hprint.to_str("ts normalize_data"))
#        # df = market_data.get_data_at_timestamp(ts, normalize_data=normalize_data)
#        # _LOG.debug("\n%s", hpandas.df_to_str(df))
#        # #
#        # end_ts = data["end_time"].min()
#        # start_ts = end_ts - pd.DateOffset(minutes=5)
#        # ts_col_name = "start_time"
#        # normalize_data = False
#        # hprint.log_frame(_LOG, "get_data_for_timestamp:" + hprint.to_str("start_ts end_ts normalize_data"))
#        # df = market_data.get_data_at_timestamp(ts, start_ts, end_ts, ts_col_name, normalize_data=normalize_data)
#        # _LOG.debug("\n%s", hpandas.df_to_str(df))
#        # #
#        # normalize_data = True
#        # hprint.log_frame(_LOG, "get_data_for_timestamp:" + hprint.to_str("start_ts end_ts normalize_data"))
#        # df = market_data.get_data_at_timestamp(ts, start_ts, end_ts, ts_col_name,
#        #                                                  normalize_data=normalize_data)
#        # _LOG.debug("\n%s", hpandas.df_to_str(df))
#
#    def test_get_data1(self) -> None:
#        with hasynci.solipsism_context() as event_loop:
#            coroutine = self.get_data_coroutine(event_loop)
#            hasynci.run(coroutine, event_loop=event_loop)
