import os

import helpers.hunit_test as hunitest
import im.eoddata.metadata.load as load
import im.eoddata.metadata.types as imeometyp


class Test_read_symbols_from_file(hunitest.TestCase):
    def test1(self) -> None:
        """
        Confirm it reads the symbol, and the exchange code is added to the
        symbol code.
        """
        symbol_code = "AAMC"
        symbol_name = "Altisource Asset"
        input_f = self.get_input_dir() + "/test.csv"
        exchange_code, _ = os.path.basename(input_f).split(".")

        actual = load.MetadataLoader().read_symbols_from_file(file_=input_f)

        expected = [
            imeometyp.Symbol(
                Code=f"{exchange_code}:{symbol_code}",
                Name=symbol_name,
                LongName=symbol_name,
            )
        ]
        self.assertListEqual(actual, expected)
