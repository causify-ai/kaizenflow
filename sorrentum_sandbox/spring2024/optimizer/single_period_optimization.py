"""
Import as:

import optimizer.single_period_optimization as osipeopt
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import core.finance as cofinanc
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import optimizer.base as opbase
import optimizer.hard_constraints as oharcons
import optimizer.soft_constraints as osofcons

# Equivalent to `import cvxpy as cpx`, but skip this module if the module is
# not present.
import pytest  # isort:skip # noqa: E402 # pylint: disable=wrong-import-order

cvx = pytest.importorskip("cvxpy")

_LOG = logging.getLogger(__name__)


# #############################################################################
# Single period optimization with costs and constraints
# #############################################################################


def optimize(
    config_dict: dict,
    df: pd.DataFrame,
    **kwargs: Dict[str, Any],
) -> pd.DataFrame:
    """
    Wrapper around `SinglePeriodOptimizer`.
    """
    spo = SinglePeriodOptimizer(config_dict, df)
    output_df = spo.optimize(**kwargs)
    return output_df


class SinglePeriodOptimizer:
    def __init__(
        self,
        config_dict: dict,
        df: pd.DataFrame,
        *,
        restrictions: Optional[pd.DataFrame] = None,
    ) -> None:
        """
        Single period optimization constructor.

        :param config: optimizer config
        :param df: dataframe with assets, volatility forecast,
            returns forecast, and current position. We pass this into the
            constructor because:
            - asset volatility is needed to generate a risk constraint
            - some restriction constraints are position-dependent
        :param restrictions: restrictions dataframe
        """
        # Process `config_dict` and extract parameters.
        self._dollar_neutrality_penalty = config_dict["dollar_neutrality_penalty"]
        self._transaction_cost_penalty = config_dict["transaction_cost_penalty"]
        self._target_gmv = config_dict["target_gmv"]
        self._target_gmv_upper_bound_penalty = config_dict[
            "target_gmv_upper_bound_penalty"
        ]
        self._target_gmv_hard_upper_bound_multiple = config_dict[
            "target_gmv_hard_upper_bound_multiple"
        ]
        self._relative_holding_penalty = config_dict["relative_holding_penalty"]
        self._relative_holding_max_frac_of_gmv = config_dict[
            "relative_holding_max_frac_of_gmv"
        ]
        self._config_dict = config_dict
        SinglePeriodOptimizer._validate_df(df)
        self._df = df
        #
        if restrictions is not None:
            SinglePeriodOptimizer._validate_restrictions_df(restrictions)
        self._restrictions = restrictions
        #
        self._asset_ids = self._df["asset_id"]
        self._n_assets = df.shape[0]
        holdings_notional = self._df["holdings_notional"]
        _LOG.debug("holdings_notional=\n%s", hpandas.df_to_str(holdings_notional))
        self._gmv = holdings_notional.abs().sum()
        self._current_weights = (
            holdings_notional * self._n_assets / self._target_gmv
        )
        _LOG.debug(
            "current_weights=\n%s", hpandas.df_to_str(self._current_weights)
        )
        # We pass "solver" as a string to avoid propagating `cvx` dependencies.
        if "solver" in config_dict:
            solver = config_dict["solver"]
            if solver == "ECOS":
                self._solver = cvx.ECOS
            elif solver == "OSQP":
                self._solver = cvx.OSQP
            elif solver == "SCS":
                self._solver = cvx.SCS
            else:
                raise ValueError("solver=%s not supported", solver)
        else:
            self._solver = None
        self._verbose = config_dict.get("verbose", False)

    def optimize(
        self,
        *,
        quantization: Optional[int] = 30,
        asset_id_to_share_decimals: Optional[Dict[int, int]] = None,
        liquidate_holdings: bool = False,
    ) -> pd.DataFrame:
        """
        Get target notional positions.
        """
        if liquidate_holdings:
            _LOG.debug("Liquidating holdings...")
            target_weights = pd.Series(
                0, index=self._asset_ids, name="target_weights"
            )
        else:
            # Compute optimal weights.
            target_weights, target_weight_diffs = self._optimize_weights()
            target_weights = pd.Series(
                data=target_weights.value,
                index=self._asset_ids,
                name="target_weights",
            )
            target_weight_diffs = pd.Series(
                data=target_weight_diffs.value,
                index=self._asset_ids,
                name="target_weight_diffs",
            )
            _LOG.debug(
                "target_weight_diffs=\n%s", hpandas.df_to_str(target_weight_diffs)
            )
            _ = target_weight_diffs
        _LOG.debug("target_weights=\n%s", hpandas.df_to_str(target_weights))
        # Convert target weights to target notional holdings.
        rescaling = self._target_gmv / self._n_assets
        _LOG.debug("rescaling factor=%f", rescaling)
        target_holdings_notional = (rescaling * target_weights).rename(
            "target_holdings_notional"
        )
        input_df = self._df.set_index("asset_id")
        target_holdings_shares = (
            target_holdings_notional / input_df["price"]
        ).rename("target_holdings_shares")
        # Quantize holdings (e.g., nearest share).
        target_holdings_shares = cofinanc.quantize_shares(
            target_holdings_shares,
            quantization,
            asset_id_to_decimals=asset_id_to_share_decimals,
        )
        # Recompute `target_holdings_notional` from shares and price.
        target_holdings_notional = (
            target_holdings_shares * input_df["price"]
        ).rename("target_holdings_notional")
        # Compute target trades.
        target_trades_shares = (
            target_holdings_shares - input_df["holdings_shares"]
        ).rename("target_trades_shares")
        # Additionally quantize shares to avoid floating point issues, e.g.,
        # `0.42000000000000004`. This is important because the broker imposes
        # restrictions on trades precision.
        target_trades_shares = cofinanc.quantize_shares(
            target_trades_shares,
            quantization,
            asset_id_to_decimals=asset_id_to_share_decimals,
        )
        # Recompute `target_trades_notional` from shares and price.
        target_trades_notional = (
            target_trades_shares * input_df["price"]
        ).rename("target_trades_notional")
        targets_df = pd.concat(
            [
                target_holdings_shares,
                target_holdings_notional,
                target_trades_shares,
                target_trades_notional,
            ],
            axis=1,
        )
        #
        result_df = pd.concat([input_df, targets_df], axis=1)
        return result_df

    def compute_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        gross_volume = df["target_trades_notional"].abs().sum()
        net_volume = df["target_trades_notional"].sum()
        gmv = df["target_holdings_notional"].abs().sum()
        nmv = df["target_holdings_notional"].sum()
        notional_stats = pd.Series(
            {
                "gross_volume": gross_volume,
                "net_volume": net_volume,
                "gmv": gmv,
                "nmv": nmv,
            }
        ).rename("notional")
        gmv_stats = 100 * (notional_stats / self._target_gmv).rename("percentage")
        return pd.concat([notional_stats, gmv_stats], axis=1)

    @staticmethod
    def _validate_df(df: pd.DataFrame) -> None:
        """
        Sanity-check `df`.
        """
        SinglePeriodOptimizer._is_df_with_asset_id_col(df)
        # Ensure the dataframe has the expected columns.
        # NOTE: Compare to columns of `TargetPositionAndOrderGenerator()` df.
        #  We should see the leading columns and the optimizer should supply
        #  the trailing columns (target holdings and trades, both notional and
        #  shares).
        expected_cols = [
            "holdings_shares",
            "price",
            "holdings_notional",
            "prediction",
            "volatility",
            # "spread",
        ]
        hdbg.dassert_is_subset(expected_cols, df.columns)
        # Ensure that the dataframe has a range-index.
        hdbg.dassert_isinstance(df.index, pd.RangeIndex)
        # Do not allow NaNs.
        for col in expected_cols:
            hdbg.dassert(not df[col].isna().any(), "Found NaNs in col=%s", col)

    @staticmethod
    def _is_df_with_asset_id_col(df: pd.DataFrame) -> None:
        # Type-check the dataframe.
        hdbg.dassert_isinstance(df, pd.DataFrame)
        hdbg.dassert_in("asset_id", df.columns)
        # Ensure that there are no duplicate asset ids.
        hdbg.dassert_eq(df["asset_id"].nunique(), df["asset_id"].count())

    @staticmethod
    def _validate_restrictions_df(df: pd.DataFrame) -> None:
        """
        Sanity-check `df` (candidate `restrictions` for self).
        """
        SinglePeriodOptimizer._is_df_with_asset_id_col(df)
        # Type-check the dataframe.
        hdbg.dassert_isinstance(df, pd.DataFrame)
        # Ensure the dataframe has the expected columns.
        restriction_cols = [
            "is_buy_restricted",
            "is_buy_cover_restricted",
            "is_sell_short_restricted",
            "is_sell_long_restricted",
        ]
        hdbg.dassert_is_subset(restriction_cols, df.columns)
        for col in restriction_cols:
            hpandas.dassert_series_type_is(df[col], np.bool_)

    def _optimize_weights(self) -> Tuple[cvx.Variable, cvx.Variable]:
        """
        Create and solve the cvx optimization problem.

        :return: target weights and weight diffs (from current weights),
            normalized by current GMV.
        """
        # Determine the current GMV and GMV-normalized weights.
        # Create a placeholder for (current) GMV-normalized weight adjustments.
        target_weight_diffs = cvx.Variable(self._n_assets)
        current_weights = self._current_weights.to_numpy()
        _LOG.debug("current_weights=\n%s", current_weights)
        target_weights = current_weights + target_weight_diffs
        # Create a placeholder for predicted returns (to maximize subject to
        # constraints).
        predictions = self._df["prediction"] * self._df["volatility"]
        predicted_returns = cvx.multiply(predictions.values, target_weights)
        mu = cvx.sum(predicted_returns)
        hdbg.dassert(mu.is_concave())
        # Get constraints.
        soft_constraints = self._get_soft_constraints()
        hard_constraints = self._get_hard_constraints()
        # Convert constraints into cvxpy expressions.
        soft_constraint_cvx_expr = [
            constraint.get_expr(
                target_weights, target_weight_diffs, self._target_gmv
            )
            for constraint in soft_constraints
        ]
        hard_constraint_cvx_expr = [
            constraint.get_expr(
                target_weights, target_weight_diffs, self._target_gmv
            )
            for constraint in hard_constraints
        ]
        # Create the cvxpy problem.
        problem = cvx.Problem(
            cvx.Maximize(mu - sum(soft_constraint_cvx_expr)),
            hard_constraint_cvx_expr,
        )
        # Optimize.
        optimal_value = problem.solve(self._solver, verbose=self._verbose)
        if problem.status != "optimal":
            _LOG.warning("problem.status=%s", problem.status)
        _LOG.debug("`optimal_value`=%0.2f", optimal_value)
        # TODO(Paul): Compute estimates for PnL, costs.
        return target_weights, target_weight_diffs

    def _get_soft_constraints(self) -> List[opbase.Expression]:
        # Create soft constraints
        soft_constraints = []
        volatility = self._df["volatility"]
        # Maybe add constant correlation risk constraint.
        if "constant_correlation" in self._config_dict:
            constant_correlation = self._config_dict["constant_correlation"]
            constant_correlation_penalty = self._config_dict[
                "constant_correlation_penalty"
            ]
            constant_correlation_risk = osofcons.ConstantCorrelationRiskModel(
                constant_correlation,
                volatility,
                constant_correlation_penalty,
            )
            soft_constraints.append(constant_correlation_risk)
        # Add GMV constraint.
        target_gmv_constraint = osofcons.TargetGmvUpperBoundSoftConstraint(
            self._target_gmv_upper_bound_penalty
        )
        soft_constraints.append(target_gmv_constraint)
        # Add dollar neutrality constraint.
        dollar_neutrality = osofcons.DollarNeutralitySoftConstraint(
            self._dollar_neutrality_penalty
        )
        soft_constraints.append(dollar_neutrality)
        # Add relative holding constraint.
        relative_holding = osofcons.RelativeHoldingSoftConstraint(
            self._relative_holding_penalty
        )
        soft_constraints.append(relative_holding)
        # Add transaction cost penalty.
        transaction_cost_penalty = osofcons.TransactionCost(
            volatility,
            self._transaction_cost_penalty,
        )
        soft_constraints.append(transaction_cost_penalty)
        return soft_constraints

    def _get_hard_constraints(self) -> List[opbase.Expression]:
        # Create hard constraints.
        hard_constraints = []
        # Add target GMV hard constraint.
        target_gmv_constraint = oharcons.TargetGmvUpperBoundHardConstraint(
            self._target_gmv,
            self._target_gmv_hard_upper_bound_multiple,
        )
        hard_constraints.append(target_gmv_constraint)
        # Add relative holding constraint.
        relative_holding_constraint = oharcons.RelativeHoldingHardConstraint(
            self._relative_holding_max_frac_of_gmv
        )
        hard_constraints.append(relative_holding_constraint)
        if self._restrictions is not None:
            restriction_constraints = self._get_restriction_constraints()
            if restriction_constraints:
                hard_constraints.extend(restriction_constraints)
        return hard_constraints

    def _get_restriction_constraints(self) -> List[opbase.Expression]:
        constraints = []
        df = self._df.merge(self._restrictions, how="left", on="asset_id").fillna(
            False
        )
        do_not_buy = ((df["holdings_shares"] >= 0) & df["is_buy_restricted"]) | (
            (df["holdings_shares"] < 0) & df["is_buy_cover_restricted"]
        )
        if do_not_buy.any():
            do_not_buy_constraint = oharcons.DoNotBuyHardConstraint(do_not_buy)
            constraints.append(do_not_buy_constraint)
        do_not_sell = (
            (df["holdings_shares"] > 0) & df["is_sell_long_restricted"]
        ) | ((df["holdings_shares"] <= 0) & df["is_sell_short_restricted"])
        if do_not_sell.any():
            do_not_sell_constraint = oharcons.DoNotSellHardConstraint(do_not_sell)
            constraints.append(do_not_sell_constraint)
        # Note: it is possible for this list to be empty.
        return constraints

    def _process_results(
        self,
        target_weights: cvx.Variable,
        target_weight_diffs: cvx.Variable,
    ) -> pd.DataFrame:
        """
        Translate optimized weights into positions and notional trades.

        :param target_weights: target weights, normalized by current GMV
        :param target_weight_diffs: target weight diffs, normalized by
            current GMV
        :return: dataframe of target positions and notional trades, in
            addition to the raw weights and weight diffs.
        """
        # Collect series.
        srs_list = []
        #
        rescaling = self._target_gmv / self._n_assets
        # Target notional holdings.
        target_holdings_notional = pd.Series(
            index=self._asset_ids,
            data=target_weights.value * rescaling,
            name="target_holdings_notional",
        )
        srs_list.append(target_holdings_notional)
        # Target notional trades.
        target_trades_notional = pd.Series(
            index=self._asset_ids,
            data=target_weight_diffs.value * rescaling,
            name="target_trades_notional",
        )
        srs_list.append(target_trades_notional)
        # Target weights.
        target_weights = pd.Series(
            index=self._asset_ids,
            data=target_weights.value,
            name="target_weight",
        )
        srs_list.append(target_weights)
        # Target weight adjustments.
        target_weight_diffs = pd.Series(
            index=self._asset_ids,
            data=target_weight_diffs.value,
            name="target_weight_diff",
        )
        srs_list.append(target_weight_diffs)
        df = pd.concat(srs_list, axis=1)
        _LOG.debug("optimizer result=\n%s", hpandas.df_to_str(df, precision=2))
        return df
