"""
Import as:

import im_v2.kibot.metadata.client.kibot_metadata as imvkmckime
"""

import logging
import re
from typing import Any, List, Tuple

import pandas as pd

import helpers.hdbg as hdbg
import im_v2.kibot.metadata.client.s3_backend as imvkmcs3ba

_LOG = logging.getLogger(__name__)


# Top contracts by file size found using
#     `KibotMetadata().read_continuous_contract_metadata()`.
TOP_KIBOT = {
    "Corn": "C",
    "Crude Oil": "CL",
    "Rough Rice": "RR",
    "Soybeans": "S",
    "Wheat": "W",
    "Copper": "HG",
    "Soybean Meal": "SM",
    "Gold": "GC",
    "Silver": "SI",
    "Palm Oil": "KPO",
}


class KibotMetadata:
    # pylint: disable=line-too-long
    """
    Generate Kibot metadata.

    The metadata is computed from:
     - minutely contract metadata (`read_1min_contract_metadata()`)
     - tick-bid-ask metadata (`read_continuous_contract_metadata()`) is used to
       extract start date and exchange, which are not available in the minutely
       metadata.

    The expiration dates provided here are accurate for both daily and minutely
    metadata.

    The metadata is indexed by the symbol.

    The metadata contains the following columns:
    - `Description`
    - `StartDate`
    - `Exchange`
    - `num_contracts`
    - `min_contract`
    - `max_contract`
    - `num_expiries`
    - `expiries`

                                   Description  StartDate                                  Exchange  num_contracts min_contract max_contract  num_expiries                                expiries
    AD   CONTINUOUS AUSTRALIAN DOLLAR CONTRACT  9/27/2009  Chicago Mercantile Exchange (CME GLOBEX)           65.0      11.2009      11.2020          12.0  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    AEX          CONTINUOUS AEX INDEX CONTRACT        NaN                                       NaN          116.0      03.2010      02.2020          12.0  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    """
    # pylint: enable=line-too-long

    def __init__(self) -> None:
        self.minutely_metadata = self._compute_kibot_metadata("1min")
        self.tickbidask_metadata = self._compute_kibot_metadata("tick-bid-ask")

    def get_metadata(self, contract_type: str = "1min") -> pd.DataFrame:
        """
        Return the metadata.
        """
        if contract_type in ["1min", "daily"]:
            # Minutely and daily dataframes are identical except for the `Link`
            # column.
            metadata = self.minutely_metadata.copy()
        elif contract_type == "tick-bid-ask":
            metadata = self.tickbidask_metadata.copy()
        else:
            raise ValueError("Invalid `contract_type`='%s'" % contract_type)
        return metadata

    def get_futures(self, contract_type: str = "1min") -> List[str]:
        """
        Return the continuous contracts, e.g., ES, CL.
        """
        futures: List[str] = self.get_metadata(contract_type).index.tolist()
        return futures

    @classmethod
    # For now the metadata is always stored on S3, so we don't need to use `cls`.
    def get_expiry_contracts(cls, symbol: str) -> List[str]:
        """
        Return the expiry contracts corresponding to a continuous contract.
        """
        one_min_contract_metadata = cls.read_1min_contract_metadata()
        one_min_contract_metadata, _ = cls._extract_month_year_expiry(
            one_min_contract_metadata
        )
        # Select the rows with the Symbol equal to the requested one.
        mask = one_min_contract_metadata["SymbolBase"] == symbol
        df = one_min_contract_metadata[mask]
        contracts: List[str] = df.loc[:, "Symbol"].tolist()
        return contracts

    @classmethod
    def read_tickbidask_contract_metadata(cls) -> pd.DataFrame:
        return imvkmcs3ba.S3Backend().read_tickbidask_contract_metadata()

    @classmethod
    def read_kibot_exchange_mapping(cls) -> pd.DataFrame:
        return imvkmcs3ba.S3Backend().read_kibot_exchange_mapping()

    @classmethod
    def read_continuous_contract_metadata(cls) -> pd.DataFrame:
        return imvkmcs3ba.S3Backend().read_continuous_contract_metadata()

    @classmethod
    def read_1min_contract_metadata(cls) -> pd.DataFrame:
        return imvkmcs3ba.S3Backend().read_1min_contract_metadata()

    @classmethod
    def read_daily_contract_metadata(cls) -> pd.DataFrame:
        return imvkmcs3ba.S3Backend().read_daily_contract_metadata()

    def get_kibot_symbols(self, contract_type: str = "1min") -> pd.Series:
        metadata = self.get_metadata(contract_type)
        return metadata["Kibot_symbol"]

    _CONTRACT_EXPIRIES = {
        "F": 1,
        "G": 2,
        "H": 3,
        "J": 4,
        "K": 5,
        "M": 6,
        "N": 7,
        "Q": 8,
        "U": 9,
        "V": 10,
        "X": 11,
        "Z": 12,
    }

    @staticmethod
    def parse_expiry_contract(v: str) -> Tuple[str, str, int]:
        """
        Parse a futures contract name into its components, e.g., in a futures
        contract name like "ESH10":

        - base symbol is ES
        - month is H
        - year is 10 (i.e., 2010)
        """
        m = re.match(r"^(\S+)(\S)(\d{2})$", v)
        if m is None:
            hdbg.dassert(m, "Invalid '%s'", v)
            return "", "", 0
        base_symbol, month, year = m.groups()
        return base_symbol, month, year

    # //////////////////////////////////////////////////////////////////////////

    # TODO(Julia): Replace `one_min` with `expiry` once the PR is approved.
    @classmethod
    def _compute_kibot_metadata(cls, contract_type: str) -> pd.DataFrame:
        if contract_type in ["1min", "daily"]:
            # Minutely and daily dataframes are identical except for the `Link`
            # column.
            one_min_contract_metadata = cls.read_1min_contract_metadata()
        elif contract_type == "tick-bid-ask":
            one_min_contract_metadata = cls.read_tickbidask_contract_metadata()
        else:
            raise ValueError("Invalid `contract_type`='%s'" % contract_type)
        continuous_contract_metadata = cls.read_continuous_contract_metadata()
        # Extract month, year, expiries and SymbolBase from the Symbol col.
        (
            one_min_contract_metadata,
            one_min_symbols_metadata,
        ) = cls._extract_month_year_expiry(one_min_contract_metadata)
        # Calculate stats for expiries.
        expiry_counts = cls._calculate_expiry_counts(one_min_contract_metadata)
        # Drop unneeded columns from the symbol metadata dataframe
        # originating from 1 min contract metadata.
        one_min_contracts = one_min_symbols_metadata.copy()
        one_min_contracts.set_index("Symbol", inplace=True)
        one_min_contracts.drop(
            columns=["year", "Link"], inplace=True, errors="ignore"
        )
        # Choose needed columns from the continuous contract metadata.
        cont_contracts_chosen = continuous_contract_metadata.loc[
            :, ["Symbol", "StartDate", "Exchange"]
        ]
        cont_contracts_chosen = cont_contracts_chosen.set_index(
            "Symbol", drop=True
        )
        # Combine 1 min metadata, continuous contract metadata and stats for
        # expiry contracts.
        if contract_type == "tick-bid-ask":
            to_concat = [one_min_contracts, expiry_counts]
        else:
            to_concat = [one_min_contracts, cont_contracts_chosen, expiry_counts]
        kibot_metadata = pd.concat(
            to_concat,
            axis=1,
            join="outer",
            sort=True,
        )
        # Sort by index.
        kibot_metadata.sort_index(inplace=True)
        # Remove empty nans.
        kibot_metadata.dropna(how="all", inplace=True)
        # Convert date columns to datetime.
        kibot_metadata["min_contract"] = pd.to_datetime(
            kibot_metadata["min_contract"], format="%m.%Y"
        )
        kibot_metadata["max_contract"] = pd.to_datetime(
            kibot_metadata["max_contract"], format="%m.%Y"
        )
        # Data can be incomplete, when mocked in a testing environment.
        kibot_metadata = kibot_metadata[kibot_metadata["num_contracts"].notna()]
        # Convert integer columns to `int`.
        kibot_metadata["num_contracts"] = kibot_metadata["num_contracts"].astype(
            int
        )
        kibot_metadata["num_expiries"] = kibot_metadata["num_expiries"].astype(
            int
        )
        # Append Exchange_symbol, Exchange_group, Globex_symbol columns.
        kibot_metadata = cls._annotate_with_exchange_mapping(kibot_metadata)
        # Change index to continuous.
        kibot_metadata = kibot_metadata.reset_index()
        kibot_metadata = kibot_metadata.rename({"index": "Kibot_symbol"}, axis=1)
        columns = [
            "Kibot_symbol",
            "Description",
            "StartDate",
            "Exchange",
            "Exchange_group",
            "Exchange_abbreviation",
            "Exchange_symbol",
            "num_contracts",
            "min_contract",
            "max_contract",
            "num_expiries",
            "expiries",
        ]
        return kibot_metadata[columns]

    @classmethod
    def _get_zero_elememt(cls, list_: List[Any]) -> Any:
        return list_[0] if list_ else None

    @classmethod
    def _extract_month_year_expiry(
        cls,
        one_min_contract_metadata: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract month, year, expiries and SymbolBase from the Symbol.
        """
        # Extract year by extracting the trailing digits. Contracts that
        # do not have a year are continuous.
        one_min_contract_metadata = one_min_contract_metadata.copy()
        one_min_contract_metadata["year"] = (
            one_min_contract_metadata["Symbol"]
            .apply(lambda x: re.findall(r"\d+$", x))
            .apply(cls._get_zero_elememt)
        )
        one_min_symbols_metadata = one_min_contract_metadata.loc[
            one_min_contract_metadata["year"].isna()
        ]
        # Drop continuous contracts.
        one_min_contract_metadata.dropna(subset=["year"], inplace=True)
        # Extract SymbolBase, month, year and expiries from contract names.
        symbol_month_year = (
            one_min_contract_metadata["Symbol"]
            .apply(cls.parse_expiry_contract)
            .apply(pd.Series)
        )
        symbol_month_year.columns = ["SymbolBase", "month", "year"]
        symbol_month_year["expiries"] = (
            symbol_month_year["month"] + symbol_month_year["year"]
        )
        symbol_month_year.drop(columns="year", inplace=True)
        one_min_contract_metadata.drop(
            columns="SymbolBase", inplace=True, errors="ignore"
        )
        one_min_contract_metadata = pd.concat(
            [one_min_contract_metadata, symbol_month_year], axis=1
        )
        return one_min_contract_metadata, one_min_symbols_metadata

    @classmethod
    def _calculate_expiry_counts(
        cls,
        one_min_contract_metadata: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate the following stats for each symbol:

        - number of contracts
        - number of expiries
        - the oldest contract
        - the newest contract

        :return: pd.DataFrame with calculated counts
        """
        one_min_contracts_with_exp = one_min_contract_metadata.copy()
        # To sort the contracts easily, revert expiries so that the year
        # comes before month.
        one_min_contracts_with_exp[
            "expiries_year_first"
        ] = one_min_contracts_with_exp["expiries"].apply(lambda x: x[1:] + x[0])
        base_groupby = one_min_contracts_with_exp.groupby("SymbolBase")
        # Count the contracts.
        num_contracts = pd.Series(
            base_groupby["expiries"].nunique(), name="num_contracts"
        )
        # Get months at which the contract expires.
        num_expiries = pd.Series(
            base_groupby["month"].nunique(), name="num_expiries"
        )
        # Get the earliest contract, bring it to the mm.yyyy format.
        min_contract = pd.Series(
            base_groupby["expiries_year_first"].min(), name="min_contract"
        )
        min_contract = min_contract.apply(
            lambda x: str(cls._CONTRACT_EXPIRIES[x[-1]]).zfill(2) + ".20" + x[:2]
        )
        # Get the oldest contract, bring it to the mm.yyyy format.
        max_contract = pd.Series(
            base_groupby["expiries_year_first"].max(), name="max_contract"
        )
        max_contract = max_contract.apply(
            lambda x: str(cls._CONTRACT_EXPIRIES[x[-1]]).zfill(2) + ".20" + x[:2]
        )
        # Get all months at which contracts for each symbol expires,
        # change the str months to the month numbers from 0 to 11.
        expiries = pd.Series(base_groupby["month"].unique(), name="expiries")
        expiries = expiries.apply(
            lambda x: list(map(lambda y: cls._CONTRACT_EXPIRIES[y], x))
        )
        # Combine all counts.
        expiry_counts = pd.concat(
            [num_contracts, min_contract, max_contract, num_expiries, expiries],
            axis=1,
        )
        return expiry_counts

    @classmethod
    def _annotate_with_exchange_mapping(
        cls,
        kibot_metadata: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Annotate Kibot with exchanges and their symbols.

        The annotations include
         - "Exchange_group" for high-level exchanges' group
         - "Exchange_abbreviation" for exchange abbreviation
         - "Exchange_symbol" for contract designation in given exchange

        Annotations are provided only for commodity-related contracts.

        :param kibot_metadata: Kibot metadata dataframe
        kibot_to_cme_mapping = (
            imvkmcs3ba.S3Backend().read_kibot_exchange_mapping()
        )
        """
        kibot_to_cme_mapping = cls.read_kibot_exchange_mapping()
        # Add mapping columns to the dataframe.
        annotated_metadata = pd.concat(
            [kibot_metadata, kibot_to_cme_mapping], axis=1
        )
        return annotated_metadata