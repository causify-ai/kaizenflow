"""
Import as:

import dataflow.pipelines.features.pipeline as dtfpifepip
"""

import datetime
import logging

import pandas as pd

import core.config as cconfig
import core.features as cofeatur
import core.finance as cofinanc
import core.signal_processing as csigproc
import dataflow.core as dtfcore

# TODO(gp): This dependency is not legal according to code_organization.md.
#  It should go into dataflow/system
import dataflow.system as dtfsys

_LOG = logging.getLogger(__name__)


# TODO(gp): -> feature_pipeline.py


class FeaturePipeline(dtfcore.DagBuilder):
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
            self._get_nid("filter_weekends"): {
                "col_mode": "replace_all",
            },
            self._get_nid("filter_ath"): {
                "col_mode": "replace_all",
                "transformer_kwargs": {
                    "start_time": datetime.time(9, 30),
                    "end_time": datetime.time(16, 00),
                },
            },
            self._get_nid("perform_col_arithmetic"): {
                "func_kwargs": {
                    cconfig.DUMMY: None,
                }
            },
            self._get_nid("add_diffs"): {
                "col_mode": "merge_all",
            },
            self._get_nid("zscore"): {
                "col_mode": "replace_all",
                "nan_mode": "drop",
            },
            self._get_nid("compress_tails"): {
                "col_mode": "replace_all",
            },
            self._get_nid("cross_feature_pairs"): {
                "func_kwargs": {
                    cconfig.DUMMY: None,
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
        tail_nid = None
        #
        stage = "load_data"
        nid = self._get_nid(stage)
        node = dtfsys.data_source_node_factory(nid, **config[nid].to_dict())
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "filter_weekends"
        nid = self._get_nid(stage)
        node = dtfcore.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_weekends_to_nan,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "filter_ath"
        nid = self._get_nid(stage)
        node = dtfcore.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_non_ath_to_nan,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "perform_col_arithmetic"
        nid = self._get_nid(stage)
        node = dtfcore.FunctionWrapper(
            nid,
            func=cofeatur.perform_col_arithmetic,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "add_diffs"
        nid = self._get_nid(stage)
        node = dtfcore.ColumnTransformer(
            nid,
            transformer_func=lambda x: x.diff(),
            col_rename_func=lambda x: x + ".diff",
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "zscore"
        nid = self._get_nid(stage)
        node = dtfcore.SeriesTransformer(
            nid,
            transformer_func=csigproc.compute_fir_zscore,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "compress_tails"
        nid = self._get_nid(stage)
        node = dtfcore.SeriesTransformer(
            nid,
            transformer_func=csigproc.compress_tails,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "cross_feature_pairs"
        nid = self._get_nid(stage)
        node = dtfcore.FunctionWrapper(
            nid,
            func=cofeatur.cross_feature_pairs,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        _ = tail_nid
        return dag
