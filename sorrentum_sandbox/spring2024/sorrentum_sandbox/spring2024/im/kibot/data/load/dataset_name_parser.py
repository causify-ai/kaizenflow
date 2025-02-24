"""
Import as:

import im.kibot.data.load.dataset_name_parser as imkdldnapa
"""

from typing import Dict, Tuple

import helpers.hdbg as hdbg
import im.common.data.types as imcodatyp
import im.kibot.data.load.kibot_file_path_generator as imkdlkfpge


class DatasetNameParser:
    """
    Convert a dataset name into enumerated types.

    E.g., all_futures_continuous_contracts_daily -> AssetClass.Futures
    ContractType.Continuous Frequency.Minutely
    """

    # TODO(*): Move out and make it private?
    FREQ_PATH_MAPPING: Dict[str, imcodatyp.Frequency] = {
        v: k
        for k, v in imkdlkfpge.KibotFilePathGenerator.FREQ_PATH_MAPPING.items()
    }

    CONTRACT_PATH_MAPPING = {
        v: k
        for k, v in imkdlkfpge.KibotFilePathGenerator.CONTRACT_PATH_MAPPING.items()
    }

    ASSET_TYPE_PREFIX = {
        v: k
        for k, v in imkdlkfpge.KibotFilePathGenerator.ASSET_TYPE_PREFIX.items()
    }

    def parse_dataset_name(
        self,
        dataset: str,
    ) -> Tuple[
        imcodatyp.AssetClass, imcodatyp.ContractType, imcodatyp.Frequency, bool
    ]:
        """
        Parse dataset name and return a tuple with types, describing the
        dataset.

        :param dataset: dataset name, e.g. all_futures_contracts_1min
        :return: tuple of (asset class, contract type, frequency, unadjusted)
        """
        asset_class = self._extract_asset_class(dataset)
        contract_type = self._extract_contract_type(dataset)
        frequency = self._extract_frequency(dataset)
        unadjusted = False
        return asset_class, contract_type, frequency, unadjusted

    def _extract_frequency(self, dataset: str) -> imcodatyp.Frequency:
        frequency = None
        for string, _frequency in self.FREQ_PATH_MAPPING.items():
            if dataset.endswith(string):
                hdbg.dassert_is(
                    frequency,
                    None,
                    "Detected multiple frequencies, e.g., %s, %s",
                    frequency,
                    _frequency,
                )
                frequency = _frequency
        if frequency is None:
            hdbg.dfatal(f"${dataset} does not contain frequency.")
        return frequency

    def _extract_asset_class(self, dataset: str) -> imcodatyp.AssetClass:
        asset_class = None
        for string, _asset_class in self.ASSET_TYPE_PREFIX.items():
            if dataset.startswith(string):
                hdbg.dassert_is(
                    asset_class,
                    None,
                    "Detected multiple asset classes, e.g., %s, %s",
                    asset_class,
                    _asset_class,
                )
                asset_class = _asset_class
        if asset_class is None:
            hdbg.dfatal(f"${dataset} does not contain asset class.")
        return asset_class

    def _extract_contract_type(self, dataset: str) -> imcodatyp.ContractType:
        contract_type = None
        for string, _contract_type in self.CONTRACT_PATH_MAPPING.items():
            if len(string) == 0:
                # Skip Expiry contract type, it is the default.
                continue
            if string in dataset:
                hdbg.dassert_is(
                    contract_type,
                    None,
                    "Detected multiple contract types, e.g., %s, %s",
                    contract_type,
                    _contract_type,
                )
                contract_type = _contract_type
        if contract_type is None:
            contract_type = imcodatyp.ContractType.Expiry
        return contract_type
