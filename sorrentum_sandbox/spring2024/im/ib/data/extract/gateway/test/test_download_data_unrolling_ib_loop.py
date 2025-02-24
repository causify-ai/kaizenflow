import logging

try:
    pass
except ModuleNotFoundError:
    print("Can't find ib_insync")
import pandas as pd
import pytest

import im.ib.data.extract.gateway.test.utils as iidegt
import im.ib.data.extract.gateway.unrolling_download_data_ib_loop as imideguddil

_LOG = logging.getLogger(__name__)


@pytest.mark.skip(reason="CmTask666")
class Test_get_historical_data(iidegt.IbExtractionTest):
    def test_get_historical_data1(self) -> None:
        """
        Test getting 1 hr data for 3 days.
        """
        start_ts = pd.Timestamp("2021-02-07 00:00:00")
        end_ts = start_ts + pd.DateOffset(days=3)
        bar_size_setting = "1 hour"
        use_rth = False
        #
        self._compare_historical_data(bar_size_setting, start_ts, end_ts, use_rth)

    def test_get_historical_data2(self) -> None:
        """
        Test getting 1 hr data for 4 days.
        """
        start_ts = pd.Timestamp("2021-02-07 18:00:00")
        end_ts = start_ts + pd.DateOffset(days=4)
        bar_size_setting = "1 hour"
        use_rth = True
        #
        self._compare_historical_data(bar_size_setting, start_ts, end_ts, use_rth)

    def test_get_historical_data3(self) -> None:
        """
        Test getting 1 hr data for 3 days.
        """
        start_ts = pd.Timestamp("2021-02-08 09:00:00")
        end_ts = start_ts + pd.DateOffset(days=3)
        bar_size_setting = "1 hour"
        use_rth = True
        #
        self._compare_historical_data(bar_size_setting, start_ts, end_ts, use_rth)

    def test_get_historical_data4(self) -> None:
        """
        Test getting 1 minute data for 3 days.
        """
        start_ts = pd.Timestamp("2021-02-07 18:00:00")
        end_ts = start_ts + pd.DateOffset(days=3)
        bar_size_setting = "1 min"
        use_rth = True
        #
        self._compare_historical_data(bar_size_setting, start_ts, end_ts, use_rth)

    def test_ib_date_range1(self) -> None:
        start_ts = pd.Timestamp("2018-02-07 00:00").tz_localize(
            tz="America/New_York"
        )
        end_ts = start_ts + pd.DateOffset(days=3)
        dates = imideguddil._ib_date_range(start_ts, end_ts)
        #
        act = "\n".join(map(str, dates))
        exp = """
        2018-02-07 18:00:00-05:00
        2018-02-08 18:00:00-05:00
        2018-02-09 18:00:00-05:00
        2018-02-10 00:00:00-05:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_ib_date_range2(self) -> None:
        start_ts = pd.Timestamp("2018-02-07 18:00").tz_localize(
            tz="America/New_York"
        )
        end_ts = start_ts + pd.DateOffset(days=1)
        dates = imideguddil._ib_date_range(start_ts, end_ts)
        #
        act = "\n".join(map(str, dates))
        exp = """
        2018-02-07 18:00:00-05:00
        2018-02-08 18:00:00-05:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_ib_date_range3(self) -> None:
        start_ts = pd.Timestamp("2018-02-07 17:59").tz_localize(
            tz="America/New_York"
        )
        end_ts = start_ts + pd.DateOffset(days=2)
        dates = imideguddil._ib_date_range(start_ts, end_ts)
        #
        act = "\n".join(map(str, dates))
        exp = """
        2018-02-07 18:00:00-05:00
        2018-02-08 18:00:00-05:00
        2018-02-09 17:59:00-05:00
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_ib_date_range4(self) -> None:
        start_ts = pd.Timestamp("2018-02-07 17:59").tz_localize(
            tz="America/New_York"
        )
        end_ts = start_ts + pd.DateOffset(days=3)
        dates = imideguddil._ib_date_range(start_ts, end_ts)
        #
        act = "\n".join(map(str, dates))
