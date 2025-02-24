"""
Import as:

import dataflow_amp.pipelines.mock_bid_ask.mock_bid_ask_pipeline as dtfapmbambap
"""

import logging

import core.config as cconfig
import core.features as cofeatur
import core.finance as cofinanc
import core.signal_processing as csigproc
import dataflow.core as dtfcore

_LOG = logging.getLogger(__name__)


class MockBidAsk_DagBuilder(dtfcore.DagBuilder):
    """
    An example pipeline of a bid-ask data-based model.
    """

    @staticmethod
    def get_column_name(tag: str) -> str:
        """
        See description in the parent class.
        """
        if tag == "price":
            result_col = "level_1.bid_ask_midpoint.close"
        elif tag == "volatility":
            result_col = "level_1.bid_ask_midpoint.close.ret_0.vol"
        elif tag == "prediction":
            result_col = "level_1.bid_ask_midpoint.close.ret_0.vol_adj"
        else:
            raise ValueError(f"Invalid tag='{tag}'")
        return result_col

    def get_trading_period(
        self, config: cconfig.Config, mark_key_as_used: bool
    ) -> str:
        """
        See description in the parent class.
        """
        _ = self
        # Get a key for trading period inside the config.
        resample_nid = self._get_nid("resample")
        key = (resample_nid, "transformer_kwargs", "rule")
        val: str = config.get_and_mark_as_used(
            key, mark_key_as_used=mark_key_as_used
        )
        return val

    def get_required_lookback_in_effective_days(
        self, config: cconfig.Config, mark_key_as_used: bool
    ) -> str:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def set_weights(self, config: cconfig.Config, weights) -> cconfig.Config:
        raise NotImplementedError

    def convert_to_fast_prod_setup(
        self, config: cconfig.Config
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_config_template(self) -> cconfig.Config:
        config = cconfig.Config.from_dict(
            {
                # Resample prices.
                self._get_nid("resample"): {
                    "in_col_groups": [
                        ("level_1.ask_price.mean",),
                        ("level_1.bid_ask_midpoint.close",),
                        ("level_1.bid_ask_midpoint.mean",),
                        ("level_1.bid_price.mean",),
                    ],
                    "out_col_group": (),
                    "transformer_kwargs": {
                        "rule": "3T",
                        "resampling_groups": [
                            (
                                {
                                    "level_1.ask_price.mean": "level_1.ask_price.mean",
                                    "level_1.bid_ask_midpoint.mean": "level_1.bid_ask_midpoint.mean",
                                    "level_1.bid_price.mean": "level_1.bid_price.mean",
                                },
                                "mean",
                                {},
                            ),
                            (
                                {
                                    "level_1.bid_ask_midpoint.close": "level_1.bid_ask_midpoint.close"
                                },
                                "last",
                                {},
                            ),
                        ],
                        "vwap_groups": [],
                    },
                    "reindex_like_input": False,
                    "join_output_with_input": False,
                },
                # Compute log returns.
                self._get_nid("compute_ret_0"): {
                    "in_col_groups": [
                        ("level_1.bid_ask_midpoint.close",),
                    ],
                    "out_col_group": (),
                    "transformer_kwargs": {
                        "mode": "pct_change",
                    },
                    "col_mapping": {
                        "level_1.bid_ask_midpoint.close": "level_1.bid_ask_midpoint.close.ret_0",
                    },
                },
                # Compute volatility.
                self._get_nid("compute_vol"): {
                    "in_col_groups": [
                        ("level_1.bid_ask_midpoint.close.ret_0",),
                    ],
                    "out_col_group": (),
                    "transformer_kwargs": {
                        "tau": 32,
                    },
                    "col_mapping": {
                        "level_1.bid_ask_midpoint.close.ret_0": "level_1.bid_ask_midpoint.close.ret_0.vol"
                    },
                },
                # Volatility-adjust returns.
                self._get_nid("adjust_rets"): {
                    "in_col_groups": [
                        ("level_1.bid_ask_midpoint.close.ret_0",),
                        ("level_1.bid_ask_midpoint.close.ret_0.vol",),
                    ],
                    "out_col_group": (),
                    "transformer_kwargs": {
                        "term1_col": "level_1.bid_ask_midpoint.close.ret_0",
                        "term2_col": "level_1.bid_ask_midpoint.close.ret_0.vol",
                        "out_col": "level_1.bid_ask_midpoint.close.ret_0.vol_adj",
                        "term2_delay": 2,
                        "operation": "div",
                    },
                    "drop_nans": True,
                },
            }
        )
        return config

    def _get_dag(
        self, config: cconfig.Config, mode: str = "strict"
    ) -> dtfcore.DAG:
        dag = dtfcore.DAG(mode=mode)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("config=%s", config)
        # Resample prices.
        stage = "resample"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid, transformer_func=cofinanc.resample_bars, **config[nid].to_dict()
        )
        dag.append_to_tail(node)
        # Compute
        stage = "compute_ret_0"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.compute_ret_0,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        # Compute volatility.
        stage = "compute_vol"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=csigproc.compute_rolling_norm,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        # Volatility-adjust returns.
        stage = "adjust_rets"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofeatur.combine_columns,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        return dag
