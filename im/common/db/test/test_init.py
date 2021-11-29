import os

import helpers.unit_test as hut
import im.common.db.create_schema as vcdini


class TestDbSchemaFile(hut.TestCase):
    def test_exist1(self) -> None:
        """
        Test that files with SQL schema exist.
        """
        for file_name in vcdini.get_init_sql_files():
            self.assertTrue(os.path.exists(file_name))
