"""
Import as:

import dataflow_amp.pipelines.mock1.mock1_pipeline as dtfapmmopi
"""

import datetime
import logging

import numpy as np
import pandas as pd

import core.config as cconfig
import core.features as cofeatur
import core.finance as cofinanc
import core.signal_processing as csigproc
import dataflow.core as dtfcore
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


class Mock1_DagBuilder(dtfcore.DagBuilder):
    """
    A pipeline similar to real models.
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

    def set_weights(
        self, config: cconfig.Config, weights: pd.Series
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        hdbg.dassert_isinstance(config, cconfig.Config)
        hdbg.dassert_isinstance(weights, pd.Series)
        # Index must be an pd.Index of consecutive integers starting at 1.
        idx = weights.index
        hdbg.dassert_eq(idx.dtype.type, np.int64)
        # idx_size = idx.size
        # hdbg.dassert_set_eq(weights.index.to_list(), list(range(1, idx_size + 1)))
        # Generate the number of features corresponding to the weights.
        # config[self._get_nid("cswt")]["transformer_kwargs"]["depth"] = idx_size
        config[self._get_nid("predict")]["in_col_groups"] = [(x,) for x in idx]
        # Set the weights.
        config[self._get_nid("predict")]["transformer_kwargs"][
            "weights"
        ] = weights.rename("prediction")
        return config

    def convert_to_fast_prod_setup(
        self, config: cconfig.Config
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        config[self._get_nid("resample")]["transformer_kwargs"]["rule"] = "2T"
        return config

    def get_config_template(self) -> cconfig.Config:
        volatility_col = self.get_column_name("volatility")
        dict_ = {
            self._get_nid("filter_ath"): {
                "col_mode": "replace_all",
                "transformer_kwargs": {
                    "start_time": datetime.time(9, 30),
                    "end_time": datetime.time(16, 00),
                },
            },
            self._get_nid("resample"): {
                "in_col_groups": [
                    ("close",),
                    ("volume",),
                    ("feature1",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "rule": "5T",
                    "resampling_groups": [
                        ({"close": "close"}, "last", {}),
                        (
                            {
                                "close": "twap",
                                "feature1": "feature1",
                            },
                            "mean",
                            {},
                        ),
                    ],
                    "vwap_groups": [
                        ("close", "volume", "vwap"),
                    ],
                },
                "reindex_like_input": False,
                "join_output_with_input": False,
            },
            self._get_nid("compute_ret_0"): {
                "in_col_groups": [
                    ("close",),
                    ("vwap",),
                    ("twap",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "mode": "log_rets",
                },
                "col_mapping": {
                    "close": "close.ret_0",
                    "vwap": "vwap.ret_0",
                    "twap": "twap.ret_0",
                },
            },
            self._get_nid("compute_vol"): {
                "in_col_group": ("vwap.ret_0",),
                "out_col_group": (volatility_col,),
                "drop_nans": True,
                "permitted_exceptions": (ValueError,),
            },
            self._get_nid("adjust_rets"): {
                "in_col_groups": [
                    ("vwap.ret_0",),
                    ("vwap.ret_0.vol",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "term1_col": "vwap.ret_0",
                    "term2_col": "vwap.ret_0.vol",
                    "out_col": "vwap.ret_0.vol_adj",
                    "term2_delay": 2,
                    "operation": "div",
                },
                "drop_nans": True,
            },
            self._get_nid("compress_rets"): {
                "in_col_groups": [
                    ("vwap.ret_0.vol_adj",),
                ],
                "out_col_group": (),
                "col_mapping": {
                    "vwap.ret_0.vol_adj": "vwap.ret_0.vol_adj.c",
                },
            },
            self._get_nid("add_lags"): {
                "in_col_groups": [("vwap.ret_0.vol_adj.c",)],
                "out_col_group": (),
                "transformer_kwargs": {
                    "lag_delay": 0,
                    "num_lags": 4,
                    "first_lag": 0,
                    "separator": ".",
                },
                "drop_nans": True,
            },
            self._get_nid("predict"): {
                "in_col_groups": [
                    ("vwap.ret_0.vol_adj.c.lag0",),
                    ("vwap.ret_0.vol_adj.c.lag1",),
                    ("vwap.ret_0.vol_adj.c.lag2",),
                    ("vwap.ret_0.vol_adj.c.lag3",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "weights": pd.Series(
                        [
                            -0.209,
                            -0.223,
                            0.304,
                            -0.264,
                        ],
                        [
                            "vwap.ret_0.vol_adj.c.lag0",
                            "vwap.ret_0.vol_adj.c.lag1",
                            "vwap.ret_0.vol_adj.c.lag2",
                            "vwap.ret_0.vol_adj.c.lag3",
                        ],
                        name="prediction",
                    ),
                    "convert_to_dataframe": True,
                },
                "drop_nans": True,
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
        stage = "filter_ath"
        nid = self._get_nid(stage)
        node = dtfcore.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_non_ath_to_nan,
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
        stage = "compute_ret_0"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.compute_ret_0,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "compute_vol"
        nid = self._get_nid(stage)
        node = dtfcore.SeriesToSeriesTransformer(
            nid,
            transformer_func=lambda x: np.sqrt(
                csigproc.compute_swt_var(x, depth=1)["swt_var"]
            ).rename(x.name),
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "adjust_rets"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofeatur.combine_columns,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "compress_rets"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=lambda x: csigproc.compress_tails(x, 4),
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "add_lags"
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("stage=%s", stage)
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofeatur.compute_lagged_columns,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "predict"
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("stage=%s", stage)
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=csigproc.compute_weighted_sum,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        return dag
