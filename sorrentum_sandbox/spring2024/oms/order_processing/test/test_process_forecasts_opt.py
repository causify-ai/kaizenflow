import asyncio
import datetime
import logging
import os
from typing import Tuple

import pandas as pd
import pytest

import core.config as cconfig
import core.finance as cofinanc
import helpers.hasyncio as hasynci
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hunit_test as hunitest
import market_data as mdata
import oms

_LOG = logging.getLogger(__name__)


@pytest.mark.skip("CmTask #1580 Optimizer-related tests fail.")
class TestDataFrameProcessForecasts1(hunitest.TestCase):

    # TODO(gp): @all This can become an _example.
    # TODO(gp): @all -> get_process_forecasts_dict
    @staticmethod
    def get_process_forecasts_config() -> cconfig.Config:
        dict_ = {
            "order_config": {
                "order_type": "price@twap",
                "order_duration_in_mins": 5,
            },
            "optimizer_config": {
                "backend": "batch_optimizer",
                "dollar_neutrality_penalty": 0.1,
                "volatility_penalty": 0.5,
                "turnover_penalty": 0.0,
                "target_gmv": 1e5,
                "target_gmv_upper_bound_multiple": 1.0,
            },
            "execution_mode": "batch",
            "ath_start_time": datetime.time(9, 30),
            "trading_start_time": datetime.time(9, 35),
            "ath_end_time": datetime.time(16, 00),
            "trading_end_time": datetime.time(15, 55),
            "liquidate_at_trading_end_time": False,
        }
        config = cconfig.Config.from_dict(dict_)
        return config

    @pytest.mark.skip("Generate manually files used by other tests")
    def test_generate_data(self) -> None:
        """
        Generate market data, predictions, and volatility files used as inputs
        by other tests.

        This test might need to be run from an `amp` container.
        """
        # TODO(gp): Why importing here? Move it up.
        import core.finance_data_example as cfidaexa

        dir_ = self.get_input_dir()
        hio.create_dir(dir_, incremental=False)
        # Market data.
        start_datetime = pd.Timestamp(
            "2000-01-01 09:35:00-05:00", tz="America/New_York"
        )
        end_datetime = pd.Timestamp(
            "2000-01-01 10:30:00-05:00", tz="America/New_York"
        )
        asset_ids = [100, 200]
        market_data_df = cofinanc.generate_random_bars(
            start_datetime, end_datetime, asset_ids
        )
        market_data_df.to_csv(os.path.join(dir_, "market_data_df.csv"))
        # Prediction.
        forecasts = cfidaexa.get_forecast_dataframe(
            start_datetime + pd.Timedelta("5T"), end_datetime, asset_ids
        )
        prediction_df = forecasts["prediction"]
        prediction_df.to_csv(os.path.join(dir_, "prediction_df.csv"))
        # Volatility.
        volatility_df = forecasts["volatility"]
        volatility_df.to_csv(os.path.join(dir_, "volatility_df.csv"))

    # ///////////////////////////////////////////////////////////////////////////

    def get_input_filename(self, filename: str) -> str:
        dir_ = self.get_input_dir(test_method_name="test_generate_data")
        filename = os.path.join(dir_, filename)
        hdbg.dassert_file_exists(filename)
        return filename

    def get_market_data(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> mdata.MarketData:
        filename = self.get_input_filename("market_data_df.csv")
        market_data_df = pd.read_csv(
            filename,
            index_col=0,
            parse_dates=["start_datetime", "end_datetime", "timestamp_db"],
        )
        market_data_df = market_data_df.convert_dtypes()
        replayed_delay_in_mins_or_timestamp = 5
        market_data, _ = mdata.get_ReplayedTimeMarketData_from_df(
            event_loop,
            replayed_delay_in_mins_or_timestamp,
            market_data_df,
        )
        return market_data

    def get_predictions_and_volatility(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        filename = self.get_input_filename("prediction_df.csv")
        prediction_df = pd.read_csv(filename, index_col=0, parse_dates=True)
        prediction_df = prediction_df.convert_dtypes()
        prediction_df.index = prediction_df.index.tz_convert("America/New_York")
        prediction_df.columns = prediction_df.columns.astype("int64")
        #
        filename = self.get_input_filename("volatility_df.csv")
        volatility_df = pd.read_csv(filename, index_col=0, parse_dates=True)
        volatility_df = volatility_df.convert_dtypes()
        volatility_df.index = volatility_df.index.tz_convert("America/New_York")
        volatility_df.columns = volatility_df.columns.astype("int64")
        return prediction_df, volatility_df

    # TODO(gp): This can become an _example.
    def get_portfolio(
        self,
        event_loop: asyncio.AbstractEventLoop,
    ) -> oms.DataFramePortfolio:
        market_data = self.get_market_data(event_loop)
        asset_ids = market_data._asset_ids
        strategy_id = "strategy"
        account = "account"
        timestamp_col = "end_datetime"
        mark_to_market_col = "close"
        pricing_method = "last"
        initial_holdings = pd.Series([-50, 50, 0], asset_ids + [-1])
        column_remap = {
            "bid": "bid",
            "ask": "ask",
            "price": "close",
            "midpoint": "midpoint",
        }
        portfolio = oms.get_DataFramePortfolio_example2(
            strategy_id,
            account,
            market_data,
            timestamp_col,
            mark_to_market_col,
            pricing_method,
            initial_holdings,
            column_remap=column_remap,
        )
        return portfolio

    async def run_process_forecasts(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        """
        Run `process_forecasts()` logic with a given prediction df to update a
        Portfolio.
        """
        predictions, volatility = self.get_predictions_and_volatility()
        portfolio = self.get_portfolio(event_loop)
        config = self.get_process_forecasts_config()
        spread_df = None
        restrictions_df = None
        # Run.
        await oms.process_forecasts(
            predictions, volatility, portfolio, config, spread_df, restrictions_df
        )
        actual = str(portfolio)
        expected = r"""
# historical holdings=
asset_id                     100    200    -1
2000-01-01 09:40:01-05:00 -50.00  50.00    0.00
2000-01-01 09:45:01-05:00 -50.13  49.91  220.24
2000-01-01 09:50:01-05:00 -50.04  49.97   71.98
2000-01-01 09:55:01-05:00 -50.18  49.88  300.22
2000-01-01 10:00:01-05:00 -50.31  49.80  502.09
2000-01-01 10:05:01-05:00 -50.43  50.03  391.05
2000-01-01 10:10:01-05:00 -50.41  50.23  178.10
2000-01-01 10:15:01-05:00 -50.51  50.18  330.05
2000-01-01 10:20:01-05:00  50.39 -50.17  356.65
2000-01-01 10:25:01-05:00  50.42 -50.18  338.24
2000-01-01 10:30:01-05:00 -50.40  50.31   70.15
# historical holdings marked to market=
asset_id                        100       200     -1
2000-01-01 09:40:01-05:00 -49870.58  50090.60    0.00
2000-01-01 09:45:01-05:00 -50093.59  49945.23  220.24
2000-01-01 09:50:01-05:00 -49853.93  50082.38   71.98
2000-01-01 09:55:01-05:00 -49877.96  50080.36  300.22
2000-01-01 10:00:01-05:00 -49881.79  49770.19  502.09
2000-01-01 10:05:01-05:00 -50017.55  49804.66  391.05
2000-01-01 10:10:01-05:00 -49899.18  50050.87  178.10
2000-01-01 10:15:01-05:00 -50117.07  50012.75  330.05
2000-01-01 10:20:01-05:00  49971.56 -49989.93  356.65
2000-01-01 10:25:01-05:00  50021.69 -49865.87  338.24
2000-01-01 10:30:01-05:00 -49954.25  50212.32   70.15
# historical flows=
asset_id                         100        200
2000-01-01 09:45:01-05:00     130.55      89.69
2000-01-01 09:50:01-05:00     -92.82     -55.45
2000-01-01 09:55:01-05:00     145.15      83.09
2000-01-01 10:00:01-05:00     120.45      81.43
2000-01-01 10:05:01-05:00     118.91    -229.95
2000-01-01 10:10:01-05:00     -17.80    -195.15
2000-01-01 10:15:01-05:00     100.43      51.52
2000-01-01 10:20:01-05:00 -100049.90  100076.50
2000-01-01 10:25:01-05:00     -26.98       8.57
2000-01-01 10:30:01-05:00   99911.92 -100180.01
# historical pnl=
asset_id                      100     200
2000-01-01 09:40:01-05:00     NaN     NaN
2000-01-01 09:45:01-05:00  -92.45  -55.69
2000-01-01 09:50:01-05:00  146.84   81.71
2000-01-01 09:55:01-05:00  121.12   81.07
2000-01-01 10:00:01-05:00  116.61 -228.74
2000-01-01 10:05:01-05:00  -16.84 -195.48
2000-01-01 10:10:01-05:00  100.56   51.07
2000-01-01 10:15:01-05:00 -117.46   13.39
2000-01-01 10:20:01-05:00   38.73   73.82
2000-01-01 10:25:01-05:00   23.15  132.64
2000-01-01 10:30:01-05:00  -64.01 -101.82
# historical statistics=
                              pnl  gross_volume  net_volume        gmv     nmv    cash  net_wealth  leverage
2000-01-01 09:40:01-05:00     NaN          0.00        0.00   99961.18  220.02    0.00      220.02    454.32
2000-01-01 09:45:01-05:00 -148.14        220.24     -220.24  100038.81 -148.36  220.24       71.88   1391.72
2000-01-01 09:50:01-05:00  228.55        148.27      148.27   99936.31  228.46   71.98      300.43    332.64
2000-01-01 09:55:01-05:00  202.18        228.24     -228.24   99958.32  202.40  300.22      502.62    198.88
2000-01-01 10:00:01-05:00 -112.13        201.88     -201.88   99651.98 -111.61  502.09      390.49    255.20
2000-01-01 10:05:01-05:00 -212.32        348.86      111.04   99822.21 -212.89  391.05      178.16    560.28
2000-01-01 10:10:01-05:00  151.63        212.95      212.95   99950.06  151.69  178.10      329.80    303.06
2000-01-01 10:15:01-05:00 -104.07        151.95     -151.95  100129.82 -104.32  330.05      225.73    443.59
2000-01-01 10:20:01-05:00  112.55     200126.40      -26.60   99961.50  -18.37  356.65      338.28    295.50
2000-01-01 10:25:01-05:00  155.78         35.55       18.41   99887.56  155.82  338.24      494.07    202.17
2000-01-01 10:30:01-05:00 -165.84     200091.94      268.09  100166.57  258.07   70.15      328.23    305.17
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    # TODO(gp): -> test1
    @pytest.mark.skip("CmTask #1607 Flaky opt tests fail.")
    def test_initialization1(self) -> None:
        """
        Run the process forecasts.
        """
        with hasynci.solipsism_context() as event_loop:
            hasynci.run(
                self.run_process_forecasts(event_loop), event_loop=event_loop
            )
