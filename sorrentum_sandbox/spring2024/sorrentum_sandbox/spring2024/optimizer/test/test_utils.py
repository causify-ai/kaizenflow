import io
import logging

import numpy as np
import pandas as pd

import helpers.hunit_test as hunitest
import optimizer.utils as oputils

_LOG = logging.getLogger(__name__)


class Test_compute_tangency_portfolio(hunitest.TestCase):
    @staticmethod
    def get_covariance() -> pd.DataFrame:
        mat = np.array(
            [
                [1, 0.9, 0.9],
                [0.9, 1, 0.9],
                [0.9, 0.9, 1],
            ]
        )
        names = ["T1", "T2", "T3"]
        covariance = pd.DataFrame(mat, index=names, columns=names)
        return covariance

    def test_toy_case(self) -> None:
        mu_txt = """
datetime,T1,T2,T3
2016-01-04 12:00:00,0.2,0.1,-0.1
2016-01-04 12:01:00,0.1,0.1,0.1
2016-01-04 12:02:00,-0.1,-0.1,0.1
2016-01-04 12:03:00,0.5,-0.5,0.0
"""
        mu = pd.read_csv(io.StringIO(mu_txt), index_col=0, parse_dates=True)
        covariance = self.get_covariance()
        actual = oputils.compute_tangency_portfolio(mu, covariance=covariance)
        txt = """
datetime,T1,T2,T3
2016-01-04 12:00:00,1.357,0.357,-1.643
2016-01-04 12:01:00,0.036,0.036,0.036
2016-01-04 12:02:00,-0.679,-0.679,1.321
2016-01-04 12:03:00,5.0,-5.0,-0
"""
        expected = pd.read_csv(io.StringIO(txt), index_col=0, parse_dates=True)
        self.assert_dfs_close(actual, expected, rtol=1e-2, atol=1e-2)

    def test_precision_equivalency(self) -> None:
        mu_txt = """
datetime,T1,T2,T3
2016-01-04 12:00:00,0.2,0.1,-0.1
2016-01-04 12:01:00,0.1,0.1,0.1
2016-01-04 12:02:00,-0.1,-0.1,0.1
2016-01-04 12:03:00,0.5,-0.5,0.0
"""
        mu = pd.read_csv(io.StringIO(mu_txt), index_col=0, parse_dates=True)
        covariance = self.get_covariance()
        actual_covariance = oputils.compute_tangency_portfolio(
            mu, covariance=covariance
        )
        precision = pd.DataFrame(
            np.linalg.inv(covariance),
            index=covariance.index,
            columns=covariance.columns,
        )
        actual_precision = oputils.compute_tangency_portfolio(
            mu, precision=precision
        )
        self.assert_dfs_close(
            actual_precision, actual_covariance, rtol=1e-5, atol=1e-5
        )
