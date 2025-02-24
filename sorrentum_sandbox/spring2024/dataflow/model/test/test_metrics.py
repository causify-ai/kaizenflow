import logging

import pandas as pd

import core.config as cconfig
import dataflow.model.metrics as dtfmodmetr
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def _get_result_data() -> pd.DataFrame:
    data = {
        ("vwap.ret_0.vol_adj.lag_-2", 1467591036): [0.199, 0.12, 0.13, 0.3],
        ("vwap.ret_0.vol_adj.lag_-2", 2002879833): [0.133, 0.2, 0.333, 0.113],
        ("vwap.ret_0.vol_adj.lag_-2", 3187272957): [0, 0.23, 0.31, 0.222],
        ("vwap.ret_0.vol_adj.shift_-2_hat", 1467591036): [
            0.22,
            0.232,
            0.221,
            0.112,
        ],
        ("vwap.ret_0.vol_adj.shift_-2_hat", 2002879833): [
            0.98,
            0.293,
            0.223,
            0.32,
        ],
        ("vwap.ret_0.vol_adj.shift_-2_hat", 3187272957): [
            0.38,
            0.283,
            0.821,
            0.922,
        ],
    }
    start_ts = pd.Timestamp("2022-08-28 00:50:00-04:00")
    end_ts = pd.Timestamp("2022-08-28 01:05:00-04:00")
    idx = pd.date_range(start_ts, end_ts, freq="5T")
    df = pd.DataFrame(data, index=idx)
    df.columns.set_names("asset_id", level=1)
    df.index.name = "end_ts"
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("result_df=\n%s", hpandas.df_to_str(df))
    return df


def _get_metrics_df() -> pd.DataFrame:
    df = _get_result_data()
    y_column_name = "vwap.ret_0.vol_adj.lag_-2"
    y_hat_column_name = "vwap.ret_0.vol_adj.shift_-2_hat"
    metrics_df = dtfmodmetr.convert_to_metrics_format(
        df, y_column_name, y_hat_column_name
    )
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("metrics_df=\n%s", hpandas.df_to_str(df))
    return metrics_df


class TestConvertToMetricsFormat(hunitest.TestCase):
    def test1(self) -> None:
        metrics_df = _get_metrics_df()
        actual = hpandas.df_to_str(metrics_df)
        expected = r"""
                                            vwap.ret_0.vol_adj.lag_-2  vwap.ret_0.vol_adj.shift_-2_hat
        end_ts                    asset_id
        2022-08-28 00:50:00-04:00 1467591036                    0.199                      0.22
                                  2002879833                    0.133                      0.98
                                  3187272957                    0.000                      0.38
        ...
        end_ts                    asset_id
        2022-08-28 01:05:00-04:00 1467591036                    0.300                     0.112
                                  2002879833                    0.113                     0.320
                                  3187272957                    0.222                     0.922
        """
        self.assert_equal(actual, expected, fuzzy_match=True)


class TestAnnotatedMetricsDf(hunitest.TestCase):
    """
    Check that metrics df is annotated correctly given a tag_mode.
    """

    def helper(self, tag_mode: str, expected: str) -> None:
        metrics_df = _get_metrics_df()
        config = {
            "backtest_config": "ccxt_small-all.5T.2022-09-01_2022-11-30",
            "column_names": {
                "target_variable": "vwap.ret_0.vol_adj.lag_-2",
                "prediction": "vwap.ret_0.vol_adj.shift_-2_hat",
            },
            "metrics": {
                "n_quantiles": 10,
            },
        }
        config = cconfig.Config().from_dict(config)
        annotated_df = dtfmodmetr.annotate_metrics_df(
            metrics_df, tag_mode, config
        )
        actual = hpandas.df_to_str(annotated_df)
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test1(self) -> None:
        """
        `tag_mode = "hour"`
        """
        tag_mode = "hour"
        expected = r"""
                                            vwap.ret_0.vol_adj.lag_-2  vwap.ret_0.vol_adj.shift_-2_hat  hour
        end_ts                    asset_id
        2022-08-28 00:50:00-04:00 1467591036                    0.199                          0.22    0
                                  2002879833                    0.133                          0.98    0
                                  3187272957                    0.000                          0.38    0
        ...
        end_ts                    asset_id
        2022-08-28 01:05:00-04:00 1467591036                    0.300                         0.112    1
                                  2002879833                    0.113                         0.320    1
                                  3187272957                    0.222                         0.922    1
        """
        self.helper(tag_mode, expected)

    def test2(self) -> None:
        """
        `tag_mode = "all"`
        """
        tag_mode = "all"
        expected = r"""
                                            vwap.ret_0.vol_adj.lag_-2  vwap.ret_0.vol_adj.shift_-2_hat   all
        end_ts                    asset_id
        2022-08-28 00:50:00-04:00 1467591036                    0.199                            0.22  all
                                  2002879833                    0.133                            0.98  all
                                  3187272957                    0.000                            0.38  all
        ...
        end_ts                    asset_id
        2022-08-28 01:05:00-04:00 1467591036                    0.300                           0.112  all
                                  2002879833                    0.113                           0.320  all
                                  3187272957                    0.222                           0.922  all
        """
        self.helper(tag_mode, expected)

    def test3(self) -> None:
        """
        `tag_mode = "target_var_magnitude_quantile_rank"`
        """
        tag_mode = "target_var_magnitude_quantile_rank"
        expected = r"""
                                             vwap.ret_0.vol_adj.lag_-2  vwap.ret_0.vol_adj.shift_-2_hat  target_var_magnitude_quantile_rank
        end_ts                    asset_id
        2022-08-28 00:50:00-04:00 1467591036                    0.199                      0.22                        6
                                  2002879833                    0.133                      0.98                        3
                                  3187272957                    0.000                      0.38                        0
        ...
        end_ts                    asset_id
        2022-08-28 01:05:00-04:00 1467591036                    0.300                     0.112                        9
                                  2002879833                    0.113                     0.320                        0
                                  3187272957                    0.222                     0.922                        3
        """
        self.helper(tag_mode, expected)

    def test4(self) -> None:
        """
        `tag_mode = "full_symbol"`
        """
        tag_mode = "full_symbol"
        expected = r"""
                                               vwap.ret_0.vol_adj.lag_-2  vwap.ret_0.vol_adj.shift_-2_hat        full_symbol
        end_ts                    asset_id
        2022-08-28 00:50:00-04:00 1467591036                      0.199                           0.22  binance::BTC_USDT
                                  2002879833                      0.133                           0.98   gateio::XRP_USDT
                                  3187272957                      0.000                           0.38   kucoin::ETH_USDT
        ...
        end_ts                    asset_id
        2022-08-28 01:05:00-04:00 1467591036                      0.300                          0.112  binance::BTC_USDT
                                  2002879833                      0.113                          0.320   gateio::XRP_USDT
                                  3187272957                      0.222                          0.922   kucoin::ETH_USDT
        """
        self.helper(tag_mode, expected)

    def test5(self) -> None:
        """
        `tag_mode = "prediction_magnitude_quantile_rank"`
        """
        tag_mode = "prediction_magnitude_quantile_rank"
        expected = r"""
                                              vwap.ret_0.vol_adj.lag_-2  vwap.ret_0.vol_adj.shift_-2_hat  prediction_magnitude_quantile_rank
        end_ts                    asset_id
        2022-08-28 00:50:00-04:00 1467591036                      0.199                           0.22                                   3
                                  2002879833                      0.133                           0.98                                   9
                                  3187272957                      0.000                           0.38                                   3
        ...
        end_ts                    asset_id
        2022-08-28 01:05:00-04:00 1467591036                      0.300                          0.112                                   0
                                  2002879833                      0.113                          0.320                                   6
                                  3187272957                      0.222                          0.922                                   9
        """
        self.helper(tag_mode, expected)
