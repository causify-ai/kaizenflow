"""
Import as:

import dataflow.system.system_signature as dtfsysysig
"""

import logging
from typing import Any, Dict, List, Tuple

import pandas as pd

import core.config as cconfig
import core.real_time as creatime
import dataflow.core as dtfcore
import dataflow.model as dtfmod
import dataflow.system.system as dtfsyssyst
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hunit_test as hunitest
import oms as oms

_LOG = logging.getLogger(__name__)

# #############################################################################
# Utils
# #############################################################################

# There are various layers in the code:
# 1) functions checking invariants
#    - E.g., check_SystemConfig, check_portfolio_stats
# 2) functions that compute signature of various pieces (currently inside
#    SystemTester)
#    - E.g., get_..._signature
# 3) get_signature, get_signature_from_result_bundle
#    - Compute a more complex signature putting together smaller pieces

# TODO(gp): The difference between get_signature and _get_signature_from_result_bundle
#  is that in the first we use the signature of ResultBundle instead of research_pnl.
#  (when we don't have a ForecastEvaluator to compute the research PnL).
#  Can we unify?


# TODO(gp): This doesn't freeze the research PnL but freezes part of the result
#  bundle.
# TODO(gp): Can we use directly _get_signature_from_result_bundle()?
def get_signature(
    system_config: cconfig.Config, result_bundle: dtfcore.ResultBundle, col: str
) -> str:
    """
    Compute the signature of a test in terms of:

    - System signature
    - Result bundle signature
    """
    txt: List[str] = []
    # 1) System config signature.
    txt.append(hprint.frame("system_config"))
    txt.append(str(system_config))
    # 2) Result bundle signature.
    txt.append(hprint.frame(col))
    result_df = result_bundle.result_df
    data = result_df[col].dropna(how="all").round(3)
    # TODO(Grisha): We should use `hpandas.df_to_str(num_rows=None)` but it displays only
    # `df.head(5)` and `df.tail(5)` while in the System tests we want to freeze the whole
    # df. Adjust `hpandas.df_to_str()` accordingly and use it here.
    data_str = data.round(3).to_string()
    txt.append(data_str)
    #
    res = "\n".join(txt)
    return res


# TODO(gp): This uses the System config for the ForecastEvaluator.
# TODO(gp): Should we add also the signature of result bundle as from get_signature()?
def get_signature_from_result_bundle(
    system: dtfsyssyst.System,
    result_bundles: List[dtfcore.ResultBundle],
    add_system_config: bool,
    add_run_signature: bool,
    add_order_processor_signature: bool,
) -> str:
    """
    Compute the signature of a test in terms of:

    - System config signature
    - Run signature
    - Order processor signature (if present)
    - System log dir signature
    """
    portfolio = system.portfolio
    dag_runner = system.dag_runner
    txt = []
    # 1) System config signature.
    hdbg.dassert(system.is_fully_built)
    if add_system_config:
        # TODO(gp): Use `check_SystemConfig`.
        txt.append(hprint.frame("system_config"))
        txt.append(str(system.config))
    # 2) Run signature.
    if add_run_signature:
        # TODO(gp): This should be factored out.
        txt.append(hprint.frame("compute_run_signature"))
        hdbg.dassert_isinstance(result_bundles, list)
        result_bundle = result_bundles[-1]
        # result_bundle.result_df = result_bundle.result_df.tail(40)
        # Check output.
        forecast_evaluator_from_prices_dict = system.config[
            "research_forecast_evaluator_from_prices"
        ].to_dict()
        txt_tmp = compute_run_signature(
            dag_runner,
            portfolio,
            result_bundle,
            forecast_evaluator_from_prices_dict,
        )
        txt.append(txt_tmp)
    # 3) Order processor signature.
    if add_order_processor_signature:
        order_processor = system.config.get("order_processor_object", None)
        if order_processor:
            txt.append(hprint.frame("OrderProcessor execution signature"))
            txt.append(order_processor.get_execution_signature())
    # 4) System log dir signature.
    txt.append(hprint.frame("system_log_dir signature"))
    log_dir = system.config["system_log_dir"]
    txt_tmp = hunitest.get_dir_signature(
        log_dir, include_file_content=False, remove_dir_name=True
    )
    txt.append(txt_tmp)
    #
    actual = "\n".join(txt)
    # Remove the following line:
    # ```
    # db_connection_object: <connection object; dsn: 'user=aljsdalsd
    #   password=xxx dbname=oms_postgres_db_local
    #   host=cf-spm-dev4 port=12056', closed: 0>
    # ```
    actual = hunitest.filter_text("db_connection_object", actual)
    actual = hunitest.filter_text("log_dir:", actual)
    actual = hunitest.filter_text("trade_date:", actual)
    return actual


def get_events_signature(events: List[creatime.Event]) -> str:
    # TODO(gp): Add a short snippet in the docstring of how the output looks like.
    # TODO(gp): Use events.to_str()
    # TODO(gp): actual -> txt
    actual = ["# event signature=\n"]
    events_as_str = "\n".join(
        [
            event.to_str(
                include_tenths_of_secs=False,
                include_wall_clock_time=False,
            )
            for event in events
        ]
    )
    actual.append("events_as_str=\n%s" % events_as_str)
    actual = "\n".join(actual)
    return actual


def get_portfolio_signature(
    portfolio: oms.Portfolio, num_periods: int = 10
) -> Tuple[str, pd.Series]:
    """
    Return the portfolio signature in terms of:

    - portfolio historical statistics
    """
    # TODO(gp): Add a short snippet in the docstring of how the output looks like.
    # TODO(gp): actual -> txt
    # 1) Portfolio signature.
    actual = ["\n# portfolio signature=\n"]
    actual.append(str(portfolio))
    actual = "\n".join(actual)
    # 2) Portfolio historical statistics.
    statistics = portfolio.get_historical_statistics(num_periods=num_periods)
    pnl = statistics["pnl"]
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("pnl=\n%s", pnl)
    return actual, pnl


# TODO(gp): -> get_historical_simulation_run
def compute_run_signature(
    dag_runner: dtfcore.DagRunner,
    portfolio: oms.Portfolio,
    result_bundle: dtfcore.ResultBundle,
    forecast_evaluator_from_prices_dict: Dict[str, Any],
) -> str:
    """
    Return the signature of an historical simulation in terms of:

    - Signature of the DagRunner events
    - Portfolio signature
    - Research PnL signature
    - Correlation between
    """
    # TODO(gp): Add a short snippet in the docstring of how the output looks like.
    # TODO(gp): actual -> txt
    hdbg.dassert_isinstance(result_bundle, dtfcore.ResultBundle)
    # Check output.
    actual = []
    # 1) Signature of the DagRunner events.
    events = dag_runner.events
    actual.append(get_events_signature(events))
    # 2) Portfolio signature.
    signature, pnl = get_portfolio_signature(portfolio)
    actual.append(signature)
    # 3) Research PnL signature using the ForecastEvaluator.
    signature, research_pnl = get_research_pnl_signature(
        result_bundle,
        forecast_evaluator_from_prices_dict,
    )
    actual.append(signature)
    # 4) Compute correlation between simulated PnL and research PnL.
    if min(pnl.count(), research_pnl.count()) > 1:
        # Drop leading NaNs and burn the first PnL entry.
        research_pnl = research_pnl.dropna().iloc[1:]
        tail = research_pnl.size
        # We create new series because the portfolio times may be
        # dis-aligned from the research bar times.
        pnl1 = pd.Series(pnl.tail(tail).values)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("portfolio pnl=\n%s", pnl1)
        #
        corr_samples = min(tail, pnl1.size)
        pnl2 = pd.Series(research_pnl.tail(corr_samples).values)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("research pnl=\n%s", pnl2)
        #
        correlation = pnl1.corr(pnl2)
        actual.append("\n# pnl agreement with research pnl\n")
        actual.append(f"corr = {correlation:.3f}")
        actual.append(f"corr_samples = {corr_samples}")
    # Assemble results.
    actual = "\n".join(map(str, actual))
    return actual


# TODO(gp): This should go first.
def get_research_pnl_signature(
    result_bundle: dtfcore.ResultBundle,
    forecast_evaluator_from_prices_dict: Dict[str, Any],
) -> Tuple[str, pd.Series]:
    hdbg.dassert_isinstance(result_bundle, dtfcore.ResultBundle)
    hdbg.dassert(
        forecast_evaluator_from_prices_dict,
        "`forecast_evaluator_from_prices_dict` must be nontrivial",
    )
    # TODO(gp): @all use actual.append(hprint.frame("system_config"))
    #  to separate the sections of the output.
    actual = ["\n# forecast_evaluator_from_prices signature=\n"]
    # Build the ForecastEvaluator.
    forecast_evaluator = dtfmod.ForecastEvaluatorFromPrices(
        **forecast_evaluator_from_prices_dict["init"],
    )
    result_df = result_bundle.result_df
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("result_df=\n%s", hpandas.df_to_str(result_df))
    # 1) Get the signature of the ForecastEvaluator.
    signature = forecast_evaluator.to_str(
        result_df,
        style=forecast_evaluator_from_prices_dict["style"],
        **forecast_evaluator_from_prices_dict["kwargs"],
    )
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("signature=\n%s", signature)
    actual.append(signature)
    # 2) Get the portfolio.
    dfs = forecast_evaluator.compute_portfolio(
        result_df,
        style=forecast_evaluator_from_prices_dict["style"],
        **forecast_evaluator_from_prices_dict["kwargs"],
    )
    hdbg.dassert_in("stats", dfs.keys())
    stats = dfs["stats"]
    # Assemble.
    actual = "\n".join(map(str, actual))
    research_pnl = stats["pnl"]
    return actual, research_pnl


def log_forecast_evaluator_portfolio(
    result_bundle: dtfcore.ResultBundle,
    forecast_evaluator_from_prices_dict: Dict[str, Any],
    log_dir: str,
) -> None:
    # Build ForecastEvaluatorFromPrices.
    hdbg.dassert(
        forecast_evaluator_from_prices_dict,
        "`forecast_evaluator_from_prices_dict` must be nontrivial",
    )
    forecast_evaluator = dtfmod.ForecastEvaluatorFromPrices(
        **forecast_evaluator_from_prices_dict["init"],
    )
    #
    hdbg.dassert_isinstance(result_bundle, dtfcore.ResultBundle)
    result_df = result_bundle.result_df
    # Save Portfolio info.
    forecast_evaluator.log_portfolio(
        result_df,
        log_dir,
        style=forecast_evaluator_from_prices_dict["style"],
        **forecast_evaluator_from_prices_dict["kwargs"],
    )


# TODO(gp): This should be used in all TestCase right after the dag_runner is
#  complete.
def check_SystemConfig(self: Any, system: dtfsyssyst.System, tag: str) -> None:
    """
    Check the signature of a System config against a golden reference.

    :param tag: it is used to distinguish multiple configs (e.g., when a
        test builds multiple Systems and we want to freeze all of them)
    """
    # Ensure that the System was built and thus the config is stable.
    hdbg.dassert(system.is_fully_built)
    txt = []
    # Add the config.
    tag = "system_config." + tag
    txt.append(hprint.frame(tag))
    txt.append(str(system.config))
    #
    txt = "\n".join(txt)
    # Remove artifacts that are specific of a run and unstable.
    txt = hunitest.filter_text("db_connection_object", txt)
    txt = hunitest.filter_text("log_dir:", txt)
    txt = hunitest.filter_text("trade_date:", txt)
    # Sometimes we want to check that the config has not changed, but it
    # was just reordered. In this case we:
    # - set `sort=True`
    # - make sure that there are no changes
    # - set `sort=False`
    # - update the golden outcomes with the updated config
    # TODO(gp): Do not commit `sort = True`.
    # sort = True
    sort = False
    self.check_string(txt, tag=tag, purify_text=True, sort=sort)


# TODO(gp): Consider passing system.portfolio directly to reduce the interface
#  surface.
def check_portfolio_state(
    self: Any, system: dtfsyssyst.System, expected_last_timestamp: pd.Timestamp
) -> None:
    """
    Check some high level property of the Portfolio, e.g., that Portfolio:

    - Contains data up to a certain `expected_last_timestamp`
    - Is not empty at the end of the simulation
    """
    portfolio = system.portfolio
    # 1) The simulation runs up to the expected time.
    last_timestamp = portfolio.get_last_timestamp()
    self.assert_equal(str(last_timestamp), str(expected_last_timestamp))
    # 2) The portfolio has some holdings.
    has_no_holdings = portfolio.has_no_holdings()
    self.assertFalse(has_no_holdings)
