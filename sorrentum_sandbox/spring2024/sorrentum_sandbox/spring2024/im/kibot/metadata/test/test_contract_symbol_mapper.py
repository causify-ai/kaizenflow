from unittest.mock import patch

import pandas as pd

import helpers.hunit_test as hunitest
import im.kibot.metadata.load.contract_symbol_mapping as imkmlcsyma


class TestContractSymbolMapper(hunitest.TestCase):
    def test_get_contract1(self):
        """
        Valid input returns a valid output.
        """
        with self._mock_csm():
            cls = imkmlcsyma.ContractSymbolMapping()
            inp = "test_symbol"
            exp = "test_exch_abbreviation:test_exch_symbol"
            act = cls.get_contract(inp)
            self.assertEqual(exp, act)

    def test_get_contract2(self):
        """
        No input returns null.
        """
        with self._mock_csm():
            cls = imkmlcsyma.ContractSymbolMapping()
            inp = ""
            exp = None
            act = cls.get_contract(inp)
            self.assertEqual(exp, act)

    def test_get_contract3(self):
        """
        Invalid input returns null.
        """
        with self._mock_csm():
            cls = imkmlcsyma.ContractSymbolMapping()
            inp = "non-existent"
            exp = None
            act = cls.get_contract(inp)
            self.assertEqual(exp, act)

    def test_get_kibot_symbol1(self):
        """
        Valid input returns valid output.
        """
        with self._mock_csm():
            cls = imkmlcsyma.ContractSymbolMapping()
            inp = "test_exch_abbreviation:test_exch_symbol"
            exp = "test_symbol"
            act = cls.get_kibot_symbol(inp)
            self.assertEqual(exp, act)

    def test_get_kibot_symbol2(self):
        """
        No input raises an error.
        """
        with self._mock_csm():
            cls = imkmlcsyma.ContractSymbolMapping()
            inp = ""
            with self.assertRaises(AssertionError):
                cls.get_kibot_symbol(inp)

    def test_get_kibot_symbol3(self):
        """
        Incorrect input raises an error.
        """
        with self._mock_csm():
            cls = imkmlcsyma.ContractSymbolMapping()
            inp = "test2"
            with self.assertRaises(AssertionError):
                cls.get_kibot_symbol(inp)

    def test_get_kibot_symbol4(self):
        """
        Invalid input raises an error.
        """
        with self._mock_csm():
            cls = imkmlcsyma.ContractSymbolMapping()
            inp = "non-existent:non-existent"
            exp = None
            act = cls.get_kibot_symbol(inp)
            self.assertEqual(exp, act)

    @staticmethod
    def _mock_csm():
        def mock_test_contract_symbol_mapping_init(
            self: imkmlcsyma.ContractSymbolMapping,
        ):
            md = {
                "Kibot_symbol": ["test_symbol"],
                "Exchange_abbreviation": ["test_exch_abbreviation"],
                "Exchange_symbol": ["test_exch_symbol"],
            }
            self._metadata = pd.DataFrame.from_dict(md)

        return patch.object(
            imkmlcsyma.ContractSymbolMapping,
            "__init__",
            mock_test_contract_symbol_mapping_init,
        )
