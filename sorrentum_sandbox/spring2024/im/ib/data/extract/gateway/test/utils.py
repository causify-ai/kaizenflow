import logging
import os
from typing import Tuple

try:
    import ib_insync
except ModuleNotFoundError:
    print("Can't find ib_insync")
import pandas as pd
import pytest

import helpers.hdbg as hdbg
import helpers.hunit_test as hunitest
import im.ib.data.extract.gateway.download_data_ib_loop as imidegddil
import im.ib.data.extract.gateway.save_historical_data_with_IB_loop as imidegshdwil
import im.ib.data.extract.gateway.unrolling_download_data_ib_loop as imideguddil
import im.ib.data.extract.gateway.utils as imidegaut

_LOG = logging.getLogger(__name__)


class IbExtractionTest(hunitest.TestCase):
    @staticmethod
    def get_df_signatures(df: pd.DataFrame) -> Tuple[str, str]:
        """
        Compute a short and a long signature for the df.

        The short signature is suitable to the self.assertEqual()
        approach. The long signature contains the data and it's suitable
        to the self.check_string() approach.
        """
        txt = []
        #
        act = imidegaut.get_df_signature(df)
        txt.append("signature=%s" % act)
        #
        if not df.empty:
            df_tmp = df.copy()
            _LOG.debug("df_tmp=\n%s", df_tmp.head())
            hdbg.dassert_isinstance(df_tmp.index[0], pd.Timestamp)
            df_tmp["time"] = df_tmp.index.time
            min_max_df = (
                df_tmp["time"].groupby(lambda x: x.date()).agg([min, max])
            )
            txt.append("min_max_df=\n%s" % min_max_df)
            short_signature = "\n".join(txt)
        else:
            short_signature = ""
        #
        txt.append("df=\n%s" % df.to_csv())
        long_signature = "\n".join(txt)
        return short_signature, long_signature

    @classmethod
    def setUpClass(cls):
        hdbg.shutup_chatty_modules()

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self):
        self.ib = imidegaut.ib_connect(
            sum(bytes(self._get_test_name(), encoding="UTF-8")), is_notebook=False
        )

    def tear_down_test(self):
        self.ib.disconnect()

    def _req_historical_data_helper(self, end_ts, use_rth) -> Tuple[str, str]:
        """
        Run imidegaut.req_historical_data() with some fixed params and return
        short and long signature.
        """
        contract = ib_insync.ContFuture("ES", "GLOBEX", currency="USD")
        what_to_show = "TRADES"
        duration_str = "1 D"
        bar_size_setting = "1 hour"
        df = imidegaut.req_historical_data(
            self.ib,
            contract,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
        )
        short_signature, long_signature = self.get_df_signatures(df)
        return short_signature, long_signature

    def _ib_loop_generator_helper(
        self,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        bar_size_setting: str,
    ) -> Tuple[pd.DataFrame, str, str]:
        """
        Return concatenated dataframe from loop generator.
        """
        _LOG.debug("start_ts='%s' end_ts='%s'", start_ts, end_ts)
        contract = ib_insync.ContFuture("ES", "GLOBEX", currency="USD")
        what_to_show = "TRADES"
        duration_str = "1 D"
        df = pd.concat(
            [
                df_
                for _, df_, _ in imidegddil.ib_loop_generator(
                    ib=self.ib,
                    contract=contract,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    duration_str=duration_str,
                    bar_size_setting=bar_size_setting,
                    what_to_show=what_to_show,
                    use_rth=False,
                )
            ]
        )
        df = df.sort_index()
        short_signature, long_signature = self.get_df_signatures(df)
        return df, short_signature, long_signature

    def _get_historical_data_with_IB_loop_helper(
        self,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        bar_size_setting: str,
        use_rth: bool,
    ) -> Tuple[pd.DataFrame, str, str]:
        _LOG.debug("start_ts='%s' end_ts='%s'", start_ts, end_ts)
        contract = ib_insync.ContFuture("ES", "GLOBEX", currency="USD")
        what_to_show = "TRADES"
        duration_str = "1 D"
        df, ts_seq = imidegddil.get_historical_data_with_IB_loop(
            self.ib,
            contract,
            start_ts,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
            return_ts_seq=True,
        )
        short_signature, long_signature = self.get_df_signatures(df)
        long_signature += "ts_seq=\n" + "\n".join(map(str, ts_seq))
        return df, short_signature, long_signature

    def _get_historical_data_helper(
        self,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        bar_size_setting: str,
        use_rth: bool,
    ) -> Tuple[pd.DataFrame, str, str]:
        _LOG.debug("start_ts='%s' end_ts='%s'", start_ts, end_ts)
        contract = ib_insync.ContFuture("ES", "GLOBEX", currency="USD")
        what_to_show = "TRADES"
        mode = "in_memory"
        client_id = 2
        df, ts_seq = imideguddil.get_historical_data(
            client_id,
            contract,
            start_ts,
            end_ts,
            bar_size_setting,
            what_to_show,
            use_rth,
            mode,
            return_ts_seq=True,
        )
        short_signature, long_signature = self.get_df_signatures(df)
        long_signature += "ts_seq=\n" + "\n".join(map(str, ts_seq))
        return df, short_signature, long_signature

    def _compare_historical_data(
        self,
        bar_size_setting: str,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        use_rth: bool,
    ) -> None:
        """
        Retrieve historical data with `get_historical_data` and
        `get_historical_data_with_IB_loop` and compare it.
        """
        # Get the data in two different ways.
        df, short_signature, long_signature = self._get_historical_data_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        (
            df2,
            short_signature2,
            long_signature2,
        ) = self._get_historical_data_with_IB_loop_helper(
            start_ts, end_ts, bar_size_setting, use_rth
        )
        # Compare the outcomes.
        self.assert_equal(df.to_csv(), df2.to_csv(), fuzzy_match=True)
        self.assert_equal(short_signature, short_signature2)
        #
        self.check_string(long_signature)

    def _save_historical_data_with_IB_loop_helper(
        self,
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        bar_size_setting: str,
        use_rth: bool,
    ) -> Tuple[pd.DataFrame, str, str]:
        _LOG.debug("start_ts='%s' end_ts='%s'", start_ts, end_ts)
        contract = ib_insync.ContFuture("ES", "GLOBEX", currency="USD")
        what_to_show = "TRADES"
        duration_str = "1 D"
        file_name = os.path.join(self.get_scratch_space(), "output.csv")
        incremental = False
        imidegshdwil.save_historical_data_with_IB_loop(
            self.ib,
            contract,
            start_ts,
            end_ts,
            duration_str,
            bar_size_setting,
            what_to_show,
            use_rth,
            file_name,
            incremental,
        )
        # Load the data generated.
        df = imidegddil.load_historical_data(file_name)
        # Check.
        short_signature, long_signature = self.get_df_signatures(df)
        return df, short_signature, long_signature
