import logging

import numpy as np

import core.statistics.binning as cstabinn
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestGetSymmetricNormalQuantiles1(hunitest.TestCase):
    def test1(self) -> None:
        bin_boundaries, bin_medians = cstabinn.get_symmetric_normal_quantiles(
            0.341
        )
        expected_bin_boundaries = np.array(
            [-np.inf, -0.4412942, 0.4412942, np.inf]
        )
        expected_bin_medians = np.array(
            [
                -0.9985762,
                0,
                0.9985762,
            ]
        )
        np.testing.assert_almost_equal(
            bin_boundaries, expected_bin_boundaries, decimal=5
        )
        np.testing.assert_almost_equal(
            bin_medians, expected_bin_medians, decimal=5
        )

    def test2(self) -> None:
        bin_boundaries, bin_medians = cstabinn.get_symmetric_normal_quantiles(
            0.25
        )
        expected_bin_boundaries = np.array(
            [-np.inf, -1.150349, -0.318639, 0.318639, 1.150349, np.inf]
        )
        expected_bin_medians = np.array(
            [
                -1.5341205,
                -0.6744898,
                0,
                0.6744898,
                1.5341205,
            ]
        )
        np.testing.assert_almost_equal(
            bin_boundaries, expected_bin_boundaries, decimal=5
        )
        np.testing.assert_almost_equal(
            bin_medians, expected_bin_medians, decimal=5
        )

    def test3(self) -> None:
        bin_boundaries, bin_medians = cstabinn.get_symmetric_normal_quantiles(0.1)
        expected_bin_boundaries = np.array(
            [
                -np.inf,
                -1.6448536269514733,
                -1.0364333894937898,
                -0.6744897501960817,
                -0.38532046640756773,
                -0.12566134685507416,
                0.12566134685507416,
                0.38532046640756773,
                0.6744897501960817,
                1.0364333894937898,
                1.6448536269514733,
                np.inf,
            ]
        )
        expected_bin_medians = np.array(
            [
                -1.959963984540054,
                -1.2815515655446004,
                -0.8416212335729143,
                -0.5244005127080407,
                -0.2533471031357997,
                0,
                0.2533471031357997,
                0.5244005127080407,
                0.8416212335729143,
                1.2815515655446004,
                1.959963984540054,
            ]
        )
        np.testing.assert_almost_equal(
            bin_boundaries, expected_bin_boundaries, decimal=5
        )
        np.testing.assert_almost_equal(
            bin_medians, expected_bin_medians, decimal=5
        )
