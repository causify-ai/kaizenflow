import unittest.mock as umock

import pytest

import helpers.hunit_test as hunitest
import im_v2.common.data.extract.extractor as imvcdexex


class TestExtractor1(hunitest.TestCase):
    # Mock `Extractor`'s abstract functions.
    abstract_methods_patch = umock.patch.object(
        imvcdexex.Extractor, "__abstractmethods__", new=set()
    )
    ohlcv_patch = umock.patch.object(
        imvcdexex.Extractor,
        "_download_ohlcv",
        spec=imvcdexex.Extractor._download_ohlcv,
    )
    bid_ask_patch = umock.patch.object(
        imvcdexex.Extractor,
        "_download_bid_ask",
        spec=imvcdexex.Extractor._download_bid_ask,
    )
    trades_patch = umock.patch.object(
        imvcdexex.Extractor,
        "_download_trades",
        spec=imvcdexex.Extractor._download_trades,
    )

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        self.abstract_methods_patch.start()
        self.ohlcv_mock: umock.MagicMock = self.ohlcv_patch.start()
        self.bid_ask_mock: umock.MagicMock = self.bid_ask_patch.start()
        self.trades_mock: umock.MagicMock = self.trades_patch.start()

    def tear_down_test(self) -> None:
        self.abstract_methods_patch.stop()
        self.ohlcv_patch.stop()
        self.bid_ask_patch.stop()
        self.trades_patch.stop()

    def test_download_data1(self) -> None:
        """
        Verify if proper function is called depending on `data_type`.
        """
        mock_map = {
            "ohlcv": self.ohlcv_mock,
            "bid_ask": self.bid_ask_mock,
            "trades": self.trades_mock,
        }
        dummy_extractor = imvcdexex.Extractor()
        test_samples = [
            ("ohlcv", "dummy_id", "dummy_currency_pair", {"type": "ohlcv"}),
            ("bid_ask", "dummy_id", "dummy_currency_pair", {"type": "bid_ask"}),
            ("trades", "dummy_id", "dummy_currency_pair", {"type": "trades"}),
        ]
        for data_type, exchange_id, currency_pair, kwargs in test_samples:
            dummy_extractor.exchange_id = exchange_id
            dummy_extractor.currency_pair = currency_pair
            dummy_extractor.kwargs = kwargs
            # Run.
            dummy_extractor.download_data(
                data_type, exchange_id, currency_pair, **kwargs
            )
            # Check function calls.
            function_mock = mock_map[data_type]
            self.assertEqual(function_mock.call_count, 1)
            actual_args = tuple(function_mock.call_args)
            expected_args = (
                ("dummy_id", "dummy_currency_pair"),
                {"type": data_type},
            )
            self.assertEqual(actual_args, expected_args)

    def test_download_data_error1(self) -> None:
        """
        Verify that error is raised on unknown `data_type`.
        """
        dummy_extractor = imvcdexex.Extractor()
        with self.assertRaises(AssertionError) as fail:
            # Run.
            dummy_extractor.download_data("dummy_data_type", "", "")
        actual_error = str(fail.exception)
        expected_error = r"""
            Unknown data type dummy_data_type.
        """
        self.assert_equal(actual_error, expected_error, fuzzy_match=True)
