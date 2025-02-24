import logging

import pandas as pd

import core.finance_data_example as cfidaexa
import core.plotting.portfolio_stats as cplposta
import helpers.hpandas as hpandas

_LOG = logging.getLogger(__name__)


class Test_plot_portfolio_stats1:
    def test1(self) -> None:
        start_datetime = pd.Timestamp("2001-01-01", tz="America/New_York")
        end_datetime = pd.Timestamp("2001-01-02", tz="America/New_York")
        bar_metrics = cfidaexa.get_portfolio_bar_metrics_dataframe(
            start_datetime, end_datetime
        )
        _LOG.debug("bar_metrics=\n%s", hpandas.df_to_str(bar_metrics))
        cplposta.plot_portfolio_stats(bar_metrics)
