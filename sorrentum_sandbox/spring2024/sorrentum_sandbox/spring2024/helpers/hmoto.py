"""
Import as:

import helpers.hmoto as hmoto
"""

import unittest.mock as umock

import pytest  # isort:skip # noqa: E402 # pylint: disable=wrong-import-position

# Equivalent to `import moto`, but skip this module if the module is not present.
# `moto` must be imported before `boto3` to properly mock it.
moto = pytest.importorskip("moto")

# It is necessary that boto3 is imported after moto.
# If not, boto3 will access real AWS.
import boto3  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position

import helpers.hdbg as hdbg
import helpers.hs3 as hs3  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-positiona
import helpers.hunit_test as hunitest  # noqa: E402 module level import not at top of file  # pylint: disable=wrong-import-position


@pytest.mark.requires_aws
@pytest.mark.requires_ck_infra
class S3Mock_TestCase(hunitest.TestCase):
    # Mocked AWS credentials.
    mock_aws_credentials_patch = umock.patch.dict(
        hs3.os.environ,
        {
            "MOCK_AWS_ACCESS_KEY_ID": "mock_key_id",
            "MOCK_AWS_SECRET_ACCESS_KEY": "mock_secret_access_key",
            "MOCK_AWS_DEFAULT_REGION": "us-east-1",
        },
    )
    mock_aws_credentials = None
    mock_aws_profile = "__mock__"
    # Mocked bucket.
    mock_s3 = moto.mock_s3()
    bucket_name = "mock_bucket"
    # TODO(Nikola): Temporary here to ensure it is called only once.
    #   Used in some tests that are obtaining data from 3rd party providers.
    binance_secret = None

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Getting necessary secret before boto3 is mocked.
        if self.binance_secret is None:
            import helpers.hsecrets as hsecret

            self.binance_secret = hsecret.get_secret("binance.preprod.trading.1")

        # Start boto3 mock.
        self.mock_s3.start()
        # Start AWS credentials mock. Must be started after moto mock,
        # or it will be overridden by moto with `foobar` values.
        self.mock_aws_credentials = self.mock_aws_credentials_patch.start()
        # Initialize boto client and create bucket for testing.
        s3_client = boto3.client("s3")
        s3_client.create_bucket(Bucket=self.bucket_name)
        # Precaution to ensure that we are using mocked botocore.
        s3_test_client = boto3.client("s3")
        buckets = s3_test_client.list_buckets()["Buckets"]
        self.assertEqual(len(buckets), 1)
        self.assertEqual(buckets[0]["Name"], self.bucket_name)

    def tear_down_test(self) -> None:
        # Empty the bucket otherwise deletion will fail.
        s3 = boto3.resource("s3")
        hdbg.dassert_eq(self.bucket_name, "mock_bucket")
        bucket = s3.Bucket(self.bucket_name)
        bucket.objects.all().delete()
        # Delete bucket.
        s3fs_ = hs3.get_s3fs(self.mock_aws_profile)
        s3fs_.delete(f"s3://{self.bucket_name}", recursive=True)
        # Stop moto.
        self.mock_aws_credentials_patch.stop()
        self.mock_s3.stop()
