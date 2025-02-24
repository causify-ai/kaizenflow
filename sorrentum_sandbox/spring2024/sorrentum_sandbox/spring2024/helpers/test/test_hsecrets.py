# TODO(gp): Use pytest.import_skip instead of all this machinery.
_HAS_MOTO = True
try:
    import moto
except ImportError:
    # `moto` is not installed in `dev_tools`, so we skip it (see "DevTools376:
    # Break 2022-02-22").
    import helpers.hgit as hgit

    assert not hgit.is_cmamp(), (
        "`cmamp` should have moto, while other repos (e.g., `amp` or `dev_tools`) "
        "are allowed to not have it)"
    )
    _HAS_MOTO = False

if _HAS_MOTO:
    import json
    import logging

    import boto3
    import botocore
    import pytest

    import helpers.henv as henv
    import helpers.hgit as hgit
    import helpers.hsecrets as hsecret
    import helpers.hunit_test as hunitest

    _LOG = logging.getLogger(__name__)

    # The `mock_secretsmanager` decorator ensures the calls to the AWS API are
    # mocked.

    @pytest.mark.requires_ck_infra
    @pytest.mark.requires_aws
    @pytest.mark.skipif(
        not henv.execute_repo_config_code("is_CK_S3_available()"),
        reason="Run only if CK S3 is available",
    )
    class TestCreateClient(hunitest.TestCase):
        def test_create_client1(self) -> None:
            """
            Simple smoke test to verify connection to AWS.
            """
            client = hsecret.get_secrets_client(aws_profile="ck")
            self.assertIsInstance(client, botocore.client.BaseClient)

    @pytest.mark.requires_ck_infra
    @pytest.mark.requires_aws
    @pytest.mark.skipif(
        not henv.execute_repo_config_code("is_CK_S3_available()"),
        reason="Run only if CK S3 is available",
    )
    class TestGetSecret(hunitest.TestCase):
        @moto.mock_secretsmanager
        def test_get_secret(self) -> None:
            """
            Verify that the secret can be retrieved correctly.
            """
            # Make sure the region name matches the one used in `hsecret` profile.
            client = boto3.client("secretsmanager", region_name="eu-north-1")
            secret = {"testkey": "testvalue"}
            secret_name = "test.local.sandbox.1"
            client.create_secret(
                Name=secret_name, SecretString=json.dumps(secret)
            )
            self.assertDictEqual(hsecret.get_secret(secret_name), secret)

    @pytest.mark.requires_ck_infra
    @pytest.mark.requires_aws
    @pytest.mark.skipif(
        not henv.execute_repo_config_code("is_CK_S3_available()"),
        reason="Run only if CK S3 is available",
    )
    class TestStoreSecret(hunitest.TestCase):
        @moto.mock_secretsmanager
        def test_store_secret1(self) -> None:
            """
            Verify that a secret can be stored correctly.
            """
            secret = {"testkey": "testvalue"}
            secret_name = "test.local.sandbox.1"
            hsecret.store_secret(secret_name, secret)
            # Make sure the region name matches the one used in `hsecret`.
            client = boto3.client("secretsmanager", region_name="eu-north-1")
            test_secret_value = json.loads(
                client.get_secret_value(SecretId=secret_name)["SecretString"]
            )
            self.assertDictEqual(test_secret_value, secret)
