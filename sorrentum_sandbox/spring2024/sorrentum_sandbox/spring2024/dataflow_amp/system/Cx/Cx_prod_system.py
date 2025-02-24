"""
Import as:

import dataflow_amp.system.Cx.Cx_prod_system as dtfasccprsy
"""

import argparse
import datetime
import logging

import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import dataflow.system as dtfsys
import dataflow_amp.system.Cx.Cx_builders as dtfasccxbu
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import im_v2.common.universe as ivcu
import market_data as mdata
import oms
import reconciliation as reconcil

# TODO(Grisha): add `hsecrets` to the `oms` package?
import oms.hsecrets as omssec

_LOG = logging.getLogger(__name__)


# #############################################################################
# Cx_ProdSystem
# #############################################################################


# TODO(Grisha): seems more general than Cx. Try to share code across Cx and Ex.
class _Cx_ProdSystemMixin(dtfsys.Time_ForecastSystem_with_DataFramePortfolio):
    def __init__(self, run_mode: str):
        """
        Construct object.

        :param run_mode: prod run mode
            - "prod": real-time `MarketData`, real `CcxtBroker`
            - "paper_trading": real-time `MarketData`, `DataFrameCcxtBroker`
            - "simulation": replayed `MarketData`, `DataFrameCcxtBroker`
            - "simulation_with_replayed_fills": replayed `MarketData`,
                `CcxtReplayedFillsDataFrameBroker`
        """
        # In general, we abhor these switches, but in this case we want to make
        # sure that the research systems are as close as possible to the prod
        # system.
        hdbg.dassert_in(
            # TODO(Grisha): rename the `system_run_modes`, see CmTask5830.
            run_mode,
            [
                "prod",
                "paper_trading",
                "simulation",
                "simulation_with_replayed_fills",
            ],
        )
        self._run_mode = run_mode
        super().__init__()

    def dassert_trade_date(self) -> None:
        """
        Check that trade date is a today's date.
        """
        trade_date = self.config["cf_config"]["trade_date"]
        trade_date = pd.Timestamp(trade_date).date()
        today_date = datetime.date.today()
        _LOG.info(hprint.to_str("trade_date today_date"))
        if trade_date != today_date:
            msg = "trade_date=%s is different than today_date=%s: exiting" % (
                trade_date,
                today_date,
            )
            _LOG.error(msg)
            raise ValueError(msg)


class Cx_ProdSystem_v1_20220727(_Cx_ProdSystemMixin):
    def __init__(
        self,
        dag_builder_ctor_as_str: str,
        *,
        run_mode: str = "prod",
    ) -> None:
        """
        Construct object.

        :param dag_builder_ctor_as_str: a pointer to a `DagBuilder` constructor,
            e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`
        :param process_forecasts_config: config for the forecasts processing.
            Includes params for optimizer and order submission
        :param run_mode: see the parent class for description
        """
        # This needs to be initialized before the other constructor.
        self._dag_builder = dtfcore.get_DagBuilder_from_string(
            dag_builder_ctor_as_str
        )
        super().__init__(run_mode)

    def _get_system_config_template(
        self,
    ) -> cconfig.Config:
        # TODO(Grisha): propagate `fit_at_beginning`.
        system_config = dtfsys.get_SystemConfig_template_from_DagBuilder(
            self._dag_builder
        )
        # For simulation the even loop object is set when running the system
        # using `solipsism_context()`.
        if self._run_mode in ["prod", "paper_trading"]:
            # A `ProdSystem` should not be simulated, and so `event_loop` is None.
            system_config["event_loop_object"] = None
        system_config["run_mode"] = self._run_mode
        return system_config

    def _get_market_data(self) -> mdata.MarketData:
        if self._run_mode in ["prod", "paper_trading"]:
            asset_ids_key = ("market_data_config", "asset_ids")
            asset_ids = self.config.get_and_mark_as_used(asset_ids_key)
            # TODO(Grisha): consider exposing `db_stage` to a `system.config`
            # separately.
            # Secret identifier contains API keys info which includes:
            # - exchange name
            # - stage; this is also a database stage
            # - account_type, e.g., for trading or testnet
            # - id as a number
            secret_identifier = self.config.get_and_mark_as_used(
                "secret_identifier_config",
            )
            db_stage = secret_identifier.stage
            # TODO(Grisha): this is a hack. The builder function should accept
            # a System object, but since we call the builder inside analysis
            # notebooks that do not have a System object, we pass it to the
            # interface as a work-around.
            table_name = self.config.get_and_mark_as_used(
                ("market_data_config", "im_client_config", "table_name")
            )
            sleep_in_secs = self.config.get_and_mark_as_used(
                ("market_data_config", "sleep_in_secs")
            )
            market_data = dtfasccxbu.get_Cx_RealTimeMarketData_prod_instance1(
                asset_ids,
                db_stage,
                table_name=table_name,
                sleep_in_secs=sleep_in_secs,
            )
        elif self._run_mode in ["simulation", "simulation_with_replayed_fills"]:
            # TODO(Grisha): pass via system.config.
            column_remap = {
                "start_timestamp": "start_datetime",
                "end_timestamp": "end_datetime",
            }
            market_data = dtfsys.get_ReplayedMarketData_from_file_from_System(
                self, column_remap
            )
        else:
            raise ValueError(f"Invalid run_mode='{self._run_mode}'")
        return market_data

    def _get_dag(self) -> dtfcore.DAG:
        if self._run_mode in ["prod", "paper_trading"]:
            self.dassert_trade_date()
        # TODO(gp): This should be passed through the config to make it customizable.
        # TODO(Grisha): the problem is that the introspection trick does not work with `self`.
        # self.config["dag_function_as_str"] = "dataflow_amp.system.Cx.get_Cx_dag_prod_instance1"
        # func_as_str = f'{self.config["dag_function_as_str"]}({self})'
        # dag = hintros.get_function_from_string(func_as_str)
        dag = dtfasccxbu.get_Cx_dag_prod_instance1(self)
        return dag

    # TODO(gp): We should dump the state of the portfolio and load it back.
    def _get_portfolio(self) -> oms.Portfolio:
        portfolio = dtfasccxbu.get_Cx_portfolio_prod_instance1(self)
        return portfolio

    def _get_dag_runner(self) -> dtfsys.RealTimeDagRunner:
        dag_runner = dtfsys.get_RealTimeDagRunner_from_System(self)
        return dag_runner


# #############################################################################
# Universe
# #############################################################################

# def _apply_top_20_universe(
#     system: dtfsys.System,
# ) -> dtfsys.System:
#     # TODO(gp): We could simulate also this part so we should move it out.
#     if False:
#         asset_ids = [
#             17085,
#             13684,
#             10971,
#             16187,
#             15794,
#             # 1435348,
#             10253,
#             # 82562,
#             14592,
#             16878,
#         ]
#         asset_ids = sorted(
#             list(set(reuniver.get_eg_universe("eg_v2_0-top200") + asset_ids))
#         )
#     else:
#         # Run small universe of 20.
#         asset_ids = sorted(
#             list(set(reuniver.get_eg_universe("top20_sp500_2022Q1-all")))
#         )
#     _LOG.info("len(asset_ids)=%s", len(asset_ids))
#     system.config["market_data_config", "asset_ids"] = asset_ids
#     return system


# #############################################################################


def get_Cx_ProdSystem_instance_v1_20220727(
    args: argparse.Namespace,
) -> dtfsys.Time_ForecastSystem_with_DatabasePortfolio:
    """
    Return the Cx System and the corresponding config.

    This is the production model.
    """
    # - Build the ProdSystem.
    dag_builder_ctor_as_str = args.dag_builder_ctor_as_str
    run_mode = args.run_mode
    system = Cx_ProdSystem_v1_20220727(dag_builder_ctor_as_str, run_mode=run_mode)
    # - Market data.
    # - Set table name.
    system.config[
        "market_data_config", "im_client_config", "table_name"
    ] = "ccxt_ohlcv_futures"
    # In production Systems we want to get the data ASAP, so there is no reason
    # to go sleep for long.
    system.config["market_data_config", "sleep_in_secs"] = 0.1
    # - Set trading period.
    system.config["trading_period"] = "5T"
    # The System assumes that a `DagBuilder` object is responsible for supplying
    # history amount, so passing None. However, a user can override the config
    # value if needed.
    system.config["market_data_config", "days"] = None
    # Set the latest universe version.
    universe_version = ivcu.get_latest_universe_version()
    system.config["market_data_config", "universe_version"] = universe_version
    # - Dag builder.
    system.config["dag_builder_config", "fast_prod_setup"] = False
    system.config["dag_property_config", "force_free_nodes"] = True
    system.config[
        "dag_property_config", "debug_mode_config"
    ] = cconfig.Config.from_dict(
        {
            "save_node_io": "df_as_pq",
            "save_node_df_out_stats": True,
            "profile_execution": True,
        }
    )
    start_time = args.start_time
    if start_time is not None:
        start_time = hdateti.timestamp_as_str_to_timestamp(start_time)
        # TODO(Grisha): consider moving the logic to AirFlow; we want to
        # start the prod system a bit earlier than the 1st bar begins to
        # account for possible delays.
        start_time = start_time - pd.Timedelta(minutes=1)
    system.config["dag_runner_config", "wake_up_timestamp"] = start_time
    system.config[
        "dag_runner_config", "rt_timeout_in_secs_or_time"
    ] = args.run_duration
    # - Portfolio.
    # Set default Portfolio config.
    system = dtfsys.apply_Portfolio_config(system)
    # TODO(gp): This order_extra_params is something that applies only to prod so
    #  it needs to be done.
    system.config["portfolio_config", "order_extra_params"] = cconfig.Config()
    system.config["portfolio_config", "retrieve_initial_holdings_from_db"] = False
    # - CF config.
    cf_config = {
        "strategy": args.strategy,
        "liveness": args.liveness,
        "instance_type": args.instance_type,
        "trade_date": args.trade_date,
    }
    system.config["cf_config"] = cconfig.Config.from_dict(cf_config)
    # - More overrides from the command line.
    # Store all logs under single location.
    system.config["system_log_dir"] = args.dst_dir
    system.config["secret_identifier_config"] = omssec.SecretIdentifier(
        args.exchange, args.stage, args.account_type, args.secret_id
    )
    # Fill `process_forecasts_node_dict`.
    order_config = dtfasccxbu.get_Cx_order_config_instance1()
    optimizer_config = dtfasccxbu.get_Cx_optimizer_config_instance1()
    log_dir = reconcil.get_process_forecasts_dir(system.config["system_log_dir"])
    system = dtfasccxbu.apply_ProcessForecastsNode_config(
        system, order_config, optimizer_config, log_dir
    )
    _LOG.info(
        "\n"
        + hprint.frame("System config before command line overrides.")
        + "\n"
        + hprint.indent(str(system.config))
        + "\n"
        + hprint.frame("End config")
    )
    # Override System config.
    config = system.config
    config = cconfig.apply_config_overrides_from_command_line(config, args)
    system.set_config(config)
    _LOG.info(
        "\n"
        + hprint.frame("System config after command line overrides.")
        + "\n"
        + hprint.indent(str(system.config))
        + "\n"
        + hprint.frame("End config")
    )
    # - Apply the universe.
    # Add asset ids to the `SystemConfig` after all values are overridden
    # because asset ids should correspond to the universe version.
    # TODO(Grisha): consider exposing `vendor` and `mode` to SystemConfig.
    vendor = "CCXT"
    mode = "trade"
    asset_ids = ivcu.get_vendor_universe_as_asset_ids(
        system.config["market_data_config", "universe_version"], vendor, mode
    )
    system.config["market_data_config", "asset_ids"] = asset_ids
    return system
