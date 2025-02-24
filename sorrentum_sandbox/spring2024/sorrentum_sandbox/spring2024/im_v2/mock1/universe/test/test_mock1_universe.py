import im_v2.common.universe.test.test_universe as imvcountt


class TestGetUniverseFilePath1(imvcountt.TestGetUniverseFilePath1_TestCase):
    def test_get_universe_file_path(self) -> None:
        """
        A smoke test to test correct file path return when correct version is
        provided.
        """
        self._test_get_universe_file_path("mock1", "trade", "small")

    def test_get_latest_file_version(self) -> None:
        """
        Verify that the max universe version is correctly detected and
        returned.
        """
        self._test_get_latest_file_version("mock1", "trade")


class TestGetUniverse1(imvcountt.TestGetUniverse1_TestCase):
    def test_get_universe1(self) -> None:
        """
        A smoke test to verify that example universe loads correctly.
        """
        self._test_get_universe1("mock1")

    def test_get_universe_invalid_version(self) -> None:
        """
        Verify that incorrect universe version is recognized.
        """
        self._test_get_universe_invalid_version("mock1")

    def test_get_vendor_universe_small(self) -> None:
        vendor = "mock1"
        self._test_get_vendor_universe_small(vendor, "binance", "ADA_USDT")

    def test_get_vendor_universe_as_full_symbol(self) -> None:
        vendor = "mock1"
        universe_as_full_symbols = [
            "binance::ADA_USDT",
            "gateio::XRP_USDT",
            "kucoin::ETH_USDT",
        ]
        self._test_get_vendor_universe_as_full_symbol(
            vendor, universe_as_full_symbols
        )


class TestGetUniverseVersions1(imvcountt.TestGetUniverseVersions1_TestCase):
    def test_get_universe_versions1(self) -> None:
        """
        Verify that universe versions are returned correctly.
        """
        vendor = "mock1"
        mode = "trade"
        expected_universes_str = "['v1']"
        self._test_get_universe_versions(vendor, mode, expected_universes_str)
