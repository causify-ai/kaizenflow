import logging

import helpers.hprint as hprint
import helpers.htable as htable
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestTable1(hunitest.TestCase):
    def test_from_text1(self) -> None:
        table = self._get_table()
        self.assertIsInstance(table, htable.Table)
        _LOG.debug(hprint.to_str("table"))

    def test_from_text_invalid1(self) -> None:
        txt = """completed failure Lint Run_linter
completed success Lint
completed success Lint Slow_tests"""
        cols = ["status", "outcome", "descr", "workflow"]
        with self.assertRaises(AssertionError) as cm:
            htable.Table.from_text(cols, txt, delimiter=" ")
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        '3'
        ==
        '4'
        Invalid row='['completed', 'success', 'Lint']' for cols='['status', 'outcome', 'descr', 'workflow']'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_from_text_invalid2(self) -> None:
        txt = """completed failure Lint Run_linter
        completed success Lint Fast_tess
        completed success Lint Slow_tests"""
        cols = ["status", "outcome", "descr", "workflow", "EXTRA"]
        with self.assertRaises(AssertionError) as cm:
            htable.Table.from_text(cols, txt, delimiter=" ")
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        '4'
        ==
        '5'
        Invalid row='['completed', 'failure', 'Lint', 'Run_linter']' for cols='['status', 'outcome', 'descr', 'workflow', 'EXTRA']'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    # #########################################################################

    def test_repr1(self) -> None:
        table = self._get_table()
        act = repr(table)
        exp = r"""
cols=['status', 'outcome', 'descr', 'workflow']
table=
['completed', 'failure', 'Lint', 'Run_linter']
['completed', 'success', 'Lint', 'Fast_tests']
['completed', 'success', 'Lint', 'Slow_tests']
size=(3, 4)
"""
        exp = exp.rstrip().lstrip()
        self.assert_equal(act, exp, fuzzy_match=False)

    def test_str1(self) -> None:
        table = self._get_table()
        act = str(table)
        exp = r"""
status    | outcome | descr | workflow   |
--------- | ------- | ----- | ---------- |
completed | failure | Lint  | Run_linter |
completed | success | Lint  | Fast_tests |
completed | success | Lint  | Slow_tests |
"""
        exp = exp.rstrip().lstrip()
        self.assert_equal(act, exp, fuzzy_match=False)

    # #########################################################################

    def test_filter_table1(self) -> None:
        """
        Filter resulting in a single matching row.
        """
        table = self._get_table()
        #
        table_filter = table.filter_rows("outcome", "failure")
        exp = r"""
cols=['status', 'outcome', 'descr', 'workflow']
table=
['completed', 'failure', 'Lint', 'Run_linter']
size=(1, 4)
"""
        act = repr(table_filter)
        exp = exp.rstrip().lstrip()
        self.assert_equal(act, exp, fuzzy_match=False)

    def test_filter_table2(self) -> None:
        """
        Filter resulting in no matches.
        """
        table = self._get_table()
        #
        table_filter = table.filter_rows("status", "in progress")
        exp = r"""
cols=['status', 'outcome', 'descr', 'workflow']
table=

size=(0, 4)
"""
        act = repr(table_filter)
        exp = exp.rstrip().lstrip()
        self.assert_equal(act, exp, fuzzy_match=False)

    def test_filter_table3(self) -> None:
        """
        Filter with a column constant using the constant value.
        """
        table = self._get_table()
        #
        table_filter = table.filter_rows("descr", "Lint")
        act = repr(table_filter)
        exp = repr(table)
        self.assert_equal(act, exp, fuzzy_match=False)

    # #########################################################################

    def test_unique1(self) -> None:
        table = self._get_table()
        #
        act = table.unique("descr")
        exp = ["Lint"]
        self.assert_equal(str(act), str(exp), fuzzy_match=False)

    def test_unique2(self) -> None:
        table = self._get_table()
        #
        act = table.unique("workflow")
        exp = ["Fast_tests", "Run_linter", "Slow_tests"]
        self.assert_equal(str(act), str(exp), fuzzy_match=False)

    # #########################################################################

    @staticmethod
    def _get_table() -> htable.Table:
        txt = """completed failure Lint Run_linter
completed success Lint Fast_tests
completed success Lint Slow_tests"""
        cols = ["status", "outcome", "descr", "workflow"]
        # table = [line for line in csv.reader(txt.split("\n"), delimiter=' ')]
        # _LOG.debug(hprint.to_str("table"))
        # _LOG.debug("size=%s", str(htable.size(table)))
        table = htable.Table.from_text(cols, txt, delimiter=" ")
        return table
