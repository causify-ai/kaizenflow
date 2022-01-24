"""
Import as:

import dataflow.system.sink_nodes as dtfsysinod
"""

# TODO(gp): -> sink_nodes.py

import collections
import logging
from typing import Any, Dict

import pandas as pd

import dataflow.core as dtfcore
import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import oms.portfolio as omportfo
import oms.process_forecasts as oprofore

_LOG = logging.getLogger(__name__)


class ProcessForecasts(dtfcore.FitPredictNode):
    """
    Place trades from a model.
    """

    def __init__(
        self,
        nid: dtfcore.NodeId,
        prediction_col: str,
        volatility_col: str,
        portfolio: omportfo.AbstractPortfolio,
        process_forecasts_config: Dict[str, Any],
    ) -> None:
        """
        Parameters have the same meaning as in `process_forecasts()`.
        """
        super().__init__(nid)
        self._prediction_col = prediction_col
        self._volatility_col = volatility_col
        self._portfolio = portfolio
        self._process_forecasts_config = process_forecasts_config

    def fit(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._compute_forecasts(df_in, fit=True)

    def predict(self, df_in: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        return self._compute_forecasts(df_in, fit=False)

    async def process_forecasts(self) -> None:
        # Get the latest `df` index value.
        await oprofore.process_forecasts(
            self._prediction_df,
            self._volatility_df,
            self._portfolio,
            self._process_forecasts_config,
        )

    def _compute_forecasts(
        self, df: pd.DataFrame, fit: bool = True
    ) -> Dict[str, pd.DataFrame]:
        hdbg.dassert_in(self._prediction_col, df.columns)
        # Make sure it's multi-index.
        hdbg.dassert_lte(2, df.columns.nlevels)
        hdbg.dassert_isinstance(df.index, pd.DatetimeIndex)
        # TODO(gp): Maybe pass the entire multi-index df and the name of
        #  pred_col and vol_col.
        prediction_df = df[self._prediction_col]
        self._prediction_df = prediction_df
        _LOG.debug("prediction_df=\n%s", hpandas.dataframe_to_str(prediction_df))
        #
        volatility_df = df[self._volatility_col]
        self._volatility_df = volatility_df
        _LOG.debug("volatility_df=\n%s", hpandas.dataframe_to_str(volatility_df))
        # Compute stats.
        info = collections.OrderedDict()
        info["df_out_info"] = dtfcore.get_df_info_as_string(df)
        mode = "fit" if fit else "predict"
        self._set_info(mode, info)
        # Pass the dataframe through.
        return {"df_out": df}
