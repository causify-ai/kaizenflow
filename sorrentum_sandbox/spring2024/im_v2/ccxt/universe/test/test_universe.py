import im_v2.common.universe.test.test_universe as imvcountt


class TestGetUniverseFilePath1(imvcountt.TestGetUniverseFilePath1_TestCase):
    def test_get_universe_file_path(self) -> None:
        """
        A smoke test to test correct file path return when correct version is
        provided.
        """
        self._test_get_universe_file_path("CCXT", "download", "v1")
        self._test_get_universe_file_path("CCXT", "download", "v3")

    def test_get_latest_file_version(self) -> None:
        """
        Verify that the max universe version is correctly detected and
        returned.
        """
        self._test_get_latest_file_version("CCXT", "download")


class TestGetUniverse1(imvcountt.TestGetUniverse1_TestCase):
    def test_get_universe1(self) -> None:
        """
        A smoke test to verify that universe loads correctly.
        """
        self._test_get_universe1("CCXT")

    def test_get_universe_invalid_version(self) -> None:
        """
        Verify that incorrect universe version is recognized.
        """
        self._test_get_universe_invalid_version("CCXT")

    def test_get_vendor_universe_small(self) -> None:
        """
        Test that vendor universe is loaded correctly as dict using small
        universe file.
        """
        self._test_get_vendor_universe_small("CCXT", "kucoin", "ETH_USDT")

    def test_get_vendor_universe_as_full_symbol(self) -> None:
        """
        Test that universe as full symbols is received correctly from small
        universal.
        """
        self._test_get_vendor_universe_as_full_symbol(
            "CCXT", ["binance::BTC_USDT", "gateio::XRP_USDT", "kucoin::ETH_USDT"]
        )


class TestGetUniverseVersions1(imvcountt.TestGetUniverseVersions1_TestCase):
    def test_get_universe_versions1(self) -> None:
        """
        Verify that trade universe versions are returned correctly.
        """
        vendor = "CCXT"
        mode = "trade"
        expected_universes_str = "['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v7.1', 'v7.2', 'v7.3', 'v7.4', 'v7.5', 'v8', 'v8.1', 'v8.2']"
        self._test_get_universe_versions(vendor, mode, expected_universes_str)

    def test_get_universe_versions2(self) -> None:
        """
        Verify that download universe versions are returned correctly.
        """
        vendor = "CCXT"
        mode = "download"
        expected_universes_str = "['v1', 'v2', 'v3', 'v4', 'v5', 'v7', 'v7.3', 'v7.4', 'v7.5', 'v7.6', 'v8', 'v8.1']"
        self._test_get_universe_versions(vendor, mode, expected_universes_str)
