import os

import pytest

import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hsql as hsql
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import im_v2.ccxt.db.utils as imvccdbut
import im_v2.common.db.db_utils as imvcddbut


class TestExtractDataFromDb1(imvcddbut.TestImDbHelper):
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        ccxt_ohlcv_table_query = imvccdbut.get_ccxt_ohlcv_create_table_query()
        ccxt_ohlcv_insert_query = """
        INSERT INTO ccxt_ohlcv_spot
        VALUES
            (66, 1637690340000, 1.04549, 1.04549, 1.04527, 1.04527,
            5898.0427797325265, 'XRP_USDT', 'gateio',
            '2021-11-23 18:03:54.318763', '2021-11-23 18:03:54.318763'),
            (71, 1637777340000, 221.391, 221.493, 221.297, 221.431,
            81.31775837, 'SOL_USDT', 'kucoin',
            '2021-11-23 18:03:54.676947', '2021-11-23 18:03:54.676947')
        """
        hsql.execute_query(self.connection, ccxt_ohlcv_table_query)
        hsql.execute_query(self.connection, ccxt_ohlcv_insert_query)

    def tear_down_test(self) -> None:
        ccxt_ohlcv_drop_query = """
        DROP TABLE IF EXISTS ccxt_ohlcv_spot;
        """
        hsql.execute_query(self.connection, ccxt_ohlcv_drop_query)

    # TODO(Nikola): Test both local and S3 (with moto).
    @pytest.mark.slow
    @pytest.mark.skip(
        reason="CmTask1305: after removing circular dependencies in "
        "`hio.from_file`, this test fails reading a parquet file"
    )
    def test_extract_data_from_db(self) -> None:
        test_dir = self.get_scratch_space()
        dst_dir = os.path.join(test_dir, "by_date")
        hio.create_dir(dst_dir, False)

        file_path = os.path.join(
            hgit.get_amp_abs_path(),
            "im_v2/common/data/transform/extract_data_from_db.py",
        )
        cmd = []
        cmd.append(file_path)
        cmd.append("--start_date 2021-11-23")
        cmd.append("--end_date 2021-11-25")
        cmd.append(f"--dst_dir {dst_dir}")
        cmd = " ".join(cmd)
        include_file_content = True
        daily_signature_before = hunitest.get_dir_signature(
            dst_dir, include_file_content
        )
        hsystem.system(cmd)
        # Check directory structure with file contents.
        actual = []
        actual.append("# before=")
        actual.append(daily_signature_before)
        daily_signature_after = hunitest.get_dir_signature(
            dst_dir, include_file_content
        )
        actual.append("# after=")
        actual.append(daily_signature_after)
        actual = "\n".join(actual)
        self.check_string(actual, purify_text=True)
