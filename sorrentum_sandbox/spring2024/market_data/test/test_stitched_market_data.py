import logging

import pandas as pd
import pytest

import helpers.henv as henv
import market_data as mdata
import market_data.market_data_example as mdmadaex

# import market_data_lime.ig_market_data_example as mdlemdaex
# import market_data_lime.ig_stitched_market_data as mdlesmada

_LOG = logging.getLogger(__name__)


@pytest.mark.skipif(
    not henv.execute_repo_config_code("is_CK_S3_available()"),
    reason="Run only if CK S3 is available",
)
class TestStitchedMarketData1(mdata.MarketData_get_data_TestCase):
    """
    For all the test methods see description of corresponding private method in
    the parent class.
    """

    @pytest.mark.superslow("~30 seconds by GH actions.")
    def test_get_data_for_interval5(self) -> None:
        # Prepare inputs.
        asset_ids = [1467591036, 1464553467]
        universe_version1 = "v4"
        data_snapshot1 = "20220707"
        #
        market_data = mdmadaex.get_CryptoChassis_BidAskOhlcvMarketData_example1(
            asset_ids,
            universe_version1,
            data_snapshot1,
        )
        start_ts = pd.Timestamp("2022-05-01T00:00:00+00:00")
        end_ts = pd.Timestamp("2022-05-01T00:30:00+00:00")
        #
        expected_length = 58
        expected_column_names = [
            "ask_price",
            "ask_size",
            "asset_id",
            "bid_price",
            "bid_size",
            "close",
            "full_symbol",
            "high",
            "knowledge_timestamp",
            "low",
            "number_of_trades",
            "open",
            "start_ts",
            "twap",
            "volume",
            "vwap",
        ]
        expected_column_unique_values = {
            "full_symbol": ["binance::BTC_USDT", "binance::ETH_USDT"]
        }
        # pylint: disable=line-too-long
        exp_df_as_str = r"""
        # df=
        index=[2022-04-30 20:01:00-04:00, 2022-04-30 20:29:00-04:00]
        columns=asset_id,full_symbol,open,high,low,close,volume,vwap,number_of_trades,twap,knowledge_timestamp,start_ts,bid_price,bid_size,ask_price,ask_size
        shape=(58, 16)
                                    asset_id        full_symbol      open      high       low     close    volume        vwap  number_of_trades        twap              knowledge_timestamp                  start_ts     bid_price  bid_size     ask_price  ask_size
        end_ts
        2022-04-30 20:01:00-04:00  1464553467  binance::ETH_USDT   2726.62   2727.16   2724.99   2725.59   648.179   2725.8408               618   2725.7606 2022-06-20 09:49:40.140622+00:00 2022-04-30 20:00:00-04:00   2725.493716  1035.828   2725.731107  1007.609
        2022-04-30 20:01:00-04:00  1467591036  binance::BTC_USDT  37635.00  37635.60  37603.70  37626.80   168.216  37619.4980              1322  37619.8180 2022-06-20 09:48:46.910826+00:00 2022-04-30 20:00:00-04:00  37620.402680   120.039  37622.417898   107.896
        2022-04-30 20:02:00-04:00  1464553467  binance::ETH_USDT   2725.59   2730.42   2725.59   2730.04  1607.265   2728.7821              1295   2728.3652 2022-06-20 09:49:40.140622+00:00 2022-04-30 20:01:00-04:00   2728.740700   732.959   2728.834137  1293.961
        ...
        2022-04-30 20:28:00-04:00  1467591036  binance::BTC_USDT  37617.30  37636.10  37609.00  37630.00  175.641  37620.1890               889  37621.0910 2022-06-20 09:48:46.910826+00:00 2022-04-30 20:27:00-04:00  37616.416796   205.573  37621.741608   105.712
        2022-04-30 20:29:00-04:00  1464553467  binance::ETH_USDT   2727.11   2727.45   2725.74   2725.75  854.813   2726.4297               604   2726.5467 2022-06-20 09:49:40.140622+00:00 2022-04-30 20:28:00-04:00   2726.427932   801.267   2726.375710  1457.017
        2022-04-30 20:29:00-04:00  1467591036  binance::BTC_USDT  37630.00  37630.10  37608.60  37612.10  128.965  37615.0390               800  37615.9640 2022-06-20 09:48:46.910826+00:00 2022-04-30 20:28:00-04:00  37616.943055    57.059  37617.898140   118.408
        """
        # pylint: enable=line-too-long
        # Run.
        self._test_get_data_for_interval5(
            market_data,
            start_ts,
            end_ts,
            asset_ids,
            expected_length,
            expected_column_names,
            expected_column_unique_values,
            exp_df_as_str,
        )

    def test_is_online1(self) -> None:
        self.assertTrue(True)


# class TestIgStitchedMarketData1(hunitest.TestCase):
#     def df_stats_to_str(self, df: pd.DataFrame) -> str:
#         txt = []
#         txt.append("min_date=%s" % df.index.min())
#         txt.append("max_date=%s" % df.index.max())
#         hdbg.dassert_in("asset_id", df.columns)
#         txt.append("asset_id=%s" % ",".join(map(str, df["asset_id"].unique())))
#         return "\n".join(txt)
#
#     def test_get_data_for_last_period1(self) -> None:
#         """
#         Get the data for the last 2 days for one EG id.
#         """
#         # TODO(gp): This test fails on Mondays. We need to extend the code to
#         #  support business days.
#         if datetime.date.today().weekday() == 0:
#             pytest.skip("Skip on Mondays")
#         asset_ids = [17085]
#         eg_stitched_market_data = mdlemdaex.get_IgStitchedMarketData_example1(
#             asset_ids
#         )
#         if mdata.skip_test_since_not_online(eg_stitched_market_data):
#             pytest.skip("Market not on-line")
#         # Query.
#         # timedelta = pd.tseries.offsets.BDay(2)
#         timedelta = pd.Timedelta("2D")
#         df = eg_stitched_market_data.get_data_for_last_period(timedelta)
#         _LOG.debug(hpandas.df_to_str(df, print_shape_info=True, tag="df"))
#         #
#         _LOG.info("result:\n%s", self.df_stats_to_str(df))
#
#     # TODO(gp): This is due to the slowdown in accessing S3 data.
#     @pytest.mark.superslow("20s")
#     def test_get_data_for_last_period2(self) -> None:
#         """
#         Get the data for the last 10 days for one EG id.
#         """
#         # TODO(gp): This test fails on Mondays. We need to extend the code to
#         #  support business days.
#         if datetime.date.today().weekday() == 0:
#             pytest.skip("Skip on Mondays")
#         asset_ids = [17085]
#         eg_stitched_market_data = mdlemdaex.get_IgStitchedMarketData_example1(
#             asset_ids
#         )
#         if mdata.skip_test_since_not_online(eg_stitched_market_data):
#             pytest.skip("Market not on-line")
#         # Query.
#         timedelta = pd.Timedelta("10D")
#         df = eg_stitched_market_data.get_data_for_last_period(timedelta)
#         _LOG.debug(hpandas.df_to_str(df, print_shape_info=True, tag="df"))
#         #
#         _LOG.info("result:\n%s", self.df_stats_to_str(df))
#
#     @pytest.mark.slow("20s")
#     def test_get_data_for_last_period3(self) -> None:
#         """
#         Get the data for the last 2 days for two EG ids.
#         """
#         # TODO(gp): This test fails on Mondays. We need to extend the code to
#         #  support business days.
#         if datetime.date.today().weekday() == 0:
#             pytest.skip("Skip on Mondays")
#         asset_ids = [17085, 13684]
#         eg_stitched_market_data = mdlemdaex.get_IgStitchedMarketData_example1(
#             asset_ids
#         )
#         if mdata.skip_test_since_not_online(eg_stitched_market_data):
#             pytest.skip("Market not on-line")
#         # Query.
#         # timedelta = pd.tseries.offsets.BDay(2)
#         timedelta = pd.Timedelta("2D")
#         df = eg_stitched_market_data.get_data_for_last_period(timedelta)
#         _LOG.debug(hpandas.df_to_str(df, print_shape_info=True, tag="df"))
#         #
#         _LOG.info("result:\n%s", self.df_stats_to_str(df))
#
#     @pytest.mark.slow("20s")
#     def test_get_data_for_last_period_compare1(self) -> None:
#         """
#         Retrieve 2 days worth of data from the RT market data and from the
#         stitched market data and compare it.
#         """
#         # TODO(gp): This test fails on Mondays. We need to extend the code to
#         #  support business days.
#         if datetime.date.today().weekday() == 0:
#             pytest.skip("Skip on Mondays")
#         asset_ids = [17085]
#         # Build the RT market data interface.
#         eg_rt_market_data = mdlemdaex.get_IgRealTimeMarketData_example1(asset_ids)
#         if mdata.skip_test_since_not_online(eg_rt_market_data):
#             pytest.skip("Market not on-line")
#         #
#         eg_stitched_market_data = mdlemdaex.get_IgStitchedMarketData_example1(
#             asset_ids
#         )
#         dst_dir = self.get_scratch_space()
#         # Query.
#         # timedelta = pd.tseries.offsets.BDay(2)
#         timedelta = pd.Timedelta("2D")
#         rt_df = eg_rt_market_data.get_data_for_last_period(timedelta)
#         rt_df.index = rt_df.index.tz_convert("America/New_York")
#         stitched_df = eg_stitched_market_data.get_data_for_last_period(timedelta)
#         stitched_df.index = stitched_df.index.tz_convert("America/New_York")
#         # Reorder the columns.
#         rt_df = mdlesmada.normalize_rt_df(rt_df)
#         # TODO(gp): Disabled due to missing `timestamp_db` in the historical flow.
#         # hdbg.dassert_set_eq(rt_df.columns, stitched_df.columns)
#         columns = sorted(rt_df)
#         rt_df = rt_df[columns]
#         stitched_df = stitched_df[columns]
#         # Save info for df_rt.
#         rt_df_as_str = hpandas.df_to_str(
#             rt_df, print_shape_info=True, tag="rt_df"
#         )
#         hio.to_file(os.path.join(dst_dir, "rt_df.txt"), rt_df_as_str)
#         rt_df.to_csv(os.path.join(dst_dir, "rt_df.csv"))
#         _LOG.debug("%s", rt_df_as_str)
#         # Save info for stitched_df.
#         stitched_df_as_str = hpandas.df_to_str(
#             stitched_df, print_shape_info=True, tag="stitched_df"
#         )
#         hio.to_file(os.path.join(dst_dir, "stitched_df.txt"), stitched_df_as_str)
#         stitched_df.to_csv(os.path.join(dst_dir, "stitched_df.csv"))
#         _LOG.debug("%s", stitched_df_as_str)
#         #
#         script_file_name = os.path.join(dst_dir, "/tmp.compare_stitched.sh")
#         txt = []
#         txt.append("vimdiff %s/rt_df.txt %s/stitched_df.txt" % (dst_dir, dst_dir))
#         txt.append("vimdiff %s/rt_df.csv %s/stitched_df.csv" % (dst_dir, dst_dir))
#         script_txt = "\n".join(txt)
#         hio.create_executable_script(script_file_name, script_txt)
#         _LOG.info("Compare with:\n%s", script_file_name)
