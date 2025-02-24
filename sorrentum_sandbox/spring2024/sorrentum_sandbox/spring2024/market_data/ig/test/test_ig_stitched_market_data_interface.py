# import datetime
# import logging
# import os
#
# import pandas as pd
# import pytest
#
# import helpers.hdbg as hdbg
# import helpers.hio as hio
# import helpers.hpandas as hpandas
# import helpers.hsystem as hsystem
# import helpers.hunit_test as hunitest
# import market_data as mdata
# import market_data_lime.ig_market_data_example as mdlemdaex
# import market_data_lime.ig_stitched_market_data as mdlesmada
#
# _LOG = logging.getLogger(__name__)
#
#
# class TestIgStitchedMarketData1(hunitest.TestCase):
#    def df_stats_to_str(self, df: pd.DataFrame) -> str:
#        txt = []
#        txt.append("min_date=%s" % df.index.min())
#        txt.append("max_date=%s" % df.index.max())
#        hdbg.dassert_in("asset_id", df.columns)
#        txt.append("asset_id=%s" % ",".join(map(str, df["asset_id"].unique())))
#        return "\n".join(txt)
#
#    def test_get_data_for_last_period1(self) -> None:
#        """
#        Get the data for the last 2 days for one IG id.
#        """
#        # TODO(gp): This test fails on Mondays. We need to extend the code to
#        #  support business days.
#        if datetime.date.today().weekday() == 0:
#            pytest.skip("Skip on Mondays")
#        asset_ids = [17085]
#        ig_stitched_market_data = mdlemdaex.get_IgStitchedMarketData_example1(
#            asset_ids
#        )
#        if mdata.skip_test_since_not_online(ig_stitched_market_data):
#            pytest.skip("Market not on-line")
#        # Query.
#        # timedelta = pd.tseries.offsets.BDay(2)
#        timedelta = pd.Timedelta("2D")
#        df = ig_stitched_market_data.get_data_for_last_period(timedelta)
#        _LOG.debug(hpandas.df_to_str(df, print_shape_info=True, tag="df"))
#        #
#        _LOG.info("result:\n%s", self.df_stats_to_str(df))
#
#    # TODO(gp): This is due to the slowdown in accessing S3 data.
#    @pytest.mark.superslow("20s")
#    def test_get_data_for_last_period2(self) -> None:
#        """
#        Get the data for the last 10 days for one IG id.
#        """
#        # TODO(gp): This test fails on Mondays. We need to extend the code to
#        #  support business days.
#        if datetime.date.today().weekday() == 0:
#            pytest.skip("Skip on Mondays")
#        asset_ids = [17085]
#        ig_stitched_market_data = mdlemdaex.get_IgStitchedMarketData_example1(
#            asset_ids
#        )
#        if mdata.skip_test_since_not_online(ig_stitched_market_data):
#            pytest.skip("Market not on-line")
#        # Query.
#        timedelta = pd.Timedelta("10D")
#        df = ig_stitched_market_data.get_data_for_last_period(timedelta)
#        _LOG.debug(hpandas.df_to_str(df, print_shape_info=True, tag="df"))
#        #
#        _LOG.info("result:\n%s", self.df_stats_to_str(df))
#
#    @pytest.mark.slow("20s")
#    def test_get_data_for_last_period3(self) -> None:
#        """
#        Get the data for the last 2 days for two IG ids.
#        """
#        # TODO(gp): This test fails on Mondays. We need to extend the code to
#        #  support business days.
#        if datetime.date.today().weekday() == 0:
#            pytest.skip("Skip on Mondays")
#        asset_ids = [17085, 13684]
#        ig_stitched_market_data = mdlemdaex.get_IgStitchedMarketData_example1(
#            asset_ids
#        )
#        if mdata.skip_test_since_not_online(ig_stitched_market_data):
#            pytest.skip("Market not on-line")
#        # Query.
#        # timedelta = pd.tseries.offsets.BDay(2)
#        timedelta = pd.Timedelta("2D")
#        df = ig_stitched_market_data.get_data_for_last_period(timedelta)
#        _LOG.debug(hpandas.df_to_str(df, print_shape_info=True, tag="df"))
#        #
#        _LOG.info("result:\n%s", self.df_stats_to_str(df))
#
#    @pytest.mark.slow("20s")
#    def test_get_data_for_last_period_compare1(self) -> None:
#        """
#        Retrieve 2 days worth of data from the RT market data and from the
#        stitched market data and compare it.
#        """
#        # TODO(gp): This test fails on Mondays. We need to extend the code to
#        #  support business days.
#        if datetime.date.today().weekday() == 0:
#            pytest.skip("Skip on Mondays")
#        asset_ids = [17085]
#        # Build the RT market data interface.
#        ig_rt_market_data = mdlemdaex.get_IgRealTimeMarketData_example1(asset_ids)
#        if mdata.skip_test_since_not_online(ig_rt_market_data):
#            pytest.skip("Market not on-line")
#        #
#        ig_stitched_market_data = mdlemdaex.get_IgStitchedMarketData_example1(
#            asset_ids
#        )
#        dst_dir = self.get_scratch_space()
#        # Query.
#        # timedelta = pd.tseries.offsets.BDay(2)
#        timedelta = pd.Timedelta("2D")
#        rt_df = ig_rt_market_data.get_data_for_last_period(timedelta)
#        rt_df.index = rt_df.index.tz_convert("America/New_York")
#        stitched_df = ig_stitched_market_data.get_data_for_last_period(timedelta)
#        stitched_df.index = stitched_df.index.tz_convert("America/New_York")
#        # Reorder the columns.
#        rt_df = mdlesmada.normalize_rt_df(rt_df)
#        # TODO(gp): Disabled due to missing `timestamp_db` in the historical flow.
#        # hdbg.dassert_set_eq(rt_df.columns, stitched_df.columns)
#        columns = sorted(rt_df)
#        rt_df = rt_df[columns]
#        stitched_df = stitched_df[columns]
#        # Save info for df_rt.
#        rt_df_as_str = hpandas.df_to_str(
#            rt_df, print_shape_info=True, tag="rt_df"
#        )
#        hio.to_file(os.path.join(dst_dir, "rt_df.txt"), rt_df_as_str)
#        rt_df.to_csv(os.path.join(dst_dir, "rt_df.csv"))
#        _LOG.debug("%s", rt_df_as_str)
#        # Save info for stitched_df.
#        stitched_df_as_str = hpandas.df_to_str(
#            stitched_df, print_shape_info=True, tag="stitched_df"
#        )
#        hio.to_file(os.path.join(dst_dir, "stitched_df.txt"), stitched_df_as_str)
#        stitched_df.to_csv(os.path.join(dst_dir, "stitched_df.csv"))
#        _LOG.debug("%s", stitched_df_as_str)
#        #
#        script_file_name = os.path.join(dst_dir, "/tmp.compare_stitched.sh")
#        txt = []
#        txt.append("vimdiff %s/rt_df.txt %s/stitched_df.txt" % (dst_dir, dst_dir))
#        txt.append("vimdiff %s/rt_df.csv %s/stitched_df.csv" % (dst_dir, dst_dir))
#        script_txt = "\n".join(txt)
#        hio.create_executable_script(script_file_name, script_txt)
#        _LOG.info("Compare with:\n%s", script_file_name)
