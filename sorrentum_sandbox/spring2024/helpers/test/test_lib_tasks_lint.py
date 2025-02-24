import logging

import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest
import helpers.lib_tasks_lint as hlitalin
import helpers.test.test_lib_tasks as httestlib

_LOG = logging.getLogger(__name__)

# pylint: disable=protected-access


class Test_parse_linter_output1(hunitest.TestCase):
    """
    Test `_parse_linter_output()`.
    """

    def test1(self) -> None:
        # pylint: disable=line-too-long
        txt = r"""
Tabs remover.............................................................Passed
autoflake................................................................Passed
isort....................................................................Failed
- hook id: isort
- files were modified by this hook

INFO: > cmd='/app/linters/amp_isort.py core/dataflow/builders.py core/test/test_core.py core/dataflow/nodes.py helpers/printing.py helpers/lib_tasks.py core/data_adapters.py helpers/test/test_dbg.py helpers/unit_test.py core/dataflow/core.py core/finance.py core/dataflow/models.py core/dataflow/visualization.py helpers/dbg.py helpers/test/test_git.py core/dataflow/runners.py core/dataflow/test/test_visualization.py helpers/test/test_lib_tasks.py'
Fixing /src/amp/core/dataflow/builders.py
Fixing /src/amp/core/data_adapters.py
Fixing /src/amp/core/dataflow/models.py

black....................................................................Passed
flake8...................................................................Failed
- hook id: flake8
- exit code: 6

INFO: > cmd='/app/linters/amp_flake8.py core/dataflow/builders.py core/test/test_core.py core/dataflow/nodes.py helpers/printing.py'
core/dataflow/nodes.py:601:9: F821 undefined name '_check_col_names'
core/dataflow/nodes.py:608:9: F821 undefined name '_check_col_names'
INFO: > cmd='/app/linters/amp_flake8.py helpers/lib_tasks.py core/data_adapters.py helpers/test/test_dbg.py helpers/unit_test.py'
helpers/lib_tasks.py:302:12: W605 invalid escape sequence '\g'
helpers/lib_tasks.py:309:27: W605 invalid escape sequence '\s'
helpers/lib_tasks.py:309:31: W605 invalid escape sequence '\S'
helpers/lib_tasks.py:309:35: W605 invalid escape sequence '\('
helpers/lib_tasks.py:2184:9: F541 f-string is missing placeholders
helpers/test/test_dbg.py:71:25: F821 undefined name 'y'
INFO: > cmd='/app/linters/amp_flake8.py core/dataflow/core.py core/finance.py core/dataflow/models.py core/dataflow/visualization.py'
core/finance.py:250:5: E301 expected 1 blank line, found 0
INFO: > cmd='/app/linters/amp_flake8.py helpers/dbg.py helpers/test/test_git.py core/dataflow/runners.py core/dataflow/test/test_visualization.py'

INFO: > cmd='/app/linters/amp_flake8.py helpers/test/test_lib_tasks.py'
helpers/test/test_lib_tasks.py:225:5: F811 redefinition of unused 'test_git_clean' from line 158

doc_formatter............................................................Passed
pylint...................................................................
"""
        # pylint: enable=line-too-long
        act = hlitalin._parse_linter_output(txt)
        # pylint: disable=line-too-long
        exp = r"""
core/dataflow/nodes.py:601:9:[flake8] F821 undefined name '_check_col_names'
core/dataflow/nodes.py:608:9:[flake8] F821 undefined name '_check_col_names'
core/finance.py:250:5:[flake8] E301 expected 1 blank line, found 0
helpers/lib_tasks.py:2184:9:[flake8] F541 f-string is missing placeholders
helpers/lib_tasks.py:302:12:[flake8] W605 invalid escape sequence '\g'
helpers/lib_tasks.py:309:27:[flake8] W605 invalid escape sequence '\s'
helpers/lib_tasks.py:309:31:[flake8] W605 invalid escape sequence '\S'
helpers/lib_tasks.py:309:35:[flake8] W605 invalid escape sequence '\('
helpers/test/test_dbg.py:71:25:[flake8] F821 undefined name 'y'
helpers/test/test_lib_tasks.py:225:5:[flake8] F811 redefinition of unused 'test_git_clean' from line 158
"""
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)

    def test2(self) -> None:
        # pylint: disable=line-too-long
        txt = """
BUILD_TAG='dev_tools-1.0.0-20210513-DevTools196_Switch_from_makefile_to_invoke-e9ee441a1144883d2e8835740cba4dc09e7d4f2a'
PRE_COMMIT_HOME=/root/.cache/pre-commit
total 44
-rw-r--r-- 1 root root   109 May 13 12:54 README
-rw------- 1 root root 20480 May 13 12:54 db.db
drwx------ 4 root root  4096 May 13 12:54 repo0a8anbxn
drwx------ 8 root root  4096 May 13 12:54 repodla_5o4g
drwx------ 9 root root  4096 May 13 12:54 repoeydyv2ho
drwx------ 7 root root  4096 May 13 12:54 repokrr14v6z
drwx------ 4 root root  4096 May 13 12:54 repozqvepk0i
5
which python: /venv/bin/python
check pandas package: <module 'pandas' from '/venv/lib/python3.8/site-packages/pandas/__init__.py'>
PATH=/app/linters:/app/dev_scripts/eotebooks:/app/documentation/scripts:/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PYTHONPATH=/app:
cmd: 'pre-commit run -c /app/.pre-commit-config.yaml --files ./core/dataflow/builders.py'
Don't commit to branch...................................................^[[42mPassed^[[m
Check for merge conflicts................................................^[[42mPassed^[[m
Trim Trailing Whitespace.................................................^[[42mPassed^[[m
Fix End of Files.........................................................^[[42mPassed^[[m
Check for added large files..............................................^[[42mPassed^[[m
CRLF end-lines remover...................................................^[[42mPassed^[[m
Tabs remover.............................................................^[[42mPassed^[[m
autoflake................................................................^[[42mPassed^[[m
isort....................................................................^[[42mPassed^[[m
black....................................................................^[[42mPassed^[[m
flake8...................................................................^[[42mPassed^[[m
doc_formatter............................................................^[[42mPassed^[[m
pylint...................................................................^[[41mFailed^[[m
^[[2m- hook id: pylint^[[m
^[[2m- exit code: 3^[[m

^[[33mWARNING^[[0m: No module named 'pandas'
^[[33mWARNING^[[0m: No module named 'matplotlib'
^[[0m^[[36mINFO^[[0m: > cmd='/app/linters/amp_pylint.py core/dataflow/builders.py'
************* Module core.dataflow.builders
core/dataflow/builders.py:104: [R1711(useless-return), DagBuilder.get_column_to_tags_mapping] Useless return at end of function or method
core/dataflow/builders.py:195: [W0221(arguments-differ), ArmaReturnsBuilder.get_dag] Parameters differ from overridden 'get_dag' method

mypy.....................................................................^[[41mFailed^[[m
^[[2m- hook id: mypy^[[m
^[[2m- exit code: 3^[[m

^[[0m^[[36mINFO^[[0m: > cmd='/app/linters/amp_mypy.py core/dataflow/builders.py'
core/dataflow/builders.py:125: error: Returning Any from function declared to return "str"  [no-any-return]
core/dataflow/builders.py:195: error: Argument 2 of "get_dag" is incompatible with supertype "DagBuilder"; supertype defines the argument type as "Optional[Any]"  [override]
core/dataflow/builders.py:195: note: This violates the Liskov substitution principle
        """
        # pylint: enable=line-too-long
        act = hlitalin._parse_linter_output(txt)
        # pylint: disable=line-too-long
        exp = r"""
core/dataflow/builders.py:104:[pylint] [R1711(useless-return), DagBuilder.get_column_to_tags_mapping] Useless return at end of function or method
core/dataflow/builders.py:125:[mypy] error: Returning Any from function declared to return "str"  [no-any-return]
core/dataflow/builders.py:195:[mypy] error: Argument 2 of "get_dag" is incompatible with supertype "DagBuilder"; supertype defines the argument type as "Optional[Any]"  [override]
core/dataflow/builders.py:195:[mypy] note: This violates the Liskov substitution principle
core/dataflow/builders.py:195:[pylint] [W0221(arguments-differ), ArmaReturnsBuilder.get_dag] Parameters differ from overridden 'get_dag' method
"""
        # pylint: enable=line-too-long
        self.assert_equal(act, exp, fuzzy_match=True)


class Test_lint_check_if_it_was_run(hunitest.TestCase):
    """
    Test `lint_check_if_it_was_run()`.
    """

    def test1(self) -> None:
        # Build a mock context.
        ctx = httestlib._build_mock_context_returning_ok()
        # Stash the leftover changes from the previous tests.
        cmd = "git stash --include-untracked"
        hsystem.system(cmd)
        # Simple check that the function does not fail.
        _ = hlitalin.lint_check_if_it_was_run(ctx)
        # Pop the stashed changes to restore the original state.
        cmd = "git stash pop"
        # Do not abort on error because the stash may be empty.
        hsystem.system(cmd, abort_on_error=False)
