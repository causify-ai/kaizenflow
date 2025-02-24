import logging
import os

import pandas as pd
import pytest

try:
    import ib_insync
except ModuleNotFoundError:
    print("Can't find ib_insync")

import helpers.hdbg as hdbg
import helpers.hunit_test as hunitest
import im.ib.data.extract.gateway.metadata as imidegame
import im.ib.data.extract.gateway.utils as imidegaut

_LOG = logging.getLogger(__name__)


@pytest.mark.skip(reason="See alphamatic/dev_tools#282")
class Test_ib_metadata1(hunitest.TestCase):
    @classmethod
    def setUpClass(cls):
        hdbg.shutup_chatty_modules()
        cls.ib = imidegaut.ib_connect(0, is_notebook=False)

    @classmethod
    def tearDownClass(cls):
        cls.ib.disconnect()

    def test1(self) -> None:
        """
        Create some metadata for NG.
        """
        file_name = os.path.join(self.get_scratch_space(), "metadata.csv")
        ibmeta = imidegame.IbMetadata(file_name)
        #
        symbol = "NG"
        contract = ib_insync.Future(symbol, includeExpired=True)
        ibmeta.update(self.ib, [contract])
        #
        df = ibmeta.load()
        #
        self._check_metadata_df(df)

    def test2(self) -> None:
        """
        Create some metadata and then update more.
        """
        file_name = os.path.join(self.get_scratch_space(), "metadata.csv")
        ibmeta = imidegame.IbMetadata(file_name)
        #
        symbol = "NG"
        contract = ib_insync.Future(symbol, includeExpired=True)
        ibmeta.update(self.ib, [contract])
        #
        symbol = "CL"
        contract = ib_insync.Future(symbol, includeExpired=True)
        ibmeta.update(self.ib, [contract], append=True)
        #
        df = ibmeta.load()
        self._check_metadata_df(df)

    def test3(self) -> None:
        """
        Test that append=False cleans up the file.
        """
        file_name = os.path.join(self.get_scratch_space(), "metadata.csv")
        ibmeta = imidegame.IbMetadata(file_name)
        #
        symbol = "NG"
        contract = ib_insync.Future(symbol, includeExpired=True)
        ibmeta.update(self.ib, [contract])
        #
        symbol = "CL"
        contract = ib_insync.Future(symbol, includeExpired=True)
        ibmeta.update(self.ib, [contract], append=False)
        #
        df = ibmeta.load()
        self._check_metadata_df(df)

    def _check_metadata_df(self, df: pd.DataFrame) -> None:
        """
        Filter contracts by expiration date to not update outcomes regularly.
        """
        filtered_df = df[
            (df["lastTradeDateOrContractMonth"] >= 20210101)
            & (df["lastTradeDateOrContractMonth"] < 20220101)
        ]
        filtered_df = filtered_df.reset_index(drop=True)
        self.check_string(filtered_df.to_csv())
