import logging

import numpy as np
import pandas as pd

import core.statistics.entropy as cstaentr
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_compute_hill_number(hunitest.TestCase):
    def test_equally_distributed1(self) -> None:
        length = 10
        data = pd.Series(index=range(0, length), data=1)
        actual = cstaentr.compute_hill_number(data, 1)
        np.testing.assert_allclose(actual, 10)

    def test_equally_distributed2(self) -> None:
        length = 10
        data = pd.Series(index=range(0, length), data=1)
        actual = cstaentr.compute_hill_number(data, 2)
        np.testing.assert_allclose(actual, 10)

    def test_equally_distributed3(self) -> None:
        length = 10
        data = pd.Series(index=range(0, length), data=1)
        actual = cstaentr.compute_hill_number(data, np.inf)
        np.testing.assert_allclose(actual, 10)

    def test_scale_invariance1(self) -> None:
        length = 32
        np.random.seed(137)
        data = pd.Series(data=np.random.rand(length, 1).flatten())
        actual_1 = cstaentr.compute_hill_number(data, 2)
        actual_2 = cstaentr.compute_hill_number(7 * data, 2)
        np.testing.assert_allclose(actual_1, actual_2)

    def test_exponentially_distributed1(self) -> None:
        data = pd.Series([2**j for j in range(10, 0, -1)])
        actual = cstaentr.compute_hill_number(data, 1)
        np.testing.assert_allclose(actual, 3.969109, atol=1e-5)

    def test_exponentially_distributed2(self) -> None:
        data = pd.Series([2**j for j in range(10, 0, -1)])
        actual = cstaentr.compute_hill_number(data, 2)
        np.testing.assert_allclose(actual, 2.994146, atol=1e-5)

    def test_exponentially_distributed3(self) -> None:
        data = pd.Series([2**j for j in range(10, 0, -1)])
        actual = cstaentr.compute_hill_number(data, np.inf)
        np.testing.assert_allclose(actual, 1.998047, atol=1e-5)
