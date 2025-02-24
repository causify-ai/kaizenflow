import logging

try:
    pass
except ModuleNotFoundError:
    print("Can't find ib_insync")
import pandas as pd
import pytest

import im.ib.data.extract.gateway.test.utils as iidegt

_LOG = logging.getLogger(__name__)


@pytest.mark.skip(reason="CmTask666")
class Test_get_historical_data(iidegt.IbExtractionTest):
    def test_save_historical_data_with_IB_loop1(self) -> None:
        # 2021-02-17 is a Wednesday and it's full day.
        start_ts = pd.Timestamp("2021-02-17 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=1)
        bar_size_setting = "1 hour"
        use_rth = False
        (
            df,
            short_signature,
            long_signature,
        ) = self._save_historical_data_with_IB_loop_helper(
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
