"""
Import as:

import dataflow_amp.pipelines.mock2.mock2_pipeline as dtapmmopi
"""

import datetime
import logging

import core.config as cconfig
import core.features as cofeatur
import core.finance as cofinanc
import core.signal_processing as csigproc
import dataflow.core as dtfcore

_LOG = logging.getLogger(__name__)


class Mock2_DagBuilder(dtfcore.DagBuilder):
    """
    An example pipeline for US equities.
    """

    @staticmethod
    def get_column_name(tag: str) -> str:
        """
        See description in the parent class.
        """
        if tag == "price":
            result_col = "vwap"
        elif tag == "volatility":
            result_col = "vwap.ret_0.vol"
        elif tag == "prediction":
            result_col = "vwap.ret_0.vol_adj.c"
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
                # Filter out weekends.
                self._get_nid("filter_weekends"): {
                    "in_col_groups": [
                        ("close",),
                        ("high",),
                        ("low",),
                        ("open",),
                        ("volume",),
                    ],
                    "out_col_group": (),
                    "join_output_with_input": False,
                },
                # Filter to active trading hours.
                self._get_nid("filter_ath"): {
                    "in_col_groups": [
                        ("close",),
                        ("high",),
                        ("low",),
                        ("open",),
                        ("volume",),
                    ],
                    "out_col_group": (),
                    "transformer_kwargs": {
                        "start_time": datetime.time(9, 30),
                        "end_time": datetime.time(16, 00),
                    },
                    "join_output_with_input": False,
                },
                # Resample prices.
                self._get_nid("resample"): {
                    "in_col_groups": [
                        ("open",),
                        ("high",),
                        ("low",),
                        ("close",),
                        ("volume",),
                    ],
                    "out_col_group": (),
                    "transformer_kwargs": {
                        "rule": "5T",
                        "resampling_groups": [
                            ({"close": "close"}, "last", {}),
                            ({"high": "high"}, "max", {}),
                            ({"low": "low"}, "min", {}),
                            ({"open": "open"}, "first", {}),
                            (
                                {"volume": "volume"},
                                "sum",
                                {"min_count": 1},
                            ),
                            (
                                {
                                    "close": "twap",
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
                # Compute returns.
                self._get_nid("compute_ret_0"): {
                    "in_col_groups": [
                        ("close",),
                        ("vwap",),
                        ("twap",),
                    ],
                    "out_col_group": (),
                    "transformer_kwargs": {
                        "mode": "pct_change",
                    },
                    "col_mapping": {
                        "close": "close.ret_0",
                        "vwap": "vwap.ret_0",
                        "twap": "twap.ret_0",
                    },
                },
                # Compute volatility.
                self._get_nid("compute_vol"): {
                    "in_col_groups": [
                        ("vwap.ret_0",),
                    ],
                    "out_col_group": (),
                    "transformer_kwargs": {
                        "tau": 32,
                    },
                    "col_mapping": {"vwap.ret_0": "vwap.ret_0.vol"},
                },
                # Volatility-adjust returns.
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
                # Clip rets.
                self._get_nid("clip"): {
                    "in_col_groups": [
                        ("vwap.ret_0.vol_adj",),
                    ],
                    "out_col_group": (),
                    "col_mapping": {
                        "vwap.ret_0.vol_adj": "vwap.ret_0.vol_adj.c",
                    },
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
        # Set returns for weekends to NaN.
        stage = "filter_weekends"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.set_weekends_to_nan,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        # Set returns for non-ATH to NaN.
        stage = "filter_ath"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.set_non_ath_to_nan,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        # Resample prices.
        stage = "resample"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid, transformer_func=cofinanc.resample_bars, **config[nid].to_dict()
        )
        dag.append_to_tail(node)
        # Compute returns.
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
        # Clip returns.
        stage = "clip"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=lambda x: x.clip(lower=-3, upper=3),
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        return dag
