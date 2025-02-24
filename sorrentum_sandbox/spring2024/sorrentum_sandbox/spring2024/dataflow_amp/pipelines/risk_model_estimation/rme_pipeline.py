"""
Import as:

import dataflow_amp.pipelines.risk_model_estimation.rme_pipeline as dtfaprmerpi
"""

import logging

import pandas as pd
import sklearn.linear_model as sklimod

import core.config as cconfig
import core.features as cofeatur
import core.signal_processing as csigproc
import dataflow.core as dtfcore

_LOG = logging.getLogger(__name__)


# TODO(Grisha): call the `DagBuilder` in the tutorial notebook,
#  i.e. in `docs/dataflow/ck.run_batch_computation_dag.tutorial.ipynb`.
class SimpleRiskModel_DagBuilder(dtfcore.DagBuilder):
    """
    A pipeline similar to real feature processing.
    """

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
        _ = self
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
        Return a config template compatible with `self.get_dag()`.
        """
        # Set input and output column names that will be passed to the node.
        columns = ["ret_0", "x_1", "x_2"]
        # X vars stands for the input features column names.
        x_vars = [x for x in columns if x != "ret_0"]
        # Y vars stands for the output column name.
        y_vars = ["ret_0"]
        dict_ = {
            self._get_nid("sklearn"): {
                "in_col_groups": [(x,) for x in columns],
                "out_col_group": (),
                "x_vars": x_vars,
                "y_vars": y_vars,
                "steps_ahead": 1,
                "model_kwargs": {
                    "fit_intercept": False,
                },
                "nan_mode": "drop",
            },
            self._get_nid("residualize"): {
                "in_col_groups": [
                    ("ret_0.shift_-1",),
                    ("ret_0.shift_-1_hat",),
                ],
                "out_col_group": (),
                "transformer_kwargs": {
                    "term1_col": "ret_0.shift_-1",
                    "term2_col": "ret_0.shift_-1_hat",
                    "out_col": "residual.shift_-1",
                    "operation": "sub",
                },
            },
            self._get_nid("compute_rolling_norm"): {
                "in_col_group": ("residual.shift_-1",),
                "out_col_group": ("smoothed_squared_residual.shift_-1",),
                "transformer_kwargs": {
                    "tau": 10,
                },
            },
        }
        config = cconfig.Config.from_dict(dict_)
        return config

    def _get_dag(
        self,
        config: cconfig.Config,
        *,
        mode: str = "strict",
    ) -> dtfcore.DAG:
        """
        Build DAG given a `config`.

        :param config: DAG configuration
        :return: resulting `DAG` that is built from an input config
        """
        dag = dtfcore.DAG(mode=mode)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", config)
        #
        stage = "sklearn"
        nid = self._get_nid(stage)
        node = dtfcore.MultiindexSkLearnModel(
            nid,
            model_func=sklimod.LinearRegression,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "residualize"
        nid = self._get_nid(stage)
        node = dtfcore.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofeatur.combine_columns,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        stage = "compute_rolling_norm"
        nid = self._get_nid(stage)
        node = dtfcore.SeriesToSeriesTransformer(
            nid,
            transformer_func=csigproc.compute_rolling_norm,
            **config[nid].to_dict(),
        )
        dag.append_to_tail(node)
        #
        return dag
