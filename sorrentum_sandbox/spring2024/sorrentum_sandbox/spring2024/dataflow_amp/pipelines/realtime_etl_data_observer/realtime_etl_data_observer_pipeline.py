"""
Import as:

import dataflow_amp.pipelines.realtime_etl_data_observer.realtime_etl_data_observer_pipeline as dtfapredoredop
"""

import datetime
import logging

import pandas as pd

import core.config as cconfig
import core.features as cofeatur
import core.finance as cofinanc
import dataflow.core as dtfcore

_LOG = logging.getLogger(__name__)


class Realtime_etl_DataObserver_DagBuilder(dtfcore.DagBuilder):
    """
    Real-time ETL data observer pipeline.
    """

    @staticmethod
    def get_column_name(tag: str) -> str:
        raise NotImplementedError

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
        raise NotImplementedError

    def convert_to_fast_prod_setup(
        self, config: cconfig.Config
    ) -> cconfig.Config:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_config_template(self) -> cconfig.Config:
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
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "rule": "1S",
                    "resampling_groups": [
                        ({"close": "close"}, "last", {}),
                        ({"volume": "volume"}, "sum", {}),
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
            self._get_nid("compute_feature"): {
                "in_col_groups": [
                    ("close",),
                    ("volume",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "term1_col": "close",
                    "term2_col": "volume",
                    "out_col": "feature",
                    "operation": "mul",
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
        stage = "compute_feature"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofeatur.combine_columns,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        return dag
