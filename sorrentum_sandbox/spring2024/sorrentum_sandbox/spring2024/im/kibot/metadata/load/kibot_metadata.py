"""
Import as:

import im.kibot.metadata.load.kibot_metadata as imkmlkime
"""

import abc
import datetime
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pandas.tseries.offsets as ptoffs
from tqdm.autonotebook import tqdm

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import im.common.data.types as imcodatyp
import im.kibot.data.load.kibot_s3_data_loader as imkdlksdlo
import im.kibot.metadata.load.expiry_contract_mapper as imkmlecoma
import im.kibot.metadata.load.s3_backend as imkmls3ba
import im.kibot.metadata.types as imkimetyp

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
# Custom type.
_SymbolToContracts = Dict[str, pd.DataFrame]


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
            raise ValueError(f"Invalid `contract_type`='{contract_type}'")
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
        return imkmls3ba.S3Backend().read_tickbidask_contract_metadata()

    @classmethod
    def read_kibot_exchange_mapping(cls) -> pd.DataFrame:
        return imkmls3ba.S3Backend().read_kibot_exchange_mapping()

    @classmethod
    def read_continuous_contract_metadata(cls) -> pd.DataFrame:
        return imkmls3ba.S3Backend().read_continuous_contract_metadata()

    @classmethod
    def read_1min_contract_metadata(cls) -> pd.DataFrame:
        return imkmls3ba.S3Backend().read_1min_contract_metadata()

    @classmethod
    def read_daily_contract_metadata(cls) -> pd.DataFrame:
        return imkmls3ba.S3Backend().read_daily_contract_metadata()

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
            raise ValueError(f"Invalid `contract_type`='{contract_type}'")
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
            .apply(imkmlecoma.ExpiryContractMapper.parse_expiry_contract)
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
            imkmls3ba.S3Backend().read_kibot_exchange_mapping()
        )
        """
        kibot_to_cme_mapping = cls.read_kibot_exchange_mapping()
        # Add mapping columns to the dataframe.
        annotated_metadata = pd.concat(
            [kibot_metadata, kibot_to_cme_mapping], axis=1
        )
        return annotated_metadata


# #############################################################################


# TODO(*): Move this code into a different file.
# -> FuturesContractLifetimeComputer.
class ContractLifetimeComputer(abc.ABC):
    """
    Abstract class computing the lifetime of a futures contract.
    """

    @abc.abstractmethod
    def compute_lifetime(self, contract_name: str) -> imkimetyp.ContractLifetime:
        """
        Compute the lifetime of a contract, e.g. 'CLJ17'.

        :param contract_name: the contract for which to compute the lifetime.
        :return: the computed lifetime.
        """


# TODO(*): Not sure if we should use Kibot since it's already in the package.
class KibotTradingActivityContractLifetimeComputer(ContractLifetimeComputer):
    """
    Use the price data from Kibot to compute the lifetime.
    """

    def __init__(self, end_timedelta_days: int = 0):
        """
        :param end_timedelta_days: number of days before the trading activity
            termination to mark as the end
        """
        hdbg.dassert_lte(0, end_timedelta_days)
        self.end_timedelta_days = end_timedelta_days

    def compute_lifetime(self, contract_name: str) -> imkimetyp.ContractLifetime:
        df = imkdlksdlo.KibotS3DataLoader().read_data(
            "Kibot",
            contract_name,
            imcodatyp.AssetClass.Futures,
            imcodatyp.Frequency.Daily,
            imcodatyp.ContractType.Expiry,
        )
        start_date = pd.Timestamp(df.first_valid_index())
        end_date = pd.Timestamp(df.last_valid_index())
        end_date -= ptoffs.BDay(self.end_timedelta_days)
        return imkimetyp.ContractLifetime(start_date, end_date)


class KibotHardcodedContractLifetimeComputer(ContractLifetimeComputer):
    """
    Use rules from exchange to compute the lifetime of a contract.
    """

    def __init__(self, start_timedelta_days: int, end_timedelta_days: int):
        """
        :param start_timedelta_days: number of days before the official termination
            date from the exchange that the contract starts
        :param end_timedelta_days: number of days before the official termination
            date from the exchange that the contract ends
        """
        hdbg.dassert_lte(0, start_timedelta_days)
        self.start_timedelta_days = start_timedelta_days
        hdbg.dassert_lte(0, end_timedelta_days)
        hdbg.dassert_lt(end_timedelta_days, start_timedelta_days)
        self.end_timedelta_days = end_timedelta_days
        self.ecm = imkmlecoma.ExpiryContractMapper()

    def compute_lifetime(self, contract_name: str) -> imkimetyp.ContractLifetime:
        symbol, month, year = self.ecm.parse_expiry_contract(contract_name)
        year = self.ecm.parse_year(year)
        month = self.ecm.expiry_to_month_num(month)
        if symbol == "CL":
            # https://www.cmegroup.com/trading/energy/crude-oil/light-sweet-crude_contract_specifications.html
            # "Trading terminates at the close of business on the third business day
            # prior to the 25th calendar day of the month preceding the delivery month."
            date = datetime.date(year, month, 25)
            # Closes 1 month preceding the expiry month.
            date -= pd.DateOffset(months=1)
            # Closes 3 business days before the 25th.
            date -= ptoffs.BDay(3)
        elif symbol == "NG":
            # https://www.cmegroup.com/trading/energy/natural-gas/natural-gas_contract_specifications.html
            # "Trading terminates on the 3rd last business days of the month
            # prior to the contract month."
            date = datetime.date(year, month, 1)
            # Closes = month preceding the expiry month.
            date += pd.offsets.BMonthEnd(-1)
            # Closes on the "3rd last business days".
            date -= ptoffs.BDay(2)
        else:
            raise NotImplementedError(
                f"Contract lifetime for symbol=`{symbol}` not implemented"
            )

        return imkimetyp.ContractLifetime(
            pd.Timestamp(date - ptoffs.BDay(self.start_timedelta_days)),
            pd.Timestamp(date - ptoffs.BDay(self.end_timedelta_days)),
        )


class FuturesContractLifetimes:
    """
    Read or save a df storing the lifetime of the contracts for a subset of
    symbols.

    The data is organized in directories like:
        - root_dir_name/
            - ContractLifetimeComputer.name/
                - ES.csv
                - CL.csv

    symbol    contract    start_date    end_date
    0    ES    ESZ09    2008-11-20    2009-11-13
    1    ES    ESH10    2009-02-22    2010-02-15
    2    ES    ESM10    2009-05-20    2010-05-13
    """

    def __init__(
        self,
        root_dir_name: str,
        lifetime_computer: ContractLifetimeComputer,
    ) -> None:
        self.root_dir_name = root_dir_name
        self.lifetime_computer = lifetime_computer

    def save(self, symbols: List[str]) -> None:
        """
        Compute the lifetime for all contracts available for all symbols passed
        in.

        :param symbols: Kibot symbols from which to retrieve contracts
        """
        kb = KibotMetadata()
        hdbg.dassert_type_is(symbols, list)
        hio.create_dir(self.root_dir_name, incremental=True)
        #
        for symbol in tqdm(symbols, desc="Processing futures contract lifetimes"):
            # For each symbol, get all the expiries.
            contracts = kb.get_expiry_contracts(symbol)
            _LOG.debug("Found %s contracts for symbol %s", len(contracts), symbol)
            _LOG.debug("contracts=%s", contracts[0])
            lifetimes = [
                self.lifetime_computer.compute_lifetime(cn) for cn in contracts
            ]
            #
            df = []
            for contract, lifetime in zip(contracts, lifetimes):
                lifetime.start_date = pd.Timestamp(lifetime.start_date)
                lifetime.end_date = pd.Timestamp(lifetime.end_date)
                _LOG.debug(
                    "contract=%s -> [%s, %s]",
                    contract,
                    lifetime.start_date,
                    lifetime.end_date,
                )
                df.append(
                    [symbol, contract, lifetime.start_date, lifetime.end_date]
                )
            df = pd.DataFrame(
                df, columns=["symbol", "contract", "start_date", "end_date"]
            )
            df = df.sort_values(by=["end_date", "start_date"])
            df.reset_index(drop=True, inplace=True)
            # Save.
            file_name = os.path.join(self._get_dir_name(), symbol + ".csv")
            hio.create_enclosing_dir(file_name, incremental=True)
            # hdbg.dassert_file_exist(file_name)
            df.to_csv(file_name)

    def load(self, symbols: List[str]) -> _SymbolToContracts:
        symbol_to_contracts: _SymbolToContracts = {}
        for symbol in symbols:
            file_name = os.path.join(self._get_dir_name(), symbol + ".csv")
            hdbg.dassert_path_exists(file_name)
            if hs3.is_s3_path(file_name):
                s3fs = hs3.get_s3fs("ck")
                kwargs = {"s3fs": s3fs}
            else:
                kwargs = {}
            stream, kwargs = hs3.get_local_or_s3_stream(file_name, **kwargs)
            df = hpandas.read_csv_to_df(stream, index_col=0, **kwargs)
            hdbg.dassert_eq(
                df.columns.tolist(),
                ["symbol", "contract", "start_date", "end_date"],
            )
            for col_name in ["start_date", "end_date"]:
                df[col_name] = pd.to_datetime(df[col_name])
            symbol_to_contracts[symbol] = df
        return symbol_to_contracts

    def _get_dir_name(self) -> str:
        name = self.lifetime_computer.__class__.__name__
        return os.path.join(self.root_dir_name, name)


class FuturesContractExpiryMapper:
    """
    Map symbols to the n-th corresponding contract, based on a certain date.
    """

    def __init__(self, symbol_to_contracts: _SymbolToContracts) -> None:
        # hdbg.dassert_eq(contracts.columns.tolist(), ["symbol", ...])
        self.symbol_to_contracts = symbol_to_contracts

    def get_nth_contract(
        self, symbol: str, date: imkimetyp.DATE_TYPE, n: int
    ) -> Optional[str]:
        """
        Return n-front contract corresponding to a given date and `n` offset.

        :param date: date to use as reference
        :param n: relative month, e.g., 1 for front month, 2 for first back month,
            and so on
        :param symbol: Kibot symbol
        :return: contract in the form of an Expiry
            absolute month and year of contract for `symbol`, expressed using Futures month codes
            and last two digits of year, e.g., `("Z", "20")`
        """
        hdbg.dassert_lte(1, n)
        # Grab all contract lifetimes.
        hdbg.dassert_in(symbol, self.symbol_to_contracts.keys())
        contracts = self.symbol_to_contracts[symbol]
        _LOG.debug("contracts=\n%s", contracts)
        date = pd.Timestamp(date)
        # Find first index with a `start_date` before `date` and
        # an `end_date` after `date`.
        idx = contracts["end_date"].searchsorted(date, side="left")
        if date < contracts["start_date"][idx]:
            # Index does not exist.
            return None
        # Add the offset.
        idx = idx + n - 1
        if idx >= contracts.shape[0]:
            # Index does not exist.
            return None
        # Return the contract.
        ret: str = contracts["contract"][idx]
        return ret

    # TODO(*): Deprecate `get_nth_contract()`.
    def get_nth_contracts(
        self,
        symbol: str,
        start_date: imkimetyp.DATE_TYPE,
        end_date: imkimetyp.DATE_TYPE,
        freq: str,
        n: int,
    ) -> Optional[pd.Series]:
        """
        Return series of nth back contracts from `start_date` to `end_date`.

        :param symbol: contract symbol, e.g., "CL"
        :param start_date: first date/datetime for lookup, inclusive
        :param end_date: last date/datetime for lookup, inclusive
        :param freq: frequency of output series index
        :param n: relative month:
            - 1 for the front month
            - 2 for the first back month
            - etc.
        :return: series of n contract names
        """
        hdbg.dassert_lte(1, n)
        idx = pd.date_range(start=start_date, end=end_date, freq=freq)
        #
        hdbg.dassert_in(symbol, self.symbol_to_contracts.keys())
        contracts = self.symbol_to_contracts[symbol]
        _LOG.debug("contracts=\n%s", contracts)
        # Index contracts by end date.
        contract_end_dates = contracts[["contract", "end_date"]].set_index(
            "end_date"
        )
        hpandas.dassert_strictly_increasing_index(contract_end_dates)
        # Shift to index nth contracts by end date.
        nth_contract_end_dates = contract_end_dates.shift(-1 * (n - 1))
        # Realign the end date to nth contract mapping to `idx` and backfill
        # the contract name.
        # TODO(*): Check for boundary effects.
        nth_contracts = nth_contract_end_dates.reindex(
            idx, method="bfill"
        ).squeeze()
        nth_contracts.name = symbol + str(n)
        return nth_contracts

    def get_contracts(
        self,
        symbols: List[str],
        start_date: imkimetyp.DATE_TYPE,
        end_date: imkimetyp.DATE_TYPE,
        freq: str,
    ) -> Optional[pd.DataFrame]:
        """
        Return dataframe of multiple back contracts.

        :param symbols: list of contract symbols combined with relative month
            for back contract, e.g., ["CL1", "CL2"]
        :param start_date: first date/datetime for lookup, inclusive
        :param end_date: last date/datetime for lookup, inclusive
        :param freq: frequency of output series index
        :return: dataframe of contract names
        """
        contracts = []
        for symbol in symbols:
            contract_name = symbol[:2]
            n = int(symbol[2:])
            srs = self.get_nth_contracts(
                symbol=contract_name,
                start_date=start_date,
                end_date=end_date,
                freq=freq,
                n=n,
            )
            contracts.append(srs)
        df = pd.concat(contracts, axis=1)
        return df
