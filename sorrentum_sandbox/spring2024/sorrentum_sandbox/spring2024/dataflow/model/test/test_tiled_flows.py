import datetime
import logging
import os
from typing import Any, Optional

import pandas as pd
import pytest

import core.config as cconfig
import core.finance_data_example as cfidaexa
import dataflow.model.forecast_evaluator_from_prices as dtfmfefrpr
import dataflow.model.tiled_flows as dtfmotiflo
import helpers.hgit as hgit
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hunit_test as hunitest
import optimizer.forecast_evaluator_with_optimizer as ofevwiop

_LOG = logging.getLogger(__name__)


class Test_evaluate_weighted_forecasts(hunitest.TestCase):
    @staticmethod
    def convert_to_parquet_format(df: pd.DataFrame) -> pd.DataFrame:
        df = df.stack()
        df.index.names = ["end_ts", "asset_id"]
        df = df.reset_index(level=1)
        df["year"] = df.index.year
        df["month"] = df.index.month
        return df

    @pytest.mark.requires_ck_infra
    def test_combine_two_signals(self) -> None:
        base_dir = self.get_scratch_space()
        start_datetime = pd.Timestamp(
            "2021-12-20 09:30:00", tz="America/New_York"
        )
        end_datetime = pd.Timestamp("2022-01-10 16:00:00", tz="America/New_York")
        asset_ids = [100, 200, 300, 400]
        # Generate strategy 1.
        df1 = cfidaexa.get_forecast_price_based_dataframe(
            start_datetime,
            end_datetime,
            asset_ids,
            bar_duration="30T",
            seed=10,
        )
        _LOG.info("df1=\n%s", df1)
        df1 = self.convert_to_parquet_format(df1)
        _LOG.info("df1=\n%s", df1)
        dir1 = os.path.join(base_dir, "sim1")
        hparque.to_partitioned_parquet(
            df1, ["asset_id", "year", "month"], dst_dir=dir1
        )
        # Generate strategy 2.
        df2 = cfidaexa.get_forecast_price_based_dataframe(
            start_datetime, end_datetime, asset_ids, bar_duration="30T", seed=20
        )
        _LOG.info("df2=\n%s", df2)
        df2 = self.convert_to_parquet_format(df2)
        _LOG.info("df2=\n%s", df2)
        dir2 = os.path.join(base_dir, "sim2")
        hparque.to_partitioned_parquet(
            df2, ["asset_id", "year", "month"], dst_dir=dir2
        )
        # Initialize dataframe pointing to the simulations.
        simulations = pd.DataFrame(
            [[dir1, "prediction"], [dir2, "prediction"]],
            ["sim1", "sim2"],
            ["dir_name", "prediction_col"],
        )
        # Initialize dataframe of weights.
        weights = pd.DataFrame(
            [[1.0, 0.0, 0.5], [0.0, 1.0, 0.5]],
            ["sim1", "sim2"],
            ["sim1", "sim2", "50-50"],
        )
        # Initialize dataframe pointing to price and volatility.
        data = pd.DataFrame(
            [[dir1, "price"], [dir1, "volatility"]],
            ["price", "volatility"],
            ["dir_name", "col"],
        )
        # Compute the resulting metrics.
        bar_metrics = dtfmotiflo.evaluate_weighted_forecasts(
            simulations,
            weights,
            data,
            datetime.date(2021, 12, 20),
            datetime.date(2022, 1, 10),
            "asset_id",
            asset_ids=None,
            annotate_forecasts_kwargs={
                "liquidate_at_end_of_day": False,
            },
            target_freq_str="30T",
            preapply_gaussian_ranking=True,
        )
        actual = hpandas.df_to_str(bar_metrics, num_rows=10, precision=2)
        expected = r"""
                              sim1                                                  sim2                                                 50-50
                               pnl gross_volume net_volume       gmv        nmv      pnl gross_volume net_volume       gmv        nmv      pnl gross_volume net_volume       gmv        nmv
end_ts
2021-12-20 12:00:00-05:00  -673.68     4.77e+05 -292609.33  9.99e+05  497751.84  -734.18     4.77e+05  -2.92e+05  9.99e+05  500200.62  -673.68     7.26e+05 -290160.55  9.99e+05  500200.62
2021-12-20 12:30:00-05:00 -1084.75     2.00e+06 -641598.62  1.00e+06 -144931.53   477.90     1.50e+06  -3.64e+05  1.00e+06  136774.80   477.90     1.38e+06 -645610.05  1.00e+06 -144931.53
2021-12-20 13:00:00-05:00  -247.31     1.43e+06  956486.47  1.00e+06  811307.62  -551.75     2.00e+06   6.75e+05  1.00e+06  811307.62  -247.31     1.43e+06  956486.47  1.00e+06  811307.62
2021-12-20 13:30:00-05:00  1079.62     1.17e+06 -850069.32  1.00e+06  -37682.08  1079.62     2.64e+05  -1.42e+05  1.00e+06  670238.89  1079.62     2.64e+05 -142148.35  1.00e+06  670238.89
2021-12-20 14:00:00-05:00  -125.20     3.63e+05 -244433.37  1.00e+06 -282240.66   448.75     2.00e+06  -1.13e+06  1.00e+06 -460021.45   448.75     1.52e+06 -653303.21  1.00e+06   17384.42
...
end_ts
2022-01-10 14:00:00-05:00  404.09     2.00e+06  521638.52  1.00e+06  309905.28  404.09     8.08e+05  183340.49  1.00e+06  -28392.76   404.09     2.00e+06  521638.52  1.00e+06  309905.28
2022-01-10 14:30:00-05:00  654.69     8.79e+05 -316012.94  1.00e+06   -5452.98  248.76     1.35e+06  149603.38  1.00e+06  121459.37   654.69     1.03e+06 -189100.59  1.00e+06  121459.37
2022-01-10 15:00:00-05:00  849.07     2.00e+06 -205502.75  1.00e+06 -210106.67  572.70     8.98e+05   88074.59  1.00e+06  210106.67   572.70     2.00e+06 -413183.39  1.00e+06 -291151.32
2022-01-10 15:30:00-05:00 -912.96     1.27e+06  270448.98  1.00e+06   59429.36  912.96     1.27e+06 -270448.98  1.00e+06  -59429.36 -1127.83     1.27e+06  255320.69  1.00e+06  -36958.46
2022-01-10 16:00:00-05:00  847.38     1.14e+06 -368085.80  9.99e+05 -307809.05 -847.38     1.31e+06   79002.84  9.99e+05   18726.10  -930.35     1.59e+06  464871.17  9.99e+05  426982.36"""
        self.assert_equal(actual, expected, fuzzy_match=True)


class Test_annotate_forecasts_by_tile(hunitest.TestCase):
    """
    Test annotating forecast by tile in dependency injection style.
    """

    @staticmethod
    def get_config() -> cconfig.Config:
        amp_dir = hgit.get_amp_abs_path()
        dir_name = os.path.join(
            amp_dir,
            "dataflow/model/test/outcomes/Test_annotate_forecasts_by_tile/input/tiled_results",
        )
        config = {
            "dir_name": dir_name,
            "start_date": datetime.date(2000, 1, 1),
            "end_date": datetime.date(2000, 2, 28),
            "asset_id_col": "asset_id",
            "pnl_resampling_frequency": "15T",
            "annotate_forecasts_kwargs": {
                "style": "longitudinal",
                "quantization": 30,
                "liquidate_at_end_of_day": False,
                "initialize_beginning_of_day_trades_to_zero": False,
                "burn_in_bars": 3,
                "compute_extended_stats": True,
                "target_dollar_risk_per_name": 1e2,
                "modulate_using_prediction_magnitude": True,
            },
            "column_names": {
                "price_col": "vwap",
                "volatility_col": "vwap.ret_0.vol",
                "prediction_col": "prediction",
            },
            "bin_annotated_portfolio_df_kwargs": {
                "proportion_of_data_per_bin": 0.2,
                "output_col": "pnl_in_bps",
                "normalize_prediction_col_values": False,
            },
        }
        config = cconfig.Config().from_dict(config)
        return config

    def test_annotate_forecasts_by_tile_from_prices(self) -> None:
        config = self.get_config()
        forecast_evaluator = dtfmfefrpr.ForecastEvaluatorFromPrices
        optimizer_config_dict = None
        exp = r"""
        pnl  gross_volume  net_volume       gmv       nmv  gpc  npc  wnl
end_ts
2000-01-01 15:30:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 15:35:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 15:40:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 15:45:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 15:50:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 15:55:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 16:00:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 16:05:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 16:10:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 16:15:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 16:20:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 16:25:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 16:30:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 16:35:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 16:40:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 16:45:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 16:50:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 16:55:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 17:00:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
2000-01-01 17:05:00+00:00  113.47      23035.27   -23035.27  11574.94 -11574.94  2.0 -2.0  2.0
2000-01-01 17:10:00+00:00  114.60      22807.20    22807.20  11346.87  11346.87  2.0  2.0  2.0
        """
        self._annotate_forecasts_by_tile_helper(
            config,
            exp,
            forecast_evaluator,
            optimizer_config_dict=optimizer_config_dict,
        )

    @pytest.mark.skip(reason="Small values.")
    def test_annotate_forecasts_by_tile_with_optimizer(self) -> None:
        config = self.get_config()
        forecast_evaluator = ofevwiop.ForecastEvaluatorWithOptimizer
        optimizer_config_dict = {
            "dollar_neutrality_penalty": 0.9,
            "constant_correlation": 0.0,
            "constant_correlation_penalty": 0.01,
            "relative_holding_penalty": 0.0,
            "relative_holding_max_frac_of_gmv": 0.6,
            "target_gmv": 1e5,
            "target_gmv_upper_bound_penalty": 0.95,
            "target_gmv_hard_upper_bound_multiple": 1.00,
            "transaction_cost_penalty": 0.01,
            "solver": "ECOS",
        }
        exp = r"""
                                pnl  gross_volume  net_volume       gmv       nmv  gpc  npc  wnl
2000-01-01 15:30:00+00:00  7.32e-10      1.49e-07    1.49e-07  7.56e-08  7.56e-08  2.0  2.0  2.0
2000-01-01 15:35:00+00:00  7.56e-10      1.53e-07   -1.53e-07  7.68e-08 -7.68e-08  2.0 -2.0  2.0
2000-01-01 15:40:00+00:00  7.60e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 15:45:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 15:50:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 15:55:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 16:00:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 16:05:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 16:10:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 16:15:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 16:20:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 16:25:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 16:30:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 16:35:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 16:40:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 16:45:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 16:50:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 16:55:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 17:00:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
2000-01-01 17:05:00+00:00  7.50e-10      1.53e-07   -1.53e-07  7.69e-08 -7.69e-08  2.0 -2.0  2.0
2000-01-01 17:10:00+00:00  7.61e-10      1.51e-07    1.51e-07  7.50e-08  7.50e-08  2.0  2.0  2.0
"""
        self._annotate_forecasts_by_tile_helper(
            config,
            exp,
            forecast_evaluator,
            optimizer_config_dict=optimizer_config_dict,
        )

    def _annotate_forecasts_by_tile_helper(
        self,
        config: cconfig.Config,
        exp: str,
        forecast_evaluator: Any,
        *,
        optimizer_config_dict: Optional[dict]
    ) -> None:
        portfolio_df, bar_metrics = dtfmotiflo.annotate_forecasts_by_tile(
            config["dir_name"],
            config["start_date"],
            config["end_date"],
            config["asset_id_col"],
            config["column_names"]["price_col"],
            config["column_names"]["volatility_col"],
            config["column_names"]["prediction_col"],
            asset_ids=None,
            annotate_forecasts_kwargs=config[
                "annotate_forecasts_kwargs"
            ].to_dict(),
            return_portfolio_df=True,
            forecast_evaluator=forecast_evaluator,
            optimizer_config_dict=optimizer_config_dict,
        )
        actual = hpandas.df_to_str(bar_metrics, num_rows=None, precision=2)
        expected = exp
        self.assert_equal(actual, expected, fuzzy_match=True)
