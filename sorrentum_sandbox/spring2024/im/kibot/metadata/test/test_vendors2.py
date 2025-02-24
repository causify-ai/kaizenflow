# import logging
# import os
#
# import pandas as pd
# import pytest
#
# import core.finance as cofinanc
# import helpers.hgit as hgit
# import helpers.hsystem as hsystem
# import helpers.hunit_test as hunitest
# import vendors.cme.reader as cmer
# import vendors.core.base_classes as etl_base
# import vendors.core.config as etl_cfg
# import vendors.csi.reader as csir
# import vendors.etfs.utils as etfut
# import vendors.first_rate.reader as frr  # type: ignore
# import im.kibot.utils as kut
# import vendors.pandas_datareader.utils as pdut  # type: ignore
#
## #############################################################################
## kibot/utils.py
## #############################################################################
#
#
# class Test_kibot_utils1(hunitest.TestCase):
#    @pytest.mark.slow
#    def test_read_data_pq1(self) -> None:
#        # TODO(gp): Use unit test cache.
#        ext = "pq"
#        nrows = 100
#        df = kut.read_data("T", "expiry", "ES", ext=ext, nrows=nrows)
#        _LOG.debug("df=%s", df.head())
#        #
#        df2 = kut.read_data(
#            "T", "expiry", "ES", ext=ext, nrows=nrows, cache_data=True
#        )
#        _LOG.debug("df2=%s", df2.head())
#        pd.testing.assert_frame_equal(df, df2)
#        #
#        df3 = kut.read_data(
#            "T", "expiry", "ES", ext=ext, nrows=nrows, cache_data=True
#        )
#        _LOG.debug("df3=%s", df3.head())
#        pd.testing.assert_frame_equal(df, df3)
#        #
#        self.check_string(hpandas.df_to_str(df, num_rows=None))
#
#    @pytest.mark.slow
#    def test_read_data_csv1(self) -> None:
#        # TODO(gp): Use unit test cache.
#        ext = "csv"
#        nrows = 100
#        df = kut.read_data("T", "expiry", "ES", ext=ext, nrows=nrows)
#        _LOG.debug("df=%s", df.head())
#        #
#        df2 = kut.read_data(
#            "T", "expiry", "ES", ext=ext, nrows=nrows, cache_data=True
#        )
#        _LOG.debug("df2=%s", df2.head())
#        pd.testing.assert_frame_equal(df, df2)
#        #
#        df3 = kut.read_data(
#            "T", "expiry", "ES", ext=ext, nrows=nrows, cache_data=True
#        )
#        _LOG.debug("df3=%s", df3.head())
#        pd.testing.assert_frame_equal(df, df3)
#        #
#        self.check_string(hpandas.df_to_str(df, num_rows=None))
#
#    @pytest.mark.skip(reason="PTask2117")
#    def test_read_metadata1(self) -> None:
#        df = kut.read_1min_contract_metadata()
#        self.check_string(hpandas.df_to_str(df, num_rows=None))
#
#    @pytest.mark.skip(reason="PTask2117")
#    def test_read_metadata2(self) -> None:
#        df = kut.read_daily_contract_metadata()
#        self.check_string(hpandas.df_to_str(df, num_rows=None))
#
#    def test_read_metadata3(self) -> None:
#        df = kut.read_tickbidask_contract_metadata()
#        self.check_string(hpandas.df_to_str(df, num_rows=None))
#
#    def test_read_metadata4(self) -> None:
#        df = kut.read_continuous_contract_metadata()
#        self.check_string(hpandas.df_to_str(df, num_rows=None))
#
#
## TODO(gp, Julia): Fix this.
## TODO(gp, Julia): Remove pylint disable after fix.
## pylint: disable=no-member
# @pytest.mark.skip(reason="# TODO(Julia): Enable this once #532 is fixed.")
# class Test_kibot_MonthExpiry1(hunitest.TestCase):
#    """
#    Test the logic comparing and processing expiry contracts, e.g., ESH19
#    """
#
#    def test_less1(self) -> None:
#        act = kut._less("U10", "V11")
#        self.assertEqual(act, "U10")
#
#    def test_less2(self) -> None:
#        act = kut._less("U10", "U11")
#        self.assertEqual(act, "U10")
#
#    def test_less3(self) -> None:
#        act = kut._less("V10", "U10")
#        self.assertEqual(act, "U10")
#
#
## pylint: enable=no-member
#
#
# class Test_kibot_utils_ExpiryContractMapper1(hunitest.TestCase):
#    """
#    Test parsing expiry contracts and sorting them.
#    """
#
#    def test_parse_expiry_contract_with_year1(self) -> None:
#        contract = "SFF19"
#        expected_result = ("SF", "F", "19")
#        actual_result = kut.ExpiryContractMapper.parse_expiry_contract(contract)
#        self.assertTupleEqual(actual_result, expected_result)
#
#    def test_parse_expiry_contract_with_year2(self) -> None:
#        contract = "SF19"
#        expected_result = ("S", "F", "19")
#        actual_result = kut.ExpiryContractMapper.parse_expiry_contract(contract)
#        self.assertTupleEqual(actual_result, expected_result)
#
#    def test_parse_expiry_contract_without_month(self) -> None:
#        contract = "S19"
#        with self.assertRaises(AssertionError):
#            kut.ExpiryContractMapper.parse_expiry_contract(contract)
#
#    def test_parse_expiry_contract_without_expiry(self) -> None:
#        contract = "S"
#        with self.assertRaises(AssertionError):
#            kut.ExpiryContractMapper.parse_expiry_contract(contract)
#
#    def test_parse_expiry_contract_without_year(self) -> None:
#        contract = "SF"
#        with self.assertRaises(AssertionError):
#            kut.ExpiryContractMapper.parse_expiry_contract(contract)
#
#    def test_sort_expiry_contract_year(self) -> None:
#        contracts = ["JYF19", "JYF09", "JYF10"]
#        expected_result = ["JYF09", "JYF10", "JYF19"]
#        actual_result = kut.ExpiryContractMapper.sort_expiry_contract(contracts)
#        self.assertListEqual(actual_result, expected_result)
#
#    def test_sort_expiry_contract_month(self) -> None:
#        contracts = ["JYF19", "JYK19", "JYH19"]
#        expected_result = ["JYF19", "JYH19", "JYK19"]
#        actual_result = kut.ExpiryContractMapper.sort_expiry_contract(contracts)
#        self.assertListEqual(actual_result, expected_result)
#
#    def test_sort_expiry_contract_month_year(self) -> None:
#        contracts = ["JYF19", "JYH15", "JYK10"]
#        expected_result = ["JYK10", "JYH15", "JYF19"]
#        actual_result = kut.ExpiryContractMapper.sort_expiry_contract(contracts)
#        self.assertListEqual(actual_result, expected_result)
#
#
# class Test_kibot_utils_KibotMetadata(hunitest.TestCase):
#    @pytest.mark.slow()
#    def test_get_metadata1(self) -> None:
#        kmd = kut.KibotMetadata()
#        df = kmd.get_metadata()
#        self.check_string(df.to_string())
#
#    @pytest.mark.slow()
#    def test_get_futures1(self) -> None:
#        kmd = kut.KibotMetadata()
#        futures = kmd.get_futures()
#        self.check_string(" ".join(map(str, futures)))
#
#    @pytest.mark.slow()
#    def test_get_metadata_tick1(self) -> None:
#        kmd = kut.KibotMetadata()
#        df = kmd.get_metadata("tick-bid-ask")
#        str_df = hpandas.df_to_str(df, num_rows=None)
#        self.check_string(str_df)
#
#    @pytest.mark.slow()
#    def test_get_futures_tick1(self) -> None:
#        kmd = kut.KibotMetadata()
#        futures = kmd.get_futures("tick-bid-ask")
#        self.check_string(" ".join(map(str, futures)))
#
#    def test_get_expiry_contract1(self) -> None:
#        expiries = kut.KibotMetadata.get_expiry_contracts("ES")
#        self.check_string(" ".join(expiries))
#
#
# class Test_kibot_utils_ContractSymbolMapping(hunitest.TestCase):
#    def test_get_contract1(self) -> None:
#        csm = kut.ContractSymbolMapping()
#        contract = csm.get_contract("CL")
#        self.assertEqual(contract, "NYMEX:CL")
#
#    def test_get_contract2(self) -> None:
#        csm = kut.ContractSymbolMapping()
#        contract = csm.get_contract("BZ")
#        self.assertEqual(contract, "NYMEX:BZT")
#
#    def test_get_kibot_symbol1(self) -> None:
#        csm = kut.ContractSymbolMapping()
#        symbol = csm.get_kibot_symbol("NYMEX:CL")
#        self.assertEqual(symbol, "CL")
#
#    def test_get_kibot_symbol2(self) -> None:
#        """
#        Test for `ICE:T` contract.
#
#        `ICE:T` is mapped to multiple symbols, we pick one in the code.
#        """
#        csm = kut.ContractSymbolMapping()
#        symbol = csm.get_kibot_symbol("ICE:T")
#        self.assertEqual(symbol, "CRD")
#
#    def test_get_kibot_symbol3(self) -> None:
#        """
#        Test for `CME:ZC` contract.
#
#        `CME:ZC` is mapped to multiple symbols.
#        """
#        csm = kut.ContractSymbolMapping()
#        symbols = csm.get_kibot_symbol("CBOT:ZC")
#        expected_result = ["COR", "CCM", "CA", "C"]
#        self.assertListEqual(sorted(symbols), sorted(expected_result))
#
#    def test_get_kibot_symbol4(self) -> None:
#        """
#        Test for `NYMEX:BZT` contract.
#
#        `NYMEX:BZT` is mapped to multiple symbols.
#        """
#        csm = kut.ContractSymbolMapping()
#        symbols = csm.get_kibot_symbol("NYMEX:BZT")
#        expected_result = ["B", "Z"]
#        self.assertListEqual(sorted(symbols), sorted(expected_result))
#
#
# class TestComputeRet0FromMultiplePrices1(hunitest.TestCase):
#    def test1(self) -> None:
#        # Read multiple futures.
#        symbols = tuple("CL NG RB BZ".split())
#        nrows = 100
#        min_price_dict_df = kut.read_data("D", "continuous", symbols, nrows=nrows)
#        # Calculate returns.
#        mode = "pct_change"
#        col_name = "close"
#        actual_result = cofinanc.compute_ret_0_from_multiple_prices(
#            min_price_dict_df, col_name, mode
#        )
#        self.check_string(actual_result.to_string())
#
#
## #############################################################################
## pandas_datareader/utils.py
## #############################################################################
#
#
# class Test_pandas_datareader_utils1(hunitest.TestCase):
#    def test_get_multiple_data1(self) -> None:
#        ydq = pdut.YahooDailyQuotes()
#        tickers = "SPY IVV".split()
#        df = ydq.get_multiple_data("Adj Close", tickers)
#        #
#        self.check_string(hpandas.get_df_signature(df))
