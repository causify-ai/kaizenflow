"""
Import as:

import oms.hsecrets.secret_identifier as oseseide
"""

import dataclasses

import helpers.hdbg as hdbg

# TODO(Juraj): possibly extend the behavior to fetch the secret values
#  themselves from AWS instead of acting as a pure dataclass.
@dataclasses.dataclass(frozen=True)
class SecretIdentifier:
    """
    Wrapper class to store categorized secret identifier.
    """

    # Identifier of the exchange (e.g., "binance").
    exchange_id: str
    # Stage where the secret is used
    # (e.g., "prod", "preprod", "local").
    stage: str
    # Account type, broker related: "sandbox", "trading").
    account_type: str
    # Integer identification (e.g. to differentiate multiple
    # binance accounts).
    id_: int

    def __post_init__(self) -> None:
        hdbg.dassert_in(self.stage, ["local", "preprod", "prod"])
        hdbg.dassert_in(self.account_type, ["sandbox", "trading"])

    def __str__(self) -> str:
        return (
            f"{self.exchange_id}.{self.stage}.{self.account_type}.{str(self.id_)}"
        )
