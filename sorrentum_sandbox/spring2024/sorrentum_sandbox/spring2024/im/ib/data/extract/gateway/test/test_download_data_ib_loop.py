import logging

try:
    pass
except ModuleNotFoundError:
    print("Can't find ib_insync")
import pandas as pd
import pytest

import helpers.hdbg as hdbg
import im.ib.data.extract.gateway.download_data_ib_loop as imidegddil
import im.ib.data.extract.gateway.test.utils as iidegt
import im.ib.data.extract.gateway.utils as imidegaut

_LOG = logging.getLogger(__name__)


@pytest.mark.skip(reason="CmTask666")
class Test_get_historical_data(iidegt.IbExtractionTest):
    def test_ib_loop_generator1(self) -> None:
        """
        Test getting 1 hr data for 1 full day.
        """
        # 2021-02-17 is a Wednesday and it's full day.
        start_ts = pd.Timestamp("2021-02-17 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=1)
        bar_size_setting = "1 hour"
        (
            df,
            short_signature,
            long_signature,
        ) = self._ib_loop_generator_helper(start_ts, end_ts, bar_size_setting)
        #
        act = "\n".join(map(str, df.index))
        # NOTE: IB returns also a bar at close 16:30 even if the frequency is hourly.
        exp = """
        2021-02-17 00:00:00-05:00
        2021-02-17 01:00:00-05:00
        2021-02-17 02:00:00-05:00
        2021-02-17 03:00:00-05:00
        2021-02-17 04:00:00-05:00
        2021-02-17 05:00:00-05:00
        2021-02-17 06:00:00-05:00
        2021-02-17 07:00:00-05:00
        2021-02-17 08:00:00-05:00
        2021-02-17 09:00:00-05:00
        2021-02-17 10:00:00-05:00
        2021-02-17 11:00:00-05:00
        2021-02-17 12:00:00-05:00
        2021-02-17 13:00:00-05:00
        2021-02-17 14:00:00-05:00
        2021-02-17 15:00:00-05:00
        2021-02-17 16:00:00-05:00
        2021-02-17 16:30:00-05:00
        2021-02-17 18:00:00-05:00
        2021-02-17 19:00:00-05:00
        2021-02-17 20:00:00-05:00
        2021-02-17 21:00:00-05:00
        2021-02-17 22:00:00-05:00
        2021-02-17 23:00:00-05:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        #
        exp_short_signature = """
        signature=len=24 [2021-02-17 00:00:00-05:00, 2021-02-17 23:00:00-05:00]
        min_max_df=
                        min       max
        2021-02-17  00:00:00  23:00:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_ib_loop_generator2(self) -> None:
        """
        Test getting 1 hr data for a part of a day.
        """
        # 2021-02-17 is a Wednesday and it's full day.
        start_ts = pd.Timestamp("2021-02-17 13:00:00")
        end_ts = start_ts + pd.DateOffset(hours=3)
        bar_size_setting = "1 hour"
        (
            df,
            short_signature,
            long_signature,
        ) = self._ib_loop_generator_helper(start_ts, end_ts, bar_size_setting)
        #
        act = "\n".join(map(str, df.index))
        # NOTE: IB returns also a bar at close 16:30 even if the frequency is hourly.
        exp = """
        2021-02-17 13:00:00-05:00
        2021-02-17 14:00:00-05:00
        2021-02-17 15:00:00-05:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        #
        exp_short_signature = """
        signature=len=3 [2021-02-17 13:00:00-05:00, 2021-02-17 15:00:00-05:00]
        min_max_df=
                        min       max
        2021-02-17  13:00:00  15:00:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_get_historical_data_with_IB_loop1(self) -> None:
        """
        Test getting 1 hr data for 1 full day.
        """
        # 2021-02-17 is a Wednesday and it's full day.
        start_ts = pd.Timestamp("2021-02-17 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=1)
        bar_size_setting = "1 hour"
        use_rth = False
        (
            df,
            short_signature,
            long_signature,
        ) = self._get_historical_data_with_IB_loop_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        #
        act = "\n".join(map(str, df.index))
        # NOTE: IB returns also a bar at close 16:30 even if the frequency is hourly.
        exp = """
        2021-02-17 00:00:00-05:00
        2021-02-17 01:00:00-05:00
        2021-02-17 02:00:00-05:00
        2021-02-17 03:00:00-05:00
        2021-02-17 04:00:00-05:00
        2021-02-17 05:00:00-05:00
        2021-02-17 06:00:00-05:00
        2021-02-17 07:00:00-05:00
        2021-02-17 08:00:00-05:00
        2021-02-17 09:00:00-05:00
        2021-02-17 10:00:00-05:00
        2021-02-17 11:00:00-05:00
        2021-02-17 12:00:00-05:00
        2021-02-17 13:00:00-05:00
        2021-02-17 14:00:00-05:00
        2021-02-17 15:00:00-05:00
        2021-02-17 16:00:00-05:00
        2021-02-17 16:30:00-05:00
        2021-02-17 18:00:00-05:00
        2021-02-17 19:00:00-05:00
        2021-02-17 20:00:00-05:00
        2021-02-17 21:00:00-05:00
        2021-02-17 22:00:00-05:00
        2021-02-17 23:00:00-05:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        #
        exp_short_signature = """
        signature=len=24 [2021-02-17 00:00:00-05:00, 2021-02-17 23:00:00-05:00]
        min_max_df=
                        min       max
        2021-02-17  00:00:00  23:00:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_get_historical_data_with_IB_loop2(self) -> None:
        """
        Like test_get_historical_data_with_IB_loop1() but for 1 regular trading
        day.
        """
        # 2021-02-17 is a Wednesday and it's full day.
        start_ts = pd.Timestamp("2021-02-17 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=1)
        bar_size_setting = "1 hour"
        use_rth = True
        (
            df,
            short_signature,
            long_signature,
        ) = self._get_historical_data_with_IB_loop_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        #
        act = "\n".join(map(str, df.index))
        exp = r"""
        2021-02-17 09:30:00-05:00
        2021-02-17 10:00:00-05:00
        2021-02-17 11:00:00-05:00
        2021-02-17 12:00:00-05:00
        2021-02-17 13:00:00-05:00
        2021-02-17 14:00:00-05:00
        2021-02-17 15:00:00-05:00
        2021-02-17 16:00:00-05:00
        2021-02-17 16:30:00-05:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        #
        exp_short_signature = """
        signature=len=9 [2021-02-17 09:30:00-05:00, 2021-02-17 16:30:00-05:00]
        min_max_df=
                        min      max
        2021-02-17 09:30:00 16:30:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_get_historical_data_with_IB_loop3(self) -> None:
        """
        Test getting 1 hr data for 1 full days.

        Data is returned for the entire day for both days.
        """
        # 2021-02-18 is a Thursday and it's full day.
        start_ts = pd.Timestamp("2021-02-17 00:00:00").tz_localize(
            tz="America/New_York"
        )
        end_ts = start_ts + pd.DateOffset(days=1)
        bar_size_setting = "1 hour"
        use_rth = False
        (
            _,
            short_signature,
            long_signature,
        ) = self._get_historical_data_with_IB_loop_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        #
        exp_short_signature = """
        signature=len=24 [2021-02-17 00:00:00-05:00, 2021-02-17 23:00:00-05:00]
        min_max_df=
                         min       max
        2021-02-17  00:00:00  23:00:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_get_historical_data_with_IB_loop4(self) -> None:
        """
        Test getting 1 hr data for 1 RTH days.

        Data is returned for the regular trading session for both days.
        """
        # 2021-02-18 is a Thursday and it's full day.
        start_ts = pd.Timestamp("2021-02-17 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=1)
        bar_size_setting = "1 hour"
        use_rth = True
        (
            df,
            short_signature,
            long_signature,
        ) = self._get_historical_data_with_IB_loop_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        #
        exp_short_signature = """
        signature=len=9 [2021-02-17 09:30:00-05:00, 2021-02-17 16:30:00-05:00]
        min_max_df=
                         min       max
        2021-02-17  09:30:00  16:30:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_get_historical_data_with_IB_loop5(self) -> None:
        """
        Test getting 1 hr data for a day when the market is closed.
        """
        # 2021-02-15 is a Monday and there is no trading activity since it's MLK day.
        start_ts = pd.Timestamp("2021-02-15 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=1)
        bar_size_setting = "1 hour"
        use_rth = False
        (
            df,
            short_signature,
            long_signature,
        ) = self._get_historical_data_with_IB_loop_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        #
        # act = ("\n".join(map(str, df.index)))
        # exp = r"""
        # """
        # self.assert_equal(act, exp, fuzzy_match=True)
        #
        exp_short_signature = """
        signature=len=19 [2021-02-15 00:00:00-05:00, 2021-02-15 23:00:00-05:00]
        min_max_df=
                         min       max
        2021-02-15  00:00:00  23:00:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_get_historical_data_with_IB_loop6(self) -> None:
        """
        Test getting 1 hr data when the market is open.
        """
        # 2021-02-07 is a Sunday.
        start_ts = pd.Timestamp("2021-02-07 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=2)
        bar_size_setting = "1 hour"
        use_rth = False
        (
            df,
            short_signature,
            long_signature,
        ) = self._get_historical_data_with_IB_loop_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        #
        act = "\n".join(map(str, df.index))
        exp = r"""
        2021-02-07 18:00:00-05:00
        2021-02-07 19:00:00-05:00
        2021-02-07 20:00:00-05:00
        2021-02-07 21:00:00-05:00
        2021-02-07 22:00:00-05:00
        2021-02-07 23:00:00-05:00
        2021-02-08 00:00:00-05:00
        2021-02-08 01:00:00-05:00
        2021-02-08 02:00:00-05:00
        2021-02-08 03:00:00-05:00
        2021-02-08 04:00:00-05:00
        2021-02-08 05:00:00-05:00
        2021-02-08 06:00:00-05:00
        2021-02-08 07:00:00-05:00
        2021-02-08 08:00:00-05:00
        2021-02-08 09:00:00-05:00
        2021-02-08 10:00:00-05:00
        2021-02-08 11:00:00-05:00
        2021-02-08 12:00:00-05:00
        2021-02-08 13:00:00-05:00
        2021-02-08 14:00:00-05:00
        2021-02-08 15:00:00-05:00
        2021-02-08 16:00:00-05:00
        2021-02-08 16:30:00-05:00
        2021-02-08 18:00:00-05:00
        2021-02-08 19:00:00-05:00
        2021-02-08 20:00:00-05:00
        2021-02-08 21:00:00-05:00
        2021-02-08 22:00:00-05:00
        2021-02-08 23:00:00-05:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        #
        exp_short_signature = """
        signature=len=30 [2021-02-07 18:00:00-05:00, 2021-02-08 23:00:00-05:00]
        min_max_df=
                         min       max
        2021-02-07  18:00:00  23:00:00
        2021-02-08  00:00:00  23:00:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_get_historical_data_with_IB_loop7(self) -> None:
        """
        Test getting 1hr data on Sunday when the market is open half day.
        """
        # 2021-02-07 is Sunday.
        start_ts = pd.Timestamp("2021-02-07 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=1)
        bar_size_setting = "1 min"
        use_rth = False
        (
            df,
            short_signature,
            long_signature,
        ) = self._get_historical_data_with_IB_loop_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        #
        exp_short_signature = """
        signature=len=360 [2021-02-07 18:00:00-05:00, 2021-02-07 23:59:00-05:00]
        min_max_df=
                        min      max
        2021-02-07 18:00:00 23:59:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)

    def test_download_ib_data1(self) -> None:
        target = "continuous_futures"
        frequency = "hour"
        use_rth = False
        symbols = "ES".split()
        currency = "USD"
        start_ts = pd.Timestamp("2020-12-09 18:00:00-05:00")
        end_ts = pd.Timestamp("2020-12-13 18:00:00-05:00")
        tasks = imidegaut.get_tasks(
            ib=self.ib,
            target=target,
            frequency=frequency,
            currency=currency,
            symbols=symbols,
            start_ts=start_ts,
            end_ts=end_ts,
            use_rth=use_rth,
        )
        #
        client_id_base = 5
        #
        num_threads = "serial"
        dst_dir = self.get_scratch_space()
        incremental = False
        file_names = imidegddil.download_ib_data(
            client_id_base, tasks, incremental, dst_dir, num_threads
        )
        hdbg.dassert_eq(len(file_names), 1)
        _LOG.debug("file_names=%s", file_names)
        # Load the data.
        df = imidegddil.load_historical_data(file_names[0])
        short_signature, long_signature = self.get_df_signatures(df)
        exp_short_signature = """
        signature=len=48 [2020-12-09 18:00:00-05:00, 2020-12-11 16:30:00-05:00]
        min_max_df=
                        min      max
        2020-12-09 18:00:00 23:00:00
        2020-12-10 00:00:00 23:00:00
        2020-12-11 00:00:00 16:30:00
        """
        self.assert_equal(short_signature, exp_short_signature, fuzzy_match=True)
        #
        self.check_string(long_signature)
