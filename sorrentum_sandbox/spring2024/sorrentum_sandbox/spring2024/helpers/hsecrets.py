"""
Import as:

import helpers.hsecrets as hsecret
"""

import json
from typing import Any, Dict, Optional

from botocore.client import BaseClient
from botocore.exceptions import ClientError

import helpers.haws as haws
import helpers.hdbg as hdbg


def get_secrets_client(aws_profile: str) -> BaseClient:
    """
    Return client to work with AWS Secrets Manager in the specified region.
    """
    session = haws.get_session(aws_profile)
    client = session.client(service_name="secretsmanager")
    return client


# TODO(Juraj): add support to access secrets for different profiles, not important rn
def get_secret(secret_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch secret values(s) from AWS secrets manager.

    :return a dictionary of key-value pairs. E.g., `get_secret('binance')` returns
    ```
    {
        'apiKey': '<secret_value>',
        'secret': '<secret_value>'
    }
    ```
    """
    # TODO(Juraj): This assertion can't be applied universally.
    # Check if the secret name format is valid.
    # dassert_valid_secret(secret_name)
    hdbg.dassert_isinstance(secret_name, str)
    # Create a AWS Secrets Manager client.
    aws_profile = "ck"
    client = get_secrets_client(aws_profile)
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # for the full list of exceptions.
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret_string = get_secret_value_response["SecretString"]
        hdbg.dassert_isinstance(secret_string, str)
        secret_val = json.loads(secret_string)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            # Let user know the secret does not exist.
            raise ValueError("No such secret: %s" % secret_name) from e
        # If not yet implemented handler then just re-raise.
        raise e
    return secret_val


# TODO(Juraj): add support to store secrets in different regions, not important rn.
def store_secret(
    secret_name: str, secret_value: Dict[str, str], *, description: str = ""
) -> Optional[bool]:
    """
    Store secret values(s) into AWS secrets manager, specify secret as a dict
    of key-value pairs.

    :return: bool representing whether writing was successful or not
    """
    hdbg.dassert_isinstance(secret_name, str)
    # Create a AWS Secrets Manager client.
    aws_profile = "ck"
    client = get_secrets_client(aws_profile)
    # See
    # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_CreateSecret.html
    # for the full list of exceptions.
    try:
        create_secret_value_response = client.create_secret(
            Name=secret_name,
            Description=description,
            SecretString=json.dumps(secret_value),
        )
        # If no exception was thrown and we get back the name we passed in the
        # response then the secret was stored successfully.
        return_name = create_secret_value_response["Name"]
        hdbg.dassert_isinstance(return_name, str)
        res: bool = create_secret_value_response["Name"] == secret_name
        return res
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceExistsException":
            # Let user know the secret with this name already exists.
            raise ValueError(
                "Secret with this name already exists:", secret_name
            ) from e
        # If not yet implemented handler then just re-raise.
        raise e
    # If we did not return inside try block then something went wrong.
    return False


# TODO(Juraj): this might be deprecated since this is only fit for exchange API keys
def dassert_valid_secret(secret_id: str) -> None:
    """
    The valid format is `exchange_id.stage.account_type.num`.
    """
    values = secret_id.split(".")
    hdbg.dassert_eq(len(values), 4)
    hdbg.dassert_in(
        values[0],
        [
            "binance",
            "bitfinex",
            "coinbase",
            "coinbaseprime",
            "coinbasepro",
            "ftx",
            "gateio",
            "huobi",
            "kraken",
            "kucoin",
            "test",
        ],
    )
    hdbg.dassert_in(values[1], ["local", "preprod"])
    hdbg.dassert_in(values[2], ["trading", "sandbox"])
    hdbg.dassert_is(values[3].isnumeric(), True)
