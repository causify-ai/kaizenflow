"""
Import as:

import dataflow.core.dag_builder_example as dtfcdabuex
"""

import datetime
import logging

import pandas as pd

import core.config as cconfig
import core.finance as cofinanc
import dataflow.core.dag as dtfcordag
import dataflow.core.dag_builder as dtfcodabui
import dataflow.core.nodes.sources as dtfconosou
import dataflow.core.nodes.transformers as dtfconotra
import dataflow.core.nodes.volatility_models as dtfcnovomo

_LOG = logging.getLogger(__name__)


# #############################################################################
# LoadPrices_DagBuilder
# #############################################################################


class LoadPrices_DagBuilder(dtfcodabui.DagBuilder):
    """
    Pipeline containing a single node with a data source node factory.
    """

    @staticmethod
    def get_column_name(tag: str) -> str:
        """
        See description in the parent class.
        """
        raise NotImplementedError

    def get_config_template(self) -> cconfig.Config:
        """
        See description in the parent class.
        """
        dict_ = {
            self._get_nid("load_prices"): {
                "func": lambda x: x,
            },
        }
        config = cconfig.Config.from_dict(dict_)
        return config

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

    def _get_dag(
        self, config: cconfig.Config, mode: str = "strict"
    ) -> dtfcordag.DAG:
        """
        See description in the parent class.
        """
        dag = dtfcordag.DAG(mode=mode)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", config)
        tail_nid = None
        # # Read data.
        stage = "load_prices"
        nid = self._get_nid(stage)
        # TDOO: Do not use this node in `core`.
        node = dtfconosou.FunctionDataSource(nid, **config[nid].to_dict())
        tail_nid = self._append(dag, tail_nid, node)
        #
        _ = tail_nid
        return dag


# #############################################################################
# Returns_DagBuilder
# #############################################################################


class Returns_DagBuilder(dtfcodabui.DagBuilder):
    """
    Pipeline for generating filtered returns from a given `DataSource` node.
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
        # Get a key for trading period inside the config.
        resample_nid = self._get_nid("rets/resample")
        key = (resample_nid, "func_kwargs", "rule")
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
        config[self._get_nid("rets/resample")]["func_kwargs"]["rule"] = "2T"
        return config

    def get_config_template(self) -> cconfig.Config:
        """
        See description in the parent class.
        """
        config = cconfig.Config.from_dict(
            {
                # Filter ATH.
                self._get_nid("rets/filter_ath"): {
                    "col_mode": "replace_all",
                    "transformer_kwargs": {
                        "start_time": datetime.time(9, 30),
                        "end_time": datetime.time(16, 00),
                    },
                },
                # Compute TWAP and VWAP.
                self._get_nid("rets/resample"): {
                    "func_kwargs": {
                        "rule": "5T",
                        "resampling_groups": [
                            (
                                {"close": "twap"},
                                "mean",
                                {},
                            ),
                        ],
                        "vwap_groups": [
                            ("close", "volume", "vwap"),
                        ],
                    },
                },
                # Calculate rets.
                self._get_nid("rets/compute_ret_0"): {
                    "cols": ["twap", "vwap"],
                    "col_mode": "merge_all",
                    "transformer_kwargs": {
                        "mode": "pct_change",
                    },
                },
                # Model volatility.
                self._get_nid("rets/model_volatility"): {
                    "cols": ["vwap_ret_0"],
                    "steps_ahead": 2,
                    "nan_mode": "leave_unchanged",
                },
                # Clip rets.
                self._get_nid("rets/clip"): {
                    "cols": ["vwap_ret_0_vol_adj"],
                    "col_mode": "replace_selected",
                },
            }
        )
        return config

    def _get_dag(
        self, config: cconfig.Config, mode: str = "strict"
    ) -> dtfcordag.DAG:
        """
        See description in the parent class.
        """
        dag = dtfcordag.DAG(mode=mode)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", config)
        # Set weekends to Nan.
        stage = "rets/filter_weekends"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_weekends_to_nan,
            col_mode="replace_all",
        )
        tail_nid = self._append(dag, None, node)
        # Set non-ATH to NaN.
        stage = "rets/filter_ath"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_non_ath_to_nan,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Resample.
        stage = "rets/resample"
        nid = self._get_nid(stage)
        node = dtfconotra.FunctionWrapper(
            nid,
            func=cofinanc.resample_bars,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Compute returns.
        stage = "rets/compute_ret_0"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=cofinanc.compute_ret_0,
            col_rename_func=lambda x: x + "_ret_0",
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Model volatility.
        stage = "rets/model_volatility"
        nid = self._get_nid(stage)
        node = dtfcnovomo.VolatilityModel(nid, **config[nid].to_dict())
        tail_nid = self._append(dag, tail_nid, node)
        # Clip rets.
        stage = "rets/clip"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=lambda x: x.clip(lower=-3, upper=3),
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        _ = tail_nid
        return dag


# #############################################################################
# ArmaReturnsBuilder
# #############################################################################


# TODO(gp): Builder -> _DagBuilder
# TODO(gp): Remove the first node from these DAG and express ArmaReturnsBuilder and
#  MvnReturnsBuilder in terms of a MarketData and ReturnsBuilder.
class ArmaReturnsBuilder(dtfcodabui.DagBuilder):
    """
    Pipeline for generating filtered returns from an ARMA process.
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
        # Get a key for trading period inside the config.
        resample_nid = self._get_nid("rets/resample")
        key = (resample_nid, "func_kwargs", "rule")
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
        config[self._get_nid("rets/resample")]["func_kwargs"]["rule"] = "2T"
        return config

    def get_config_template(self) -> cconfig.Config:
        """
        See description in the parent class.
        """
        config = cconfig.Config.from_dict(
            {
                # Load prices.
                self._get_nid("rets/read_data"): {
                    "frequency": "T",
                    "start_date": "2010-01-04 09:00:00",
                    "end_date": "2010-01-04 16:30:00",
                    "ar_coeffs": [0],
                    "ma_coeffs": [0],
                    "scale": 0.1,
                    "burnin": 0,
                    "seed": 0,
                },
                # Filter ATH.
                self._get_nid("rets/filter_ath"): {
                    "col_mode": "replace_all",
                    "transformer_kwargs": {
                        "start_time": datetime.time(9, 30),
                        "end_time": datetime.time(16, 00),
                    },
                },
                # Compute TWAP and VWAP.
                self._get_nid("rets/resample"): {
                    "func_kwargs": {
                        "rule": "5T",
                        "resampling_groups": [
                            (
                                {"close": "twap"},
                                "mean",
                                {},
                            ),
                        ],
                        "vwap_groups": [
                            ("close", "volume", "vwap"),
                        ],
                    },
                },
                # Calculate rets.
                self._get_nid("rets/compute_ret_0"): {
                    "cols": ["twap", "vwap"],
                    "col_mode": "merge_all",
                    "transformer_kwargs": {
                        "mode": "pct_change",
                    },
                },
                # Model volatility.
                self._get_nid("rets/model_volatility"): {
                    "cols": ["vwap_ret_0"],
                    "steps_ahead": 2,
                    "nan_mode": "leave_unchanged",
                },
                # Clip rets.
                self._get_nid("rets/clip"): {
                    "cols": ["vwap_ret_0_vol_adj"],
                    "col_mode": "replace_selected",
                },
            }
        )
        return config

    def _get_dag(
        self, config: cconfig.Config, mode: str = "strict"
    ) -> dtfcordag.DAG:
        """
        See description in the parent class.
        """
        dag = dtfcordag.DAG(mode=mode)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", config)
        # Read data.
        stage = "rets/read_data"
        nid = self._get_nid(stage)
        node = dtfconosou.ArmaDataSource(nid, **config[nid].to_dict())
        tail_nid = self._append(dag, None, node)
        # Set weekends to Nan.
        stage = "rets/filter_weekends"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_weekends_to_nan,
            col_mode="replace_all",
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Set non-ATH to NaN.
        stage = "rets/filter_ath"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_non_ath_to_nan,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Resample.
        stage = "rets/resample"
        nid = self._get_nid(stage)
        node = dtfconotra.FunctionWrapper(
            nid,
            func=cofinanc.resample_bars,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Compute returns.
        stage = "rets/compute_ret_0"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=cofinanc.compute_ret_0,
            col_rename_func=lambda x: x + "_ret_0",
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        # Model volatility.
        stage = "rets/model_volatility"
        nid = self._get_nid(stage)
        node = dtfcnovomo.VolatilityModel(nid, **config[nid].to_dict())
        tail_nid = self._append(dag, tail_nid, node)
        # Clip rets.
        stage = "rets/clip"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=lambda x: x.clip(lower=-3, upper=3),
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        _ = tail_nid
        return dag


# #############################################################################
# MvnReturns_DagBuilder
# #############################################################################


# TODO(gp): -> MultivariateReturns_DagBuilder
class MvnReturns_DagBuilder(dtfcodabui.DagBuilder):
    """
    Pipeline for generating filtered returns from a Multivariate Normal
    process.
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
        config[self._get_nid("resample")]["transformer_kwargs"]["rule"] = "2T"
        return config

    def get_config_template(self) -> cconfig.Config:
        """
        See description in the parent class.
        """
        config = cconfig.Config.from_dict(
            {
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
                        "rule": "5T",
                        "resampling_groups": [
                            (
                                {"close": "close"},
                                "last",
                                {},
                            ),
                            (
                                {"close": "twap"},
                                "mean",
                                {},
                            ),
                            (
                                {
                                    "volume": "volume",
                                },
                                "sum",
                                {"min_count": 1},
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
            },
        )
        return config

    def _get_dag(
        self, config: cconfig.Config, mode: str = "strict"
    ) -> dtfcordag.DAG:
        """
        Generate pipeline DAG.
        """
        dag = dtfcordag.DAG(mode=mode)
        if _LOG.isEnabledFor(logging.DEBUG):
            _LOG.debug("%s", config)
        #
        stage = "filter_weekends"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_weekends_to_nan,
            col_mode="replace_all",
        )
        tail_nid = self._append(dag, None, node)
        #
        stage = "filter_ath"
        nid = self._get_nid(stage)
        node = dtfconotra.ColumnTransformer(
            nid,
            transformer_func=cofinanc.set_non_ath_to_nan,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "resample"
        nid = self._get_nid(stage)
        node = dtfconotra.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.resample_bars,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        stage = "compute_ret_0"
        nid = self._get_nid(stage)
        node = dtfconotra.GroupedColDfToDfTransformer(
            nid,
            transformer_func=cofinanc.compute_ret_0,
            **config[nid].to_dict(),
        )
        tail_nid = self._append(dag, tail_nid, node)
        #
        _ = tail_nid
        return dag
