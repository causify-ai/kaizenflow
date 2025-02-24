"""
Import as:

import core.statistics as cstats
"""

from core.statistics.binning import *  # pylint: disable=unused-import # NOQA
from core.statistics.correlation import *  # pylint: disable=unused-import # NOQA
from core.statistics.covariance_shrinkage import *  # pylint: disable=unused-import # NOQA
from core.statistics.cross_validation import *  # pylint: disable=unused-import # NOQA
from core.statistics.descriptive import *  # pylint: disable=unused-import # NOQA
from core.statistics.drawdown import *  # pylint: disable=unused-import # NOQA
from core.statistics.empirical_distribution_function import *  # pylint: disable=unused-import # NOQA
from core.statistics.entropy import *  # pylint: disable=unused-import # NOQA
from core.statistics.forecastability import *  # pylint: disable=unused-import # NOQA
from core.statistics.hitting_time import *  # pylint: disable=unused-import # NOQA
from core.statistics.interarrival_time import *  # pylint: disable=unused-import # NOQA
from core.statistics.local_level_model import *  # pylint: disable=unused-import # NOQA
from core.statistics.normality import *  # pylint: disable=unused-import # NOQA
from core.statistics.q_values import *  # pylint: disable=unused-import # NOQA
from core.statistics.random_samples import *  # pylint: disable=unused-import # NOQA
from core.statistics.regression import *  # pylint: disable=unused-import # NOQA

# Disable pymc3 import since our container does not currently have the package.
# from core.statistics.requires_pymc3 import *  # pylint: disable=unused-import # NOQA
from core.statistics.requires_statsmodels import *  # pylint: disable=unused-import # NOQA
from core.statistics.returns_and_volatility import *  # pylint: disable=unused-import # NOQA
from core.statistics.sharpe_ratio import *  # pylint: disable=unused-import # NOQA
from core.statistics.signed_runs import *  # pylint: disable=unused-import # NOQA
from core.statistics.t_test import *  # pylint: disable=unused-import # NOQA
from core.statistics.turnover import *  # pylint: disable=unused-import # NOQA
