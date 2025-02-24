"""
Import as:

import im.kibot.data.load.kibot_file_path_generator as imkdlkfpge
"""

# TODO(*): -> kibot_file_path_generator.py

import os
from typing import Optional, cast

import helpers.hdbg as hdbg
import im.common.data.load.file_path_generator as imcdlfpage
import im.common.data.types as imcodatyp
import im.kibot.data.config as imkidacon


class KibotFilePathGenerator(imcdlfpage.FilePathGenerator):
    FREQ_PATH_MAPPING = {
        imcodatyp.Frequency.Daily: "daily",
        imcodatyp.Frequency.Minutely: "1min",
        imcodatyp.Frequency.Tick: "tick",
    }

    CONTRACT_PATH_MAPPING = {
        imcodatyp.ContractType.Continuous: "continuous_",
        imcodatyp.ContractType.Expiry: "",
    }

    ASSET_TYPE_PREFIX = {
        imcodatyp.AssetClass.ETFs: "all_etfs_",
        imcodatyp.AssetClass.Stocks: "all_stocks_",
        imcodatyp.AssetClass.Forex: "all_forex_pairs_",
        imcodatyp.AssetClass.Futures: "all_futures",
        imcodatyp.AssetClass.SP500: "sp_500_",
    }

    @staticmethod
    def get_latest_symbols_file() -> str:
        """
        Get the latest available file with symbols.
        """
        raise NotImplementedError

    def generate_file_path(
        self,
        symbol: str,
        aws_profile,
        frequency: imcodatyp.Frequency,
        asset_class: imcodatyp.AssetClass = imcodatyp.AssetClass.Futures,
        contract_type: Optional[imcodatyp.ContractType] = None,
        exchange: Optional[str] = None,
        currency: Optional[str] = None,
        unadjusted: Optional[bool] = None,
        ext: imcodatyp.Extension = imcodatyp.Extension.Parquet,
    ) -> str:
        """
        Get the path to a specific Kibot dataset on S3.

        Parameters as in `read_data()`.

        :return: path to the file
        """
        freq_path = self.FREQ_PATH_MAPPING[frequency]
        asset_class_prefix = self.ASSET_TYPE_PREFIX[asset_class]
        modifier = self._generate_modifier(
            asset_class=asset_class,
            contract_type=contract_type,
            unadjusted=unadjusted,
        )
        dir_name = f"{asset_class_prefix}{modifier}{freq_path}"
        file_path = os.path.join(dir_name, symbol)
        if ext == imcodatyp.Extension.Parquet:
            # Parquet files are located in `pq/` subdirectory.
            file_path = os.path.join("pq", file_path)
            file_path += ".pq"
        elif ext == imcodatyp.Extension.CSV:
            file_path += ".csv.gz"
        # TODO(amr): should we allow pointing to a local file here?
        # or rename the method to `generate_s3_path`?
        s3_prefix = imkidacon.get_s3_prefix(aws_profile)
        file_path = os.path.join(s3_prefix, file_path)
        return file_path

    @staticmethod
    def _generate_unadjusted_modifier(unadjusted: bool) -> str:
        adjusted_modifier = "unadjusted_" if unadjusted else ""
        return adjusted_modifier

    def _generate_contract_path_modifier(
        self, contract_type: imcodatyp.ContractType
    ) -> str:
        contract_path = self.CONTRACT_PATH_MAPPING[contract_type]
        return f"_{contract_path}contracts_"

    def _generate_modifier(
        self,
        asset_class: imcodatyp.AssetClass,
        unadjusted: Optional[bool] = None,
        contract_type: Optional[imcodatyp.ContractType] = None,
    ) -> str:
        """
        Generate a modifier to the file path, based on some asset class
        options.

        :param asset_class: asset class
        :param unadjusted: required for asset classes of type: `stocks` & `etfs`
        :param contract_type: required for asset class of type: `futures`
        :return: a path modifier
        """
        modifier = ""
        if asset_class == imcodatyp.AssetClass.Futures:
            hdbg.dassert_is_not(
                contract_type,
                None,
                msg="`contract_type` is a required arg for asset class: 'futures'",
            )
            modifier = self._generate_contract_path_modifier(
                contract_type=contract_type
            )
        elif asset_class in [
            imcodatyp.AssetClass.Stocks,
            imcodatyp.AssetClass.ETFs,
            imcodatyp.AssetClass.SP500,
        ]:
            hdbg.dassert_is_not(
                unadjusted,
                None,
                msg="`unadjusted` is a required arg for asset "
                "classes: 'stocks' & 'etfs' & 'sp_500'",
            )
            modifier = self._generate_unadjusted_modifier(
                unadjusted=cast(bool, unadjusted)
            )
        return modifier
