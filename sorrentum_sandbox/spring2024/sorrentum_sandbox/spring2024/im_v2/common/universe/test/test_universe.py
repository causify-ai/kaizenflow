"""
Import as:

import im_v2.common.universe.test_universe as imvcounte
"""

import os
from typing import List

import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hunit_test as hunitest
import im_v2.common.universe.full_symbol as imvcufusy
import im_v2.common.universe.universe as imvcounun

# #############################################################################
# TestGetUniverse
# #############################################################################


class TestGetUniverseGeneral1(hunitest.TestCase):
    def test_get_universe_invalid_vendor(self) -> None:
        """
        Verify that incorrect vendor name is recognized.
        """
        with self.assertRaises(AssertionError):
            _ = imvcounun._get_vendor_universe("unknown", "download")


class TestGetUniverseFilePath1_TestCase(hunitest.TestCase):
    def _test_get_universe_file_path(
        self, vendor: str, mode: str, version: str
    ) -> None:
        """
        A smoke test to test correct file path return when correct version is
        provided.

        :param vendor: vendor to apply test to, e.g. CCXT
        :param version: version to test (should be present for a given vendor)
         e.g. CCXT -> v1/v2/v3
        """
        # These should already exist in the filesystem.
        expected_part = "im_v2/{}/universe/{}/universe_{}.json"
        actual = imvcounun._get_universe_file_path(vendor, mode, version=version)
        expected = os.path.join(
            hgit.get_amp_abs_path(),
            expected_part.format(vendor.lower(), mode, version),
        )
        self.assertEqual(actual, expected)

    def _test_get_latest_file_version(self, vendor: str, mode: str) -> None:
        """
        Verify that the max universe version is correctly detected and
        returned.

        :param vendor: vendor to apply test to, e.g. CCXT
        """
        # Future proof this test when new versions are added.
        # Assuming we won't have more versions :).
        max_ver = 9999
        expected_part = "im_v2/{}/universe/{}/universe_v{}.json"
        mock_universe = os.path.join(
            hgit.get_amp_abs_path(),
            expected_part.format(vendor.lower(), mode, max_ver),
        )
        # Create tmp mock file as max version.
        with open(mock_universe, mode="w", encoding="utf-8") as _:
            pass
        actual = imvcounun._get_universe_file_path(vendor, mode)
        # Delete tmp file.
        hio.delete_file(mock_universe)
        self.assertEqual(actual, mock_universe)


# TODO(gp): -> Remove the prefix Test
class TestGetUniverse1_TestCase(hunitest.TestCase):
    def _test_get_universe1(self, vendor: str) -> None:
        """
        A smoke test to verify that universe loads correctly.

        :param vendor: vendor to apply test to, e.g. CCXT 
        """
        _ = imvcounun._get_vendor_universe(vendor, "trade")
        _ = imvcounun._get_vendor_universe(vendor, "trade", version="v1")

    def _test_get_universe_invalid_version(
        self, vendor: str, *, version: str = "unknown"
    ) -> None:
        """
        Verify that incorrect universe version is recognized.

        :param vendor: vendor to apply test to, e.g. CCXT 
        """
        with self.assertRaises(AssertionError):
            _ = imvcounun._get_vendor_universe(
                vendor, mode="download", version=version
            )

    def _test_get_vendor_universe_small(
        self, vendor: str, exchange: str, currency_pair: str
    ) -> None:
        """
        Test that vendor universe is loaded correctly as dict using small
        universe file.

        :param vendor: vendor to apply test to, e.g. CCXT 
        :param exchange: exchange to load currency pairs for
        :param currency_pair: currency pair in format: SYMBOL_SYMBOL
        """
        self._get_vendor_universe_small(vendor, exchange, currency_pair)

    def _get_vendor_universe_small(
        self, vendor: str, exchange: str, currency_pair: str
    ) -> None:
        """
        Helper function to test universe is loaded correctly as dict.
        """
        universe = imvcounun.get_vendor_universe(vendor, "trade", version="small")
        self.assertIn(exchange, universe)
        self.assertEqual([currency_pair], universe[exchange])

    def _test_get_vendor_universe_as_full_symbol(
        self, vendor: str, universe_as_full_symbols: List[imvcufusy.FullSymbol]
    ) -> None:
        """
        Test that universe as full symbols is received correctly from small
        universe.

        :param vendor: vendor to apply test to, e.g. CCXT 
        :param universe_as_full_symbols: list of currency pairs as
            full symbols in format exchange_id::SYMBOL_SYMBOL
        """
        actual = imvcounun.get_vendor_universe(
            vendor, "trade", version="small", as_full_symbol=True
        )
        self.assertEqual(len(universe_as_full_symbols), len(actual))
        self.assertEqual(actual[0], universe_as_full_symbols[0])
        self.assertEqual(actual[1], universe_as_full_symbols[1])


class TestGetUniverseVersions1_TestCase(hunitest.TestCase):
    def _test_get_universe_versions(
        self, vendor: str, mode: str, expected_universes_str: str
    ) -> None:
        """
        Verify that download universe versions for the specified vendor
        are correctly detected and returned.

        :param vendor: vendor to apply test to, e.g. CCXT 
        :param mode: download or trade universe
        :param expected_universes_str: string representation of the expected
            universe versions
        """
        actual_universes_str = str(
            imvcounun.get_universe_versions(vendor, mode)
        )
        self.assertEqual(actual_universes_str, expected_universes_str)
