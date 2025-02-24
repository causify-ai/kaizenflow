import logging
from typing import List

import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.htraceback as htraceb
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_Traceback1(hunitest.TestCase):
    def test_parse1(self) -> None:
        """
        Parse traceback with all files from Docker that actually exist in the
        current repo.
        """
        txt = """

                TEST
        Traceback
            TEST
        Traceback (most recent call last):
          File "/app/amp/helpers/test/test_lib_tasks.py", line 27, in test_get_gh_issue_title2
            act = ltasks._get_gh_issue_title(issue_id, repo)
          File "/app/amp/helpers/lib_tasks.py", line 1265, in _get_gh_issue_title
            task_prefix = hgit.get_task_prefix_from_repo_short_name(repo_short_name)
          File "/app/amp/helpers/git.py", line 397, in get_task_prefix_from_repo_short_name
            if repo_short_name == "amp":
        NameError: name 'repo_short_name' is not defined
            TEST TEST TEST
        """
        purify_from_client = False
        # pylint: disable=line-too-long
        exp_cfile = [
            (
                "$GIT_ROOT/helpers/test/test_lib_tasks.py",
                27,
                "test_get_gh_issue_title2:act = ltasks._get_gh_issue_title(issue_id, repo)",
            ),
            (
                "$GIT_ROOT/helpers/lib_tasks.py",
                1265,
                "_get_gh_issue_title:task_prefix = hgit.get_task_prefix_from_repo_short_name(repo_short_name)",
            ),
            (
                "$GIT_ROOT/helpers/git.py",
                397,
                'get_task_prefix_from_repo_short_name:if repo_short_name == "amp":',
            ),
        ]
        exp_cfile = htraceb.cfile_to_str(exp_cfile)
        # pylint: enable=line-too-long
        exp_traceback = """
        Traceback (most recent call last):
          File "$GIT_ROOT/helpers/test/test_lib_tasks.py", line 27, in test_get_gh_issue_title2
            act = ltasks._get_gh_issue_title(issue_id, repo)
          File "$GIT_ROOT/helpers/lib_tasks.py", line 1265, in _get_gh_issue_title
            task_prefix = hgit.get_task_prefix_from_repo_short_name(repo_short_name)
          File "$GIT_ROOT/helpers/git.py", line 397, in get_task_prefix_from_repo_short_name
            if repo_short_name == "amp":
        NameError: name 'repo_short_name' is not defined
            TEST TEST TEST
        """
        self._parse_traceback_helper(
            txt, purify_from_client, exp_cfile, exp_traceback
        )

    def test_parse_empty_traceback1(self) -> None:
        """
        Parse an empty traceback file.
        """
        txt = """

                TEST
        Traceback
            TEST TEST TEST
        """
        purify_from_client = True
        exp_cfile: List[htraceb.CfileRow] = []
        exp_cfile = htraceb.cfile_to_str(exp_cfile)
        exp_traceback = "None"
        self._parse_traceback_helper(
            txt, purify_from_client, exp_cfile, exp_traceback
        )

    def test_parse2(self) -> None:
        """
        Parse a traceback file with both files from Docker and local files.
        """
        # Use references to this file so that we are independent from the file
        # layout.
        # pylint: disable=line-too-long
        txt = """
        Traceback (most recent call last):
          File "./helpers/test/test_traceback.py", line 146, in <module>
            _main(_parse())
          File "./helpers/test/test_traceback.py", line 105, in _main
            configs = cdtfut.get_configs_from_command_line(args)
          File "/app/amp/./helpers/test/test_traceback.py", line 228, in get_configs_from_command_line
            "config_builder": args.config_builder,
        """
        purify_from_client = True
        exp_cfile = """
        helpers/test/test_traceback.py:146:<module>:_main(_parse())
        helpers/test/test_traceback.py:105:_main:configs = cdtfut.get_configs_from_command_line(args)
        helpers/test/test_traceback.py:228:get_configs_from_command_line:"config_builder": args.config_builder,
        """
        exp_traceback = """
        Traceback (most recent call last):
          File "./helpers/test/test_traceback.py", line 146, in <module>
            _main(_parse())
          File "./helpers/test/test_traceback.py", line 105, in _main
            configs = cdtfut.get_configs_from_command_line(args)
          File "$GIT_ROOT/./helpers/test/test_traceback.py", line 228, in get_configs_from_command_line
            "config_builder": args.config_builder,
        """
        # pylint: enable=line-too-long
        self._parse_traceback_helper(
            txt, purify_from_client, exp_cfile, exp_traceback
        )

    def test_parse3(self) -> None:
        """
        Parse a traceback file with both files from Docker and local files.
        """
        # Use references to this file so that we are independent from the file
        # layout.
        # pylint: disable=line-too-long
        txt = """
        collected 6 items

        helpers/test/test_lib_tasks.py::Test_pytest_failed1::test_classes1 (0.02 s) FAILED [ 16%]

        =================================== FAILURES ===================================
        ______________________ Test_pytest_failed1.test_classes1 _______________________
        Traceback (most recent call last):
          File "/app/amp/helpers/test/test_lib_tasks.py", line 1460, in test_classes1
            self._helper(file_name, target_type, exp)
          File "/app/amp/helpers/test/test_lib_tasks.py", line 1440, in _helper
            act = ltasks.pytest_failed(ctx, use_frozen_list=use_frozen_list,
          File "/venv/lib/python3.8/site-packages/invoke/tasks.py", line 127, in __call__
            result = self.body(*args, **kwargs)
          File "/app/amp/helpers/lib_tasks.py", line 2140, in pytest_failed
            hdbg.dassert(m, "Invalid test='%s'", test)
          File "/app/amp/helpers/dbg.py", line 129, in dassert
            _dfatal(txt, msg, *args)
          File "/app/amp/helpers/dbg.py", line 117, in _dfatal
            dfatal(dfatal_txt)
          File "/app/amp/helpers/dbg.py", line 63, in dfatal
            raise assertion_type(ret)
        AssertionError:
        * Failed assertion *
        cond=None
        Invalid test='dev_scripts/testing/test/test_run_tests.py'
        """
        # pylint: enable=line-too-long
        purify_from_client = False
        exp_cfile = """
        $GIT_ROOT/helpers/test/test_lib_tasks.py:1460:test_classes1:self._helper(file_name, target_type, exp)
        $GIT_ROOT/helpers/test/test_lib_tasks.py:1440:_helper:act = ltasks.pytest_failed(ctx, use_frozen_list=use_frozen_list,
        /venv/lib/python3.8/site-packages/invoke/tasks.py:127:__call__:result = self.body(*args, **kwargs)
        $GIT_ROOT/helpers/lib_tasks.py:2140:pytest_failed:hdbg.dassert(m, "Invalid test='%s'", test)
        $GIT_ROOT/helpers/dbg.py:129:dassert:_dfatal(txt, msg, *args)
        $GIT_ROOT/helpers/dbg.py:117:_dfatal:dfatal(dfatal_txt)
        $GIT_ROOT/helpers/dbg.py:63:dfatal:raise assertion_type(ret)"""
        exp_traceback = r"""
        Traceback (most recent call last):
          File "$GIT_ROOT/helpers/test/test_lib_tasks.py", line 1460, in test_classes1
            self._helper(file_name, target_type, exp)
          File "$GIT_ROOT/helpers/test/test_lib_tasks.py", line 1440, in _helper
            act = ltasks.pytest_failed(ctx, use_frozen_list=use_frozen_list,
          File "/venv/lib/python3.8/site-packages/invoke/tasks.py", line 127, in __call__
            result = self.body(*args, **kwargs)
          File "$GIT_ROOT/helpers/lib_tasks.py", line 2140, in pytest_failed
            hdbg.dassert(m, "Invalid test='%s'", test)
          File "$GIT_ROOT/helpers/dbg.py", line 129, in dassert
            _dfatal(txt, msg, *args)
          File "$GIT_ROOT/helpers/dbg.py", line 117, in _dfatal
            dfatal(dfatal_txt)
          File "$GIT_ROOT/helpers/dbg.py", line 63, in dfatal
            raise assertion_type(ret)
        AssertionError:
        * Failed assertion *
        cond=None
        Invalid test='dev_scripts/testing/test/test_run_tests.py'
        """
        self._parse_traceback_helper(
            txt, purify_from_client, exp_cfile, exp_traceback
        )

    def test_parse4(self) -> None:
        """
        Parse a traceback file with both files from Docker and local files.
        """
        # pylint: disable=line-too-long
        txt = """
        =================================== FAILURES ===================================
        ____________ TestEgSingleInstrumentDataReader2.test_true_real_time1 ____________
        Traceback (most recent call last):
          File "/app/core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py", line 182, in test_true_real_time1
            self._execute_node(node)
          File "/app/core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py", line 238, in _execute_node
            dict_ = node.fit()
          File "/app/amp/core/dataflow/nodes/sources.py", line 385, in fit
            self.df = self._get_data_until_current_time()
          File "/app/amp/core/dataflow/nodes/sources.py", line 429, in _get_data_until_current_time
            df = self._get_data()
          File "/app/amp/core/dataflow/nodes/sources.py", line 574, in _get_data
            hdbg.dassert_lte(df.index.max(), current_time)
          File "/app/amp/helpers/dbg.py", line 172, in dassert_lte
            cond = val1 <= val2
          TypeError: '<=' not supported between instances of 'float' and 'Timestamp'
        ============================= slowest 3 durations ==============================
        """
        purify_from_client = False
        exp_cfile = r"""
        $GIT_ROOT/core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py:182:test_true_real_time1:self._execute_node(node)
        $GIT_ROOT/core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py:238:_execute_node:dict_ = node.fit()
        $GIT_ROOT/core/dataflow/nodes/sources.py:385:fit:self.df = self._get_data_until_current_time()
        $GIT_ROOT/core/dataflow/nodes/sources.py:429:_get_data_until_current_time:df = self._get_data()
        $GIT_ROOT/core/dataflow/nodes/sources.py:574:_get_data:hdbg.dassert_lte(df.index.max(), current_time)
        $GIT_ROOT/helpers/dbg.py:172:dassert_lte:cond = val1 <= val2/TypeError: '<=' not supported between instances of 'float' and 'Timestamp'"""
        exp_traceback = r"""
        Traceback (most recent call last):
          File "$GIT_ROOT/core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py", line 182, in test_true_real_time1
            self._execute_node(node)
          File "$GIT_ROOT/core_lime/dataflow/nodes/test/test_core_lime_dataflow_nodes.py", line 238, in _execute_node
            dict_ = node.fit()
          File "$GIT_ROOT/core/dataflow/nodes/sources.py", line 385, in fit
            self.df = self._get_data_until_current_time()
          File "$GIT_ROOT/core/dataflow/nodes/sources.py", line 429, in _get_data_until_current_time
            df = self._get_data()
          File "$GIT_ROOT/core/dataflow/nodes/sources.py", line 574, in _get_data
            hdbg.dassert_lte(df.index.max(), current_time)
          File "$GIT_ROOT/helpers/dbg.py", line 172, in dassert_lte
            cond = val1 <= val2
          TypeError: '<=' not supported between instances of 'float' and 'Timestamp'"""
        # pylint: enable=line-too-long
        self._parse_traceback_helper(
            txt, purify_from_client, exp_cfile, exp_traceback
        )

    def test_parse5(self) -> None:
        """
        Parse a traceback file with both files from Docker and local files.
        """
        # pylint: disable=line-too-long
        txt = """
        Traceback (most recent call last):
          File "/app/dataflow_lm/pipelines/E8/test/test_E8d_configs.py", line 37, in test1
            configs = dtfmoexuti.get_configs_from_command_line(args)
          File "/app/amp/dataflow/model/experiment_utils.py", line 195, in get_configs_from_command_line
            configs = cconfig.get_configs_from_builder(config_builder)
          File "/app/amp/core/config/builder.py", line 46, in get_configs_from_builder
            imp = importlib.import_module(import_)
          File "/usr/lib/python3.8/importlib/__init__.py", line 127, in import_module
            return _bootstrap._gcd_import(name[level:], package, level)
          File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
          File "<frozen importlib._bootstrap>", line 991, in _find_and_load
          File "<frozen importlib._bootstrap>", line 973, in _find_and_load_unlocked
        ModuleNotFoundError: No module named 'dataflow_lm.pipelines.E8.8Ed_configs'
        """
        purify_from_client = False
        exp_cfile = """
        $GIT_ROOT/dataflow_lm/pipelines/E8/test/test_E8d_configs.py:37:test1:configs = dtfmoexuti.get_configs_from_command_line(args)
        $GIT_ROOT/dataflow/model/experiment_utils.py:195:get_configs_from_command_line:configs = cconfig.get_configs_from_builder(config_builder)
        $GIT_ROOT/core/config/builder.py:46:get_configs_from_builder:imp = importlib.import_module(import_)
        /usr/lib/python3.8/importlib/__init__.py:127:import_module:return _bootstrap._gcd_import(name[level:], package, level)
        <frozen importlib._bootstrap>:1014:_gcd_import:
        <frozen importlib._bootstrap>:991:_find_and_load:
        <frozen importlib._bootstrap>:973:_find_and_load_unlocked:
        """
        exp_traceback = """
        Traceback (most recent call last):
          File "$GIT_ROOT/dataflow_lm/pipelines/E8/test/test_E8d_configs.py", line 37, in test1
            configs = dtfmoexuti.get_configs_from_command_line(args)
          File "$GIT_ROOT/dataflow/model/experiment_utils.py", line 195, in get_configs_from_command_line
            configs = cconfig.get_configs_from_builder(config_builder)
          File "$GIT_ROOT/core/config/builder.py", line 46, in get_configs_from_builder
            imp = importlib.import_module(import_)
          File "/usr/lib/python3.8/importlib/__init__.py", line 127, in import_module
            return _bootstrap._gcd_import(name[level:], package, level)
          File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
          File "<frozen importlib._bootstrap>", line 991, in _find_and_load
          File "<frozen importlib._bootstrap>", line 973, in _find_and_load_unlocked
        ModuleNotFoundError: No module named 'dataflow_lm.pipelines.E8.8Ed_configs'
        """
        # pylint: enable=line-too-long
        self._parse_traceback_helper(
            txt, purify_from_client, exp_cfile, exp_traceback
        )

    # pylint: disable=line-too-long
    # TODO(gp): Add test and fix for the following traceback:

    # Bug1:
    # Traceback (most recent call last):
    #   File "/Users/saggese/src/venv/amp.client_venv/bin/invoke", line 8, in <module>
    #     sys.exit(program.run())
    #   File "/Users/saggese/src/venv/amp.client_venv/lib/python3.9/site-packages/invoke/program.py", line 373, in run
    #     self.parse_collection()
    #   File "/Users/saggese/src/venv/amp.client_venv/lib/python3.9/site-packages/invoke/program.py", line 465, in parse_collection
    #     self.load_collection()
    #   File "/Users/saggese/src/venv/amp.client_venv/lib/python3.9/site-packages/invoke/program.py", line 696, in load_collection
    #     module, parent = loader.load(coll_name)
    #   File "/Users/saggese/src/venv/amp.client_venv/lib/python3.9/site-packages/invoke/loader.py", line 76, in load
    #     module = imp.load_module(name, fd, path, desc)
    #   File "/usr/local/Cellar/python@3.9/3.9.5/Frameworks/Python.framework/Versions/3.9/lib/python3.9/imp.py", line 234, in load_module
    #     return load_source(name, filename, file)
    #   File "/usr/local/Cellar/python@3.9/3.9.5/Frameworks/Python.framework/Versions/3.9/lib/python3.9/imp.py", line 171, in load_source
    #     module = _load(spec)
    #   File "<frozen importlib._bootstrap>", line 711, in _load
    #   File "<frozen importlib._bootstrap>", line 680, in _load_unlocked
    #   File "<frozen importlib._bootstrap_external>", line 855, in exec_module
    #   File "<frozen importlib._bootstrap>", line 228, in _call_with_frames_removed
    #   File "/Users/saggese/src/lem1/amp/tasks.py", line 8, in <module>
    #     from helpers.lib_tasks import set_default_params  # This is not an invoke target.
    #   File "/Users/saggese/src/lem1/amp/helpers/lib_tasks.py", line 23, in <module>
    #     import helpers.hgit as hgit
    #   File "/Users/saggese/src/lem1/amp/helpers/git.py", line 16, in <module>
    #     import helpers.hsystem as hsystem
    #   File "/Users/saggese/src/lem1/amp/helpers/system_interaction.py", line 529
    #     signature2 = _compute_file_signature(file_name, dir_depth)
    #     ^
    # SyntaxError: invalid syntax
    # Traceback (most recent call last):
    #   File "/Users/saggese/src/lem1/amp/dev_scripts/tg.py", line 21, in <module>
    #     import helpers.hsystem as hsystem
    #   File "/Users/saggese/src/lem1/amp/helpers/system_interaction.py", line 529
    #     signature2 = _compute_file_signature(file_name, dir_depth)
    #     ^
    # SyntaxError: invalid syntax

    # Bug2:
    # Traceback (most recent call last):
    #   File "/app/amp/dataflow/pipelines/real_time/test/test_dataflow_amp_real_time_pipeline.py", line 46, in test1
    #     ) = mdmdinex.get_ReplayedTimeMarketData_example2(
    # TypeError: get_ReplayedTimeMarketData_example2() got an unexpected keyword argument 'df'
    #
    # 13:34:45 INFO  traceback_to_cfile  : _main                         : 76  : in_file_name=log.txt
    # 13:34:45 INFO  parser              : read_file                     : 304 : Reading from 'log.txt'
    # 13:34:45 ERROR traceback_to_cfile  : _main                         : 87  : Can't find traceback in the file

    # Bug3:
    # =================================== FAILURES ===================================
    # _________________________ TestGetDataForInterval.test1 _________________________
    # Traceback (most recent call last):
    #   File "/venv/lib/python3.8/site-packages/pandas/core/indexes/base.py", line 3361, in get_loc
    #     return self._engine.get_loc(casted_key)
    #   File "pandas/_libs/index.pyx", line 76, in pandas._libs.index.IndexEngine.get_loc
    #   File "pandas/_libs/index.pyx", line 108, in pandas._libs.index.IndexEngine.get_loc
    #   File "pandas/_libs/hashtable_class_helper.pxi", line 5198, in pandas._libs.hashtable.PyObjectHashTable.get_item
    #   File "pandas/_libs/hashtable_class_helper.pxi", line 5206, in pandas._libs.hashtable.PyObjectHashTable.get_item
    # KeyError: 'end_ts'
    #
    # The above exception was the direct cause of the following exception:
    #
    # Traceback (most recent call last):
    #   File "/app/amp/market_data/test/test_market_data_client.py", line 46, in test1
    #     data = market_data_client.get_data_for_interval(
    #   File "/app/amp/market_data/market_data.py", line 212, in get_data_for_interval
    #     df = self._get_data(
    #   File "/app/amp/market_data/market_data_client.py", line 93, in _get_data
    #     market_data["start_ts"] = market_data["end_ts"] - pd.Timedelta(
    #   File "/venv/lib/python3.8/site-packages/pandas/core/frame.py", line 3458, in __getitem__
    #     indexer = self.columns.get_loc(key)
    #   File "/venv/lib/python3.8/site-packages/pandas/core/indexes/base.py", line 3363, in get_loc
    #     raise KeyError(key) from err
    # KeyError: 'end_ts'

    # Bug4:
    # dataflow/model/test/test_experiment_utils.py::Test_get_configs_from_command_line1::test1 (0.01 s) FAILED [100%]
    #
    # =================================== FAILURES ===================================
    # __________________ Test_get_configs_from_command_line1.test1 ___________________
    # Traceback (most recent call last):
    #   File "/app/dataflow/model/test/test_experiment_utils.py", line 35, in test1
    #     configs = dtfmoexuti.get_configs_from_command_line(args)
    #   File "/app/dataflow/model/experiment_utils.py", line 195, in get_configs_from_command_line
    #     configs = cconfig.get_configs_from_builder(config_builder)
    #   File "/app/core/config/builder.py", line 48, in get_configs_from_builder
    #     imp = importlib.import_module(import_)
    #   File "/usr/lib/python3.8/importlib/__init__.py", line 127, in import_module
    #     return _bootstrap._gcd_import(name[level:], package, level)
    #   File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
    #   File "<frozen importlib._bootstrap>", line 991, in _find_and_load
    #   File "<frozen importlib._bootstrap>", line 961, in _find_and_load_unlocked
    #   File "<frozen importlib._bootstrap>", line 219, in _call_with_frames_removed
    #   File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
    #   File "<frozen importlib._bootstrap>", line 991, in _find_and_load
    #   File "<frozen importlib._bootstrap>", line 961, in _find_and_load_unlocked
    #   File "<frozen importlib._bootstrap>", line 219, in _call_with_frames_removed
    #   File "<frozen importlib._bootstrap>", line 1014, in _gcd_import
    #   File "<frozen importlib._bootstrap>", line 991, in _find_and_load
    #   File "<frozen importlib._bootstrap>", line 973, in _find_and_load_unlocked
    # ModuleNotFoundError: No module named 'research'
    # ============================= slowest 3 durations ==============================

    # pylint: enable=line-too-long

    def _parse_traceback_helper(
        self,
        txt: str,
        purify_from_client: bool,
        exp_cfile: str,
        exp_traceback: str,
    ) -> None:
        hdbg.dassert_isinstance(txt, str)
        hdbg.dassert_isinstance(exp_cfile, str)
        hdbg.dassert_isinstance(exp_traceback, str)
        txt = hprint.dedent(txt)
        # Run the function under test.
        act_cfile, act_traceback = htraceb.parse_traceback(
            txt, purify_from_client=purify_from_client
        )
        _LOG.debug("act_cfile=\n%s", act_cfile)
        _LOG.debug("act_traceback=\n%s", act_traceback)
        # Compare cfile.
        act_cfile = htraceb.cfile_to_str(act_cfile)
        exp_cfile = hprint.dedent(exp_cfile)
        self.assert_equal(
            act_cfile, exp_cfile, fuzzy_match=True, purify_text=True
        )
        # Compare traceback.
        # Handle `None`.
        act_traceback = str(act_traceback)
        exp_traceback = hprint.dedent(exp_traceback)
        self.assert_equal(
            act_traceback, exp_traceback, fuzzy_match=True, purify_text=True
        )
