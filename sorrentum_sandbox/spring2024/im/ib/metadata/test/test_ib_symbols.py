import os

import pytest

import helpers.hunit_test as hunitest
import im.common.data.types as imcodatyp
import im.common.metadata.symbols as imcomesym
import im.ib.data.config as imibdacon
import im.ib.data.load.ib_file_path_generator as imidlifpge
import im.ib.metadata.ib_symbols as imimeibsy


class TestIbSymbolUniverse(hunitest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Disable the chatty modules when debugging with DEBUG verbosity. We need to
        # disable the modules after they have been imported.
        # import helpers.hdbg as hdbg
        # hdbg.shutup_chatty_modules(verbose=True)
        hunitest.TestCase.setUpClass()

    def test_parse_symbols_file1(self) -> None:
        """
        Test parsing a file checked in the repo.
        """
        symbols_file = os.path.join(self.get_input_dir(), "test_symbols.csv")
        symbols = imimeibsy.IbSymbolUniverse._parse_symbols_file(symbols_file)
        # Build string to check.
        symbols_str = "\n".join([str(symbol) for symbol in symbols])
        self.check_string(symbols_str)

    @pytest.mark.superslow("Parse real large file with symbols. Approx. > 30 sec via GH actions.")
    def test_parse_symbols_file2(self) -> None:
        """
        Test parsing the real file.
        """
        symbols_file = os.path.join(
            imibdacon.S3_PREFIX, "metadata/symbols-2021-04-01-134738089177.csv"
        )
        symbols = imimeibsy.IbSymbolUniverse._parse_symbols_file(symbols_file)
        # Construct string to check.
        symbols_str = "Total parsed symbols: %i\n" % len(symbols)
        # Add first 5 symbols.
        symbols_str += "\n".join([str(symbol) for symbol in symbols[:5]])
        # Add last 5 symbols.
        symbols_str += "\n"
        symbols_str += "\n".join([str(symbol) for symbol in symbols[-5:]])
        self.check_string(symbols_str)

    def test_convert_df_to_row_to_symbol1(self) -> None:
        """
        Test supported stocks symbol converting.
        """
        act = imimeibsy.IbSymbolUniverse._convert_df_to_row_to_symbol(
            ib_ticker="AA",
            ib_exchange="New York (NYSE)",
            ib_asset_class="Stocks",
            ib_currency="USD",
        )
        exp = imcomesym.Symbol(
            ticker="AA",
            exchange="NYSE",
            asset_class=imcodatyp.AssetClass.Stocks,
            contract_type=None,
            currency="USD",
        )
        self.assertEqual(act, exp)

    def test_convert_df_to_row_to_symbol2(self) -> None:
        """
        Test supported futures symbol converting.
        """
        converted_symbol = (
            imimeibsy.IbSymbolUniverse._convert_df_to_row_to_symbol(
                ib_ticker="ZC",
                ib_exchange="CME part (ECBOT)",
                ib_asset_class="Futures",
                ib_currency="USD",
            )
        )
        expected_symbol = imcomesym.Symbol(
            ticker="ZC",
            exchange="ECBOT",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
        )
        self.assertEqual(converted_symbol, expected_symbol)

    def test_convert_df_to_row_to_symbol3(self) -> None:
        """
        Test symbol with unsupported exchange.
        """
        converted_symbol = (
            imimeibsy.IbSymbolUniverse._convert_df_to_row_to_symbol(
                ib_ticker="AA",
                ib_exchange="No brackets exchange",
                ib_asset_class="Stocks",
                ib_currency="USD",
            )
        )
        self.assertIsNone(converted_symbol)

    def test_convert_df_to_row_to_symbol4(self) -> None:
        """
        Test symbol with unsupported asset class.
        """
        converted_symbol = (
            imimeibsy.IbSymbolUniverse._convert_df_to_row_to_symbol(
                ib_ticker="AA",
                ib_exchange="New York (NYSE)",
                ib_asset_class="Warrants",
                ib_currency="USD",
            )
        )
        self.assertIsNone(converted_symbol)

    def test_extract_exchange_code_from_full_name1(self) -> None:
        """
        Test uppercase name extraction from single brackets.
        """
        extracted_exchange = (
            imimeibsy.IbSymbolUniverse._extract_exchange_code_from_full_name(
                "What a great (NAME)"
            )
        )
        self.assert_equal(extracted_exchange, "NAME")

    def test_extract_exchange_code_from_full_name2(self) -> None:
        """
        Test uppercase name extraction from no brackets string.
        """
        extracted_exchange = (
            imimeibsy.IbSymbolUniverse._extract_exchange_code_from_full_name(
                "NAME"
            )
        )
        self.assert_equal(extracted_exchange, "NAME")

    def test_extract_exchange_code_from_full_name3(self) -> None:
        """
        Test non-uppercase name extraction from single brackets.
        """
        extracted_exchange = (
            imimeibsy.IbSymbolUniverse._extract_exchange_code_from_full_name(
                "What a great (Name)"
            )
        )
        self.assertIsNone(extracted_exchange)

    def test_extract_exchange_code_from_full_name4(self) -> None:
        """
        Test non-uppercase name extraction from no brackets string.
        """
        extracted_exchange = (
            imimeibsy.IbSymbolUniverse._extract_exchange_code_from_full_name(
                "Name"
            )
        )
        self.assertIsNone(extracted_exchange)

    def test_extract_exchange_code_from_full_name5(self) -> None:
        """
        Test latest uppercase name extraction from two pairs of brackets
        string.
        """
        extracted_exchange = (
            imimeibsy.IbSymbolUniverse._extract_exchange_code_from_full_name(
                "One (NAME) two (NAMES)"
            )
        )
        self.assert_equal(extracted_exchange, "NAMES")

    # The 1st test parses the large file, which is used by the tests
    # `test_get_2`, `test_get_3`, `test_get_4`. They run < 5 seconds,
    # but they depend on the `test_get_1`, so they should be in one
    # test category, i.e. `slow` tests.
    @pytest.mark.superslow("~30 seconds.")
    def test_get_1(self) -> None:
        """
        Test that ES symbol is returned by request.
        """
        # Parse real large file with symbols.
        file_name = imidlifpge.IbFilePathGenerator.get_latest_symbols_file()
        ib_universe = imimeibsy.IbSymbolUniverse(file_name)
        matched = ib_universe.get(
            ticker="ES",
            exchange="GLOBEX",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
        )
        # TODO(gp): Use the actual outcome.
        self.assertEqual(len(matched), 1)

    @pytest.mark.superslow("depends on `test_get_1`.")
    def test_get_2(self) -> None:
        """
        Test that NON_EXISTING symbol is returned by request.
        """
        # Parse real large file with symbols.
        file_name = imidlifpge.IbFilePathGenerator.get_latest_symbols_file()
        ib_universe = imimeibsy.IbSymbolUniverse(file_name)
        matched = ib_universe.get(
            ticker="NON_EXISTING",
            exchange="GLOBEX",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
        )
        self.assertEqual(matched, [])

    @pytest.mark.superslow("depends on `test_get_1`.")
    def test_get_3(self) -> None:
        """
        Test that NG symbol is in downloaded list.
        """
        # Parse real large file with symbols.
        file_name = imidlifpge.IbFilePathGenerator.get_latest_symbols_file()
        ib_universe = imimeibsy.IbSymbolUniverse(file_name)
        matched = ib_universe.get(
            ticker="NG",
            exchange="NYMEX",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
            is_downloaded=True,
            frequency=imcodatyp.Frequency.Minutely,
            path_generator=imidlifpge.IbFilePathGenerator(),
        )
        # TODO(gp): Use the actual outcome.
        self.assertEqual(len(matched), 1)

    @pytest.mark.superslow("depends on `test_get_1`.")
    def test_get_4(self) -> None:
        """
        Test that NON_EXISTING symbol is not in the downloaded list.
        """
        # Parse real large file with symbols.
        file_name = imidlifpge.IbFilePathGenerator.get_latest_symbols_file()
        ib_universe = imimeibsy.IbSymbolUniverse(file_name)
        matched = ib_universe.get(
            ticker="NON_EXISTING",
            exchange="GLOBEX",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Continuous,
            currency="USD",
            is_downloaded=True,
            frequency=imcodatyp.Frequency.Minutely,
            path_generator=imidlifpge.IbFilePathGenerator(),
        )
        self.assertEqual(matched, [])
