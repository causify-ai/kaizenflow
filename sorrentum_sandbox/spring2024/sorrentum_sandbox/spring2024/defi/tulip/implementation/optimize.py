"""
Import as:

import defi.tulip.implementation.optimize as dtuimopt
"""

import logging
from typing import Any, Dict, List, Tuple

import defi.tulip.implementation.order as dtuimord
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# Equivalent to `import x as x`, but skip this module if the module is
# not present.
import pytest  # isort:skip # noqa: E402 # pylint: disable=wrong-import-position

pulp = pytest.importorskip("pulp")

_LOG = logging.getLogger(__name__)


# TODO(Paul): Deprecate.
def run_solver(
    orders: List[dtuimord.Order], prices: Dict[str, float]
) -> Dict[str, Any]:
    """
    Find the maximum exchanged volume given the constraints.

    :param orders: buy / sell orders
    :param exchange_rate: price (in terms of quote token) per unit of base token
    :return: solver's output in human readable format
    """
    _LOG.debug(hprint.to_str("orders"))
    n_orders = len(orders)
    hdbg.dassert_lt(0, n_orders)
    hdbg.dassert_container_type(orders, list, dtuimord.Order)
    #
    _LOG.debug(hprint.to_str("prices"))
    hdbg.dassert_isinstance(prices, dict)
    hdbg.dassert_lt(0, len(prices))
    # Initialize the model.
    problem = pulp.LpProblem("The DaoCross problem", pulp.LpMaximize)
    # Specify the executed quantities vars. Setting the lower bound to zero
    # allows to omit the >= 0 constraint.
    q_base_asterisk = [
        pulp.LpVariable(f"q_base_asterisk_{i}", lowBound=0)
        for i in range(n_orders)
    ]
    # Objective function. Maximize the total exchanged volume.
    problem += pulp.lpSum(
        q_base_asterisk[i] * prices[orders[i].base_token] for i in range(n_orders)
    )
    # Constraints.
    # Impose constraints on executed quantites on the order level.
    for i in range(n_orders):
        # TODO(Grisha): could be a separate function with relevant assertions,
        # e.g., `get_price_quote_per_base(base_token, quote_token, prices)`.
        hdbg.dassert_in(orders[i].base_token, prices)
        base_price = prices[orders[i].base_token]
        hdbg.dassert_in(orders[i].quote_token, prices)
        quote_price = prices[orders[i].quote_token]
        price_quote_per_base = quote_price / base_price
        _LOG.debug(hprint.to_str("price_quote_per_base"))
        limit_price_cond = (
            price_quote_per_base * orders[i].action_as_int
            <= orders[i].limit_price * orders[i].action_as_int
        )
        _LOG.debug(hprint.to_str("limit_price_cond"))
        if limit_price_cond:
            # Executed quantity is less than or equal to the requested quantity.
            problem += q_base_asterisk[i] <= orders[i].quantity
        else:
            # Executed quantity is zero, i.e., the order cannot be executed.
            problem += q_base_asterisk[i] == 0
    # Impose constraints on the token level: the amount of sold tokens must match that
    # of bought tokens for each token.
    base_tokens = [order.base_token for order in orders]
    for token in base_tokens:
        problem += (
            pulp.lpSum(
                # TODO(Grisha): the `if-else` part could become a separate function,
                # i.e. the indicator function -- Tau.
                q_base_asterisk[i]
                * orders[i].action_as_int
                * (1 if orders[i].base_token == token else 0)
                for i in range(n_orders)
            )
            == 0
        )
    # Use the default solver and suppress the solver's log.
    solver = pulp.getSolver("PULP_CBC_CMD", msg=0)
    problem.solve(solver)
    # Display the results.
    # TODO(Grisha): move packaging to a separate function.
    result: Dict[str, Any] = {}
    result["problem_status"] = pulp.LpStatus[problem.status]
    result["problem_objective_value"] = pulp.value(problem.objective)
    # TODO(Grisha): maybe store in a dict? e.g., `{order_i: q_base_asterisk_i}`.
    result["q_base_asterisk"] = [var.varValue for var in q_base_asterisk]
    # TODO(Grisha): double-check that time is in seconds.
    result["solution_time_in_secs"] = round(problem.solutionTime, 2)
    return result


def get_tulip_problem_and_variables(
    orders: List[dtuimord.Order],
) -> Tuple[pulp.LpProblem, List[pulp.LpVariable], List[pulp.LpVariable]]:
    """
    Return the basic tulip problem and variables.

    :param orders: list of limit orders
    :return: tuple, with elements as follows:
      - pulp problem
      - list of pulp variables q_pi_star
    """
    _LOG.debug(hprint.to_str("orders"))
    n_orders = len(orders)
    hdbg.dassert_lt(0, n_orders)
    hdbg.dassert_container_type(orders, list, dtuimord.Order)
    # Initialize the model.
    problem = pulp.LpProblem("TuLiP", pulp.LpMaximize)
    # Specify the executed quantities vars. Setting the lower bound to zero
    # allows to omit the >= 0 constraint.
    q_pi_star = [
        pulp.LpVariable(f"q_pi_star_{i}", lowBound=0) for i in range(n_orders)
    ]
    q_tau_star = [
        pulp.LpVariable(f"q_tau_star_{i}", lowBound=0) for i in range(n_orders)
    ]
    # Objective function. Maximize the total exchanged volume.
    # problem.setObjective(pulp.lpSum(
    #     [q_pi_star[i] + q_tau_star[i] for i in range(n_orders)]
    # ))
    problem += pulp.lpSum(q_pi_star[i] + q_tau_star[i] for i in range(n_orders))
    # Constraints.
    # Impose limit order quantity constraint.
    for i in range(n_orders):
        problem += q_pi_star[i] <= orders[i].quantity
    # Impose limit order price constraint.
    for i in range(n_orders):
        # For the purposes of implementation, we should condition on the
        # direction of the inequality.
        if orders[i].action_as_int == 1:
            problem += q_tau_star[i] <= q_pi_star[i] * orders[i].limit_price
        elif orders[i].action_as_int == -1:
            problem += q_tau_star[i] >= q_pi_star[i] * orders[i].limit_price
    # Impose constraints on the token level: the amount of sold tokens must match that
    # of bought tokens for each token.
    tokens = list(
        set(
            [order.base_token for order in orders]
            + [order.quote_token for order in orders]
        )
    )
    for token in tokens:
        problem += (
            pulp.lpSum(
                -orders[i].action_as_int
                * q_pi_star[i]
                * (1 if orders[i].base_token == token else 0)
                + orders[i].action_as_int
                * q_tau_star[i]
                * (1 if orders[i].quote_token == token else 0)
                for i in range(n_orders)
            )
            == 0
        )
    return problem, q_pi_star, q_tau_star


# TODO(Paul): Reorganize code.
def run_daoswap_solver(
    orders: List[dtuimord.Order],
) -> Dict[str, Any]:
    """
    Find the maximum exchanged volume given the constraints.

    :param orders: buy / sell orders
    :return: solver's output in human-readable format
    """
    problem, q_pi_star, q_tau_star = get_tulip_problem_and_variables(orders)
    # # Non-LP constraint:
    # # `TypeError: Non-constant expressions cannot be multiplied`
    # if impose_single_clearing_price:
    #     for i in range(n_orders):
    #         pi = orders[i].base_token
    #         tau = orders[i].quote_token
    #         for j in range(i + 1, n_orders):
    #             if orders[j].base_token == pi and orders[j].quote_token == tau:
    #                 problem += (
    #                     q_pi_star[i] * q_tau_star[j] - q_tau_star[i] * q_pi_star[j] == 0
    #                 )
    #             elif orders[j].quote_token == pi and orders[j].base_token == tau:
    #                 problem += (
    #                     q_pi_star[i] * q_pi_star[j] - q_tau_star[i] * q_tau_star[j] == 0
    #                 )
    # Use the default solver and suppress the solver's log.
    # solver = pulp.getSolver("PULP_CBC_CMD", msg=0)
    solver = pulp.getSolver("PULP_CBC_CMD")
    problem.solve(solver)
    # Display the results.
    # TODO(Grisha): move packaging to a separate function.
    result: Dict[str, Any] = {}
    result["problem_status"] = pulp.LpStatus[problem.status]
    result["problem_objective_value"] = pulp.value(problem.objective)
    result["q_pi_star"] = [var.varValue for var in q_pi_star]
    result["q_tau_star"] = [var.varValue for var in q_tau_star]
    # TODO(Grisha): double-check that time is in seconds.
    result["solution_time_in_secs"] = round(problem.solutionTime, 2)
    #
    result_df = dtuimord.convert_orders_to_dataframe(orders)
    result_df["q_pi_star"] = result["q_pi_star"]
    result_df["q_tau_star"] = result["q_tau_star"]
    result_df["effective_price"] = (
        result_df["q_tau_star"] / result_df["q_pi_star"]
    )
    return result_df


def run_daocross_solver(
    orders: List[dtuimord.Order],
    prices: Dict[str, float],
) -> Dict[str, Any]:
    """
    Find the maximum exchanged volume given the constraints.

    :param orders: buy / sell orders
    :return: solver's output in human-readable format
    """
    problem, q_pi_star, q_tau_star = get_tulip_problem_and_variables(orders)
    #
    _LOG.debug(hprint.to_str("prices"))
    hdbg.dassert_isinstance(prices, dict)
    hdbg.dassert_lt(0, len(prices))
    # Impose unique clearing price constraint
    n_orders = len(orders)
    for i in range(n_orders):
        hdbg.dassert_in(orders[i].base_token, prices)
        base_price = prices[orders[i].base_token]
        hdbg.dassert_in(orders[i].quote_token, prices)
        quote_price = prices[orders[i].quote_token]
        price_quote_per_base = quote_price / base_price
        # For the purposes of implementation, we should condition on the
        # direction of the inequality.
        if orders[i].action_as_int == 1:
            problem += q_tau_star[i] == q_pi_star[i] * price_quote_per_base
        elif orders[i].action_as_int == -1:
            problem += q_tau_star[i] == q_pi_star[i] * price_quote_per_base
    # Use the default solver and suppress the solver's log.
    solver = pulp.getSolver("PULP_CBC_CMD", msg=0)
    problem.solve(solver)
    # Display the results.
    # TODO(Grisha): move packaging to a separate function.
    result: Dict[str, Any] = {}
    result["problem_status"] = pulp.LpStatus[problem.status]
    result["problem_objective_value"] = pulp.value(problem.objective)
    # TODO(Grisha): maybe store in a dict? e.g., `{order_i: q_base_asterisk_i}`.
    result["q_pi_star"] = [var.varValue for var in q_pi_star]
    result["q_tau_star"] = [var.varValue for var in q_tau_star]
    # TODO(Grisha): double-check that time is in seconds.
    result["solution_time_in_secs"] = round(problem.solutionTime, 2)
    #
    result_df = dtuimord.convert_orders_to_dataframe(orders)
    result_df["q_pi_star"] = result["q_pi_star"]
    result_df["q_tau_star"] = result["q_tau_star"]
    result_df["effective_price"] = (
        result_df["q_tau_star"] / result_df["q_pi_star"]
    )
    return result_df
