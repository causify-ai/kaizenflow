"""
Import as:

import data_schema.dataset_schema_utils as dsdascut
"""

# TODO(Juraj): At high level this module essentially performs the same thing as
#  im_v2/common/universe/universe.py -> try to extract the common logic
#  according to DRY principle.

import copy
import logging
import os
from typing import Any, Dict, Optional

import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hstring as hstring
import im_v2.common.universe.universe as imvcounun

_LOG = logging.getLogger(__name__)


# #############################################################################
# Retrieve schema.
# #############################################################################


def _get_dataset_schema_file_path(*, version: Optional[str] = None) -> str:
    """
    Get file path of the dataset schema based on the version.

    :param version: dataset schema version (e.g. "v01"). If None it uses
        the latest version available
    :return: file path to the dataset schema file corresponding to the
        specified version
    """
    # TODO(Juraj): Implement dynamic version resolving and remove hardcoded logic.
    if version is not None:
        raise ValueError("Dynamic custom version not supported.")
    ds_file_path = os.path.join(
        hgit.get_amp_abs_path(),
        "data_schema/dataset_schema_versions/dataset_schema_v3.json",
    )
    hdbg.dassert_path_exists(ds_file_path)
    _LOG.info(f"Loading dataset schema file: {ds_file_path}")
    return ds_file_path


def get_dataset_schema(*, version: Optional[str] = None) -> Dict[str, Any]:
    """
    Get dataset schema for a specified version, if version is `None` fetch the
    latest version of the schema.

    :param version: dataset schema version (e.g. "v01") to load. If
        None, the latest version is loaded.
    :return: dataset schema as a nested dictionary, e.g. ``` {
        "dataset_signature":
        "download_mode.downloading_entity.action_tag",
        "token_separator_character": ".", "allowed_values": {
        "download_mode": ["bulk", "periodic_daily"],
        "downloading_entity": ["airflow", "manual"], "action_tag":
        ["downloaded_1sec", "resampled_1min"] } "version": "v3" } ```
    """
    # Load dataset schema as JSON.
    ds_file_path = _get_dataset_schema_file_path()
    dataset_schema = hio.from_json(ds_file_path)
    # Resolve version name.
    ds_version = hstring.extract_version_from_file_name(ds_file_path)
    # Transform version to string and remove trailing zero.
    ds_version = "v" + ".".join(map(str, ds_version)).rstrip(".0")
    # Append version from the file name to the schema dictionary.
    _LOG.info(f"Loaded dataset schema version {ds_version}")
    dataset_schema["version"] = ds_version
    # TODO(Juraj): assert that the schema file itself is well-formed.
    return dataset_schema


# #############################################################################
# Validate schema.
# #############################################################################


def _validate_dataset_signature_syntax(
    signature: str, dataset_schema: Dict[str, Any]
) -> bool:
    """
    Validate syntax of a dataset signature based on provided schema.

    For example refer to docstring of
    data_schema/validate_dataset_signature.py

    :param signature: dataset signature to validate
    :param dataset_schema: dataset schema to validate against
    :return: True if the signature is syntactically well-formed, False
        otherwise
    """
    token_separator_char = dataset_schema["token_separator_character"]
    signature_list = signature.split(token_separator_char)
    schema_signature_list = dataset_schema["dataset_signature"].split(
        token_separator_char
    )
    is_syntax_correct = len(signature_list) == len(schema_signature_list)
    if not is_syntax_correct:
        _LOG.warning(
            f"Signature is malformed. Expected number of tokens"
            + f" is: {len(signature_list)}, actual number of tokens is: {len(schema_signature_list)}"
        )
    return is_syntax_correct


def _validate_dataset_signature_semantics(
    signature: str, dataset_schema: Dict[str, Any]
) -> bool:
    """
    Validate semantics of a dataset signature based on provided schema.

    For example refer to docstring of
    data_schema/validate_dataset_signature.py

    :param signature: dataset signature to validate
    :param dataset_schema: dataset schema to validate against
    :return: True if the signature is semantically correct, False
        otherwise
    """
    # TODO(Juraj): syntax checks starts the same, avoid duplication
    #  according to DRY.
    token_separator_char = dataset_schema["token_separator_character"]
    signature_list = signature.split(token_separator_char)
    schema_signature_list = dataset_schema["dataset_signature"].split(
        token_separator_char
    )
    allowed_values_dict = dataset_schema["allowed_values"]
    # Assumes the syntax check has been performed.
    warning_messages = []
    # Prepare a dict with tokens and their values.
    tokens_values = dict(zip(schema_signature_list, signature_list))
    # Check if the version is supported for the given vendor.
    if "vendor" in tokens_values and "universe" in tokens_values:
        try:
            # TODO(Juraj): #CmTask7605 support checking both download and trade universe.
            mode = "download"
            vendor = tokens_values["vendor"]
            # Convert universe version to the format used in the vendor.
            version = tokens_values["universe"].replace("_", ".")
            imvcounun.get_vendor_universe(vendor, mode, version=version)
        except AssertionError:
            warning_messages.append(
                f"Universe version {version} is not supported for vendor {vendor}"
            )
    # Remove universe from the tokens_values dict in order to
    # avoid checking it in the next step.
    tokens_values.pop("universe", None)
    for token, value in tokens_values.items():
        if value not in allowed_values_dict[token]:
            warning_messages.append(
                f"Identifier {token} contains invalid value: {value}, "
                + f"allowed_values: {allowed_values_dict[token]}"
            )
    if warning_messages:
        _LOG.warning("\n".join(warning_messages))
    return warning_messages == []


def validate_dataset_signature(
    signature: str, dataset_schema: Dict[str, Any]
) -> bool:
    """
    Validate syntax and semantics of a dataset signature based on provided
    schema.

    For example refer to the docstring of
    `data_schema/validate_dataset_signature.py`

    :param signature: dataset signature to validate
    :param dataset_schema: dataset schema to validate against
    :return: True if the signature is syntactically AND semantically
        correct, False otherwise
    """
    # TODO(Juraj): Ideally this function should encapsulate a final state
    # machine-like validator but for now this more primitive check is good
    # enough.
    # Check syntax of the signature.
    # Currently the smenatic check implicitly decides the syntactic check as
    # well, but later down the line the syntax/semantics distinction might make
    # sense.
    is_correct_signature = _validate_dataset_signature_syntax(
        signature, dataset_schema
    )
    # If syntax is correct, check the semantics.
    # TODO(Juraj): Add strictness parameter `assert_mode`
    if is_correct_signature:
        is_correct_signature = _validate_dataset_signature_semantics(
            signature, dataset_schema
        )
    else:
        _LOG.warning("Syntax validation failed, skipping semantic validation.")
    return is_correct_signature


# #############################################################################
#
# #############################################################################


def _build_dataset_signature_from_args(
    args: Dict[str, Any], dataset_schema: Dict[str, Any]
) -> str:
    """
    Build a dataset signature from provided arguments.

    :param args: arguments to build the dataset signature from
    :param dataset_schema: dataset schema to build signature from.
    :return:
    """
    token_separator_char = dataset_schema["token_separator_character"]
    schema_signature_list = dataset_schema["dataset_signature"].split(
        token_separator_char
    )
    # Replace schema signature identifiers with the actual values if an
    # argument is missing and exception is raised.
    try:
        dataset_signature = list(map(lambda x: args[x], schema_signature_list))
    except KeyError as e:
        raise KeyError(
            "Missing required identifier for schema version"
            + f" {dataset_schema['version']}: {str(e)}"
        )
    return token_separator_char.join(dataset_signature)


def parse_dataset_signature_to_args(
    signature: str, dataset_schema: Dict[str, Any]
) -> Dict[str, str]:
    """
    Parse signature string into key-value mapping according to the data schema.

    :param signature: dataset signature to parse,
        e.g. `bulk.airflow.resampled_1min.parquet.bid_ask.spot.v3.crypto_chassis.binance.v1_0_0`
    :param dataset_schema: dataset schema to parse against
    :return: signature arguments mapping, e.g.
        ```
        {
            "download_mode": "bulk",
            "downloading_entity": "airflow",
            "action_tag": "resampled_1min",
            "data_format": "parquet",
            "data_type": "bid_ask",
            "asset_type": "spot",
            "universe": "v3",
            "vendor": "crypto_chassis",
            "exchange_id": "binance",
            "version": "v1_0_0"
        }
        ```
    """
    hdbg.dassert_eq(validate_dataset_signature(signature, dataset_schema), True)
    token_separator = dataset_schema["token_separator_character"]
    keys = dataset_schema["dataset_signature"].split(token_separator)
    values = signature.split(token_separator)
    args = {keys[i]: values[i] for i in range(len(keys))}
    return args


# #############################################################################
# S3 file interface.
# #############################################################################


def get_vendor_from_s3_path(s3_path: str) -> str:
    """
    Extract vendor from S3 path.

    :param s3_path: S3 path to extract vendor from
    :return: vendor name
    """
    tokens = s3_path.replace("/", ".").split(".")
    vendors_from_schema = get_dataset_schema()["allowed_values"]["vendor"]
    for token in tokens:
        if token in vendors_from_schema:
            return token
    raise ValueError(f"Vendor not found in S3 path: {s3_path}")


def build_s3_dataset_path_from_args(
    s3_base_path: str, args: Dict[str, Any], *, version=None
) -> str:
    """
    Build an S3 path given a bucket and a dict of arguments based on dataset
    schema of the given version.

    If the provided arguments form an invalid signature an exception is
    raised.

    :param s3_base_path: Base S3 path to use, i.e.
    's3://cryptokaizen-data'
     :param s3_base_path: Base S3 path to use, i.e.
    's3://cryptokaizen-data'
    :param s3_base_path: Base S3 path to use, i.e. 's3://cryptokaizen-
        data'
    :param s3_base_path: Base S3 path to use, i.e. 's3://cryptokaizen-
        data'
    :param args: arguments to build the dataset signature from
    :param version: version of the dataset schema to use, if None,
        latest version
    """
    _args = copy.deepcopy(args)
    s3_path = s3_base_path
    schema = get_dataset_schema(version=version)
    s3_path = os.path.join(s3_path, schema["version"])
    # TODO(Juraj): If preprocessing operations pile up, divide them into
    # separate functions.
    if _args.get("universe"):
        _args["universe"] = _args["universe"].replace(".", "_")
    dataset_signature = _build_dataset_signature_from_args(_args, schema)
    if not validate_dataset_signature(dataset_signature, schema):
        raise ValueError(
            f"Invalid argument values for schema version: {schema['version']}"
        )
    dataset_signature = dataset_signature.replace(
        schema["token_separator_character"], "/"
    )
    s3_path = os.path.join(s3_path, dataset_signature)
    return s3_path


# #############################################################################
# IM interface.
# #############################################################################


def get_im_db_table_name_from_signature(
    signature: str, dataset_schema: Dict[str, Any]
) -> str:
    """
    Get database table name from provided signature for datasets with data
    format "postgres".

    Based on historical naming conventions for DB tables the table name is not directly
    inferrable from the signature, this function provides a mapping from signatures to DB table names.

    :param signature: dataset signature to parse,
        e.g. `realtime.airflow.downloaded_1min.postgres.ohlcv.futures.v7.ccxt.binance.v1_0_0`
    :param dataset_schema: dataset schema to parse against
    :return: DB table name corresponding to the signature, e.g.
        input signature: `realtime.airflow.downloaded_1min.postgres.ohlcv.futures.v7.ccxt.binance.v1_0_0`
        output table: ccxt_ohlcv_futures
    """
    args = parse_dataset_signature_to_args(signature, dataset_schema)
    hdbg.dassert_eq(args["data_format"], "postgres")
    table_name = args["vendor"] + f"_{args['data_type']}_{args['asset_type']}"
    action_tag = args["action_tag"]
    if action_tag == "resampled_1min":
        table_name += f"_{action_tag}"
    else:
        if args["data_type"] == "bid_ask":
            table_name += "_raw"
        elif args["data_type"] == "trades":
            table_name += f"_{action_tag}"
    return table_name
