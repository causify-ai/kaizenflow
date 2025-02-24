import os

import pytest

import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest
import im_v2.common.data_snapshot.data_snapshot_utils as imvcdsdsut


class Test_get_data_snapshot(hunitest.TestCase):
    @staticmethod
    def get_base_test_dir() -> str:
        base_dir = os.path.join(
            hgit.get_amp_abs_path(),
            "im_v2/common/data_snapshot/test/test_data_snapshots",
        )
        return base_dir

    def test_get_data_snapshot1(self) -> None:
        """
        All data snapshots in `root_dir` are numeric.
        """
        base_dir = self.get_base_test_dir()
        test_dir = os.path.join(base_dir, "numeric_data_snapshots")
        aws_profile = None
        data_snapshot = "latest"
        actual = imvcdsdsut.get_data_snapshot(
            test_dir, data_snapshot, aws_profile
        )
        expected = "20220720"
        self.assert_equal(actual, expected)

    def test_get_data_snapshot2(self) -> None:
        """
        `root_dir` contains alpha-numeric data snapshots.
        """
        base_dir = self.get_base_test_dir()
        test_dir = os.path.join(base_dir, "alpha_numeric_data_snapshots")
        aws_profile = None
        data_snapshot = "latest"
        actual = imvcdsdsut.get_data_snapshot(
            test_dir, data_snapshot, aws_profile
        )
        expected = "20220130"
        self.assert_equal(actual, expected)

    def test_get_data_snapshot3(self) -> None:
        """
        `root_dir` doesn't contain numeric data snapshot.
        """
        test_dir = self.get_base_test_dir()
        aws_profile = None
        data_snapshot = "latest"
        with self.assertRaises(AssertionError):
            imvcdsdsut.get_data_snapshot(test_dir, data_snapshot, aws_profile)

    @pytest.mark.skipif(
        not henv.execute_repo_config_code("is_CK_S3_available()"),
        reason="Run only if CK S3 is available",
    )
    def test_get_data_snapshot4(self) -> None:
        """
        Check that empty `data_snapshot` works for the daily staged Airflow data.
        """
        aws_profile = "ck"
        s3_bucket = hs3.get_s3_bucket_path(aws_profile)
        airflow_dir = "daily_staged.airflow.pq"
        daily_data_snapshot_root_dir = os.path.join(
            s3_bucket, "reorg", airflow_dir
        )
        data_snapshot = ""
        actual = imvcdsdsut.get_data_snapshot(
            daily_data_snapshot_root_dir, data_snapshot, aws_profile
        )
        expected = data_snapshot
        self.assert_equal(actual, expected)
