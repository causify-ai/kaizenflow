"""
Import as:

import optimizer.soft_constraints as osofcons
"""

import abc
import logging

import pandas as pd

import helpers.hdbg as hdbg
import optimizer.base as opbase
import optimizer.utils as oputils

# Equivalent to `import cvxpy as cpx`, but skip this module if the module is
# not present.
import pytest  # isort:skip # noqa: E402 # pylint: disable=wrong-import-position

cvx = pytest.importorskip("cvxpy")

_LOG = logging.getLogger(__name__)


# #############################################################################
# Class and builder for objective function costs.
# #############################################################################


class SoftConstraint(abc.ABC):
    """
    Base class for soft constraints.
    """

    def __init__(self, gamma: float = 1.0) -> None:
        """
        Initialize the Lagrange multiplier to 1.0.
        """
        hdbg.dassert_lte(0, gamma)
        self.gamma = cvx.Parameter(nonneg=True, value=gamma)
        self.expr = None

    def __mul__(self, other):
        """
        Scale the cost by the constant.
        """
        self.gamma.value *= other
        return self

    def __rmul__(self, other):
        """
        Scale the cost by the constant.
        """
        return self.__mul__(other)

    def get_expr(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        expr = self._estimate(target_weights, target_weight_diffs, gmv)
        self.expr = expr.copy()
        return self.gamma * expr

    @abc.abstractmethod
    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        ...


# #############################################################################
# Risk models.
# #############################################################################


class VolatilityRiskModel(SoftConstraint):
    """
    Impose a diagonal volatility cost.
    """

    def __init__(self, volatility: pd.Series, gamma: float = 1.0) -> None:
        self._volatility = volatility
        super().__init__(gamma)

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        expr = cvx.quad_form(
            target_weights, cvx.diag(self._volatility.values**2)
        )
        return expr


class CovarianceRiskModel(SoftConstraint):
    """
    Utilize a full covariance matrix for the risk model.
    """

    def __init__(self, risk: pd.DataFrame, gamma: float = 1.0) -> None:
        hdbg.dassert(oputils.is_symmetric(risk))
        self._risk = risk
        super().__init__(gamma)

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        expr = cvx.quad_form(target_weights, self._risk.values)
        return expr


class ConstantCorrelationRiskModel(SoftConstraint):
    """
    Use per-asset volatility but assume constant correlation.
    """

    def __init__(
        self, correlation: float, volatility: pd.Series, gamma: float = 1.0
    ) -> None:
        self._correlation = correlation
        self._volatility = volatility
        super().__init__(gamma)

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        expr1 = (1 - self._correlation) * cvx.sum_squares(
            cvx.multiply(target_weights, self._volatility.values)
        )
        expr2 = self._correlation * cvx.power(
            target_weights @ self._volatility.values, 2
        )
        expr = expr1 + expr2
        return expr


# #############################################################################
# Transaction costs.
# #############################################################################


class SpreadCost(SoftConstraint):
    def __init__(self, spread: pd.Series, gamma: float = 1.0) -> None:
        hdbg.dassert_isinstance(spread, pd.Series)
        hdbg.dassert((spread >= 0).all())
        self._spread = spread
        super().__init__(gamma)

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weights
        _ = gmv
        expr = (self._spread.values / 2) @ cvx.abs(target_weight_diffs).T
        return expr


class TransactionCost(SoftConstraint):
    def __init__(self, volatility: pd.Series, gamma: float = 1.0) -> None:
        hdbg.dassert_isinstance(volatility, pd.Series)
        self._volatility = volatility
        super().__init__(gamma)

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weights
        _ = gmv
        expr = self._volatility.values @ cvx.abs(target_weight_diffs).T
        return expr


# #############################################################################
# Soft constraints.
# #############################################################################


class TargetGmvUpperBoundSoftConstraint(SoftConstraint):
    """
    Impose a cost on going above the target GMV.
    """

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        return cvx.pos(cvx.norm(target_weights, 1) - target_weights.shape[0])


class DollarNeutralitySoftConstraint(SoftConstraint):
    """
    Impose a cost on violating dollar neutrality.
    """

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        return cvx.abs(sum(target_weights))


class RelativeHoldingSoftConstraint(SoftConstraint):
    """
    Impose a cost on asset allocation that is uneven with respect to GMV.
    """

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weight_diffs
        _ = gmv
        return cvx.pos(cvx.norm(target_weights, "inf") - 1)


class TurnoverSoftConstraint(SoftConstraint):
    """
    Impose a cost on turnover.
    """

    def _estimate(self, target_weights, target_weight_diffs, gmv) -> opbase.EXPR:
        _ = target_weights
        _ = gmv
        return cvx.norm(target_weight_diffs, 1)
