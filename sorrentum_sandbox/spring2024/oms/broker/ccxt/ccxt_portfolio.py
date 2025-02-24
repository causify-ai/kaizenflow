"""
Import as:

import oms.broker.ccxt.ccxt_portfolio as obccccpo
"""

import logging
from typing import Any, Dict, List, Optional

import market_data as mdata
import oms.broker.ccxt.ccxt_broker_instances as obccbrin
import oms.broker.ccxt.dataframe_ccxt_broker as obcdccbr
import oms.hsecrets as omssec
import oms.portfolio.dataframe_portfolio as opdapor

_LOG = logging.getLogger(__name__)


class CcxtPortfolio(opdapor.DataFramePortfolio):
    """
    A Portfolio that stores the information in a dataframe backed by
    CcxtBroker.
    """

    def __init__(
        self,
        *args: Any,
        **kwargs: Dict[str, Any],
    ):
        """
        Constructor.
        """
        super().__init__(
            *args,
            **kwargs,
        )


def get_CcxtPortfolio_prod_instance1(
    run_mode: str,
    strategy_id: str,
    market_data: mdata.MarketData,
    column_remap: Optional[Dict[str, str]],
    universe_version: Optional[str],
    secret_identifier: Optional[omssec.SecretIdentifier],
    pricing_method: str,
    asset_ids: Optional[List[int]],
    broker_config: Dict[str, Any],
    log_dir: str,
    mark_to_market_col: str,
) -> CcxtPortfolio:
    """
    Initialize the `CcxtPortfolio` with cash using `CcxtBroker`.

    :param run_mode: see `_Cx_ProdSystem`
    :param strategy_id: see `Broker`
    :param market_data: see `Broker`
    :param column_remap: see `Broker`
    :param universe_version: see `CcxtBroker`
    :param secret_identifier: see `CcxtBroker`
    :param pricing_method: see `Portfolio` ctor
    :param asset_ids: see `Portfolio.from_cash()`
    :param broker_config: config to initialize `Broker` with
    :param log_dir: directory for portfolio logging
    """
    # We prefer to configure code statically (e.g., without switches) but in this
    # case the prod Portfolio vs its paper-trading version are so close (and we
    # want to keep them close) that we use a switch.
    if run_mode == "prod":
        # Build `CcxtBroker` that is connected to the real exchange.
        broker = obccbrin.get_CcxtBroker_prod_instance1(
            strategy_id,
            market_data,
            universe_version,
            secret_identifier,
            broker_config,
            log_dir,
        )
    elif run_mode in ["paper_trading", "simulation"]:
        _LOG.warning("Running the system with the `DataFrameCcxtBroker`")
        # TODO(Grisha): revisit. Do we need stage for paper_trading and simulation?
        # Use the `DataFrameCcxtBroker`, i.e. no interaction with
        # the real exchange.
        stage = "preprod"
        broker = obcdccbr.get_DataFrameCcxtBroker_instance1(
            strategy_id,
            market_data,
            universe_version,
            stage,
            column_remap=column_remap,
        )
    elif run_mode == "simulation_with_replayed_fills":
        _LOG.warning(
            "Running the system with the `ReplayedFillsDataFrameBroker`."
        )
        # TODO(Grisha): this is a hack to make the corresponding test work,
        # however we need to get the path from the `system.config`.
        # pylint: disable=line-too-long
        log_dir = "/app/dataflow_orange/system/Cx/test/outcomes/Test_run_Cx_prod_simulation_with_replayed_fills.test1/tmp.scratch/log"
        # pylint: enable=line-too-long
        # TODO(Grisha): infer `stage` from `system.config["secret_identifier"]`.
        stage = "preprod"
        broker = obccbrin.get_CcxtReplayedFillsDataFrameBroker_instance1(
            log_dir,
            strategy_id,
            market_data,
            universe_version,
            stage,
            column_remap=column_remap,
        )
    else:
        raise ValueError(f"Invalid run_mode='{run_mode}'")
    # Build CcxtPortfolio.
    initial_cash = 700
    portfolio = CcxtPortfolio.from_cash(
        broker,
        mark_to_market_col,
        pricing_method,
        initial_cash=initial_cash,
        asset_ids=asset_ids,
    )
    return portfolio
