import math
import os
from typing import Any

import pandas as pd
import pytest

import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest
import oms.broker.ccxt.ccxt_aggregation_functions as obccagfu
import oms.broker.ccxt.ccxt_execution_quality as obccexqu
import oms.broker.ccxt.ccxt_logger as obcccclo


def _check(self_: Any, actual: pd.DataFrame) -> None:
    actual = hpandas.df_to_str(actual, num_rows=None)
    self_.check_string(actual)


def _load_data_from_s3(
    self_: Any, use_only_test_class: bool
) -> obcccclo.CcxtLogger:
    # Load the data from S3.
    s3_input_dir = self_.get_s3_input_dir(use_only_test_class=use_only_test_class)
    scratch_dir = self_.get_scratch_space()
    aws_profile = "ck"
    hs3.copy_data_from_s3_to_local_dir(s3_input_dir, scratch_dir, aws_profile)
    ccxt_log_reader = obcccclo.CcxtLogger(scratch_dir)
    return ccxt_log_reader


def _load_oms_child_order_df(self_: Any) -> pd.DataFrame:
    """
    Load unpacked OMS child order DataFrame.
    """
    # Get path to prices.
    oms_child_order_path = os.path.join(
        self_._base_dir_name, "mock/oms_child_orders_unpacked.csv"
    )
    oms_child_order_df = pd.read_csv(
        oms_child_order_path,
        index_col="order_id",
        parse_dates=[
            "end_timestamp",
            "creation_timestamp",
            "start_timestamp",
            "exchange_timestamp",
            "knowledge_timestamp",
            "end_download_timestamp",
            "stats__submit_twap_child_order::get_open_positions.done",
            "stats__submit_twap_child_order::bid_ask_market_data.start",
            "stats__submit_twap_child_order::bid_ask_market_data.done",
            "stats__submit_twap_child_order::child_order.created",
            "stats__submit_twap_child_order::child_order.limit_price_calculated",
            "stats__submit_single_order_to_ccxt::start.timestamp",
            "stats__submit_single_order_to_ccxt::all_attempts_end.timestamp",
            "stats__submit_twap_child_order::child_order.submission_started",
            "stats__submit_twap_child_order::child_order.submitted",
        ],
    )
    return oms_child_order_df


class Test_get_limit_order_price(hunitest.TestCase):
    """
    Verify that `get_limit_order_price()` gets limit order prices from orders
    correctly.
    """

    @pytest.mark.slow("~7 sec.")
    def test1(self) -> None:
        """
        Test using the real data.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        oms_child_order_df = logger.load_oms_child_order(
            convert_to_dataframe=True
        )
        freq = "T"
        # Run.
        actual = obccexqu.get_limit_order_price(oms_child_order_df, freq=freq)
        # Check.
        _check(self, actual)


class Test_align_ccxt_orders_and_fills(hunitest.TestCase):
    """
    Verify that CCXT orders and fills are aligned correctly.
    """

    @pytest.mark.slow("~8 sec.")
    def test1(self) -> None:
        """
        Check filled Dataframe.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        ccxt_order_response_df = logger.load_ccxt_order_response(
            convert_to_dataframe=True
        )
        # Run.
        filled_df, _ = obccexqu.align_ccxt_orders_and_fills(
            ccxt_order_response_df, fills_df
        )
        # Check filled df.
        _check(self, filled_df)

    @pytest.mark.slow("~8 sec.")
    def test2(self) -> None:
        """
        Check unfilled Dataframe.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        ccxt_order_response_df = logger.load_ccxt_order_response(
            convert_to_dataframe=True
        )
        # Run.
        _, unfilled_df = obccexqu.align_ccxt_orders_and_fills(
            ccxt_order_response_df, fills_df
        )
        # Check unfilled df.
        _check(self, unfilled_df)


class Test_annotate_fills_df_with_wave_id(hunitest.TestCase):
    """
    Verify that fills are annotated with wave_id's correctly.
    """

    @pytest.mark.slow("~7 sec.")
    def test1(self) -> None:
        """
        Test using the real data.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        child_order_df = logger.load_oms_child_order(convert_to_dataframe=True)
        # Run.
        annotated_fills_df = obccexqu.annotate_fills_df_with_wave_id(
            fills_df, child_order_df
        )
        # Check.
        _check(self, annotated_fills_df)


class Test_compute_filled_order_execution_quality(hunitest.TestCase):
    """
    Verify that filled order execution quality is computed correctly.
    """

    @pytest.mark.slow("~7 sec.")
    def test1(self) -> None:
        """
        Test using the real data.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        ccxt_order_response_df = logger.load_ccxt_order_response(
            convert_to_dataframe=True
        )
        # Get filled orders.
        filled_ccxt_orders, _ = obccexqu.align_ccxt_orders_and_fills(
            ccxt_order_response_df, fills_df
        )
        tick_decimals = 2
        # Run.
        actual = obccexqu.compute_filled_order_execution_quality(
            filled_ccxt_orders, tick_decimals
        )
        # Check.
        _check(self, actual)


class Test_convert_bar_fills_to_portfolio_df(hunitest.TestCase):
    """
    Verify that fills, aggregated by bar, are converted into a portfolio df
    correctly.
    """

    @pytest.mark.slow("~7 sec.")
    # TODO(Sonya): Inline the result dataframe.
    def test1(self) -> None:
        """
        Test using the real data.
        """
        # Load the data.
        use_only_test_class = False
        # The downloaded sample is a copy of
        # `ecs/test/system_reconciliation/C5b/prod/20231124_093000.20231124_102500/system_log_dir.manual/process_forecasts`.
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        bar_duration = "5T"
        bar_fills = obccagfu.aggregate_fills_by_bar(
            fills_df, bar_duration, groupby_id_col="asset_id"
        )
        # Use `twap` price.
        price_df = self._load_bar_price_reference(bar_duration)
        # Run.
        portfolio_df = obccexqu.convert_bar_fills_to_portfolio_df(
            bar_fills, price_df
        )
        # Check.
        _check(self, portfolio_df)

    @pytest.mark.slow("~7 sec.")
    def test2(self) -> None:
        """
        Test on data that contains bars with 0 trades.
        """
        # Load the data.
        use_only_test_class = False
        # The downloaded sample is a copy of
        # `/data/shared/ecs/test/system_reconciliation/C12a/prod/20240212_150000.20240212_155700/system_log_dir.manual/process_forecasts`.
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        bar_duration = "3T"
        bar_fills = obccagfu.aggregate_fills_by_bar(
            fills_df, bar_duration, groupby_id_col="asset_id"
        )
        # Use `close` price.
        price_df = self._load_bar_price_reference(bar_duration)
        # Run.
        portfolio_df = obccexqu.convert_bar_fills_to_portfolio_df(
            bar_fills, price_df
        )
        # Check.
        _check(self, portfolio_df)

    def _load_bar_price_reference(self, index_freq: str):
        """
        Load bar reference price from CSV file.
        """
        # It is assumed that price data is copied from S3 to the scratch dir.
        scratch_dir = self.get_scratch_space()
        # Get path to prices.
        # This is a dump of OHLCV data from the pre-prod db. The time period must match one in `fills_df`.
        price_df_path = os.path.join(scratch_dir, "bar_reference_price.csv")
        # Price Dataframe is stored in database so we have the copy on github for the test purposes.
        price_df = pd.read_csv(
            price_df_path,
            parse_dates=["end_timestamp"],
            index_col="end_timestamp",
        )
        price_df.index = price_df.index.tz_convert("America/New_York")
        price_df.index.freq = index_freq
        price_df.columns = price_df.columns.astype(int)
        return price_df


class Test_generate_fee_summary(hunitest.TestCase):
    """
    Test that fees are summarized correctly.
    """

    @pytest.mark.slow("~6 sec.")
    def test1(self) -> None:
        """
        Test grouping by takerOrMaker to get fee summary.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        group_by_col = "is_maker"
        # Run.
        actual = obccexqu.generate_fee_summary(fills_df, group_by_col)
        # Check.
        _check(self, actual)

    @pytest.mark.slow("~6 sec.")
    def test2(self) -> None:
        """
        Test grouping by takerOrMaker to get fee summary.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        group_by_col = "is_positive_realized_pnl"
        # Run.
        actual = obccexqu.generate_fee_summary(fills_df, group_by_col)
        # Check.
        _check(self, actual)

    @pytest.mark.slow("~7 sec.")
    def test3(self) -> None:
        """
        Test grouping by takerOrMaker to get fee summary.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        group_by_col = "is_positive_realized_pnl"
        # Run.
        actual = obccexqu.generate_fee_summary(fills_df, group_by_col)
        # Check.
        _check(self, actual)

    @pytest.mark.slow("~7 sec.")
    def test4(self) -> None:
        """
        Test grouping by wave_id to get fee summary.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        child_order_df = logger.load_oms_child_order(convert_to_dataframe=True)
        fills_df = obccexqu.annotate_fills_df_with_wave_id(
            fills_df, child_order_df
        )
        group_by_col = "wave_id"
        # Run.
        actual = obccexqu.generate_fee_summary(fills_df, group_by_col)
        # Check.
        _check(self, actual)


class Test_compute_adj_fill_ecdfs(hunitest.TestCase):
    """
    Verify that adjusted time-to-fill eCDFs are computed correctly.
    """

    @pytest.mark.superslow("~8 sec.")
    def test1(self) -> None:
        """
        Test using the real data.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        oms_child_order_df = logger.load_oms_child_order(
            convert_to_dataframe=True
        )
        ccxt_order_response_df = logger.load_ccxt_order_response(
            convert_to_dataframe=True
        )
        # Run.
        adj_ecdf_df = obccexqu.compute_adj_fill_ecdfs(
            fills_df, ccxt_order_response_df, oms_child_order_df
        )
        # Check.
        _check(self, adj_ecdf_df)

    @pytest.mark.superslow("~8 sec.")
    def test2(self) -> None:
        """
        Test using the real data, separated by wave.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        oms_child_order_df = logger.load_oms_child_order(
            convert_to_dataframe=True
        )
        ccxt_order_response_df = logger.load_ccxt_order_response(
            convert_to_dataframe=True
        )
        # Run.
        by_wave = True
        adj_ecdf = obccexqu.compute_adj_fill_ecdfs(
            fills_df, ccxt_order_response_df, oms_child_order_df, by_wave=by_wave
        )
        # Check.
        #
        # Convert DataFrames to string.
        actual_dict = {}
        for wave_id, df in adj_ecdf.items():
            actual_df = hpandas.df_to_str(df)
            actual_dict[wave_id] = actual_df
        self.check_string(str(actual_dict))

    @pytest.mark.slow("~8 sec.")
    def test3(self) -> None:
        """
        Test using the real data with empty fills, separated by wave.
        """
        # Load the data.
        use_only_test_class = True
        logger = _load_data_from_s3(self, use_only_test_class)
        #
        fills_df = logger.load_ccxt_trades(convert_to_dataframe=True)
        oms_child_order_df = logger.load_oms_child_order(
            convert_to_dataframe=True
        )
        ccxt_order_response_df = logger.load_ccxt_order_response(
            convert_to_dataframe=True
        )
        # Run.
        by_wave = True
        adj_ecdf = obccexqu.compute_adj_fill_ecdfs(
            fills_df, ccxt_order_response_df, oms_child_order_df, by_wave=by_wave
        )
        # Check.
        #
        # Convert DataFrames to string.
        actual_dict = {}
        for wave_id, df in adj_ecdf.items():
            actual_df = hpandas.df_to_str(df)
            actual_dict[wave_id] = actual_df
        self.check_string(str(actual_dict))


class Test_get_oms_child_order_timestamps(hunitest.TestCase):
    """
    Verify that timing columns are extracted correctly from oms child order
    DataFrame.
    """

    def test1(self) -> None:
        """
        Test using valid data.
        """
        # Load the data.
        oms_child_order_df = _load_oms_child_order_df(self)
        # Run.
        actual = obccexqu.get_oms_child_order_timestamps(oms_child_order_df)
        actual_str = hpandas.df_to_str(actual)
        # Check.
        self.check_string(actual_str)

    def test2(self) -> None:
        """
        Test with missing columns.
        """
        # Load the data.
        oms_child_order_df = _load_oms_child_order_df(self)
        #
        oms_child_order_df = oms_child_order_df.drop(
            columns=[
                "stats__submit_twap_child_order::bid_ask_market_data.start",
                "exchange_timestamp",
            ]
        )
        # Run.
        with self.assertRaises(KeyError) as cm:
            obccexqu.get_oms_child_order_timestamps(oms_child_order_df)
        # Check.
        exp = r"""
        "['exchange_timestamp', 'stats__submit_twap_child_order::bid_ask_market_data.start'] not in index"
        """
        self.assert_equal(str(cm.exception), exp, fuzzy_match=True)


class Test_get_time_delay_between_events(hunitest.TestCase):
    """
    Verify that delays in seconds before the previous timestamp are extracted
    for each timestamp.
    """

    def test1(self) -> None:
        """
        Test using unsorted data.
        """
        # Prepare the data.
        oms_child_order_df = _load_oms_child_order_df(self)
        wave = obccexqu.get_oms_child_order_timestamps(oms_child_order_df)
        # Run.
        with self.assertRaises(AssertionError) as cm:
            obccexqu.get_time_delay_between_events(wave)
        # Check.
        exp = r"""
        * Failed assertion *
        '10'
        ==
        '0'
        """
        self.assert_equal(str(cm.exception), exp, fuzzy_match=True)

    def test2(self) -> None:
        """
        Test using sorted data.
        """
        # Prepare the data.
        oms_child_order_df = _load_oms_child_order_df(self)
        wave = obccexqu.get_oms_child_order_timestamps(oms_child_order_df)
        wave = wave.sort_values(wave.first_valid_index(), axis=1)
        # Run.
        time_delays = obccexqu.get_time_delay_between_events(wave)
        # Convert DataFrame to string and check.
        actual = hpandas.df_to_str(time_delays)
        self.check_string(actual)

    def test3(self) -> None:
        """
        Test using data where earliest `stats_` have earlier timestamp than
        `knowledge_timestamp`.
        """
        # Prepare the data.
        oms_child_order_df = _load_oms_child_order_df(self)
        wave = obccexqu.get_oms_child_order_timestamps(oms_child_order_df)
        wave = wave.sort_values(wave.first_valid_index(), axis=1)
        # Increase knowledge_timestamp by 0.1 second.
        wave["knowledge_timestamp"] = wave["knowledge_timestamp"] + pd.Timedelta(
            seconds=0.1
        )
        # Run.
        time_delays = obccexqu.get_time_delay_between_events(wave)
        # Convert DataFrame to string and check.
        actual = hpandas.df_to_str(time_delays)
        self.check_string(actual)


class Test_get_adjusted_close_price(hunitest.TestCase):
    """
    Verify that adjusted close is computed correctly.
    """

    def test1(self) -> None:
        """
        Test if adjusted close is computed correctly.
        """
        # Set up test data.
        close = pd.Series([None, 0.28475, None, 0.28505])
        open = pd.Series([0.28375, 0.28495, 0.28475, 0.28495])
        total = pd.Series([0.000284, 0.000364, 0.000287, 0.000462])
        # Run.
        act = list(obccexqu.get_adjusted_close_price(close, open, total))
        # Check.
        # We cannot use `self.assert_equal()` on `nan` because `nan != nan`.
        # So we check all values separately.
        self.assertTrue(math.isnan(act[0]))
        self.assertEqual(act[1], -0.5494505494504889)
        self.assertTrue(math.isnan(act[2]))
        self.assertEqual(act[3], 0.21645021645031276)

    def test2(self) -> None:
        """
        Test if adjusted close is computed correctly with no NaNs.
        """
        # Set up test data.
        close = pd.Series([0.28435, 0.28475, 0.28495, 0.28505])
        open = pd.Series([0.28375, 0.28495, 0.28475, 0.28495])
        total = pd.Series([0.000284, 0.000364, 0.000287, 0.000462])
        # Run.
        act = list(obccexqu.get_adjusted_close_price(close, open, total))
        exp = [
            2.1126760563379907,
            -0.5494505494504889,
            0.6968641114981812,
            0.21645021645031276,
        ]
        # Check.
        # We cannot use `self.assert_equal()` on `nan` because `nan != nan`.
        # So we check all values separately.
        self.assertListEqual(act, exp)
