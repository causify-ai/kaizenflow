"""
Import as:

import im.kibot.metadata.load.s3_backend as imkmls3ba
"""

import logging
import os
from typing import List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import im.kibot.data.config as imkidacon
import im.kibot.metadata.config as imkimecon

_LOG = logging.getLogger("amp" + __name__)

# TODO(Amr): Extract the 2 distinct functions here
# TODO(Amr): Map the functions onto `KibotContractType`, so you provide a type,
# and get back a dataframe with its metadata
# TODO(gp): We're fetching this from S3 and not kibot, how do we pick up the updates?
# perhaps these should be move to `transform` stage and we should output pq files?
# TODO(Amr): highlight the relation to `metadata/types`
# TODO(Amr): perhaps these functions shou

# TODO(gp): Might make sense to cache the metadata too to avoid S3 access.

_AWS_PROFILE = "ck"

class S3Backend:
    def __init__(self, max_rows: Optional[int] = None):
        self._max_rows = max_rows

    @staticmethod
    def read_kibot_exchange_mapping() -> pd.DataFrame:
        file_name = os.path.join(imkimecon.S3_PREFIX, "kibot_to_exchange.csv")
        hs3.dassert_is_s3_path(file_name)
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        stream, kwargs = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
        kibot_to_cme_mapping = hpandas.read_csv_to_df(
            stream, index_col="Kibot_symbol", **kwargs
        )
        return kibot_to_cme_mapping

    @staticmethod
    def get_symbols_for_dataset(data_type: str) -> List[str]:
        """
        Get a list of symbols stored on S3 in a specific data type, e.g.
        All_Futures_Continuous_Contracts_1min.

        :param data_type: specific data type, e.g. All_Futures_Continuous_Contracts_1min
        :return: list of symbols
        """

        def _extract_filename_without_extension(file_path: str) -> str:
            """
            Return only basename of the path without the .csv.gz or .pq
            extensions.

            :param file_path: a full path of a file
            :return: file name without extension
            """
            filename = os.path.basename(file_path)
            filename = filename.replace(".csv.gz", "")
            return filename

        aws_csv_gz_dir = os.path.join(imkidacon.S3_PREFIX, data_type)
        # List all existing csv gz files on S3.
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        csv_gz_s3_file_paths = [
            filename
            for filename in s3fs.ls(aws_csv_gz_dir)
            if filename.endswith("csv.gz")
        ]
        # Get list of symbols to convert.
        symbols = list(
            map(_extract_filename_without_extension, csv_gz_s3_file_paths)
        )
        hdbg.dassert_no_duplicates(symbols)
        symbols = sorted(list(set(symbols)))
        return symbols

    def read_1min_contract_metadata(self) -> pd.DataFrame:
        # pylint: disable=line-too-long
        """
        Read minutely contract metadata.

        Contains a mapping from all 1-min prices for each contract to a download
        path (not interesting) and a description.

        Columns are:
        - Symbol
        - Link
        - Description

        Symbol    Link                                                Description
        JY        http://api.kibot.com/?action=download&link=151...   CONTINUOUS JAPANESE YEN CONTRACT
        JYF18     http://api.kibot.com/?action=download&link=vrv...   JAPANESE YEN JANUARY 2018
        """
        # pylint: enable=line-too-long
        file_name = os.path.join(
            imkimecon.S3_PREFIX, "All_Futures_Contracts_1min.csv.gz"
        )
        _LOG.debug("file_name=%s", file_name)
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        stream, kwargs = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
        df = hpandas.read_csv_to_df(
            stream,
            index_col=0,
            nrows=self._max_rows,
            encoding="utf-8",
            **kwargs,
        )
        df = df.iloc[:, 1:]
        _LOG.debug("df=\n%s", df.head(3))
        _LOG.debug("df.shape=%s", df.shape)
        return df

    def read_daily_contract_metadata(self) -> pd.DataFrame:
        # pylint: disable=line-too-long
        """
        Read daily contract metadata.

        Same mapping as `read_1min_contract_metadata()` but for daily prices.

        Columns are:
        - Symbol
        - Link
        - Description

        Symbol    Link                                                Description
        JY        http://api.kibot.com/?action=download&link=151...   CONTINUOUS JAPANESE YEN CONTRACT
        JYF18    http://api.kibot.com/?action=download&link=vrv...    JAPANESE YEN JANUARY 2018
        """
        # pylint: enable=line-too-long
        file_name = os.path.join(
            imkimecon.S3_PREFIX, "All_Futures_Contracts_daily.csv.gz"
        )
        hs3.dassert_is_s3_path(file_name)
        _LOG.debug("file_name=%s", file_name)
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        stream, kwargs = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
        df = hpandas.read_csv_to_df(
            stream, index_col=0, nrows=self._max_rows, **kwargs
        )
        df = df.iloc[:, 1:]
        _LOG.debug("df=\n%s", df.head(3))
        _LOG.debug("df.shape=%s", df.shape)
        return df

    def read_tickbidask_contract_metadata(self) -> pd.DataFrame:
        # pylint: disable=line-too-long
        """
        Read tick-bid-ask contract metadata.

        Mapping between symbols (both continuous and not), start date, description,
        and exchange for tickbidask.

        Columns:
        - SymbolBase
        - Symbol
        - StartDate
        - Size
        - Description
        - Exchange

        SymbolBase    Symbol    StartDate    Size(MB)    Description                           Exchange
        ES            ES        9/30/2009    50610.0     CONTINUOUS E-MINI S&P 500 CONTRACT    Chicago Mercantile Exchange Mini Sized Contrac...
        ES            ESH11     4/6/2010     891.0       E-MINI S&P 500 MARCH 2011             Chicago Mercantile Exchange Mini Sized Contrac...
        """
        # pylint: enable=line-too-long
        file_name = os.path.join(imkimecon.S3_PREFIX, "Futures_tickbidask.txt.gz")
        _LOG.debug("file_name=%s", file_name)
        hs3.dassert_is_s3_path(file_name)
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        stream, kwargs = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
        df = hpandas.read_csv_to_df(
            stream,
            index_col=0,
            skiprows=5,
            header=None,
            sep="\t",
            nrows=self._max_rows,
            **kwargs,
        )
        df.columns = (
            "SymbolBase Symbol StartDate Size(MB) Description Exchange".split()
        )
        df.dropna(inplace=True, how="all")
        # hdbg.dassert_eq(df_shape[0], df_shape_after_dropna[0])
        df.index = df.index.astype(int)
        df.index.name = None
        df["StartDate"] = pd.to_datetime(df["StartDate"])
        _LOG.debug("df=\n%s", df.head(3))
        _LOG.debug("df.shape=%s", df.shape)
        return df

    def read_continuous_contract_metadata(self) -> pd.DataFrame:
        # pylint: disable=line-too-long
        """
        Read tick-bid-ask metadata for continuous contracts.

        Returns a continuous contract subset of
        `read_tickbidask_contract_metadata()`.

        Columns:
        - SymbolBase
        - Symbol
        - StartDate
        - Size
        - Description
        - Exchange

        SymbolBase Symbol  StartDate  Size(MB)    Description                                  Exchange
        JY         JY      9/27/2009  183.0       CONTINUOUS JAPANESE YEN CONTRACT             Chicago Mercantile Exchange (CME GLOBEX)
        TY         TY      9/27/2009  180.0       CONTINUOUS 10 YR US TREASURY NOTE CONTRACT   Chicago Board Of Trade (CBOT GLOBEX)
        FV         FV      9/27/2009  171.0       CONTINUOUS 5 YR US TREASURY NOTE CONTRACT    Chicago Board Of Trade (CBOT GLOBEX)
        """
        # pylint: enable=line-too-long
        file_name = os.path.join(
            imkimecon.S3_PREFIX, "FuturesContinuous_intraday.txt.gz"
        )
        _LOG.debug("file_name=%s", file_name)
        hs3.dassert_is_s3_path(file_name)
        s3fs = hs3.get_s3fs(_AWS_PROFILE)
        stream, kwargs = hs3.get_local_or_s3_stream(file_name, s3fs=s3fs)
        df = hpandas.read_csv_to_df(
            stream,
            index_col=0,
            skiprows=5,
            header=None,
            sep="\t",
            nrows=self._max_rows,
            **kwargs,
        )
        df.columns = (
            "SymbolBase Symbol StartDate Size(MB) Description Exchange".split()
        )
        df_shape = df.shape
        df.dropna(inplace=True, how="all")
        df_shape_after_dropna = df.shape
        hdbg.dassert_eq(df_shape[0] - 1, df_shape_after_dropna[0])
        df.index = df.index.astype(int)
        df.index.name = None
        df["StartDate"] = pd.to_datetime(df["StartDate"])
        _LOG.debug("df=\n%s", df.head(3))
        _LOG.debug("df.shape=%s", df.shape)
        return df
