"""
Import as:

import dataflow.pipelines.execution.execution_pipeline as dtfpexexpi
"""

import logging

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import dataflow.core as dtfcore

# TODO(gp): This dependency is not legal according to code_organization.md.
#  It should go into dataflow/system
import dataflow.system as dtfsys

_LOG = logging.getLogger(__name__)


class ExecutionPipeline(dtfcore.DagBuilder):
    @staticmethod
    def get_column_name(tag: str) -> str:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_trading_period(
        self, config: cconfig.Config, mark_key_as_used: bool
    ) -> str:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_required_lookback_in_effective_days(
        self, config: cconfig.Config, mark_key_as_used: bool
    ) -> str:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def set_weights(
        self, config: cconfig.Config, weights: pd.Series
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def convert_to_fast_prod_setup(
        self, config: cconfig.Config
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_config_template(self) -> cconfig.Config:
        """
        See description in the parent class.
        """
        dict_ = {
            self._get_nid("load_data"): {
                cconfig.DUMMY: None,
            },
            self._get_nid("generate_limit_orders"): {
                "in_col_groups": [
                    ("bid_price",),
                    ("ask_price",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "bid_col": "bid_price",
                    "ask_col": "ask_price",
                    "buy_reference_price_col": "bid_price",
                    "sell_reference_price_col": "ask_price",
                    "buy_spread_frac_offset": 0.5,
                    "sell_spread_frac_offset": -0.5,
                    "subsample_freq": "1s",
                    "freq_offset": "0s",
                    "ffill_limit": 60,
                    "tick_decimals": 6,
                },
            },
            self._get_nid("resample"): {
                "in_col_groups": [
                    ("buy_limit_order_price",),
                    ("sell_limit_order_price",),
                    ("limit_buy_executed",),
                    ("limit_sell_executed",),
                    ("buy_trade_price",),
                    ("sell_trade_price",),
                    ("bid_price",),
                    ("ask_price",),
                    ("buy_order_num",),
                    ("sell_order_num",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "rule": "5T",
                    "resampling_groups": [
                        (
                            {
                                "buy_limit_order_price": "buy_limit_order_price",
                                "sell_limit_order_price": "sell_limit_order_price",
                                "limit_buy_executed": "limit_buy_executed",
                                "limit_sell_executed": "limit_sell_executed",
                                "buy_trade_price": "buy_trade_price",
                                "sell_trade_price": "sell_trade_price",
                                "bid_price": "bid_price",
                                "ask_price": "ask_price",
                                # TODO(Paul): Consider resampling these as "last".
                                "buy_order_num": "buy_order_num",
                                "sell_order_num": "sell_order_num",
                            },
                            "mean",
                            {},
                        ),
                    ],
                    "vwap_groups": [],
                },
                "reindex_like_input": False,
                "join_output_with_input": False,
            },
            self._get_nid("compute_bid_ask_execution_quality"): {
                "in_col_groups": [
                    ("bid_price",),
                    ("ask_price",),
                    ("buy_trade_price",),
                    ("sell_trade_price",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "bid_col": "bid_price",
                    "ask_col": "ask_price",
                    "buy_trade_price_col": "buy_trade_price",
                    "sell_trade_price_col": "sell_trade_price",
                },
            },
            self._get_nid("compute_trade_vs_limit_execution_quality"): {
                "in_col_groups": [
                    ("buy_limit_order_price",),
                    ("sell_limit_order_price",),
                    ("buy_trade_price",),
                    ("sell_trade_price",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "buy_limit_price_col": "buy_limit_order_price",
                    "sell_limit_price_col": "sell_limit_order_price",
                    "buy_trade_price_col": "buy_trade_price",
                    "sell_trade_price_col": "sell_trade_price",
                },
            },
        }
        config = cconfig.Config.from_dict(dict_)
        return config

    def _get_dag(
        self, config: cconfig.Config, mode: str = "strict"
    ) -> dtfcore.DAG:
        dag = dtfcore.DAG(mode=mode)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", config)
        #
        stage = "load_data"
        nid = self._get_nid(stage)
        node = dtfsys.data_source_node_factory(nid, **config[nid].to_dict())
        dag.append_to_tail(node)
        #
        stage = "generate_limit_orders"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.generate_limit_orders_and_estimate_execution,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "resample"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.resample_bars,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "compute_bid_ask_execution_quality"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.compute_bid_ask_execution_quality,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "compute_trade_vs_limit_execution_quality"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.compute_trade_vs_limit_execution_quality,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        return dag
