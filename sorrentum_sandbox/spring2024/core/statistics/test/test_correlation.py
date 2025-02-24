import logging

import core.statistics.correlation as cstacorr
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestComputeCorrelationConfidenceDensityApproximation1(hunitest.TestCase):
    def test1(self) -> None:
        rho = 0.1
        n_samples = 100
        grid_size = 0.025
        srs = cstacorr.compute_correlation_confidence_density_approximation(
            rho,
            n_samples,
            grid_size=grid_size,
        )
        actual = hpandas.df_to_str(srs, num_rows=None)
        expected = r"""
           confidence_density
-0.098350            0.581239
-0.088233            0.702893
-0.078099            0.841640
-0.067948            0.997850
-0.057783            1.171405
-0.047606            1.361606
-0.037419            1.567108
-0.027225            1.785867
-0.017024            2.015126
-0.006821            2.251430
 0.003385            2.490678
 0.013589            2.728223
 0.023791            2.959001
 0.033988            3.177702
 0.044177            3.378970
 0.054358            3.557609
 0.064527            3.708813
 0.074683            3.828373
 0.084823            3.912876
 0.094946            3.959864
 0.105049            3.967955
 0.115131            3.936907
 0.125188            3.867634
 0.135221            3.762160
 0.145225            3.623519
 0.155200            3.455611
 0.165144            3.263022
 0.175054            3.050814
 0.184928            2.824306
 0.194766            2.588855
 0.204564            2.349650
 0.214322            2.111533
 0.224037            1.878847
 0.233707            1.655326
 0.243332            1.444022
 0.252909            1.247273
 0.262437            1.066711
 0.271913            0.903293
 0.281338            0.757368
 0.290708            0.628754
"""
        self.assert_equal(actual, expected, fuzzy_match=True)
