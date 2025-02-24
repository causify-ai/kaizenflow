"""
Import as:

import optimizer.hard_constraints as oharcons
"""

import logging

import pandas as pd

import helpers.hdbg as hdbg
import optimizer.base as opbase

# Equivalent to `import cvxpy as cpx`, but skip this module if the module is
# not present.
import pytest  # isort:skip # noqa: E402 # pylint: disable=wrong-import-position

cvx = pytest.importorskip("cvxpy")

_LOG = logging.getLogger(__name__)


# #############################################################################
# Hard constraints.
# #############################################################################


class ConcentrationHardConstraint(opbase.Expression):
    """
    Restrict max weight in an asset.
    """

    def __init__(self, concentration_bound: float) -> None:
        hdbg.dassert_lte(0, concentration_bound)
        self._concentration_bound = concentration_bound

    def get_expr(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        # TODO(Paul): Volatility-normalize this?
        return cvx.max(cvx.abs(target_weights)) <= self._concentration_bound


class DollarNeutralityHardConstraint(opbase.Expression):
    """
    Require sum of longs weights equals sum of shorts weights.
    """

    def get_expr(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        return sum(target_weights) == 0


class RelativeHoldingHardConstraint(opbase.Expression):
    """
    Restrict the maximum fraction of GMV that can be allocated to an asset.
    """

    def __init__(self, max_frac_of_gmv: float) -> None:
        hdbg.dassert_lte(0, max_frac_of_gmv)
        hdbg.dassert_lte(max_frac_of_gmv, 1)
        self._max_frac_of_gmv = max_frac_of_gmv

    def get_expr(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        return (
            cvx.norm(target_weights, "inf")
            <= self._max_frac_of_gmv * target_weights.shape[0]
        )


class TargetGmvUpperBoundHardConstraint(opbase.Expression):
    """
    Impose an upper bound on GMV.
    """

    def __init__(
        self,
        target_gmv: float,
        upper_bound_multiple: float,
    ) -> None:
        hdbg.dassert_lte(0, target_gmv)
        hdbg.dassert_lte(1.0, upper_bound_multiple)
        self._target_gmv = target_gmv
        self._upper_bound_multiple = upper_bound_multiple

    def get_expr(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        return (
            cvx.norm(target_weights, 1)
            <= target_weights.shape[0] * self._upper_bound_multiple
        )


class DoNotTradeHardConstraint(opbase.Expression):
    def __init__(self, do_not_trade: pd.Series) -> None:
        hdbg.dassert_isinstance(do_not_trade, pd.Series)
        hdbg.dassert(do_not_trade.any())
        self._do_not_trade = do_not_trade

    def get_expr(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weights
        _ = gmv
        return cvx.multiply(target_weight_diffs, self._do_not_trade) == 0


class DoNotBuyHardConstraint(opbase.Expression):
    def __init__(self, do_not_buy: pd.Series) -> None:
        hdbg.dassert_isinstance(do_not_buy, pd.Series)
        hdbg.dassert(do_not_buy.any())
        self._do_not_buy = do_not_buy

    def get_expr(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weights
        _ = gmv
        return cvx.multiply(target_weight_diffs, self._do_not_buy.values) <= 0


class DoNotSellHardConstraint(opbase.Expression):
    def __init__(self, do_not_sell: pd.Series) -> None:
        hdbg.dassert_isinstance(do_not_sell, pd.Series)
        hdbg.dassert(do_not_sell.any())
        self._do_not_sell = do_not_sell

    def get_expr(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weights
        _ = gmv
        return cvx.multiply(target_weight_diffs, self._do_not_sell.values) >= 0
