"""
Import as:

import oms.broker.ccxt.ccxt_logger as obcccclo
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from tqdm.autonotebook import tqdm

import core.config as cconfig
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hprint as hprint
import helpers.hwall_clock_time as hwacltim
import oms.fill as omfill
import oms.order.order as oordorde

# TODO(Danya): Redefining to avoid circular dependency with `abstract_ccxt_broker`.
CcxtData = Dict[str, Any]

_LOG = logging.getLogger(__name__)


# TODO(gp): This should go after CcxtLogger.
def load_oms_fills(logs_dir: str) -> List[List[omfill.Fill]]:
    """
    Load OMS `Fill`.

    :param logs_dir: same as in `CcxtLogger`
    :return: OMS `Fill`, where the innermost list contains per-asset `Fill`
        and the outermost list contains per-bar `Fill`
    """
    # Initialize logger.
    logger = CcxtLogger(logs_dir, mode="read")
    # Read OMS fills and OMS parent orders from logs.
    oms_fills_file_paths = logger._get_files(logger._oms_fills_dir)
    oms_parent_orders_file_paths = logger._get_files(
        logger._oms_parent_orders_dir, file_extension="json"
    )
    # `Fills` and `Orders` should have equal number of file paths.
    hdbg.dassert_eq(len(oms_fills_file_paths), len(oms_parent_orders_file_paths))
    oms_fills = []
    for order_path, fill_path in zip(
        oms_parent_orders_file_paths, oms_fills_file_paths
    ):
        orders_data = hio.from_json(order_path, use_types=True)
        fills_data = hio.from_json(fill_path, use_types=True)
        for order_data, fill_data in zip(orders_data, fills_data):
            # Get OMS `Order`.
            order = oordorde.Order(
                order_data["creation_timestamp"],
                order_data["asset_id"],
                order_data["type_"],
                order_data["start_timestamp"],
                order_data["end_timestamp"],
                order_data["curr_num_shares"],
                order_data["diff_num_shares"],
                order_id=order_data["order_id"],
                extra_params=order_data["extra_params"],
            )
            # Get OMS `Fill`.
            fill = omfill.Fill(
                order,
                fill_data["timestamp"],
                fill_data["num_shares"],
                fill_data["price"],
            )
            oms_fills.append([fill])
    return oms_fills


class CcxtLogger:
    """
    Write and read logs for `CcxtBroker`.

    The logs include:
    - `oms.Fills` for all the CCXT trades
    - CCXT order responses for all children orders
    - Submitted child orders

    For more info on logs structure, see
    `docs/trade_execution/ck.ccxt_broker_logs_schema.reference.md`
    """

    # Default locations of log files.
    CCXT_CHILD_ORDER_FILLS = "child_order_fills"
    CCXT_FILLS = os.path.join(CCXT_CHILD_ORDER_FILLS, "ccxt_fills")
    CCXT_CHILD_ORDER_TRADES = os.path.join(CCXT_CHILD_ORDER_FILLS, "ccxt_trades")
    OMS_FILLS = os.path.join(CCXT_CHILD_ORDER_FILLS, "oms_fills")
    CCXT_CHILD_ORDER_RESPONSE = "ccxt_child_order_responses"
    OMS_CHILD_ORDERS = "oms_child_orders"
    OMS_PARENT_ORDERS = "oms_parent_orders"
    BID_ASK = "bid_ask"
    # This location contains bid/ask data used for the full experiment.
    # This is in contrast with BID_ASK, which stores files per each child order
    # wave(see CmampTask7262)
    BID_ASK_FULL = "bid_ask_full"
    POSITIONS = "positions"
    EXCHANGE_MARKETS = "exchange_markets"
    LEVERAGE_INFO = "leverage_info"
    BALANCES = "balances"
    BROKER_CONFIG = "broker_config.json"
    ARGS_FILE = "args.json"

    def __init__(self, log_dir: str, *, mode: str = "read"):
        """
        Constructor.

        :param log_dir: target directory to put logs in,
            e.g. "/shared_data/system_log_dir_20230315_30minutes/".
        :param mode: there are two modes:
            - write: the logger will write log files in `log_dir`
            - read: the logger will read log files from `log_dir`
        """
        self._log_dir = log_dir
        hdbg.dassert_is_not(self._log_dir, None)
        if mode == "read":
            fields = [
                "args",
                "broker_config",
                "ccxt_order_responses",
                "oms_parent_orders",
                "ccxt_trades",
                "oms_child_orders",
                "oms_fills",
                "ccxt_fills",
                "exchange_markets",
                "leverage_info",
                "bid_ask_files",
                "positions",
                "balances",
                "reduce_only_order_responses",
                "reduce_only_child_orders",
            ]
            self._has_data = {field: False for field in fields}
            self._init_log_subdirectories()
        # We aim to log the initial exchange position once and avoid redundant
        # position logging. This strategy simplifies the process of mock/replay
        # for the exchange, as position updates are based on the executed
        # orders rather than continuous logging. By reducing the frequency of
        # position logging, we enhance logging efficiency and streamline
        # debugging when replaying exchange scenarios.
        self._enable_positions_logging = True

    # #########################################################################
    # Write logs
    # #########################################################################

    def log_broker_config(self, broker_configuration: Dict[str, Any]) -> None:
        """
        Log the broker configuration.

        The config is saved as a JSON file in the root log directory, e.g.
        `{log_dir}/broker_config.json`

        :param broker_configuration: broker config as dict, e.g.
        ```
        {
            "bid_ask_lookback": "60S",
            "child_order_quantity_computer": {
                "object_type": "StaticSchedulingChildOrderQuantityComputer"
            },
            "limit_price_computer": {
                "max_deviation": 0.01,
                "object_type": "LimitPriceComputerUsingSpread",
                "passivity_factor": 0.55
            },
            "log_dir": "/app/system_log_dir",
            "raw_data_reader_signature": "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0",
            "secret_identifier": "binance.preprod.trading.4",
            "stage": "preprod",
            "universe_version": "v7.4"
        }
        ```
        """
        file_path = os.path.join(self._log_dir, self.BROKER_CONFIG)
        hio.to_json(file_path, broker_configuration)

    def log_child_order(
        self,
        get_wall_clock_time: Callable,
        oms_child_order: oordorde.Order,
        ccxt_child_order_response: CcxtData,
        extra_info: CcxtData,
    ) -> None:
        """
        Log a child order with CCXT order info and additional parameters.

        OMS child order information and corresponding CCXT order response are
        saved into a JSON file in a format like:
            ```
            {log_dir}/oms_child_orders/...
            {log_dir}/ccxt_child_order_responses/...
            ```

        :param get_wall_clock_time: function to retrieve the current wall clock
            time
        :param oms_child_order: an order to be logged
        :param ccxt_child_order_response: CCXT order structure from the exchange,
            corresponding to the child order
        :param extra_info: values to include into the logged order, for example
            `{'bid': 0.277, 'ask': 0.279}`
        """
        if "reduce_only" in oms_child_order.extra_params:
            # Save reduce-only order in a separate subdirectory. This is done to
            # separate market orders used for flattening the account from child
            # orders generated by the system.
            child_orders_log_dir = os.path.join(self._log_dir, "reduce_only")
        else:
            child_orders_log_dir = self._log_dir
        # Add `extra_info` to the OMS child order.
        logged_oms_child_order = oms_child_order.to_dict()
        hdbg.dassert_not_intersection(
            logged_oms_child_order.keys(),
            extra_info.keys(),
            msg="There should be no overlapping keys",
        )
        logged_oms_child_order.update(extra_info)
        # Add CCXT id to the child order, -1 if there was no response.
        logged_oms_child_order["ccxt_id"] = logged_oms_child_order[
            "extra_params"
        ].get("ccxt_id", -1)
        # Get current timestamp and bar.
        wall_clock_time_str = hdateti.timestamp_to_str(
            get_wall_clock_time(), include_msec=True
        )
        bar_timestamp = hwacltim.get_current_bar_timestamp(
            as_str=True, include_msec=True
        )
        order_asset_id = logged_oms_child_order["asset_id"]
        # 1) Save OMS child orders.
        incremental = True
        oms_order_log_dir = os.path.join(
            child_orders_log_dir, self.OMS_CHILD_ORDERS
        )
        hio.create_dir(oms_order_log_dir, incremental)
        oms_order_file_name = (
            f"{order_asset_id}_{bar_timestamp}.{wall_clock_time_str}.json"
        )
        oms_order_file_name = os.path.join(oms_order_log_dir, oms_order_file_name)
        hio.to_json(oms_order_file_name, logged_oms_child_order, use_types=True)
        _LOG.debug(
            "Saved OMS child orders log file %s",
            hprint.to_str("oms_order_file_name"),
        )
        # 2) Save CCXT order response.
        ccxt_log_dir = os.path.join(
            child_orders_log_dir, self.CCXT_CHILD_ORDER_RESPONSE
        )
        hio.create_dir(ccxt_log_dir, incremental)
        response_file_name = (
            f"{order_asset_id}_{bar_timestamp}.{wall_clock_time_str}.json"
        )
        response_file_name = os.path.join(ccxt_log_dir, response_file_name)
        hio.to_json(response_file_name, ccxt_child_order_response, use_types=True)
        _LOG.debug(
            "Saved CCXT child order response log file %s",
            hprint.to_str("response_file_name"),
        )

    def log_ccxt_fills(
        self,
        get_wall_clock_time: Callable,
        ccxt_fills: List[CcxtData],
    ) -> None:
        """
        Save fills and trades to separate files.

        :param log_dir: dir to store logs in. The data structure looks like:
            ```
            {log_dir}/child_order_fills/ccxt_fills/ccxt_fills_20230515-112313.json
            ```
        :param get_wall_clock_time: retrieve the current wall clock time
        :param ccxt_fills: list of CCXT fills loaded from CCXT
            - The CCXT objects correspond to closed order (i.e., not in execution
              on the exchange any longer)
            - Represent the cumulative fill for the closed orders across all
              trades
        """
        fills_log_dir = os.path.join(self._log_dir, self.CCXT_CHILD_ORDER_FILLS)
        hio.create_dir(fills_log_dir, incremental=True)
        # Save CCXT fills, e.g.,
        # log_dir/child_order_fills/ccxt_fills/ccxt_fills_20230511-114405.json
        timestamp_str = hdateti.timestamp_to_str(get_wall_clock_time())
        ccxt_fills_file_name = os.path.join(
            self._log_dir, self.CCXT_FILLS, f"ccxt_fills_{timestamp_str}.json"
        )
        _LOG.debug(hprint.to_str("ccxt_fills_file_name"))
        hio.to_json(ccxt_fills_file_name, ccxt_fills, use_types=True)

    def log_ccxt_trades(
        self,
        wall_clock_time: Callable,
        ccxt_trades: List[CcxtData],
    ) -> None:
        """
        Save fills and trades to separate files.

        :param log_dir: dir to store logs in. The data structure looks like:
            ```
            {log_dir}/child_order_fills/ccxt_trades/ccxt_trades_20230515-112313.json
            ```
        :param wall_clock_time: the actual wall clock time of the running system
            for accounting
        :param ccxt_trades: list of CCXT trades corresponding to the CCXT fills
        """
        fills_log_dir = os.path.join(self._log_dir, self.CCXT_CHILD_ORDER_FILLS)
        hio.create_dir(fills_log_dir, incremental=True)
        timestamp_str = hdateti.timestamp_to_str(wall_clock_time())
        # Save CCXT trades, e.g.,
        # log_dir/child_order_fills/ccxt_trades/ccxt_trades_20230511-114405.json
        ccxt_trades_file_name = os.path.join(
            self._log_dir,
            self.CCXT_CHILD_ORDER_TRADES,
            f"ccxt_trades_{timestamp_str}.json",
        )
        _LOG.debug(hprint.to_str("ccxt_trades_file_name"))
        hio.to_json(ccxt_trades_file_name, ccxt_trades, use_types=True)

    def log_oms_fills(
        self, get_wall_clock_time: Callable, oms_fills: List[omfill.Fill]
    ) -> None:
        """
        Log OMS fills into a separate file.

        :param get_wall_clock_time: retrieve the current wall clock time
        :param oms_fills: list of `oms.Fill` objects
            - The OMS fill objects correspond to `oms.Fill` objects before they
              are submitted upstream to the Portfolio (e.g., before child
              orders are merged into parent orders for accounting by the
              `Portfolio`).
        """
        if self._log_dir is None:
            _LOG.warning("No log dir provided.")
            return
        # Save OMS fills, e.g.,
        # log_dir/child_order_fills/oms_fills/oms_fills_20230511-114405.json
        if oms_fills:
            oms_fills = [fill.to_dict() for fill in oms_fills]
        timestamp_str = hdateti.timestamp_to_str(get_wall_clock_time())
        oms_fills_file_name = os.path.join(
            self._log_dir,
            self.OMS_FILLS,
            f"oms_fills_{timestamp_str}.json",
        )
        _LOG.debug(hprint.to_str("oms_fills_file_name"))
        hio.to_json(oms_fills_file_name, oms_fills, use_types=True)

    # TODO(gp): Reorganize the format to be a bit regular
    # 1) always OMS data before than CCXT
    # 2) flatten the directory structure
    # 3) use the same format with `bar_timestamp` and `get_wall_clock_time`
    #    f"XYZ.{bar_timestamp}.{get_wall_clock_time}.json"`
    # 4) clarify when orders are parent or child

    def log_oms_parent_orders(
        self,
        get_wall_clock_time: Callable,
        oms_parent_orders: List[oordorde.Order],
    ) -> None:
        """
        Log OMS parent orders before dividing them into child orders.

        The orders are logged before they are submitted, in the same format
        as they are passed from `TargetPositionAndOrderGenerator`.

        :param log_dir: dir to store logs in. The data structure looks like:
            ```
            {log_dir}/oms_parent_orders/oms_parent_orders_{bar_timestamp}.json.{wallclock_time}
            # E.g.,
            {log_dir}/oms_parent_orders/oms_parent_orders_20230622-084000.json.20230622-084421
            ```
        :param get_wall_clock_time: retrieve the current wall clock time
        :param oms_parent_orders: list of OMS parent orders
        """
        # Generate file name based on the bar timestamp.
        # TODO(gp): P1, @all Factor out the logic to format the timestamps.
        wall_clock_time = hdateti.timestamp_to_str(
            get_wall_clock_time(), include_msec=True
        )
        bar_timestamp = hwacltim.get_current_bar_timestamp(
            as_str=True, include_msec=True
        )
        # Create enclosing dir.
        oms_parent_orders_log_filename = os.path.join(
            self._log_dir,
            self.OMS_PARENT_ORDERS,
            f"oms_parent_orders_{bar_timestamp}.json",
        )
        # Create enclosing dir.
        hio.create_enclosing_dir(oms_parent_orders_log_filename, incremental=True)
        # Check if there is a parent order log for previous wave of child orders.
        # The parent order log contains information which is updated
        # with each new wave, e.g. CCXT IDs of bound child orders.
        hio.rename_file_if_exists(
            oms_parent_orders_log_filename,
            wall_clock_time,
            before_extension=False,
        )
        # Serialize and save parent orders as JSON file.
        oms_parent_orders = [order.to_dict() for order in oms_parent_orders]
        hio.to_json(
            oms_parent_orders_log_filename, oms_parent_orders, use_types=True
        )
        _LOG.debug(hprint.to_str("oms_parent_orders_log_filename"))

    def log_exchange_markets(
        self,
        get_wall_clock_time: Callable,
        exchange_markets: CcxtData,
        leverage_info: CcxtData,
    ) -> None:
        """
        Log exchange info on markets and leverage info from CCXT Exchange as
        JSON.

        The use-case `ReplayedCcxtExchange` where these information assist in
        replaying an experiment perfectly.

        :param get_wall_clock_time: retrieve the current wall clock time
        :param exchange_markets: info on markets provided by CCXT Exchange
            Download exchange_markets. See more about the output format:
            https://docs.ccxt.com/#/README?id=market-structure.
        :param leverage_info: leverage info returned for the desired `symbol` by
            CCXT Exchange.
            Download leverage information. See more about the output format:
            https://docs.ccxt.com/#/README?id=leverage-tiers-structure.
        """
        # Generate file name based on the bar timestamp.
        wall_clock_time = hdateti.timestamp_to_str(get_wall_clock_time())
        # Create enclosing dir.
        exchange_market_log_filename = os.path.join(
            self._log_dir,
            self.EXCHANGE_MARKETS,
            f"exchange_markets.{wall_clock_time}.json",
        )
        leverage_info_log_filename = os.path.join(
            self._log_dir,
            self.LEVERAGE_INFO,
            f"leverage_info.{wall_clock_time}.json",
        )
        # Create enclosing dir.
        hio.to_json(
            exchange_market_log_filename, exchange_markets, use_types=True
        )
        hio.to_json(leverage_info_log_filename, leverage_info, use_types=True)
        _LOG.debug(hprint.to_str("exchange_market_log_filename"))

    def log_bid_ask_data(
        self,
        get_wall_clock_time: Callable,
        bid_ask_data: pd.DataFrame,
        *,
        log_full_experiment_data: bool = False,
    ) -> None:
        """
        Log bid_ask data for replay the CCXT exchange. The logging happens
        immediately after data is fetched via `RawDataReader` prior to any
        transformations.

        :param get_wall_clock_time: retrieve the current wall clock time
        :param bid_ask_data: data frame received from `RawDataReader`
        """
        # Generate file name based on the bar timestamp.
        wall_clock_time = hdateti.timestamp_to_str(get_wall_clock_time())
        bar_timestamp = hwacltim.get_current_bar_timestamp(
            as_str=True, include_msec=True
        )
        bid_ask_log_filename = os.path.join(
            self._log_dir,
            self.BID_ASK_FULL if log_full_experiment_data else self.BID_ASK,
            f"{bar_timestamp}.{wall_clock_time}.csv",
        )
        # Create enclosing dir.
        hio.create_enclosing_dir(bid_ask_log_filename, incremental=True)
        # Bid ask data has timestamp index which is also needed.
        bid_ask_data.to_csv(bid_ask_log_filename, index=True)

    def log_positions(
        self,
        get_wall_clock_time: Callable,
        positions: CcxtData,
    ) -> None:
        """
        Log current positions from CCXT Exchange as JSON.

        Using replayed exchange, It is possible to reconstruct the
        portfolio at any given moment using the CCXT order responses,
        but the missing piece of information is the initial USDT
        balance.

        :param get_wall_clock_time: retrieve the current wall clock time
        :param positions: info current positions provided by CCXT
            Exchange Download positions. See more about the output
            format: https://docs.ccxt.com/#/README?id=positions.
        """
        dir_name = self.POSITIONS
        file_name_tag = "positions"
        if self._enable_positions_logging:
            self._log_raw_data(
                dir_name, file_name_tag, get_wall_clock_time, positions
            )
            self._enable_positions_logging = False

    def log_balance(
        self,
        get_wall_clock_time: Callable,
        balance: Dict[str, any],
    ) -> None:
        """
        Log current balance from CCXT Exchange as JSON.

        Using replayed exchange, It is possible to reconstruct the portfolio at
        any given moment using the CCXT order responses, but the missing piece
        of information is the initial USDT balance which will now be obtained
        using this balance log.

        :param get_wall_clock_time: retrieve the current wall clock time
        :param balance: info current balance provided by CCXT Exchange
            `fetchBalance`. See more about the output format:
            https://docs.ccxt.com/#/README?id=balance-structure.
        """
        dir_name = self.BALANCES
        file_name_tag = "balance"
        self._log_raw_data(dir_name, file_name_tag, get_wall_clock_time, balance)

    # #########################################################################
    # Read logs
    # #########################################################################

    def load_all_data(
        self,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load all data.

        :param convert_to_dataframe: loads the data into a Pandas DataFrame
            instead of the default Dict.
        :param abort_on_missing_data: allow to continue or abort when some data
            (e.g., data corresponding to `ccxt_order_responses`) is missing.
            Typically, we assume that all the data should be present. This param is
            useful when we want to read data from previous runs that don't have all
            the information after updating the format, or incomplete data.
        :return: dictionary storing the logged data
        """
        all_data = {
            "args": self.load_args(abort_on_missing_data=abort_on_missing_data),
            "broker_config": self.load_broker_config(
                abort_on_missing_data=abort_on_missing_data
            ),
            "ccxt_order_responses": self.load_ccxt_order_response(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "oms_parent_orders": self.load_oms_parent_order(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "ccxt_trades": self.load_ccxt_trades(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "oms_child_orders": self.load_oms_child_order(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "oms_fills": self.load_oms_fills(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "ccxt_fills": self.load_ccxt_fills(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "exchange_markets": self.load_exchange_markets(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "leverage_info": self.load_leverage_info(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "bid_ask_files": self.load_bid_ask_files(
                abort_on_missing_data=abort_on_missing_data,
            ),
            "positions": self.load_positions(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            "balances": self.load_balances(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
            ),
            # Load reduce-only orders response placed for account flattening.
            "reduce_only_order_responses": self.load_ccxt_order_response(
                convert_to_dataframe=convert_to_dataframe,
                abort_on_missing_data=abort_on_missing_data,
                reduce_only=True,
            ),
        }
        return all_data

    def load_broker_config(
        self, *, abort_on_missing_data: bool = True
    ) -> Dict[str, Any]:
        """
        Load the broker configuration.

        For example of the data see `log_broker_configuration`.

        :return: broker configuration as dict
        """
        data_key = "broker_config"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return {}
        file_name = "broker_config.json"
        file_path = os.path.join(self._log_dir, file_name)
        broker_config = hio.from_json(file_path)
        return broker_config

    def load_ccxt_order_response(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
        reduce_only: bool = False,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load CCXT order responses from the JSON files in the log directory as
        Dict or DataFrame.

        :param convert_to_dataframe: same interface as `load_all_data()`.
        :param abort_on_missing_data: same interface as `load_all_data()`.
        :param reduce_only parameter if True, only reduce_only orders are loaded.

        The order response is a CCXT order structure, as described in
        https://docs.ccxt.com/#/?id=order-structure.

        E.g., a timeseries from return DataFrame looks like:
        ```
        info                    {'orderId': '7954906695', 'symbol': 'APEUSDT',...
        order                   7954906695
        client_order_id         x-xcKtGhcub89989e55d47273a3610a9
        timestamp               1678898138582
        datetime                2023-03-15 16:35:38.582000+00:00
        last_trade_timestamp    None
        symbol                  APE/USDT
        order_type              limit
        time_in_force           GTC
        post_only               False
        reduce_only             False
        side                    buy
        order_price             4.12
        stop_price              NaN
        order_amount            10.0
        cost                    0.0
        average                 NaN
        filled                  0.0
        remaining               10.0
        status                  open
        fee                     NaN
        trades                  []
        fees                    []
        order_update_timestamp  1678898138582
        order_update_datetime   1970-01-01 00:27:58.898138582+00:00
        ```
        """
        # Get the files.
        if reduce_only:
            data_key = "reduce_only_order_responses"
            if not self._has_data[data_key]:
                self._fatal_missing_data(data_key, abort_on_missing_data)
                return []
            dir_name = self._reduce_only_order_responses_dir
        else:
            data_key = "ccxt_order_responses"
            if not self._has_data[data_key]:
                self._fatal_missing_data(data_key, abort_on_missing_data)
                return []
            dir_name = self._ccxt_order_responses_dir
        ccxt_order_responses = self._load_raw_data(dir_name)
        if convert_to_dataframe:
            ccxt_order_responses = (
                self._convert_ccxt_order_structures_to_dataframe(
                    ccxt_order_responses
                )
            )
        return ccxt_order_responses

    def load_oms_parent_order(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load parent orders from the JSON files in the log directory as Dict or
        DataFrame.

        :param convert_to_dataframe: same interface as
            `load_all_data()`.
        :param abort_on_missing_data: same interface as
            `load_all_data()`.
        """
        # Get the files.
        # Specify the file extension as JSON, as OMS parent order folder
        # contains multiple copies of the same parent orders with extra
        # params updated at each wave of child orders.
        # Latest OMS parent orders have the file name pattern:
        # `oms_parent_orders_{bar_timestamp}.json`.
        # Outdated OMS parent order for previous waves:
        # `oms_parent_orders_{bar_timestamp}.json.{wall_clock_time}`.
        # `wall_clock_time` indicates the point up to which these logs were relevant.
        data_key = "oms_parent_orders"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        files = self._get_files(
            self._oms_parent_orders_dir, file_extension="json"
        )
        # Read all the files.
        parent_orders = []
        # Load individual orders as pd.Series.
        for path in tqdm(files, desc=f"Loading '{self._oms_parent_orders_dir}'"):
            # Load parent order files from JSON format.
            data = hio.from_json(path, use_types=True)
            parent_orders.extend(data)
        if convert_to_dataframe:
            parent_orders = self._convert_oms_parent_orders_to_dataframe(
                parent_orders
            )
        return parent_orders

    def load_oms_child_order(
        self,
        *,
        unpack_extra_params: bool = False,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
        reduce_only: bool = False,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load child orders from the JSON files in the log directory as Dict or
        DataFrame.

        :param unpack_extra_params: if True, unpack `extra_params` field into
            output DataFrame columns
        :param convert_to_dataframe: same interface as `load_all_data()`.
        :param abort_on_missing_data: same interface as `load_all_data()`.
        :param reduce_only parameter if True, only reduce_only orders are loaded.

        Example of data returned as DataFrame:
        ```
                creation_timestamp              asset_id    type_  \
        order_id
        20       2023-03-15 16:35:37.825835+00:00  6051632686  limit
        21       2023-03-15 16:35:38.718960+00:00  8717633868  limit

                start_timestamp               end_timestamp  \
        order_id
        20       2023-03-15 16:35:37.825835+00:00 2023-03-15 16:36:37.825835+00:00
        21       2023-03-15 16:35:38.718960+00:00 2023-03-15 16:36:38.718960+00:00

                curr_num_shares  diff_num_shares  tz            passivity_factor    \
        order_id
        20       0.0          10.0        America/New_York   0.55
        21       0.0          -1.0        America/New_York    0.55

                latest_bid_price  latest_ask_price  bid_price_mean  ask_price_mean  \
        order_id
        20       4.120             4.121    4.125947    4.126974
        21       15.804            15.805   15.818162   15.819432

                used_bid_price    used_ask_price  limit_price      ccxt_id  \
        order_id
        20       latest_bid_price  latest_ask_price    4.12045   7954906695
        21       latest_bid_price  latest_ask_price    15.80455  14412582631
        ```
        """

        # Get the files.
        if reduce_only:
            data_key = "reduce_only_child_orders"
            if not self._has_data[data_key]:
                self._fatal_missing_data(data_key, abort_on_missing_data)
                return []
            dir_name = self._reduce_only_child_order_dir
        else:
            data_key = "oms_child_orders"
            if not self._has_data[data_key]:
                self._fatal_missing_data(data_key, abort_on_missing_data)
                return []
            dir_name = self._oms_child_orders_dir
        child_orders = self._load_raw_data(dir_name)
        if convert_to_dataframe:
            child_orders = self._convert_oms_child_orders_to_dataframe(
                child_orders,
                unpack_extra_params=unpack_extra_params,
            )
        return child_orders

    def load_ccxt_trades(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load trades from the JSON files in the log directory as Dict or
        DataFrame.

        :param convert_to_dataframe: same interface as `load_all_data()`.
        :param abort_on_missing_data: same interface as `load_all_data()`.

        Example of data returned as Dict:
        ```
        {
        "info": {
            "symbol": "APEUSDT",
            "id": "356819245",
            "orderId": "8077704766",
            "side": "SELL",
            "price": "4.0400",
            "qty": "6",
            "realizedPnl": 0.0,
            "marginAsset": "USDT",
            "quoteQty": "24.2400",
            "commission": "0.00969600",
            "commissionAsset": "USDT",
            "time": "1679560540879",
            "positionSide": "BOTH",
            "buyer": False,
            "maker": False
        },
            "timestamp": 1679560540879,
            "datetime": "Timestamp('2023-03-23 08:35:40.879000+0000', tz='UTC')",
            "symbol": "APE/USDT",
            "asset_id": 6051632686,
            "id": 356819245,
            "order": 8077704766,
            "type": None,
            "side": "sell",
            "takerOrMaker": "taker",
            "price": 4.04,
            "amount": 6.0,
            "cost": 24.24,
            "fee": {
                "cost": 0.009696,
                "currency": "USDT"
            },
            "fees": [
                {
                    "currency": "USDT",
                    "cost": 0.009696
                }
            ]
        }
        ```

        Example of data returned as DataFrame:
        ```
                                timestamp    symbol         id       order  side  \
        0 2022-09-29 16:46:39.509000+00:00  APE/USDT  282773274  5772340563  sell
        1 2022-09-29 16:51:58.567000+00:00  APE/USDT  282775654  5772441841   buy
        2 2022-09-29 16:57:00.267000+00:00  APE/USDT  282779084  5772536135   buy
        3 2022-09-29 17:02:00.329000+00:00  APE/USDT  282780259  5772618089  sell
        4 2022-09-29 17:07:03.097000+00:00  APE/USDT  282781536  5772689853   buy

        takerOrMaker  price  amount    cost      fees fees_currency realized_pnl
        0        taker  5.427     5.0  27.135  0.010854          USDT            0
        1        taker  5.398     6.0  32.388  0.012955          USDT   0.14500000
        2        taker  5.407     3.0  16.221  0.006488          USDT            0
        3        taker  5.395     9.0  48.555  0.019422          USDT  -0.03900000
        4        taker  5.381     8.0  43.048  0.017219          USDT   0.07000000
        ```
        """
        data_key = "ccxt_trades"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        dir_name = self._ccxt_trades_dir
        ccxt_child_order_trades = self._load_raw_data(dir_name, append_list=False)
        if convert_to_dataframe:
            # Convert fills to DataFrame.
            ccxt_child_order_trades_duped = (
                self._convert_ccxt_trades_json_to_dataframe(
                    ccxt_child_order_trades
                )
            )
            # Remove full duplicates for fills.
            # Note: generally fills are loaded in bulk via CCXT `fetchMyTrades()`
            # method, which allows only for queries based on time range and full
            # symbol. In some cases, there is an overlap between queries, which leads
            # to full duplicates appearing in the resulting DataFrame.
            # Duplicates are determined via timestamp, `id` of the trade and `order` id.
            ccxt_child_order_trades = (
                ccxt_child_order_trades_duped.drop_duplicates(
                    subset=["timestamp", "id", "order"], keep="last"
                )
            )
            # TODO(pp): Use hdbg.to_perc to get a better output.
            _LOG.debug(
                "%s duplicates were removed from original data.",
                ccxt_child_order_trades_duped.shape[0]
                - ccxt_child_order_trades.shape[0],
            )
        return ccxt_child_order_trades

    def load_oms_fills(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load the oms fills from the JSON files in the log directory as Dict or
        DataFrame.

        :param convert_to_dataframe: same interface as `load_all_data()`.
        :param abort_on_missing_data: same interface as `load_all_data()`.

        Example of data returned as Dict:
        ```
        {
            "asset_id": 5115052901,
            "fill_id": 6,
            "timestamp": "2023-05-23T11:58:50.201000+00:00",
            "num_shares": 93.0,
            "price": 69.5733
        }
        ```

        Example of data returned as DataFrame:
        ```
           asset_id         fill_id  timestamp                      num_shares    price
        0  8717633868        2  2023-05-23T11:58:49.172000+00:00       1.000  14.7540
        1  1467591036        4  2023-05-23T11:58:49.687000+00:00       0.001  27.3304
        2  5115052901        6  2023-05-23T11:58:50.201000+00:00      93.000  69.5733
        3  3401245610        7  2023-05-23T11:58:50.456000+00:00       3.000   6.5460
        ```
        """
        data_key = "oms_fills"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        dir_name = self._oms_fills_dir
        oms_child_order_fills = self._load_raw_data(dir_name, append_list=False)
        if convert_to_dataframe:
            oms_child_order_fills = pd.DataFrame(oms_child_order_fills)
        return oms_child_order_fills

    def load_ccxt_fills(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load the CCXT filled order from the JSON files in the log directory as
        Dict or DataFrame.

        :param convert_to_dataframe: same interface as `load_all_data()`.
        :param abort_on_missing_data: same interface as `load_all_data()`.

        These representations correspond to closed orders.

        Example of one entity of input JSON data:
        ```
        {
        "info": {
            "orderId": "2187830797",
            "symbol": "CTKUSDT",
            "status": "FILLED",
            "clientOrderId": "x-xcKtGhcuda5dde8563a5c1568a5893",
            "price": "0.74810",
            "avgPrice": "0.74810",
            "origQty": "93",
            "executedQty": "93",
            "cumQuote": "69.57330",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "reduceOnly": False,
            "closePosition": False,
            "side": "BUY",
            "positionSide": "BOTH",
            "stopPrice": "0",
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "origType": "LIMIT",
            "time": "1684843130201",
            "updateTime": 1684843130201
        },
        "id": 2187830797,
        "clientOrderId": "x-xcKtGhcuda5dde8563a5c1568a5893",
        "timestamp": 1684843130201,
        "datetime": "Timestamp('2023-05-23 11:58:50.201000+0000', tz='UTC')",
        "lastTradeTimestamp": None,
        "symbol": "CTK/USDT",
        "type": "limit",
        "timeInForce": "GTC",
        "postOnly": False,
        "reduceOnly": False,
        "side": "buy",
        "price": 0.7481,
        "stopPrice": "nan",
        "amount": 93.0,
        "cost": 69.5733,
        "average": 0.7481,
        "filled": 93.0,
        "remaining": 0.0,
        "status": "closed",
        "fee": "nan",
        "trades": [],
        "fees": []
        }
        ```

        E.g., a timeseries from return DataFrame looks like:
        ```
        info                      {'orderId': '14901643572', 'symbol': 'AVAXUSDT...
        order                      14901643572
        client_order_id                x-xcKtGhcu8261da0e4a2533b528e0e2
        timestamp                   1684843129172
        datetime                    2023-05-23 11:58:49.172000+00:00
        last_trade_timestamp             None
        symbol                     AVAX/USDT
        order_type                   limit
        time_in_force                 GTC
        post_only                   False
        reduce_only                  False
        side                       buy
        order_price                  14.761
        stop_price                   NaN
        order_amount                 1.0
        cost                      14.754
        average                    14.754
        filled                      1.0
        remaining                   0.0
        status                     closed
        fee                       NaN
        trades                     []
        fees                      []
        order_update_timestamp          1684843129172
        order_update_datetime           1970-01-01 00:28:04.843129172+00:00
        ```
        """
        data_key = "ccxt_fills"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        dir_name = self._ccxt_fills_dir
        ccxt_fills = self._load_raw_data(dir_name, append_list=False)
        if convert_to_dataframe:
            ccxt_fills = self._convert_ccxt_order_structures_to_dataframe(
                ccxt_fills
            )
        return ccxt_fills

    def load_bid_ask_files(
        self,
        *,
        abort_on_missing_data: bool = True,
        load_data_for_full_period: bool = False,
    ) -> List:
        """
        Load the list of bid ask file paths.

        Bid ask files are in CSV format, these contain the raw data logged
        directly from `RawDataReader` prior to any transformations.

        :param abort_on_missing_data: same interface as `load_all_data()`.
        :param load_data_for_full_period: if True loads data fetched for the
         entire experiment independently of the run, otherwise loads data logged during
         the experiment run.

        Example of data returned:
        [
        "log/bid_ask/20231009_212500.20231009-172500.csv",
        "log/bid_ask/20231009_212500.20231009-172600.csv",
        "log/bid_ask/20231009_212500.20231009-172700.csv",
        "log/bid_ask/20231009_212500.20231009-172800.csv",
        ]
        """
        data_key = (
            "bid_ask_full_files" if load_data_for_full_period else "bid_ask_files"
        )
        bid_ask_dir = (
            self._bid_ask_full_dir
            if load_data_for_full_period
            else self._bid_ask_dir
        )
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        files = self._get_files(bid_ask_dir)
        return files

    def load_exchange_markets(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load the exchange markets data from the JSON files in the log directory
        as Dict.

        The exchange markets has the exchange structure, as described in
        https://docs.ccxt.com/#/?id=exchange-structure.

        :param convert_to_dataframe: same interface as
            `load_all_data()`.
        :param abort_on_missing_data: same interface as
            `load_all_data()`.
        """
        data_key = "exchange_markets"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        dir_name = self._exchange_markets_dir
        exchange_markets = self._load_raw_data(dir_name)
        if convert_to_dataframe:
            exchange_markets = self._convert_raw_data_to_dataframe(
                exchange_markets
            )
        return exchange_markets

    def load_leverage_info(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load the leverage info data from JSON files in the log directory as
        Dict.

        The leverage info has the leverage tiers structure, as described
        in
        https://docs.ccxt.com/#/?id=leverage-tiers-structure.

        :param convert_to_dataframe: same interface as
            `load_all_data()`.
        :param abort_on_missing_data: same interface as
            `load_all_data()`.
        """
        data_key = "leverage_info"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        dir_name = self._leverage_info_dir
        leverage_info = self._load_raw_data(dir_name)
        if convert_to_dataframe:
            leverage_info = self._convert_raw_data_to_dataframe(leverage_info)
        return leverage_info

    def load_positions(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load the positions data from JSON.

        :param convert_to_dataframe: same interface as
            `load_all_data()`.
        :param abort_on_missing_data: same interface as
            `load_all_data()`.
        """
        data_key = "positions"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        dir_name = self._positions_dir
        positions = self._load_raw_data(dir_name, append_list=False)
        # Convert data type str to float.
        for position in positions:
            position["info"]["positionAmt"] = float(
                position["info"]["positionAmt"]
            )
        if convert_to_dataframe:
            positions = pd.DataFrame(positions)
        return positions

    def load_balances(
        self,
        *,
        convert_to_dataframe: bool = False,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load the balance data from JSON.

        The balance JSON files has the balance structure, as described
        in
        https://docs.ccxt.com/#/README?id=balance-structure.

        :param convert_to_dataframe: same interface as
            `load_all_data()`.
        :param abort_on_missing_data: same interface as
            `load_all_data()`.
        """
        data_key = "balances"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return []
        dir_name = self._balances_dir
        balances = self._load_raw_data(dir_name, append_list=True)
        if convert_to_dataframe:
            balances = pd.DataFrame(balances)
        return balances

    def load_args(
        self,
        *,
        abort_on_missing_data: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Load the arguments used for the run from JSON.

        The args JSON files has the following structure,
        ```
        {
            "secret_id": 4,
            "max_parent_order_notional": 100,
            "randomize_orders": true,
            "log_dir": "/shared_data/sameep/daily_experiments/20231205_experiment3",
            "clean_up_before_run": true,
            "clean_up_after_run": true,
            "parent_order_duration_in_min": 5,
            "num_parent_orders_per_bar": 5,
            "num_bars": 6,
            "close_positions_using_twap": false,
            "db_stage": "prod",
            "child_order_execution_freq": "10S",
            "incremental": false,
            "log_level": "DEBUG"
        }
        ```

        :param abort_on_missing_data: same interface as
            `load_all_data()`.
        """
        data_key = "args"
        if not self._has_data[data_key]:
            self._fatal_missing_data(data_key, abort_on_missing_data)
            return {}
        file_name = self.ARGS_FILE
        file_path = os.path.join(self._log_dir, file_name)
        args = hio.from_json(file_path)
        return args

    # #########################################################################
    # Private methods
    # #########################################################################

    @staticmethod
    def _get_files(
        log_dir: str, *, file_extension: Optional[str] = None
    ) -> List[str]:
        """
        Get a list of files from the directory.

        :param file_extension: added to the file search pattern, e.g.
            "json". Can be used with or without the initial "."
        """
        pattern = "*"
        if file_extension:
            pattern += file_extension
        only_files = True
        use_relative_paths = False
        files: List[str] = hio.listdir(
            log_dir, pattern, only_files, use_relative_paths
        )
        files.sort()
        return files

    @staticmethod
    def _convert_ccxt_order_structures_to_dataframe(
        ccxt_order_structures: List[CcxtData],
    ) -> pd.DataFrame:
        """
        Convert a list of CCXT order structures to a DataFrame.

        `child_order_response` and `ccxt_fill` are exactly the same data
        structures (see http://docs.ccxt.com/#/?id=order-structure) that
        we encode as `obcaccbr.CcxtData` (`Dict[str, Any]` under the
        hood). Thus, we refer to the common data structure as
        `ccxt_order_structure` and use this function for both data
        structures.
        """
        ccxt_order_structures_series_list = []
        for ccxt_order_structure in ccxt_order_structures:
            # Skip the response JSON if it is empty.
            if (
                not ccxt_order_structure
                or ccxt_order_structure.get("empty") == True
            ):
                continue
            srs = pd.Series(
                ccxt_order_structure.values(), ccxt_order_structure.keys()
            )
            # Get order update Unix timestamp from the exchange.
            info_timestamp = ccxt_order_structure["info"]["updateTime"]
            srs["info_timestamp"] = info_timestamp
            # Convert to datetime.
            # Note: using 'coerce' since we expect the exchange to return a
            # correct timestamp, and raising would block the loading of the
            # DataFrame altogether.
            srs["info_datetime"] = pd.to_datetime(
                pd.to_numeric(info_timestamp, errors="coerce"),
                unit="ms",
                utc=True,
            )
            ccxt_order_structures_series_list.append(srs)
        ccxt_order_df = pd.concat(ccxt_order_structures_series_list, axis=1).T
        # Transform timestamp columns to UTC.
        ccxt_order_df = ccxt_order_df.map(
            lambda x: x.tz_convert("UTC") if isinstance(x, pd.Timestamp) else x
        )
        #  Check the timestamp logs in `CcxtBroker` and update the conversion accordingly.
        # Rename columns.
        ccxt_order_df = ccxt_order_df.rename(
            columns={
                "id": "order",
                "clientOrderId": "client_order_id",
                "lastTradeTimestamp": "last_trade_timestamp",
                "type": "order_type",
                "timeInForce": "time_in_force",
                "postOnly": "post_only",
                "reduceOnly": "reduce_only",
                "price": "order_price",
                "stopPrice": "stop_price",
                "amount": "order_amount",
                "info_timestamp": "order_update_timestamp",
                "info_datetime": "order_update_datetime",
            }
        )
        # Convert id data type to int.
        ccxt_order_df["order"] = ccxt_order_df["order"].astype(int)
        return ccxt_order_df

    @staticmethod
    def _normalize_fills_dataframe(fills_df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate a fills DataFrame and normalize for chaining
        `obccagfu._aggregate_fills()`.

        Ensure `df` is a DataFrame with certain columns and restricted values.

        :param df: a fills DataFrame as returned by
            `convert_fills_json_to_dataframe()`
        """
        # Sanity-check the DataFrame.
        hdbg.dassert_isinstance(fills_df, pd.DataFrame)
        required_cols = [
            "timestamp",
            "datetime",
            "side",
            "takerOrMaker",
            "price",
            "amount",
            "cost",
            "transaction_cost",
        ]
        hdbg.dassert_is_subset(required_cols, fills_df.columns)
        # Ensure categoricals lie in expected sets.
        hdbg.dassert_is_subset(fills_df["side"].unique(), ["buy", "sell"])
        hdbg.dassert_is_subset(
            fills_df["takerOrMaker"].unique(), ["taker", "maker", np.nan]
        )
        # Check self-consistency of prices/costs/amounts.
        hdbg.dassert_lte(
            ((fills_df["cost"] / fills_df["amount"]) - fills_df["price"]).sum(),
            1e-6,
        )
        #
        fills_df = fills_df.copy()
        fills_df["datetime"] = pd.to_datetime(fills_df["datetime"])
        # Assign additional datetime columns.
        fills_df["first_timestamp"] = fills_df["timestamp"]
        fills_df["last_timestamp"] = fills_df["timestamp"]
        fills_df["first_datetime"] = fills_df["datetime"]
        fills_df["last_datetime"] = fills_df["datetime"]
        # Accumulate buy/sell counts.
        fills_df["buy_count"] = (fills_df["side"] == "buy").astype(int)
        fills_df["sell_count"] = (fills_df["side"] == "sell").astype(int)
        # Accumulate taker/maker counts.
        fills_df["taker_count"] = (fills_df["takerOrMaker"] == "taker").astype(
            int
        )
        fills_df["maker_count"] = (fills_df["takerOrMaker"] == "maker").astype(
            int
        )
        # Process fills data for volume.
        fills_df["buy_volume"] = np.where(
            fills_df["side"] == "buy", fills_df["amount"], 0
        )
        fills_df["sell_volume"] = np.where(
            fills_df["side"] == "sell", fills_df["amount"], 0
        )
        fills_df["taker_volume"] = np.where(
            fills_df["takerOrMaker"] == "taker", fills_df["amount"], 0
        )
        fills_df["maker_volume"] = np.where(
            fills_df["takerOrMaker"] == "maker", fills_df["amount"], 0
        )
        # Process fills data for notional.
        fills_df["buy_notional"] = np.where(
            fills_df["side"] == "buy", fills_df["cost"], 0
        )
        fills_df["sell_notional"] = np.where(
            fills_df["side"] == "sell", fills_df["cost"], 0
        )
        fills_df["taker_notional"] = np.where(
            fills_df["takerOrMaker"] == "taker", fills_df["cost"], 0
        )
        fills_df["maker_notional"] = np.where(
            fills_df["takerOrMaker"] == "maker", fills_df["cost"], 0
        )
        return fills_df

    @staticmethod
    def _convert_oms_fills_to_dataframe(
        oms_fills: List[CcxtData],
    ) -> pd.DataFrame:
        """
        Convert a list of OMS fill dicts into a DataFrame.
        """
        oms_fills_df = pd.DataFrame(oms_fills)
        #
        expected_columns = [
            "asset_id",
            "fill_id",
            "timestamp",
            "num_shares",
            "price",
        ]
        hdbg.dassert_set_eq(oms_fills_df.columns, expected_columns)
        return oms_fills_df

    @staticmethod
    def _convert_raw_data_to_dataframe(
        raw_data_list: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Convert a list of raw data dicts into a DataFrame.
        """
        df = pd.DataFrame()
        for raw_data in raw_data_list:
            raw_data = pd.DataFrame.from_dict(raw_data, orient="index")
            df = pd.concat([df, raw_data])
        return df

    @staticmethod
    def _path_exists(path: str) -> bool:
        exists = os.path.exists(path)
        if not exists:
            txt = f"Path '{path}' doesn't exist!"
            _LOG.warning(txt)
        return exists

    @staticmethod
    def _fatal_missing_data(data_key: str, abort_on_missing_data: bool) -> None:
        if abort_on_missing_data:
            raise FileNotFoundError(
                "Missing required data for '%s': returning empty data", data_key
            )
        else:
            _LOG.warning(
                "Missing required data for '%s': continuing as per user request",
                data_key,
            )

    def _init_log_subdirectories(self) -> None:
        """
        Generate and store subdirectories with Broker logs.

        The directory is expected to follow the same structure, with
        fills and orders stored in '{log_dir}/'
        """
        # TODO(Sameep): Update the init to support the previous versions of the logs.
        # Will be added in CmTask5749.
        if self._log_dir is None:
            _LOG.info(
                "No log directory provided, loading log files is impossible."
            )
            return
        hdbg.dassert_path_exists(self._log_dir)
        # Check if the broker config is saved.
        # The presence of the config is not strictly enforced since earlier
        # experiments did not dump the config data.
        broker_config_file = os.path.join(self._log_dir, self.BROKER_CONFIG)
        if self._path_exists(broker_config_file):
            self._has_data["broker_config"] = True
            self._broker_config_file = broker_config_file
        args_file = os.path.join(self._log_dir, self.ARGS_FILE)
        if self._path_exists(args_file):
            self._has_data["args"] = True
            self._args_file = args_file
        child_order_fills_dir = os.path.join(
            self._log_dir, self.CCXT_CHILD_ORDER_FILLS
        )
        # Verify that the fills dir conforms to expected structure.
        # If there are no subdirectories, the reader expects to find child order
        # fill logs. If there are subdirectories, the reader expect them to
        # conform to the structure outlined in the constructor.
        if self._path_exists(child_order_fills_dir):
            child_order_fills_dir_contents = os.scandir(child_order_fills_dir)
            has_subdirectories = any(
                [path.is_dir() for path in child_order_fills_dir_contents]
            )
            if has_subdirectories:
                # Get a subdirectory for CCXT fill representations.
                # E.g. 'system_log_dir_20230315_30minutes/child_order_fills/ccxt_fills'.
                ccxt_fills_dir = os.path.join(self._log_dir, self.CCXT_FILLS)
                if self._path_exists(ccxt_fills_dir):
                    self._has_data["ccxt_fills"] = True
                    self._ccxt_fills_dir = ccxt_fills_dir
                # Get a subdirectory for CCXT trades.
                # E.g. 'system_log_dir_20230315_30minutes/child_order_fills/ccxt_trades'.
                ccxt_child_order_trades_dir = os.path.join(
                    self._log_dir, self.CCXT_CHILD_ORDER_TRADES
                )
                if self._path_exists(ccxt_child_order_trades_dir):
                    self._has_data["ccxt_trades"] = True
                    self._ccxt_trades_dir = ccxt_child_order_trades_dir
                # Get a subdirectory for OMS fills.
                # E.g. 'system_log_dir_20230315_30minutes/child_order_fills/oms_fills'.
                oms_fills_dir = os.path.join(self._log_dir, self.OMS_FILLS)
                if self._path_exists(oms_fills_dir):
                    self._has_data["oms_fills"] = True
                    self._oms_fills_dir = oms_fills_dir
            else:
                # Get subdirectory for CCXT representations child order fills.
                # E.g. 'system_log_dir_20230315_30minutes/child_order_fills'.
                self._ccxt_trades_dir = child_order_fills_dir
        # Get subdirectory for CCXT order responses.
        # E.g. 'system_log_dir_20230315_30minutes/ccxt_child_order_responses'.
        ccxt_order_responses_dir = os.path.join(
            self._log_dir, self.CCXT_CHILD_ORDER_RESPONSE
        )
        if self._path_exists(ccxt_order_responses_dir):
            self._has_data["ccxt_order_responses"] = True
            self._ccxt_order_responses_dir = ccxt_order_responses_dir
        # Get subdirectory for submitted child orders.
        # E.g. 'system_log_dir_20230315_30minutes/oms_child_orders'.
        oms_child_orders_dir = os.path.join(self._log_dir, self.OMS_CHILD_ORDERS)
        if self._path_exists(oms_child_orders_dir):
            self._has_data["oms_child_orders"] = True
            self._oms_child_orders_dir = oms_child_orders_dir
        # Get subdirectory for parent orders.
        # E.g. 'system_log_dir_20230315_30minutes/oms_parent_orders/'.
        oms_parent_orders_dir = os.path.join(
            self._log_dir, self.OMS_PARENT_ORDERS
        )
        if self._path_exists(oms_parent_orders_dir):
            self._has_data["oms_parent_orders"] = True
            self._oms_parent_orders_dir = oms_parent_orders_dir
        # Get subdirectory for bid ask data.
        # E.g. 'system_log_dir_20230315_30minutes/bid_ask/'.
        bid_ask_dir = os.path.join(self._log_dir, self.BID_ASK)
        if self._path_exists(bid_ask_dir):
            self._has_data["bid_ask_files"] = True
            self._bid_ask_dir = bid_ask_dir
        # Get subdirectory for bid ask data for the full
        # experiment period.
        # E.g. 'system_log_dir_20230315_30minutes/bid_ask_full/'.
        bid_ask_dir_full = os.path.join(self._log_dir, self.BID_ASK_FULL)
        if self._path_exists(bid_ask_dir):
            self._has_data["bid_ask_full_files"] = True
            self._bid_ask_full_dir = bid_ask_dir_full
        # Get subdirectory for exchange markets.
        # E.g. 'system_log_dir_20230315_30minutes/exchange_markets/'.
        exchange_markets_dir = os.path.join(self._log_dir, self.EXCHANGE_MARKETS)
        if self._path_exists(exchange_markets_dir):
            self._has_data["exchange_markets"] = True
            self._exchange_markets_dir = exchange_markets_dir
        # Get subdirectory for leverage info.
        # E.g. 'system_log_dir_20230315_30minutes/leverage_info/'.
        leverage_info_dir = os.path.join(self._log_dir, self.LEVERAGE_INFO)
        if self._path_exists(leverage_info_dir):
            self._has_data["leverage_info"] = True
            self._leverage_info_dir = leverage_info_dir
        # Get subdirectory for positions.
        # E.g. 'system_log_dir_20230315_30minutes/log/positions/'.
        positions_dir = os.path.join(self._log_dir, self.POSITIONS)
        if self._path_exists(positions_dir):
            self._has_data["positions"] = True
            self._positions_dir = positions_dir
        # E.g. 'system_log_dir_20230315_30minutes/log/balances/'.
        balances_dir = os.path.join(self._log_dir, self.BALANCES)
        if self._path_exists(balances_dir):
            self._has_data["balances"] = True
            self._balances_dir = balances_dir
        # E.g. 'system_log_dir_20230315_30minutes/log/reduce_only/ccxt_child_order_responses'.
        reduce_only_order_responses_dir = os.path.join(
            self._log_dir, "reduce_only", self.CCXT_CHILD_ORDER_RESPONSE
        )
        if self._path_exists(reduce_only_order_responses_dir):
            self._has_data["reduce_only_order_responses"] = True
            self._reduce_only_order_responses_dir = (
                reduce_only_order_responses_dir
            )
        # TODO(Sameep): Replace this subdirectory-based reduce-only shift with
        # one based on order parameters.
        # E.g. 'system_log_dir_20230315_30minutes/log/reduce_only/ccxt_child_order_responses'.
        reduce_only_child_order_dir = os.path.join(
            self._log_dir, "reduce_only", self.OMS_CHILD_ORDERS
        )
        if self._path_exists(reduce_only_child_order_dir):
            self._has_data["reduce_only_child_orders"] = True
            self._reduce_only_child_order_dir = reduce_only_child_order_dir

    def _convert_oms_parent_orders_to_dataframe(
        self, oms_parent_orders: List[CcxtData]
    ) -> pd.DataFrame:
        """
        Convert a list of OMS parent orders into a single DataFrame and
        normalize.

        Example of input OMS parent orders:
        [OrderedDict([('order_id', 0),
        ('creation_timestamp',
        Timestamp('2023-06-21 10:15:49.589872-0400',
        tz='America/New_York')),                         ('asset_id',
        3065029174),                         ('type_', 'price@twap'),
        ('start_timestamp',
        Timestamp('2023-06-21 10:15:49.589872-0400',
        tz='America/New_York')),
        ('end_timestamp',                         Timestamp('2023-06-21
        10:20:49.589872-0400', tz='America/New_York')),
        ('curr_num_shares', 0.0),
        ('diff_num_shares', -900.0),                         ('tz',
        <DstTzInfo 'America/New_York' EST-1 day, 19:00:00 STD>),
        ('extra_params', {})]),             OrderedDict([('order_id',
        1),                         ('creation_timestamp',
        Timestamp('2023-06-21 10:15:49.590399-0400',
        tz='America/New_York')),                         ('asset_id',
        6051632686),                         ('type_', 'limit'),
        ('start_timestamp',
        Timestamp('2023-06-21 10:15:49.590399-0400',
        tz='America/New_York')),
        ('end_timestamp',                         Timestamp('2023-06-21
        10:20:49.590399-0400', tz='America/New_York')),
        ('curr_num_shares', 0.0),
        ('diff_num_shares', 33.0),                         ('tz',
        <DstTzInfo 'America/New_York' EST-1 day, 19:00:00 STD>),
        ('extra_params', {})])]         Example of output:         ```
        creation_timestamp    asset_id       type_
        start_timestamp                    end_timestamp
        curr_num_shares  diff_num_shares               tz
        extra_params order_id 0        2023-06-22 08:44:21.852271+00:00
        3065029174  price@twap 2023-06-22 08:44:21.852271+00:00
        2023-06-22 08:49:21.852271+00:00              0.0
        -900.0  America/New_York           {} 1        2023-06-22
        08:44:21.852754+00:00  6051632686       limit 2023-06-22
        08:44:21.852754+00:00 2023-06-22 08:49:21.852754+00:00
        0.0             33.0  America/New_York           {}         ```
        """
        # Combine into a single DataFrame.
        oms_parent_orders_df = pd.DataFrame(oms_parent_orders)
        oms_parent_orders_df["order_id"] = oms_parent_orders_df[
            "order_id"
        ].astype(int)
        oms_parent_orders_df = oms_parent_orders_df.set_index("order_id")
        # Transform timestamp columns to UTC.
        oms_parent_orders_df = oms_parent_orders_df.map(
            lambda x: x.tz_convert("UTC") if isinstance(x, pd.Timestamp) else x
        )
        return oms_parent_orders_df

    def _convert_oms_child_orders_to_dataframe(
        self,
        oms_child_orders: List[CcxtData],
        *,
        unpack_extra_params: bool = False,
    ) -> pd.DataFrame:
        """
        Convert list of OMS child order Series into a DataFrame and normalize.

        Example of input OMS child order:
        ```
        {
            "order_id": 20,
            "creation_timestamp": "Timestamp('2023-03-15 12:35:37.825835-0400', tz='pytz.FixedOffset(-240)')",
            "asset_id": 6051632686,
            "type_": "limit",
            "start_timestamp": "Timestamp('2023-03-15 12:35:37.825835-0400', tz='pytz.FixedOffset(-240)')",
            "end_timestamp": "Timestamp('2023-03-15 12:36:37.825835-0400', tz='pytz.FixedOffset(-240)')",
            "curr_num_shares": 0.0,
            "diff_num_shares": 10.0,
            "tz": "America/New_York",
            "passivity_factor": 0.55,
            "latest_bid_price": 4.12,
            "latest_ask_price": 4.121,
            "bid_price_mean": 4.125947368421053,
            "ask_price_mean": 4.126973684210526,
            "used_bid_price": "latest_bid_price",
            "used_ask_price": "latest_ask_price",
            "limit_price": 4.12045,
            "ccxt_id": 7954906695
        }
        ```

        E.g., a timeseries from return DataFrame:
        ```
        order_id                 20
        creation_timestamp          2023-03-15 12:35:37.825835-04:00
        asset_id                 6051632686
        type_                   limit
        start_timestamp            2023-03-15 12:35:37.825835-04:00
        end_timestamp             2023-03-15 12:36:37.825835-04:00
        curr_num_shares            0.0
        diff_num_shares            10.0
        tz                     America/New_York
        passivity_factor            0.55                                                                                                                 latest_bid_price                                                   4.12
        latest_ask_price            4.121
        bid_price_mean             4.125947368421053
        ask_price_mean             4.126973684210526                                                                                                                 used_bid_price                                         latest_bid_price
        used_ask_price             latest_ask_price                                                                                                                 limit_price                                                     4.12045
        ccxt_id                  7954906695
        extra_params              {'order_generated_timestamp': datetime.datetim...
        ```
        """
        # Convert to DataFrame.
        oms_child_orders_series_list = []
        for oms_child_order_srs in oms_child_orders:
            order_id = oms_child_order_srs["order_id"]
            # Name each series according to internal order_id.
            oms_child_order_srs["name"] = order_id
            oms_child_orders_series_list.append(oms_child_order_srs)
        oms_child_orders_df = pd.DataFrame(oms_child_orders_series_list)
        oms_child_orders_df["order_id"] = oms_child_orders_df["order_id"].astype(
            int
        )
        oms_child_orders_df = oms_child_orders_df.set_index("order_id")
        # Transform timestamp columns to UTC.
        oms_child_orders_df = oms_child_orders_df.map(
            lambda x: x.tz_convert("UTC") if isinstance(x, pd.Timestamp) else x
        )
        # Unpack ccxt_id from the list format.
        # E.g. [12028516372] -> 12028516372.
        hdbg.dassert_in("ccxt_id", oms_child_orders_df.columns)
        # Make sure that all CCXT ID lists have length of 1.
        hdbg.dassert_eq_all(set(oms_child_orders_df["ccxt_id"].str.len()), {1})
        oms_child_orders_df["ccxt_id"] = oms_child_orders_df["ccxt_id"].apply(
            lambda x: x[0]
        )
        # Convert ccxt id data type to int.
        oms_child_orders_df["ccxt_id"] = oms_child_orders_df["ccxt_id"].astype(
            int
        )
        # Extract number of submission attempts.
        # Verify that `stats` is present in all child order `extra_params`.
        stats_are_present = all(
            [
                "stats" in extra_params
                for extra_params in oms_child_orders_df["extra_params"].to_list()
            ]
        )
        hdbg.dassert(
            stats_are_present,
            msg="`stats` not present in all child orders `extra_params`.",
        )
        # Get the key for the number of the successful submission attempt.
        # TODO(Danya): This will break if the calling function ever changes.
        # A better solution would be to either log `attempt_num` separately from
        # `stats` (like ccxt_id) or find the key by prefix.
        attempt_num_stats_key = "_submit_single_order_to_ccxt::attempt_num"
        attempt_num_is_present = all(
            [
                attempt_num_stats_key in extra_params["stats"]
                for extra_params in oms_child_orders_df["extra_params"].to_list()
            ]
        )
        hdbg.dassert(
            attempt_num_is_present,
            msg="`attempt_num_present_cond` not present in all `extra_params['stats']`.",
        )
        oms_child_orders_df["attempt_num"] = oms_child_orders_df[
            "extra_params"
        ].apply(lambda x: x["stats"][attempt_num_stats_key])
        if unpack_extra_params:
            # Unpack 'extra params' dictionary into a DataFrame.
            extra_params_df = pd.json_normalize(
                oms_child_orders_df["extra_params"], sep="_"
            ).set_index(oms_child_orders_df.index)
            # Remove duplicated columns that were unpacked earlier.
            # The columns are `ccxt_id` and `attempt_num`, which are logged
            # in the child order `extra_params['stats']` during submission.
            extra_params_df = extra_params_df.drop(
                ["ccxt_id", "stats_" + attempt_num_stats_key], axis=1
            )
            # Add extra_params columns to the child orders DataFrame.
            oms_child_orders_df = pd.concat(
                [oms_child_orders_df, extra_params_df], axis=1
            )
            # Remove the extra_params column to avoid data duplication.
            oms_child_orders_df = oms_child_orders_df.drop(
                ["extra_params"], axis=1
            )
        return oms_child_orders_df

    def _convert_ccxt_trades_json_to_dataframe(
        self, trades_json: List[CcxtData]
    ) -> pd.DataFrame:
        """
        Convert JSON-format trades into a DataFrame.

        - Unpack nested values;
        - Convert unix epoch to pd.Timestamp;
        - Remove duplicated information;
        """
        hdbg.dassert_lte(1, len(trades_json))
        trades = pd.DataFrame(trades_json)
        hdbg.dassert_in("asset_id", trades.columns)
        # Extract nested values.
        # Note: `transaction_cost` is extracted from the `fee`
        #  value for the base/quote currency.
        #  See https://docs.ccxt.com/#/?id=trade-structure.
        #
        trades["transaction_cost"] = [fee["cost"] for fee in trades["fee"]]
        trades["fees_currency"] = [fee["currency"] for fee in trades["fee"]]
        trades["realized_pnl"] = [info["realizedPnl"] for info in trades["info"]]
        # Force conversion of PnL to float.
        # PnL is extracted from `info` field, which stores all values as strings.
        trades["realized_pnl"] = trades["realized_pnl"].astype(float)
        # Convert order ID and trade ID to int.
        trades["order"] = trades["order"].astype(int)
        trades["id"] = trades["id"].astype(int)
        # Replace unix epoch with a timestamp.
        trades["timestamp"] = trades["timestamp"].apply(
            hdateti.convert_unix_epoch_to_timestamp
        )
        # Set columns.
        columns = [
            "timestamp",
            "datetime",
            "symbol",
            "asset_id",
            "id",
            "order",
            "side",
            "takerOrMaker",
            "price",
            "amount",
            "cost",
            "transaction_cost",
            "fees_currency",
            "realized_pnl",
        ]
        trades = trades[columns]
        # Normalize data types.
        trades = self._normalize_fills_dataframe(trades)
        # Set timestamp index.
        trades = trades.set_index("timestamp", drop=False)
        return trades

    def _log_raw_data(
        self,
        dir_name: str,
        file_name_tag: str,
        get_wall_clock_time: Callable,
        data: CcxtData,
    ) -> None:
        """
        Log raw data from CCXT Exchange as JSON.

        :param get_wall_clock_time: retrieve the current wall clock time
        """
        # Generate file name based on the bar timestamp.
        wall_clock_time = hdateti.timestamp_to_str(get_wall_clock_time())
        # Create enclosing dir.
        log_filename = os.path.join(
            self._log_dir,
            dir_name,
            f"{file_name_tag}.{wall_clock_time}.json",
        )
        # Create enclosing dir.
        hio.to_json(log_filename, data, use_types=True)
        _LOG.debug(hprint.to_str("log_filename"))

    def _load_raw_data(
        self,
        dir_name: str,
        *,
        append_list: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Load raw data from the JSON files in the log directory.

        :param append_list: Set to True for DataFrame.extend() or False
            for DataFrame.append().
        """
        files = self._get_files(dir_name)
        data_list = []
        for path in tqdm(files, desc=f"Loading '{dir_name}'"):
            data = hio.from_json(path, use_types=True)
            if append_list:
                data_list.append(data)
            else:
                data_list.extend(data)
        return data_list


# #############################################################################
# Config loading
# #############################################################################


def load_config_for_execution_analysis(system_log_dir: str) -> pd.DataFrame:
    """
    Load the configuration used for execution analysis.

    Receive a full path to the log directory for a full system or broker-only
    experiment, e.g.
    '/shared_data/ecs/test/.../system_log_dir.manual/process_forecasts'

    :param system_log_dir: dir used in the execution analysis notebook.
    If ends with 'process_forecasts', the function expects the config file
    to be located a level above the input directory.
    """
    #
    config_file_path = system_log_dir.rstrip("/")
    # Return to a level higher for the full system log dir.
    if config_file_path.endswith("process_forecasts"):
        config_file_path = config_file_path.rstrip("process_forecasts")
    # Get a full path to the config pickle file.
    file_name = "system_config.output.values_as_strings.pkl"
    config_file_path = os.path.join(config_file_path, file_name)
    _LOG.info("Loading config from %s", config_file_path)
    # Show a warning if the file does not exist.
    # This could indicate an error or a broker-only run.
    if not os.path.exists(config_file_path):
        _LOG.warning("Config file %s does not exist", config_file_path)
        config = None
    # Load the config as a string.
    else:
        config = cconfig.load_config_from_pickle(config_file_path)
        hdbg.dassert_in("dag_runner_config", config)
        if isinstance(config["dag_runner_config"], tuple):
            # This is a hack to display a config that was made from unpickled dict.
            config = config.to_string("only_values").replace("\\n", "\n")
    return config


# #############################################################################
# Child order timestamp processing
# #############################################################################


def process_timestamps_and_prices_for_a_single_order(
    child_order: pd.Series, fills_df: pd.DataFrame, resample_freq: str
) -> pd.DataFrame:
    """
    Organize submission event and CCXT trade timestamps and related prices.

    Apply `process_child_order_execution_timestamps` and
    `process_child_order_trades_timestamps` for a single child order,
    and add multilevel index on `asset_id`.

    :param child_order: a single child order from `oms_child_order_df`
        Example:

        creation_timestamp                         2023-08-29 12:35:00.939164+00:00
        asset_id                                                         1030828978
        type_                                                                 limit
        start_timestamp                            2023-08-29 12:35:00.939164+00:00
        end_timestamp                                     2023-08-29 12:36:00+00:00
        curr_num_shares                                                         0.0
        diff_num_shares                                                      -162.0
        tz                                                         America/New_York
        extra_params              {'stats': {'_submit_twap_child_order::wave_id'...
        passivity_factor                                                       0.55
        latest_bid_price                                                     0.1552
        latest_ask_price                                                     0.1553
        bid_price_mean                                                       0.1552
        ask_price_mean                                                       0.1553
        used_bid_price                                             latest_bid_price
        used_ask_price                                             latest_ask_price
        exchange_timestamp                         2023-08-29 12:34:58.561000+00:00
        knowledge_timestamp                        2023-08-29 12:34:58.710276+00:00
        end_download_timestamp                     2023-08-29 12:34:58.685410+00:00
        limit_price                                                        0.155255
        ccxt_id                                                         12049653207
        name                                                                      9
        Name: 9, dtype: object
    :param fills_df: output of `load_ccxt_trades_df()`
    :param resample_freq: frequency to resample timestamps to. Should be equal
    to the doubled order book sampling frequency, e.g.,
    for "200ms" order book sampling -> "100ms".
    :return: DataFrame of event timestamps and prices for a single order, e.g.:
                                                                                event limit_price signed_quantity snapshot_ask_price snapshot_bid_price
                                                                            1030828978  1030828978      1030828978         1030828978         1030828978
    timestamp
    2023-09-01 10:34:58.100000+00:00                                knowledge_timestamp         NaN             NaN             0.1583             0.1582
    2023-09-01 10:35:00.900000+00:00  _submit_twap_child_order::child_order.limit_pr...    0.158245           160.0                NaN                NaN
    2023-09-01 10:35:05+00:00           _submit_twap_child_order::child_order.submitted         NaN             NaN                NaN                NaN
    2023-09-01 10:35:23.600000+00:00                                            trade.1    0.158200           160.0                NaN                NaN
    2023-09-01 10:36:00+00:00                                             end_timestamp         NaN             NaN                NaN                NaN
    """
    #
    execution_timestamps = process_child_order_execution_timestamps(child_order)
    #
    trade_timestamps = process_child_order_trades_timestamps(
        fills_df, child_order.ccxt_id
    )
    # TODO(Danya): Move this section to both functions above so that they can
    # be called separately with the same kind of output.
    df_subset = pd.concat([execution_timestamps, trade_timestamps])
    df_subset = df_subset.reset_index()
    df_subset = df_subset.set_index("timestamp")
    # Sort index, since trades are not located in the correct order with
    # respect to order submission events.
    df_subset = df_subset.sort_index()
    # Resample.
    df_subset.index = df_subset.index.ceil(resample_freq)
    out_df = pd.concat({child_order["asset_id"]: df_subset}, axis=1)
    out_df = out_df.swaplevel(axis=1).sort_index(axis=1)
    return out_df


def process_child_order_execution_timestamps(
    child_order: pd.Series,
) -> pd.DataFrame:
    """
    Organize timestamps associated to order book snapshot and limit order.

    :param child_order: a single child order from `oms_child_order_df`
        Example:

        creation_timestamp                         2023-08-29 12:35:00.939164+00:00
        asset_id                                                         1030828978
        type_                                                                 limit
        start_timestamp                            2023-08-29 12:35:00.939164+00:00
        end_timestamp                                     2023-08-29 12:36:00+00:00
        curr_num_shares                                                         0.0
        diff_num_shares                                                      -162.0
        tz                                                         America/New_York
        extra_params              {'stats': {'_submit_twap_child_order::wave_id'...
        passivity_factor                                                       0.55
        latest_bid_price                                                     0.1552
        latest_ask_price                                                     0.1553
        bid_price_mean                                                       0.1552
        ask_price_mean                                                       0.1553
        used_bid_price                                             latest_bid_price
        used_ask_price                                             latest_ask_price
        exchange_timestamp                         2023-08-29 12:34:58.561000+00:00
        knowledge_timestamp                        2023-08-29 12:34:58.710276+00:00
        end_download_timestamp                     2023-08-29 12:34:58.685410+00:00
        limit_price                                                        0.155255
        ccxt_id                                                         12049653207
        name                                                                      9
        Name: 9, dtype: object
    :return: DataFrame of submission event timestamps and related prices, e.g.:
                                                                            timestamp  limit_price  signed_quantity  snapshot_bid_price  snapshot_ask_price
    event
    knowledge_timestamp                                2023-09-01 10:34:58.050280+00:00          NaN              NaN              0.1582              0.1583
    _submit_twap_child_order::child_order.limit_pri... 2023-09-01 10:35:00.803694+00:00     0.158245            160.0                 NaN                 NaN
    _submit_twap_child_order::child_order.submitted    2023-09-01 10:35:04.905545+00:00          NaN              NaN                 NaN                 NaN
    end_timestamp                                             2023-09-01 10:36:00+00:00          NaN              NaN                 NaN                 NaN
    """
    # Get data and child order timestamps.
    events = child_order[
        [
            "start_timestamp",
            "end_timestamp",
            "exchange_timestamp",
            "end_download_timestamp",
            "knowledge_timestamp",
        ]
    ]
    events = pd.to_datetime(events)
    # Get timestamps of order submission events.
    stats = child_order["extra_params"]["stats"].copy()
    # Remove non-timestamp stats not related to time profiling.
    # The non-timestamp stats include:
    # `wave_id` (`int`);
    # `attempt_num` (`int`);
    # `exception_on_retry` (`str`, optional for cases when order was not submitted).
    for key in list(stats):
        if not isinstance(stats[key], pd.Timestamp):
            stats.pop(key)
            _LOG.debug("Popped %s from `stats`", key)
    stats_events = pd.Series(stats.keys(), stats.values(), name="event")
    stats_events = stats_events.tz_convert("UTC")
    stats_events = pd.Series(
        stats_events.index, stats_events.values, name="timestamp"
    )
    # Combine into a DataFrame.
    all_events = (
        pd.concat([events, stats_events]).sort_values().rename("timestamp")
    )
    all_events = all_events.to_frame()
    # Add order and order book data.
    limit_price = pd.Series(
        child_order["limit_price"],
        ["_submit_twap_child_order::child_order.limit_price_calculated"],
        name="limit_price",
    )
    signed_quantity = pd.Series(
        child_order["diff_num_shares"],
        ["_submit_twap_child_order::child_order.limit_price_calculated"],
        name="signed_quantity",
    )
    snapshot_bid_price = pd.Series(
        child_order["latest_bid_price"],
        ["knowledge_timestamp"],
        name="snapshot_bid_price",
    )
    snapshot_ask_price = pd.Series(
        child_order["latest_ask_price"],
        ["knowledge_timestamp"],
        name="snapshot_ask_price",
    )
    prices = pd.concat(
        [limit_price, signed_quantity, snapshot_bid_price, snapshot_ask_price],
        axis=1,
    )
    df = pd.concat([all_events, prices], axis=1)
    df.index.name = "event"
    #
    # Combine event timestamps and price data into a single DataFrame.
    # Currently we are subselecting only certain columns for analysis.
    # Other columns available are:
    #  "exchange_timestamp",
    #  "end_download_timestamp",
    #  "_submit_twap_child_order::bid_ask_market_data.start",
    #  "_submit_twap_child_order::bid_ask_market_data.done",
    #  "_submit_twap_child_order::get_open_positions.done",
    #  "_submit_twap_child_order::child_order.created",
    #  "_submit_single_order_to_ccxt_with_retry::start.timestamp",
    #  "_submit_single_order_to_ccxt_with_retry::end.timestamp"
    execution_timestamps_and_prices = df.loc[
        [
            "knowledge_timestamp",
            "_submit_twap_child_order::child_order.limit_price_calculated",
            "_submit_twap_child_order::child_order.submitted",
            "end_timestamp",
        ]
    ]
    return execution_timestamps_and_prices


def process_child_order_trades_timestamps(
    fills_df: pd.DataFrame, ccxt_id: int
) -> pd.DataFrame:
    """
    Process timestamp and price of trades related to a single child order.

    :param fills_df: output of `load_ccxt_trades_df`
    :param ccxt_id: ccxt_id of the child order
    :return: timestamp, price and signed quantity of trades for a given order
    Example:

                                    timestamp  limit_price  signed_quantity
    event
    trade.1 2023-09-01 10:35:23.508000+00:00       0.1582            160.0
    """
    # Add timestamps for trades.
    # TODO(Danya): CMTask5287.
    child_order_trades = fills_df.loc[fills_df["order"] == ccxt_id]
    if not child_order_trades.empty:
        trade_timestamps = []
        limit_prices = []
        signed_quantities = []
        # Process trades for the given child order.
        for trade_n in range(len(child_order_trades)):
            trade = child_order_trades.iloc[trade_n]
            # Get timestamp of a trade.
            trade_timestamp = pd.Series(
                trade.timestamp, [f"trade.{trade_n+1}"], name="timestamp"
            )
            trade_timestamps.append(trade_timestamp)
            # Get price of a trade
            limit_price = pd.Series(
                trade.price, [f"trade.{trade_n+1}"], name="limit_price"
            )
            limit_prices.append(limit_price)
            # Get quanitity of a trade.
            signed_quantity = trade.amount
            if trade.side == "sell":
                signed_quantity = -signed_quantity
            signed_quantity = pd.Series(
                signed_quantity, [f"trade.{trade_n+1}"], name="signed_quantity"
            )
            signed_quantities.append(signed_quantity)
        # Combine into a single DataFrame.
        trade_timestamps = pd.concat(trade_timestamps)
        limit_prices = pd.concat(limit_prices)
        signed_quantities = pd.concat(signed_quantities)
        #
        trade_timestamps = pd.concat(
            [trade_timestamps, limit_prices, signed_quantities], axis=1
        )
        trade_timestamps.index.name = "event"
    else:
        # Return an empty DataFrame if no related trades are found.
        trade_timestamps = pd.DataFrame()
    return trade_timestamps


def process_child_order_timestamps_and_prices_for_single_asset(
    oms_child_order_df: pd.DataFrame,
    fills_df: pd.DataFrame,
    asset_id: int,
    resample_freq: str,
) -> pd.DataFrame:
    """
    Apply child order and trade timestamp processing to multiple child orders
    belonging a single asset.

    :param oms_child_order_df: OMS child order DataFrame
    :param asset_id: asset_id to apply the processing to
    :param resample_freq: see `process_child_order_timestamps` docstring
    :return: timestamps and prices for a single asset, e.g.:
                                                                                    event limit_price signed_quantity snapshot_ask_price snapshot_bid_price
                                                                            1467591036  1467591036      1467591036         1467591036         1467591036
    timestamp
    2023-09-01 10:34:58.100000+00:00                                knowledge_timestamp         NaN             NaN            26000.0            25999.9
    2023-09-01 10:35:00.800000+00:00  _submit_twap_child_order::child_order.limit_pr...   25999.955          -0.001                NaN                NaN
    2023-09-01 10:35:04.900000+00:00    _submit_twap_child_order::child_order.submitted         NaN             NaN                NaN                NaN
    2023-09-01 10:35:12.200000+00:00                                            trade.1   26000.000          -0.001                NaN                NaN
    2023-09-01 10:36:00+00:00                                             end_timestamp         NaN             NaN                NaN                NaN
    2023-09-01 10:36:00+00:00                                       knowledge_timestamp         NaN             NaN            25996.9            25996.8
    2023-09-01 10:36:02.300000+00:00  _submit_twap_child_order::child_order.limit_pr...   25996.855          -0.001                NaN                NaN
    2023-09-01 10:36:02.600000+00:00    _submit_twap_child_order::child_order.submitted         NaN             NaN                NaN                NaN
    2023-09-01 10:36:20.700000+00:00                                            trade.1   25996.900          -0.001                NaN                NaN
    2023-09-01 10:36:58.300000+00:00                                knowledge_timestamp         NaN             NaN            25998.7            25998.6
    """
    oms_child_order_df = oms_child_order_df[
        oms_child_order_df["asset_id"] == asset_id
    ]
    processed_orders = []
    for idx in oms_child_order_df.index:
        child_order = oms_child_order_df.loc[idx]
        processed_order = process_timestamps_and_prices_for_a_single_order(
            child_order, fills_df, resample_freq
        )
        processed_orders.append(processed_order)
    result = pd.concat(processed_orders, axis=0)
    return result
