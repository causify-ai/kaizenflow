import helpers.hunit_test as hunitest
import oms.execution_analysis_configs as oexancon


class Test_build_broker_portfolio_reconciliation_configs(hunitest.TestCase):
    """
    Test that Broker Portfolio config is built correctly.
    """

    def test1(self) -> None:
        # Define params for config.
        system_log_dir = self.get_scratch_space()
        id_col = "asset_id"
        universe_version = "v7.4"
        price_column_name = "close"
        vendor = "CCXT"
        mode = "download"
        bar_duration = "5T"
        table_name = "ccxt_ohlcv_futures"
        actual = oexancon.build_broker_portfolio_reconciliation_configs(
            system_log_dir,
            id_col,
            universe_version,
            price_column_name,
            vendor,
            mode,
            bar_duration,
            table_name,
        )
        # Convert `Config` into a string.
        mode = "only_values"
        actual = actual[0].to_string(mode)
        #
        expected = r"""
        id_col: asset_id
        system_log_dir: $GIT_ROOT/oms/test/outcomes/Test_build_broker_portfolio_reconciliation_configs.test1/tmp.scratch
        market_data:
            vendor: CCXT
            mode: download
            universe_version: v7.4
            im_client_config:
                table_name: ccxt_ohlcv_futures
        price_column_name: close
        bar_duration: 5T
        share_asset_ids_with_no_fills: 0.3
        n_index_elements_to_ignore: 2
        target_positions_columns_to_compare: ['price', 'holdings_shares', 'holdings_notional', 'target_holdings_shares', 'target_holdings_notional', 'target_trades_shares', 'target_trades_notional']
        compare_dfs_kwargs:
            row_mode: inner
            column_mode: inner
            diff_mode: pct_change
            assert_diff_threshold: 0.001
            log_level: 20
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)
