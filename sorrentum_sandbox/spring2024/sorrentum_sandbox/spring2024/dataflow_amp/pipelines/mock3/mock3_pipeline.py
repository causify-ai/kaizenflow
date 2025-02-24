"""
Import as:

import dataflow_amp.pipelines.mock3.mock3_pipeline as dtfapmmopi
"""

import logging

import pandas as pd

import core.config as cconfig
import dataflow.core as dtfcore
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# TODO(Grisha): move to a more general lib, e.g., `core.finance`.
def compute_half_spread(
    bid_ask_data: pd.DataFrame, ask_price_col: str, bid_price_col: str
) -> pd.DataFrame:
    hdbg.dassert_is_subset([ask_price_col, bid_price_col], bid_ask_data.columns)
    half_spread = 0.5 * (
        bid_ask_data[ask_price_col] - bid_ask_data[bid_price_col]
    )
    half_spread.name = "half_spread"
    return half_spread.to_frame()


# TODO(Grisha): move to a more general lib, e.g., `core.finance`.
def compute_bid_ask_midpoint(
    bid_ask_data: pd.DataFrame, ask_price_col: str, bid_price_col: str
) -> pd.DataFrame:
    hdbg.dassert_is_subset([ask_price_col, bid_price_col], bid_ask_data.columns)
    bid_ask_midpoint = 0.5 * (
        bid_ask_data[ask_price_col] + bid_ask_data[bid_price_col]
    )
    bid_ask_midpoint.name = "bid_ask_midpoint"
    return bid_ask_midpoint.to_frame()


# TODO(Grisha): move to a more general lib, e.g., `core.finance`.
def compute_half_spread_in_bps(
    bid_ask_data: pd.DataFrame, half_spread_col: str, bid_ask_midpoint_col: str
) -> pd.DataFrame:
    hdbg.dassert_is_subset(
        [half_spread_col, bid_ask_midpoint_col], bid_ask_data.columns
    )
    half_spread_in_bps = (
        1e4 * bid_ask_data[half_spread_col] / bid_ask_data[bid_ask_midpoint_col]
    )
    half_spread_in_bps.name = "half_spread_in_bps"
    return half_spread_in_bps.to_frame()


class Mock3_DagBuilder(dtfcore.DagBuilder):
    """
    An example pipeline for Stitched (OHLCV and Bid/Ask) data.
    """

    @staticmethod
    def get_column_name(tag: str) -> str:
        """
        See description in the parent class.
        """
        if tag == "price":
            res_col = "vwap"
        elif tag == "volatility":
            res_col = "vwap.ret_0.vol"
        elif tag == "prediction":
            res_col = "feature1"
        else:
            raise ValueError(f"Invalid tag='{tag}'")
        return res_col

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

    def convert_to_fast_prod_setup(
        self, config: cconfig.Config
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        config[self._get_nid("resample")]["transformer_kwargs"]["rule"] = "2T"
        return config

    def set_weights(
        self, config: cconfig.Config, weights: pd.Series
    ) -> cconfig.Config:
        """
        Return a modified copy of `config` using given feature `weights`.
        """
        raise NotImplementedError

    def get_config_template(self) -> cconfig.Config:
        dict_ = {
            self._get_nid("compute_half_spread"): {
                "in_col_groups": [
                    ("level_1.ask_price.close",),
                    ("level_1.bid_price.close",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "ask_price_col": "level_1.ask_price.close",
                    "bid_price_col": "level_1.bid_price.close",
                },
            },
            self._get_nid("compute_bid_ask_midpoint"): {
                "in_col_groups": [
                    ("level_1.ask_price.close",),
                    ("level_1.bid_price.close",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "ask_price_col": "level_1.ask_price.close",
                    "bid_price_col": "level_1.bid_price.close",
                },
            },
            self._get_nid("compute_half_spread_in_bps"): {
                "in_col_groups": [
                    ("half_spread",),
                    ("bid_ask_midpoint",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "half_spread_col": "half_spread",
                    "bid_ask_midpoint_col": "bid_ask_midpoint",
                },
            },
        }
        config = cconfig.Config.from_dict(dict_)
        return config

    def _get_dag(
        self,
        config: cconfig.Config,
        mode: str = "strict",
    ) -> dtfcore.DAG:
        dag = dtfcore.DAG(mode=mode)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", config)
        #
        stage = "compute_half_spread"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=compute_half_spread,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "compute_bid_ask_midpoint"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=compute_bid_ask_midpoint,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "compute_half_spread_in_bps"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=compute_half_spread_in_bps,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        return dag
