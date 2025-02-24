import copy
import unittest.mock as umock

import data_schema.dataset_schema_utils as dsdascut
import helpers.hio as hio
import helpers.hunit_test as hunitest

DUMMY_SCHEMA = {
    "dataset_signature": "download_mode.downloading_entity.action_tag",
    "token_separator_character": ".",
    "allowed_values": {
        "download_mode": ["bulk"],
        "downloading_entity": ["airflow"],
        "action_tag": ["downloaded_1sec"],
    },
}


class TestGetVendorFromS3Path1(hunitest.TestCase):
    def test_get_vendor_from_s3_path1(self) -> None:
        """
        Verify that vendor is extracted correctly from the path.
        """
        test_path = "s3://bucket-name/reorg/daily_staged.airflow.pq/bid_ask/crypto_chassis.downloaded_1sec"
        expected_value = "crypto_chassis"
        actual_value = dsdascut.get_vendor_from_s3_path(test_path)
        self.assertEqual(expected_value, actual_value)


class TestGetDatasetSchema1(hunitest.TestCase):
    @umock.patch.object(dsdascut, "_get_dataset_schema_file_path")
    @umock.patch.object(hio, "from_json")
    def test_get_dataset_schema1(
        self,
        mock_from_json: umock.MagicMock,
        mock_get_dataset_schema_file_path: umock.MagicMock,
    ) -> None:
        """
        Verify that dataset schema is loaded correctly.
        """
        test_schema = copy.deepcopy(DUMMY_SCHEMA)
        mock_from_json.return_value = copy.deepcopy(DUMMY_SCHEMA)
        mock_get_dataset_schema_file_path.return_value = "dataset_schema_v3.json"
        expected_value = test_schema
        expected_value["version"] = "v3"
        actual_value = dsdascut.get_dataset_schema()
        self.assertDictEqual(expected_value, actual_value)


class TestValidateDatasetSignatureSyntax1(hunitest.TestCase):
    def test_validate_dataset_signature_syntax_valid1(self) -> None:
        """
        Assure that valid signature passes the syntax check.
        """
        # This signature is valid according to the DUMMY_SCHEMA.
        valid_signature = "bulk.airflow.downloaded_1sec"
        self.assertTrue(
            dsdascut._validate_dataset_signature_syntax(
                valid_signature, DUMMY_SCHEMA
            )
        )

    def test_validate_dataset_signature_syntax_invalid1(self) -> None:
        """
        Assure that invalid signature fails the syntax check.
        """
        # This signature is invalid according to the DUMMY_SCHEMA.
        invalid_signature = "airflow.downloaded_1sec"
        self.assertFalse(
            dsdascut._validate_dataset_signature_syntax(
                invalid_signature, DUMMY_SCHEMA
            )
        )


class TestValidateDatasetSignatureSemantics1(hunitest.TestCase):
    def test_validate_dataset_signature_semantics_valid1(self) -> None:
        """
        Assure that valid signature passes the semantics check.
        """
        # This signature is valid according to the DUMMY_SCHEMA.
        valid_signature = "bulk.airflow.downloaded_1sec"
        self.assertTrue(
            dsdascut._validate_dataset_signature_semantics(
                valid_signature, DUMMY_SCHEMA
            )
        )

    def test_validate_dataset_signature_semantics_invalid1(self) -> None:
        """
        Assure that invalid signature fails the semantics check.
        """
        # This signature is invalid according to the DUMMY_SCHEMA.
        invalid_signature = "bulk.airflow.downloaded_48sec"
        self.assertFalse(
            dsdascut._validate_dataset_signature_semantics(
                invalid_signature, DUMMY_SCHEMA
            )
        )


class TestValidateDatasetSignature1(hunitest.TestCase):
    def test_validate_dataset_signature_valid1(self) -> None:
        """
        Assure that valid signature passes the validation.
        """
        # This signature is valid according to the DUMMY_SCHEMA.
        valid_signature = "bulk.airflow.downloaded_1sec"
        self.assertTrue(
            dsdascut.validate_dataset_signature(valid_signature, DUMMY_SCHEMA)
        )

    def test_validate_dataset_signature_invalid1(self) -> None:
        """
        Assure that syntactically invalid signature fails the validation.
        """
        # This signature is invalid according to the DUMMY_SCHEMA.
        invalid_signature = "bulk.downloaded_48sec"
        self.assertFalse(
            dsdascut.validate_dataset_signature(invalid_signature, DUMMY_SCHEMA)
        )

    def test_validate_dataset_signature_invalid2(self) -> None:
        """
        Assure that semantically invalid signature fails the validation.
        """
        # This signature is invalid according to the DUMMY_SCHEMA.
        invalid_signature = "madeup.airflow.downloaded_1sec"
        self.assertFalse(
            dsdascut.validate_dataset_signature(invalid_signature, DUMMY_SCHEMA)
        )


@umock.patch.object(dsdascut, "_get_dataset_schema_file_path")
@umock.patch.object(hio, "from_json")
class TestBuildS3DatasetPathFromArgs1(hunitest.TestCase):

    test_bucket = "s3://cryptokaizen-test"

    def test_build_s3_dataset_path_from_valid_args1(
        self,
        mock_from_json: umock.MagicMock,
        mock_get_dataset_schema_file_path: umock.MagicMock,
    ) -> None:
        """
        Verify S3 path is build correctl from valid arguments.
        """
        mock_from_json.return_value = copy.deepcopy(DUMMY_SCHEMA)
        mock_get_dataset_schema_file_path.return_value = "dataset_schema_v3.json"
        test_args = {
            "download_mode": "bulk",
            "downloading_entity": "airflow",
            "action_tag": "downloaded_1sec",
        }
        expected_value = f"{self.test_bucket}/v3/bulk/airflow/downloaded_1sec"
        actual_value = dsdascut.build_s3_dataset_path_from_args(
            self.test_bucket, test_args
        )
        self.assertEqual(expected_value, actual_value)

    def test_build_s3_dataset_path_from_invalid_args1(
        self,
        mock_from_json: umock.MagicMock,
        mock_get_dataset_schema_file_path: umock.MagicMock,
    ) -> None:
        """
        Verify S3 path building funciton throws exception when called with
        invalid arguments.
        """
        mock_from_json.return_value = copy.deepcopy(DUMMY_SCHEMA)
        mock_get_dataset_schema_file_path.return_value = "dataset_schema_v3.json"
        test_args = {
            "download_mode": "bulk",
            "downloading_entity": "madeup",
            "action_tag": "downloaded_1sec",
        }
        with self.assertRaises(ValueError) as e:
            dsdascut.build_s3_dataset_path_from_args(self.test_bucket, test_args)
        actual_exception = str(e.exception)
        expected_exception = r"""
        Invalid argument values for schema version: v3
        """
        self.assert_equal(actual_exception, expected_exception, fuzzy_match=True)

    def test_build_s3_dataset_path_from_missing_args1(
        self,
        mock_from_json: umock.MagicMock,
        mock_get_dataset_schema_file_path: umock.MagicMock,
    ) -> None:
        """
        Verify S3 path building function throws exception when called with
        missing arguments.
        """
        mock_from_json.return_value = copy.deepcopy(DUMMY_SCHEMA)
        mock_get_dataset_schema_file_path.return_value = "dataset_schema_v3.json"
        test_args = {
            "download_mode": "bulk",
            "downloading_entity": "airflow",
        }
        with self.assertRaises(KeyError) as e:
            dsdascut.build_s3_dataset_path_from_args(self.test_bucket, test_args)
        actual_exception = str(e.exception)
        expected_exception = r"""
        "Missing required identifier for schema version v3: 'action_tag'"
        """
        self.assert_equal(actual_exception, expected_exception, fuzzy_match=True)


class TestGetImDbTableNameFromSignature(hunitest.TestCase):

    DUMMY_SCHEMA_FOR_DB = {
        "dataset_signature": "download_mode.downloading_entity.action_tag.data_format.data_type.asset_type.universe.vendor.exchange_id.version",
        "token_separator_character": ".",
        "allowed_values": {
            "download_mode": ["realtime"],
            "downloading_entity": ["airflow"],
            "action_tag": [
                "downloaded_200ms",
                "resampled_1min",
                "downloaded_1min",
            ],
            "data_format": ["postgres"],
            "data_type": ["ohlcv", "bid_ask", "trades"],
            "asset_type": ["futures", "spot"],
            "universe": ["v7", "v3"],
            "vendor": ["ccxt"],
            "exchange_id": ["binance"],
            "version": ["v1_0_0"],
        },
    }

    def test_get_im_db_table_name_from_signature(self):
        """
        Test mapping signatures to IM DB table names.
        """
        signature1 = "realtime.airflow.downloaded_1min.postgres.ohlcv.futures.v7.ccxt.binance.v1_0_0"
        table_name1 = dsdascut.get_im_db_table_name_from_signature(
            signature1, self.DUMMY_SCHEMA_FOR_DB
        )
        self.assert_equal("ccxt_ohlcv_futures", table_name1)
        signature2 = "realtime.airflow.downloaded_1min.postgres.ohlcv.spot.v7.ccxt.binance.v1_0_0"
        table_name2 = dsdascut.get_im_db_table_name_from_signature(
            signature2, self.DUMMY_SCHEMA_FOR_DB
        )
        self.assert_equal("ccxt_ohlcv_spot", table_name2)
        signature3 = "realtime.airflow.resampled_1min.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        table_name3 = dsdascut.get_im_db_table_name_from_signature(
            signature3, self.DUMMY_SCHEMA_FOR_DB
        )
        self.assert_equal("ccxt_bid_ask_futures_resampled_1min", table_name3)
        signature4 = "realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0"
        table_name4 = dsdascut.get_im_db_table_name_from_signature(
            signature4, self.DUMMY_SCHEMA_FOR_DB
        )
        self.assert_equal("ccxt_bid_ask_futures_raw", table_name4)
