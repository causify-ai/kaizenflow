import pytest

import dataflow.system.source_nodes as dtfsysonod
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest


@pytest.mark.skip(reason="Kibot Equity Reader not in use ref. #5582.")
class TestKibotEquityReader(hunitest.TestCase):
    @pytest.mark.slow
    def test1(self) -> None:
        node = dtfsysonod.KibotEquityReader(
            "reader",
            ["AAPL", "GOOG"],
            "T",
            "2018-01-02 09:30:00",
            "2018-01-02 10:00:00",
        )
        df = node.fit()["df_out"]
        df_str = hpandas.df_to_str(df, num_rows=None)
        self.check_string(df_str)
