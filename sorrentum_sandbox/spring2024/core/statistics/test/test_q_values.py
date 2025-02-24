import io
import logging

import pandas as pd

import core.statistics.q_values as cstqval
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_estimate_q_values(hunitest.TestCase):
    def test_small_df(self) -> None:
        p_val_txt = """
,id1,id2
exp1,0.1,0.2
exp2,0.01,0.05
"""
        p_vals = pd.read_csv(io.StringIO(p_val_txt), index_col=0)
        actual = cstqval.estimate_q_values(p_vals)
        # These values are equivalent to BH-adjusted values.
        q_val_txt = """
,id1,id2
exp1,0.133333,0.2
exp2,0.04,0.1
"""
        expected = pd.read_csv(io.StringIO(q_val_txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)

    def test_small_series(self) -> None:
        p_val_txt = """
p_val
0.1
0.2
0.01
0.05
"""
        p_vals = pd.read_csv(io.StringIO(p_val_txt)).squeeze()
        actual = cstqval.estimate_q_values(p_vals)
        q_val_txt = """
q_val
0.133333
0.2
0.04
0.1
"""
        expected = pd.read_csv(io.StringIO(q_val_txt)).squeeze()
        self.assert_dfs_close(
            actual.to_frame(), expected.to_frame(), rtol=1e-6, atol=1e-6
        )

    def test_user_supplied_pi0(self) -> None:
        p_val_txt = """
,id1,id2
exp1,0.1,0.2
exp2,0.01,0.05
"""
        p_vals = pd.read_csv(io.StringIO(p_val_txt), index_col=0)
        actual = cstqval.estimate_q_values(p_vals, pi0=0.8)
        q_val_txt = """
,id1,id2
exp1,0.106667,0.16
exp2,0.032,0.08
"""
        expected = pd.read_csv(io.StringIO(q_val_txt), index_col=0)
        self.assert_dfs_close(actual, expected, rtol=1e-6, atol=1e-6)
