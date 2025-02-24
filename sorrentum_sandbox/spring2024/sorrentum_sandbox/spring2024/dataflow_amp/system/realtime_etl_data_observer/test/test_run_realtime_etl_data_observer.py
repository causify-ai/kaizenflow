from typing import List

import pytest

import dataflow_amp.system.realtime_etl_data_observer.scripts.run_realtime_etl_data_observer as dtfasredosrredo
import helpers.hprint as hprint
import helpers.hunit_test as hunitest


class Test_run_realtime_etl_data_observer(hunitest.TestCase):
    @pytest.mark.slow("~5 seconds.")
    def test1(self) -> None:
        """
        Test running real time ETL data observer.
        """
        result_bundle = dtfasredosrredo.run()
        txt: List[str] = []
        # Result bundle signature.
        col = "feature"
        txt.append(hprint.frame(col))
        result_df = result_bundle[-1].result_df
        data = result_df[col].dropna(how="all")
        data_str = data.round(3).to_string()
        txt.append(data_str)
        #
        actual = "\n".join(txt)
        self.check_string(actual, fuzzy_match=True, purify_text=True)
