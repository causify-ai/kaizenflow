import collections
import datetime
import logging
import os
import pprint
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pytest

import core.config as cconfig
import core.config.config_ as cconconf
import helpers.hdbg as hdbg
import helpers.hintrospection as hintros
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################
# Utils
# #############################################################################


def _check_config_string(
    self: Any, config: cconfig.Config, exp: str, mode: str = "str"
) -> None:
    _LOG.debug("config=\n%s", config)
    if mode == "str":
        act = str(config)
    elif mode == "repr":
        act = repr(config)
    else:
        raise ValueError(f"Invalid mode='{mode}'")
    self.assert_equal(act, exp, fuzzy_match=True)


def _check_roundtrip_transformation(self_: Any, config: cconfig.Config) -> str:
    """
    Convert a config into Python code and back.

    :return: signature of the test
    """
    # Convert a config to Python code.
    code = config.to_python()
    _LOG.debug("code=%s", code)
    # Build a config from Python code.
    config2 = cconfig.Config.from_python(code)
    # Verify that the round-trip transformation is correct.
    self_.assertEqual(str(config), str(config2))
    # Build the signature of the test.
    act = []
    act.append("# config=\n%s" % str(config))
    act.append("# code=\n%s" % str(code))
    act = "\n".join(act)
    return act


def _purify_assertion_string(txt: str) -> str:
    # For some reason (probably the catch and re-raise of exceptions) the assertion
    # has `\n` literally and not interpreted as new lines, e.g.,
    # exp = r"""'"key=\'nrows_tmp\' not in:\\n  nrows: 10000\\n  nrows2: hello"\nconfig=\n  nrows: 10000\n  nrows2: hello'
    txt = txt.replace(r"\\n", "\n")
    txt = txt.replace(r"\n", "\n")
    txt = txt.replace(r"\'", "'")
    txt = txt.replace(r"\\", "")
    return txt


# #############################################################################
# Test_flat_config_set1
# #############################################################################


def _get_flat_config1(self: Any) -> cconfig.Config:
    config = cconfig.Config()
    config["hello"] = "world"
    config["foo"] = [1, 2, 3]
    # Check.
    exp = """
    hello: world
    foo: [1, 2, 3]
    """
    _check_config_string(self, config, exp)
    return config


class Test_flat_config_set1(hunitest.TestCase):
    def test_set1(self) -> None:
        """
        Set a key and print a flat config.
        """
        config = cconfig.Config()
        config["hello"] = "world"
        act = str(config)
        exp = r"""
        hello: world
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_roundtrip_transform1(self) -> None:
        """
        Test serialization/deserialization for a flat config.
        """
        config = _get_flat_config1(self)
        #
        act = _check_roundtrip_transformation(self, config)
        exp = r"""
        # config=
        hello: world
        foo: [1, 2, 3]
        # code=
        Config([('hello', 'world'), ('foo', [1, 2, 3])])
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_config_with_function(self) -> None:
        config = cconfig.Config()
        config[
            "filters"
        ] = "[(<function _filter_relevance at 0x7fe4e35b1a70>, {'thr': 90})]"
        # Check.
        expected_result = "filters: [(<function _filter_relevance>, {'thr': 90})]"
        actual_result = str(config)
        self.assertEqual(actual_result, expected_result)

    def test_config_with_object(self) -> None:
        config = cconfig.Config()
        config[
            "dag_builder"
        ] = "<dataflow_p1.task2538_pipeline.ArPredictorBuilder object at 0x7fd7a9ddd190>"
        # Check.
        expected_result = "dag_builder: <dataflow_p1.task2538_pipeline.ArPredictorBuilder object>"
        actual_result = str(config)
        self.assertEqual(actual_result, expected_result)


# #############################################################################
# Test_flat_config_get1
# #############################################################################


def _get_flat_config2(self: Any) -> cconfig.Config:
    config = cconfig.Config()
    config["nrows"] = 10000
    config["nrows2"] = "hello"
    # Check.
    exp = r"""
    nrows: 10000
    nrows2: hello
    """
    _check_config_string(self, config, exp)
    return config


class Test_flat_config_get1(hunitest.TestCase):
    """
    Test `__getitem__()` and `get()`.
    """

    def test_existing_key1(self) -> None:
        """
        Look up an existing key.
        """
        config = _get_flat_config2(self)
        exp = r"""
        nrows: 10000
        nrows2: hello
        """
        self.assert_equal(str(config), exp, fuzzy_match=True)
        #
        self.assertEqual(config["nrows"], 10000)

    def test_existing_key2(self) -> None:
        """
        Look up a key that exists and thus ignore the default value.
        """
        config = _get_flat_config2(self)
        #
        self.assertEqual(config.get("nrows", None), 10000)
        self.assertEqual(config.get("nrows", "hello"), 10000)

    # /////////////////////////////////////////////////////////////////////////////

    def test_non_existing_key1(self) -> None:
        """
        Look up a non-existent key, passing a default value.
        """
        config = _get_flat_config2(self)
        #
        self.assertEqual(config.get("nrows_tmp", None), None)
        self.assertEqual(config.get("nrows_tmp", "hello"), "hello")
        self.assertEqual(config.get(("nrows", "nrows_tmp"), "hello"), "hello")

    def test_non_existing_key2(self) -> None:
        """
        Look up a non-existent key, not passing a default value.
        """
        config = _get_flat_config2(self)
        # TODO(gp): There are nested exceptions here. Not sure it's a good idea or
        # not.
        # _________________ Test_flat_config_get1.test_non_existing_key2 _________________
        # Traceback (most recent call last):
        #   File "/app/amp/core/config/config_.py", line 163, in __getitem__
        #     ret = self._get_item(key, level=level)
        #   File "/app/amp/core/config/config_.py", line 626, in _get_item
        #     raise KeyError(msg)
        # KeyError: "key='nrows_tmp' not in:\n  nrows: 10000\n  nrows2: hello"
        #
        # During handling of the above exception, another exception occurred:
        #
        # Traceback (most recent call last):
        #   File "/app/amp/core/config/test/test_config.py", line 189, in test_non_existing_key2
        #     config.get("nrows_tmp")
        #   File "/app/amp/core/config/config_.py", line 372, in get
        #     raise e
        #   File "/app/amp/core/config/config_.py", line 361, in get
        #     ret = self.__getitem__(
        #   File "/app/amp/core/config/config_.py", line 173, in __getitem__
        #     raise e
        # KeyError: '"key=\'nrows_tmp\' not in:\n  nrows: 10000\n  nrows2: hello"\nconfig=\n  nrows: 10000\n  nrows2: hello'
        with self.assertRaises(KeyError) as cm:
            config.get("nrows_tmp", report_mode="verbose_exception")
        act = str(cm.exception)
        act = _purify_assertion_string(act)
        exp = r"""
        'exception="key='nrows_tmp' not in ['nrows', 'nrows2'] at level 0"
        key='nrows_tmp'
        config=
          nrows: 10000
          nrows2: hello'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_non_existing_key3(self) -> None:
        """
        Look up a non-existent multiple key, not passing a default value.
        """
        config = _get_flat_config2(self)
        #
        with self.assertRaises(KeyError) as cm:
            config.get(("nrows2", "nrows_tmp"), report_mode="verbose_exception")
        act = str(cm.exception)
        act = _purify_assertion_string(act)
        exp = r"""
        'exception="tail_key=('nrows_tmp',) at level 0"
        key='('nrows2', 'nrows_tmp')'
        config=
          nrows: 10000
          nrows2: hello'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_non_existing_key4(self) -> None:
        """
        Look up a non-existent multiple key, not passing a default value.
        """
        config = _get_flat_config2(self)
        #
        with self.assertRaises(KeyError) as cm:
            config.get(("nrows2", "hello"), report_mode="verbose_exception")
        act = str(cm.exception)
        act = _purify_assertion_string(act)
        exp = r"""
        'exception="tail_key=('hello',) at level 0"
        key='('nrows2', 'hello')'
        config=
          nrows: 10000
          nrows2: hello'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    # /////////////////////////////////////////////////////////////////////////////

    def test_existing_key_with_type1(self) -> None:
        """
        'nrows' exists, so the default value is not used.
        """
        config = _get_flat_config2(self)
        self.assertEqual(config.get("nrows", None, int), 10000)
        self.assertEqual(config.get("nrows", "hello", int), 10000)

    def test_existing_key_with_type2(self) -> None:
        """
        'nrows3' is missing so the default value is used.
        """
        config = _get_flat_config2(self)
        self.assertEqual(config.get("nrows3", 5, int), 5)
        self.assertEqual(config.get("nrows3", "hello", str), "hello")

    def test_existing_key_with_type3(self) -> None:
        """
        'nrows' exists, so the default value is not used but the type is
        checked.
        """
        config = _get_flat_config2(self)
        with self.assertRaises(AssertionError) as cm:
            _ = config.get("nrows", None, str, report_mode="verbose_exception")
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        Instance of '10000' is '<class 'int'>' instead of '<class 'str'>'
        """
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)

    def test_non_existing_key_with_type1(self) -> None:
        """
        'nrows' exists (so the default value is not used) but it's int and not
        str.
        """
        config = _get_flat_config2(self)
        with self.assertRaises(AssertionError) as cm:
            _ = config.get("nrows", "hello", str, report_mode="verbose_exception")
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        Instance of '10000' is '<class 'int'>' instead of '<class 'str'>'
        """
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)


# #############################################################################
# Test_flat_config_in1
# #############################################################################


class Test_flat_config_in1(hunitest.TestCase):
    def test_in1(self) -> None:
        """
        Test in operator.
        """
        config = _get_flat_config2(self)
        #
        self.assertTrue("nrows" in config)
        self.assertTrue("nrows2" in config)

    def test_not_in1(self) -> None:
        """
        Test not in operator.
        """
        config = _get_flat_config2(self)
        #
        self.assertTrue("nrows3" not in config)
        self.assertFalse("nrows3" in config)
        self.assertTrue("hello" not in config)
        self.assertTrue(("nrows", "world") not in config)
        self.assertTrue(("hello", "world") not in config)


# #############################################################################
# Test_nested_config_get1
# #############################################################################


def _get_nested_config1(self: Any) -> cconfig.Config:
    config = cconfig.Config()
    config["nrows"] = 10000
    #
    config.add_subconfig("read_data")
    config["read_data"]["file_name"] = "foo_bar.txt"
    config["read_data"]["nrows"] = 999
    #
    config["single_val"] = "hello"
    #
    config.add_subconfig("zscore")
    config["zscore"]["style"] = "gaz"
    config["zscore"]["com"] = 28
    # Check.
    exp = r"""
    nrows: 10000
    read_data:
      file_name: foo_bar.txt
      nrows: 999
    single_val: hello
    zscore:
      style: gaz
      com: 28
    """
    _check_config_string(self, config, exp)
    return config


class Test_nested_config_get1(hunitest.TestCase):
    def test_existing_key1(self) -> None:
        """
        Check that a key exists.
        """
        config = _get_nested_config1(self)
        #
        elem = config["read_data"]["file_name"]
        self.assertEqual(elem, "foo_bar.txt")

    def test_existing_key2(self) -> None:
        """
        Test accessing the config with nested vs chained access.
        """
        config = _get_nested_config1(self)
        #
        elem1 = config[("read_data", "file_name")]
        elem2 = config["read_data"]["file_name"]
        self.assertEqual(elem1, "foo_bar.txt")
        self.assertEqual(str(elem1), str(elem2))

    def test_existing_key3(self) -> None:
        """
        Show that nested access is equivalent to chained access.
        """
        config = _get_nested_config1(self)
        #
        elem1 = config.get(("read_data", "file_name"))
        elem2 = config["read_data"]["file_name"]
        self.assertEqual(elem1, "foo_bar.txt")
        self.assertEqual(str(elem1), str(elem2))

    def test_existing_key4(self) -> None:
        config = _get_nested_config1(self)
        #
        elem = config.get(("read_data2", "file_name"), "hello_world1")
        self.assertEqual(elem, "hello_world1")
        #
        elem = config.get(("read_data2", "file_name2"), "hello_world2")
        self.assertEqual(elem, "hello_world2")
        #
        elem = config.get(("read_data", "file_name2"), "hello_world3")
        self.assertEqual(elem, "hello_world3")

    # /////////////////////////////////////////////////////////////////////////////

    def test_non_existing_key1(self) -> None:
        """
        Check a non-existent key at the first level.
        """
        config = _get_nested_config1(self)
        #
        with self.assertRaises(KeyError) as cm:
            _ = config["read_data2"]
        act = str(cm.exception)
        act = _purify_assertion_string(act)
        exp = r"""
        "key='read_data2' not in ['nrows', 'read_data', 'single_val', 'zscore'] at level 0"
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_non_existing_key2(self) -> None:
        """
        Check a non-existent key at the second level.
        """
        config = _get_nested_config1(self)
        #
        with self.assertRaises(KeyError) as cm:
            _ = config["read_data"]["file_name2"]
        act = str(cm.exception)
        act = _purify_assertion_string(act)
        exp = r"""
        "key='file_name2' not in ['file_name', 'nrows'] at level 0"
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_non_existing_key3(self) -> None:
        """
        Check a non-existent key at the first level.
        """
        config = _get_nested_config1(self)
        #
        with self.assertRaises(KeyError) as cm:
            _ = config["read_data2"]["file_name2"]
        act = str(cm.exception)
        act = _purify_assertion_string(act)
        exp = r"""
        "key='read_data2' not in ['nrows', 'read_data', 'single_val', 'zscore'] at level 0"
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# Test_nested_config_set1
# #############################################################################


class Test_nested_config_set1(hunitest.TestCase):
    def test_not_existing_key1(self) -> None:
        """
        Set a key that doesn't exist.
        """
        config = cconfig.Config.from_dict(
            {
                "rets/read_data": cconfig.DUMMY,
            }
        )
        exp = r"""
        rets/read_data: __DUMMY__"""
        self.assert_equal(str(config), hprint.dedent(exp))
        # Set a key that doesn't exist.
        config["rets/hello"] = "world"
        # Check.
        exp = r"""
        rets/read_data: __DUMMY__
        rets/hello: world"""
        self.assert_equal(str(config), hprint.dedent(exp))

    def test_existing_key1(self) -> None:
        """
        Set a key that already exists.
        """
        config = cconfig.Config.from_dict(
            {
                "rets/read_data": cconfig.DUMMY,
            }
        )
        config.update_mode = "overwrite"
        # Overwrite an existing value.
        config["rets/read_data"] = "hello world"
        # Check.
        exp = r"""
        rets/read_data: hello world"""
        self.assert_equal(str(config), hprint.dedent(exp))

    @pytest.mark.skip(reason="See AmpTask1573")
    def test_existing_key2(self) -> None:
        """
        Set a key that doesn't exist in the hierarchy.
        """
        config = cconfig.Config.from_dict(
            {
                "rets/read_data": cconfig.DUMMY,
            }
        )
        # Set a key that doesn't exist in the hierarchy.
        config["rets/read_data", "source_node_name"] = "data_downloader"
        # This also doesn't work.
        # config["rets/read_data"]["source_node_name"] = "data_downloader"
        # Check.
        exp = r"""
        rets/read_data: hello world"""
        self.assert_equal(str(config), hprint.dedent(exp))

    def test_existing_key3(self) -> None:
        """
        Set a key that exist in the hierarchy with a Config.
        """
        config = cconfig.Config.from_dict(
            {
                "rets/read_data": cconfig.DUMMY,
            }
        )
        config.update_mode = "overwrite"
        # Assign a config to an existing key.
        config["rets/read_data"] = cconfig.Config.from_dict(
            {"source_node_name": "data_downloader"}
        )
        # Check.
        exp = r"""
        rets/read_data:
          source_node_name: data_downloader"""
        self.assert_equal(str(config), hprint.dedent(exp))

    def test_existing_key4(self) -> None:
        """
        Set a key that exists with a complex Config.
        """
        config = cconfig.Config.from_dict(
            {
                "rets/read_data": cconfig.DUMMY,
            }
        )
        config.update_mode = "overwrite"
        # Assign a config.
        config["rets/read_data"] = cconfig.Config.from_dict(
            {
                "source_node_name": "data_downloader",
                "source_node_kwargs": {
                    "exchange": "NASDAQ",
                    "symbol": "AAPL",
                    "root_data_dir": None,
                    "start_date": datetime.datetime(2020, 1, 4, 9, 30, 0),
                    "end_date": datetime.datetime(2021, 1, 4, 9, 30, 0),
                    "nrows": None,
                    "columns": None,
                },
            }
        )
        # Check.
        exp = r"""
        rets/read_data:
          source_node_name: data_downloader
          source_node_kwargs:
            exchange: NASDAQ
            symbol: AAPL
            root_data_dir: None
            start_date: 2020-01-04 09:30:00
            end_date: 2021-01-04 09:30:00
            nrows: None
            columns: None"""
        self.assert_equal(str(config), hprint.dedent(exp))


# #############################################################################
# Test_nested_config_misc1
# #############################################################################


def _get_nested_config2(self: Any) -> cconfig.Config:
    config = cconfig.Config()
    config["nrows"] = 10000
    #
    config_tmp = config.add_subconfig("read_data")
    config_tmp["file_name"] = "foo_bar.txt"
    config_tmp["nrows"] = 999
    #
    config["single_val"] = "hello"
    #
    config_tmp = config.add_subconfig("zscore")
    config_tmp["style"] = "gaz"
    config_tmp["com"] = 28
    # Check.
    exp = r"""
    nrows: 10000
    read_data:
      file_name: foo_bar.txt
      nrows: 999
    single_val: hello
    zscore:
      style: gaz
      com: 28
    """
    _check_config_string(self, config, exp)
    return config


def _get_nested_config3(self: Any) -> cconfig.Config:
    config = cconfig.Config()
    #
    config_tmp = config.add_subconfig("read_data")
    config_tmp["file_name"] = "foo_bar.txt"
    config_tmp["nrows"] = 999
    #
    config["single_val"] = "hello"
    #
    config_tmp = config.add_subconfig("zscore")
    config_tmp["style"] = "gaz"
    config_tmp["com"] = 28
    # Check.
    exp = r"""
    read_data:
      file_name: foo_bar.txt
      nrows: 999
    single_val: hello
    zscore:
      style: gaz
      com: 28
    """
    _check_config_string(self, config, exp)
    return config


def _get_nested_config4(self: Any) -> cconfig.Config:
    """
    Build a nested config, that looks like:
    """
    config = cconfig.Config()
    #
    config_tmp = config.add_subconfig("write_data")
    config_tmp["file_name"] = "baz.txt"
    config_tmp["nrows"] = 999
    #
    config["single_val2"] = "goodbye"
    #
    config_tmp = config.add_subconfig("zscore2")
    config_tmp["style"] = "gaz"
    config_tmp["com"] = 28
    # Check.
    exp = """
    write_data:
      file_name: baz.txt
      nrows: 999
    single_val2: goodbye
    zscore2:
      style: gaz
      com: 28
    """
    _check_config_string(self, config, exp)
    return config


def _get_nested_config5(self: Any) -> cconfig.Config:
    """
    Build a nested config, that looks like:
    """
    config = cconfig.Config()
    #
    config_tmp = config.add_subconfig("read_data")
    config_tmp["file_name"] = "baz.txt"
    config_tmp["nrows"] = 999
    #
    config["single_val"] = "goodbye"
    #
    config_tmp = config.add_subconfig("zscore")
    config_tmp["style"] = "super"
    #
    config_tmp = config.add_subconfig("extra_zscore")
    config_tmp["style"] = "universal"
    config_tmp["tau"] = 32
    # Check.
    exp = """
    read_data:
      file_name: baz.txt
      nrows: 999
    single_val: goodbye
    zscore:
      style: super
    extra_zscore:
      style: universal
      tau: 32
    """
    _check_config_string(self, config, exp)
    return config


class Test_nested_config_misc1(hunitest.TestCase):
    def test_config_print1(self) -> None:
        """
        Test printing a config.
        """
        config = _get_nested_config1(self)
        #
        act = str(config)
        exp = r"""
        nrows: 10000
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_config_to_python1(self) -> None:
        """
        Test `to_python()` on a nested config.
        """
        config = _get_nested_config1(self)
        # Check.
        act = config.to_python()
        exp = r"""
        Config([('nrows', 10000), ('read_data', Config([('file_name', 'foo_bar.txt'), ('nrows', 999)])), ('single_val', 'hello'), ('zscore', Config([('style', 'gaz'), ('com', 28)]))])
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_roundtrip_transform1(self) -> None:
        """
        Test serialization/deserialization for nested config.
        """
        config = _get_nested_config1(self)
        # Check.
        act = _check_roundtrip_transformation(self, config)
        exp = r"""
        # config=
        nrows: 10000
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        # code=
        Config([('nrows', 10000), ('read_data', Config([('file_name', 'foo_bar.txt'), ('nrows', 999)])), ('single_val', 'hello'), ('zscore', Config([('style', 'gaz'), ('com', 28)]))])
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_config1(self) -> None:
        """
        Compare two different styles of building a nested config.
        """
        config1 = _get_nested_config1(self)
        config2 = _get_nested_config2(self)
        #
        self.assert_equal(str(config1), str(config2))


# #############################################################################
# Test_nested_config_in1
# #############################################################################


class Test_nested_config_in1(hunitest.TestCase):
    def test_in1(self) -> None:
        """
        Test `in` with nested access.
        """
        config = _get_nested_config1(self)
        #
        act = str(config)
        exp = r"""
        nrows: 10000
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        #
        self.assertTrue("nrows" in config)
        #
        self.assertTrue("read_data" in config)

    def test_in2(self) -> None:
        config = _get_nested_config1(self)
        #
        self.assertTrue(("read_data", "file_name") in config)
        self.assertTrue(("zscore", "style") in config)

    def test_not_in1(self) -> None:
        config = _get_nested_config1(self)
        #
        self.assertTrue("read_data3" not in config)

    def test_not_in2(self) -> None:
        config = _get_nested_config1(self)
        #
        self.assertTrue(("read_data2", "file_name") not in config)

    def test_not_in3(self) -> None:
        config = _get_nested_config1(self)
        #
        self.assertTrue(("read_data", "file_name2") not in config)

    def test_not_in4(self) -> None:
        config = _get_nested_config1(self)
        #
        self.assertTrue(("read_data", "file_name", "foo_bar") not in config)


# #############################################################################
# Test_nested_config_update1
# #############################################################################


class Test_nested_config_update1(hunitest.TestCase):
    def test_update1(self) -> None:
        config1 = _get_nested_config3(self)
        config2 = _get_nested_config4(self)
        #
        config1.update(config2)
        # Check.
        act = str(config1)
        exp = r"""
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        write_data:
          file_name: baz.txt
          nrows: 999
        single_val2: goodbye
        zscore2:
          style: gaz
          com: 28
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_update2(self) -> None:
        config1 = _get_nested_config3(self)
        config2 = _get_nested_config5(self)
        #
        config1.update(config2, update_mode="overwrite")
        # Check.
        act = str(config1)
        exp = r"""
        read_data:
          file_name: baz.txt
          nrows: 999
        single_val: goodbye
        zscore:
          style: super
          com: 28
        extra_zscore:
          style: universal
          tau: 32
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_update3(self) -> None:
        """
        Generate a config of `{"key1": {"key0": }}` structure.
        """
        config = cconfig.Config()
        config_tmp = config.add_subconfig("key1")
        exp = """
        key1:
        """
        _check_config_string(self, config, exp)
        #
        subconfig = cconfig.Config()
        subconfig.add_subconfig("key0")
        exp = """
        key0:
        """
        _check_config_string(self, subconfig, exp)
        #
        _LOG.debug("\n" + hprint.frame("update"))
        config_tmp.update(subconfig)
        #
        _LOG.debug("\n" + hprint.frame("check"))
        expected_result = cconfig.Config()
        config_tmp = expected_result.add_subconfig("key1")
        config_tmp.add_subconfig("key0")
        #
        self.assert_equal(str(config), str(expected_result))
        exp = r"""
        key1:
          key0:
        """
        exp = hprint.dedent(exp)
        self.assert_equal(str(config), exp)


# #############################################################################
# Test_nested_config_update2
# #############################################################################


class Test_nested_config_update2(hunitest.TestCase):
    """
    Test the different update_modes for `config.update()`.
    """

    def test_assert_on_overwrite1(self) -> None:
        """
        Update with update_mode="assert_on_overwrite" and values that are not
        present.
        """
        for update_mode in (
            "assert_on_overwrite",
            "overwrite",
            "assign_if_missing",
        ):
            config1 = _get_nested_config3(self)
            # Check the value of the config.
            exp = """
            read_data:
              file_name: foo_bar.txt
              nrows: 999
            single_val: hello
            zscore:
              style: gaz
              com: 28
            """
            self.assert_equal(str(config1), exp, fuzzy_match=True)
            #
            config2 = cconfig.Config()
            config2["read_data", "file_name2"] = "hello"
            config2["read_data2"] = "world"
            # The new values don't exist so we should update the old config, no
            # matter what update_mode we are using.
            config1.update(config2, update_mode=update_mode)
            # Check.
            act = str(config1)
            exp = r"""
            read_data:
              file_name: foo_bar.txt
              nrows: 999
              file_name2: hello
            single_val: hello
            zscore:
              style: gaz
              com: 28
            read_data2: world
            """
            self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert_on_overwrite2(self) -> None:
        """
        Update with update_mode="assert_on_overwrite" and values that are
        present.
        """
        config1 = _get_nested_config3(self)
        #
        config2 = cconfig.Config()
        config2["read_data", "file_name"] = "hello"
        config2["read_data2"] = "world"
        config1.report_mode = "verbose_exception"
        # config1.update(config2)
        # The first value exists so we should assert.
        with self.assertRaises(cconfig.OverwriteError) as cm:
            config1.update(config2)
        act = str(cm.exception)
        exp = r"""
        exception=Trying to overwrite old value 'foo_bar.txt' with new value 'hello' for key 'file_name' when update_mode=assert_on_overwrite
        self=
          file_name: foo_bar.txt
          nrows: 999
        key='('read_data', 'file_name')'
        config=
          read_data:
            file_name: foo_bar.txt
            nrows: 999
          single_val: hello
          zscore:
            style: gaz
            com: 28
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    # /////////////////////////////////////////////////////////////////////////

    def test_overwrite1(self) -> None:
        """
        Update with update_mode="overwrite".
        """
        config1 = _get_nested_config3(self)
        # Check the value of the config.
        exp = """
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        """
        self.assert_equal(str(config1), exp, fuzzy_match=True)
        #
        config2 = cconfig.Config()
        config2["read_data", "file_name"] = "hello"
        config2["read_data2"] = "world"
        # Just overwrite.
        config1.update(config2, update_mode="overwrite")
        # Check.
        act = str(config1)
        exp = r"""
        read_data:
          file_name: hello
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        read_data2: world
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    # /////////////////////////////////////////////////////////////////////////

    def test_assign_if_missing1(self) -> None:
        """
        Update with update_mode="assert_on_overwrite" and values that are
        present.
        """
        config1 = _get_nested_config3(self)
        # Check the value of the config.
        exp = """
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        """
        self.assert_equal(str(config1), exp, fuzzy_match=True)
        #
        config2 = cconfig.Config()
        config2["read_data", "file_name"] = "hello"
        config2["read_data2"] = "world"
        # Do not assign the first value since the key already exists, while assign
        # the second since it doesn't exist.
        config1.update(config2, update_mode="assign_if_missing")
        # Check.
        act = str(config1)
        exp = r"""
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        read_data2: world
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# Test_nested_config_flatten1
# #############################################################################


def _get_nested_config6(self: Any) -> cconfig.Config:
    # Build config.
    config = cconfig.Config()
    #
    config_tmp = config.add_subconfig("read_data")
    config_tmp["file_name"] = "foo_bar.txt"
    config_tmp["nrows"] = 999
    #
    config["single_val"] = "hello"
    #
    config.add_subconfig("zscore")
    # Check.
    exp = r"""
    read_data:
      file_name: foo_bar.txt
      nrows: 999
    single_val: hello
    zscore:
    """
    _check_config_string(self, config, exp)
    return config


class Test_nested_config_flatten1(hunitest.TestCase):
    def test_flatten1(self) -> None:
        # Build config.
        config = cconfig.Config()
        #
        config_tmp = config.add_subconfig("read_data")
        config_tmp["file_name"] = "foo_bar.txt"
        config_tmp["nrows"] = 999
        #
        config["single_val"] = "hello"
        #
        config_tmp = config.add_subconfig("zscore")
        config_tmp["style"] = "gaz"
        config_tmp["com"] = 28
        # Check the representation.
        act = str(config)
        exp = r"""
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # Run.
        flattened = config.flatten()
        # Check the output.
        act = pprint.pformat(flattened)
        exp = r"""
        OrderedDict([(('read_data', 'file_name'), 'foo_bar.txt'),
             (('read_data', 'nrows'), 999),
             (('single_val',), 'hello'),
             (('zscore', 'style'), 'gaz'),
             (('zscore', 'com'), 28)])
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_flatten2(self) -> None:
        config = _get_nested_config6(self)
        # Run.
        flattened = config.flatten()
        # Check.
        act = pprint.pformat(flattened)
        exp = r"""
        OrderedDict([(('read_data', 'file_name'), 'foo_bar.txt'),
                    (('read_data', 'nrows'), 999),
                    (('single_val',), 'hello'),
                    (('zscore',), )])
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# Test_subtract_config1
# #############################################################################


class Test_subtract_config1(hunitest.TestCase):
    def test1(self) -> None:
        config1 = cconfig.Config()
        config1[("l0",)] = "1st_floor"
        config1[["l1", "l2"]] = "2nd_floor"
        config1[["r1", "r2", "r3"]] = [1, 2]
        #
        config2 = cconfig.Config()
        config2["l0"] = "Euro_1nd_floor"
        config2[["l1", "l2"]] = "2nd_floor"
        config2[["r1", "r2", "r3"]] = [1, 2]
        #
        diff = cconfig.subtract_config(config1, config2)
        # Check.
        act = str(diff)
        exp = r"""
        l0: 1st_floor
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test2(self) -> None:
        config1 = cconfig.Config()
        config1[("l0",)] = "1st_floor"
        config1[["l1", "l2"]] = "2nd_floor"
        config1[["r1", "r2", "r3"]] = [1, 2, 3]
        #
        config2 = cconfig.Config()
        config2["l0"] = "Euro_1nd_floor"
        config2[["l1", "l2"]] = "2nd_floor"
        config2[["r1", "r2", "r3"]] = [1, 2]
        config2["empty"] = cconfig.Config()
        #
        diff = cconfig.subtract_config(config1, config2)
        # Check.
        act = str(diff)
        exp = r"""
        l0: 1st_floor
        r1:
          r2:
            r3: [1, 2, 3]
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# Test_dassert_is_serializable1
# #############################################################################


class Test_dassert_is_serializable1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test a config that can be serialized correctly.
        """
        src_dir = "../../test"
        eval_config = cconfig.Config.from_dict(
            {
                "load_experiment_kwargs": {
                    "src_dir": src_dir,
                    "file_name": "result_bundle.v2_0.pkl",
                    "experiment_type": "ins_oos",
                    "selected_idxs": None,
                    "aws_profile": None,
                },
                "model_evaluator_kwargs": {
                    "predictions_col": "mid_ret_0_vol_adj_clipped_2_hat",
                    "target_col": "mid_ret_0_vol_adj_clipped_2",
                    # "oos_start": "2017-01-01",
                },
                "bh_adj_threshold": 0.1,
                "resample_rule": "W",
                "mode": "ins",
                "target_volatility": 0.1,
            }
        )
        # Make sure that it can be serialized.
        actual = eval_config.is_serializable()
        self.assertTrue(actual)

    def test2(self) -> None:
        """
        Test a config that can't be serialized since there is a function
        pointer.
        """
        src_dir = "../../test"
        func = lambda x: x + 1
        eval_config = cconfig.Config.from_dict(
            {
                "load_experiment_kwargs": {
                    "src_dir": src_dir,
                    "experiment_type": "ins_oos",
                    "selected_idxs": None,
                    "aws_profile": None,
                },
                "model_evaluator_kwargs": {
                    "predictions_col": "mid_ret_0_vol_adj_clipped_2_hat",
                    "target_col": "mid_ret_0_vol_adj_clipped_2",
                    # "oos_start": "2017-01-01",
                },
                "bh_adj_threshold": 0.1,
                "resample_rule": "W",
                "mode": "ins",
                "target_volatility": 0.1,
                "func": func,
            }
        )
        # Make sure that it can be serialized.
        actual = eval_config.is_serializable()
        self.assertFalse(actual)


# #############################################################################
# Test_from_env_var1
# #############################################################################


class Test_from_env_var1(hunitest.TestCase):
    @pytest.mark.requires_ck_infra
    def test1(self) -> None:
        eval_config = cconfig.Config.from_dict(
            {
                "load_experiment_kwargs": {
                    "file_name": "result_bundle.v2_0.pkl",
                    "experiment_type": "ins_oos",
                    "selected_idxs": None,
                    "aws_profile": None,
                }
            }
        )
        # Make sure that it can be serialized.
        self.assertTrue(eval_config.is_serializable())
        #
        python_code = eval_config.to_python(check=True)
        env_var = "AM_CONFIG_CODE"
        pre_cmd = f'export {env_var}="{python_code}"'
        python_code = (
            "import core.config as cconfig; "
            f'print(cconfig.Config.from_env_var("{env_var}"))'
        )
        cmd = f"{pre_cmd}; python -c '{python_code}'"
        _LOG.debug("cmd=%s", cmd)
        hsystem.system(cmd, suppress_output=False)


# #############################################################################
# Test_make_read_only1
# #############################################################################


class Test_make_read_only1(hunitest.TestCase):
    def test_set1(self) -> None:
        """
        Setting a value that already exists on a read-only config raises.
        """
        config = _get_nested_config1(self)
        _LOG.debug("config=\n%s", config)
        config.update_mode = "overwrite"
        config.clobber_mode = "allow_write_after_use"
        # Assigning values is not a problem, since the config is not read only.
        self.assertEqual(config["zscore", "style"], "gaz")
        config["zscore", "style"] = "gasoline"
        self.assertEqual(config["zscore", "style"], "gasoline")
        # Mark as read-only.
        config.mark_read_only()
        # Try to assign an existing key and check it raises an error.
        with self.assertRaises(cconfig.ReadOnlyConfigError) as cm:
            config["zscore", "style"] = "oil"
        act = str(cm.exception)
        exp = r"""
        Can't set key='('zscore', 'style')' to val='oil' in read-only config
        self=
          nrows: 10000
          read_data:
            file_name: foo_bar.txt
            nrows: 999
          single_val: hello
          zscore:
            style: gasoline
            com: 28
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_set2(self) -> None:
        """
        Setting a value that doesn't exists on a read-only config raises.
        """
        config = _get_nested_config1(self)
        _LOG.debug("config=\n%s", config)
        # Mark as read-only.
        config.mark_read_only()
        # Try to assign a new key and check it raises an error.
        with self.assertRaises(cconfig.ReadOnlyConfigError) as cm:
            config["zscore2"] = "gasoline"
        act = str(cm.exception)
        exp = r"""
        Can't set key='zscore2' to val='gasoline' in read-only config
        self=
          nrows: 10000
          read_data:
            file_name: foo_bar.txt
            nrows: 999
          single_val: hello
          zscore:
            style: gaz
            com: 28
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_set3(self) -> None:
        """
        Updating a read-only config raises.
        """
        config1 = _get_nested_config3(self)
        config2 = _get_nested_config4(self)
        config1.update(config2)
        # Mark as read-only.
        config1.mark_read_only()
        # Check.
        with self.assertRaises(RuntimeError) as cm:
            config1.update(config2, update_mode="overwrite")
        act = str(cm.exception)
        exp = r"""
        Can't set key='('write_data', 'file_name')' to val='baz.txt' in read-only config
        self=
          read_data:
            file_name: foo_bar.txt
            nrows: 999
          single_val: hello
          zscore:
            style: gaz
            com: 28
          write_data:
            file_name: baz.txt
            nrows: 999
          single_val2: goodbye
          zscore2:
            style: gaz
            com: 28
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_set4(self) -> None:
        """
        Show that by setting `value=False` config can be updated.
        """
        config = _get_nested_config1(self)
        _LOG.debug("config=\n%s", config)
        config.update_mode = "overwrite"
        config.clobber_mode = "allow_write_after_use"
        # Assign the value.
        self.assertEqual(config["zscore", "style"], "gaz")
        config["zscore", "style"] = "gasoline"
        self.assertEqual(config["zscore", "style"], "gasoline")
        # Mark as read-only.
        config.mark_read_only(value=False)
        # Assign new values.
        config["zscore", "com"] = 11
        self.assertEqual(config["zscore", "com"], 11)
        config["single_val"] = "hello1"
        self.assertEqual(config["single_val"], "hello1")
        # Check the final config.
        act = str(config)
        exp = r"""
        nrows: 10000
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello1
        zscore:
          style: gasoline
          com: 11
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# Test_to_dict1
# #############################################################################


class Test_to_dict1(hunitest.TestCase):
    def helper(
        self,
        config_as_dict: Dict[str, Any],
        expected_result_as_str: str,
    ) -> None:
        """
        Check that a `Config`'s conversion to a dict is correct.

        :param config_as_dict: a dictionary to build a `Config` from
        :param expected_result_as_str: expected `Config` value as string
        """
        config = cconfig.Config.from_dict(config_as_dict)
        act = str(config)
        self.assert_equal(act, expected_result_as_str, fuzzy_match=True)
        # Ensure that the round trip transform is correct.
        config_as_dict2 = config.to_dict()
        _LOG.debug("type(config_as_dict)=%s", type(config_as_dict))
        _LOG.debug("type(config_as_dict2)=%s", type(config_as_dict2))
        self.assert_equal(str(config_as_dict), str(config_as_dict2))

    def test1(self) -> None:
        """
        Test a regular `Config`.
        """
        config_as_dict = collections.OrderedDict(
            {
                "param1": 1,
                "param2": 2,
                "param3": 3,
            }
        )
        #
        exp = r"""
        param1: 1
        param2: 2
        param3: 3
        """
        self.helper(config_as_dict, exp)

    def test2(self) -> None:
        """
        Test a `Config` with a non-empty sub-config.
        """
        sub_config_dict = collections.OrderedDict(
            {
                "sub_key1": "sub_value1",
                "sub_key2": "sub_value2",
            }
        )
        config_as_dict = collections.OrderedDict(
            {
                "param1": 1,
                "param2": 2,
                "param3_as_config": sub_config_dict,
            }
        )
        #
        exp = r"""
        param1: 1
        param2: 2
        param3_as_config:
          sub_key1: sub_value1
          sub_key2: sub_value2
        """
        self.helper(config_as_dict, exp)

    def test3(self) -> None:
        """
        Test a `Config` with an empty sub-config.
        """
        config_as_dict = collections.OrderedDict(
            {
                "param1": 1,
                "param2": 2,
                # The empty leaves are converted to Configs,
                #  which are retained when converting back to dict.
                "param3": cconfig.Config(),
            }
        )
        #
        exp = r"""
        param1: 1
        param2: 2
        param3:
        """
        self.helper(config_as_dict, exp)

    # def test4(self):
    #     import dataflow_lime.pipelines.E8.E8d_pipeline as dtflpee8pi
    #     obj = dtflpee8pi.E8d_DagBuilder()
    #     obj.get_config_template()
    #     assert 0
    #     dict_ = {
    #         "resample": {
    #             "in_col_groups": [
    #                 ("close",),
    #                 ("volume",),
    #                 ("sbc_sac.compressed_difference",),
    #                 ("day_spread",),
    #                 ("day_num_spread",),
    #             ],
    #             "out_col_group": (),
    #             "transformer_kwargs": {
    #                 "rule": "5T",
    #                 # "rule": "15T",
    #                 "resampling_groups": [
    #                     ({"close": "close"}, "last", {}),
    #                     (
    #                         {
    #                             "close": "twap",
    #                             "sbc_sac.compressed_difference": "sbc_sac.compressed_difference",
    #                         },
    #                         "mean",
    #                         # TODO(gp): Use {}
    #                         # {},
    #                         None,
    #                     ),
    #                     (
    #                         {
    #                             "day_spread": "day_spread",
    #                             "day_num_spread": "day_num_spread",
    #                             "volume": "volume",
    #                         },
    #                         "sum",
    #                         {"min_count": 1},
    #                     ),
    #                 ],
    #                 "vwap_groups": [
    #                     ("close", "volume", "vwap"),
    #                 ],
    #             },
    #             "reindex_like_input": False,
    #             "join_output_with_input": False,
    #         },
    #     }
    #     config_tail = cconfig.Config.from_dict(dict_)
    #     config = cconfig.Config()
    #     config.update(config_tail)


class Test_to_dict2(hunitest.TestCase):
    def test1(self) -> None:
        config = _get_nested_config6(self)
        # Run.
        flattened = config.to_dict()
        # Check.
        act = pprint.pformat(flattened)
        exp = r"""
        OrderedDict([('read_data',
                    OrderedDict([('file_name', 'foo_bar.txt'), ('nrows', 999)])),
                    ('single_val', 'hello'),
                    ('zscore', )])
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test2(self) -> None:
        config = _get_nested_config6(self)
        # Run.
        flattened = config.to_dict(keep_leaves=False)
        # Check.
        act = pprint.pformat(flattened)
        exp = r"""
        OrderedDict([('read_data',
              OrderedDict([('file_name', 'foo_bar.txt'), ('nrows', 999)])),
             ('single_val', 'hello')])
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# Test_get_config_from_flattened_dict1
# #############################################################################


class Test_get_config_from_flattened_dict1(hunitest.TestCase):
    def test1(self) -> None:
        flattened = collections.OrderedDict(
            [
                (("read_data", "file_name"), "foo_bar.txt"),
                (("read_data", "nrows"), 999),
                (("single_val",), "hello"),
                (("zscore", "style"), "gaz"),
                (("zscore", "com"), 28),
            ]
        )
        config = cconconf.Config._get_config_from_flattened_dict(flattened)
        act = str(config)
        exp = r"""
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28"""
        exp = hprint.dedent(exp)
        self.assert_equal(act, exp, fuzzy_match=False)

    def test2(self) -> None:
        flattened = collections.OrderedDict(
            [
                (("read_data", "file_name"), "foo_bar.txt"),
                (("read_data", "nrows"), 999),
                (("single_val",), "hello"),
                (("zscore",), cconfig.Config()),
            ]
        )
        config = cconconf.Config._get_config_from_flattened_dict(flattened)
        act = str(config)
        exp = r"""
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
        """
        exp = hprint.dedent(exp)
        self.assert_equal(act, exp, fuzzy_match=False)


# #############################################################################
# Test_from_dict1
# #############################################################################


class Test_from_dict1(hunitest.TestCase):
    def test1(self) -> None:
        nested = {
            "read_data": {
                "file_name": "foo_bar.txt",
                "nrows": 999,
            },
            "single_val": "hello",
            "zscore": {
                "style": "gaz",
                "com": 28,
            },
        }
        config = cconfig.Config.from_dict(nested)
        act = str(config)
        exp = r"""
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28"""
        exp = hprint.dedent(exp)
        self.assert_equal(act, exp, fuzzy_match=False)

    def test2(self) -> None:
        nested = {
            "read_data": {
                "file_name": "foo_bar.txt",
                "nrows": 999,
            },
            "single_val": "hello",
            "zscore": cconfig.Config(),
        }
        config = cconfig.Config.from_dict(nested)
        act = str(config)
        exp = r"""
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
        """
        exp = hprint.dedent(exp)
        self.assert_equal(act, exp, fuzzy_match=False)

    def test3(self) -> None:
        """
        One of the dict's values is an empty dict.
        """
        nested = {
            "key1": "val1",
            "key2": {"key3": {"key4": {}}},
        }
        config = cconfig.Config.from_dict(nested)
        act = str(config)
        exp = r"""
        key1: val1
        key2:
          key3:
            key4:
        """
        exp = hprint.dedent(exp)
        self.assert_equal(act, exp, fuzzy_match=False)
        # Check the the value type.
        check = isinstance(config["key2", "key3", "key4"], cconfig.Config)
        self.assertTrue(check)
        # Check length.
        length = len(config["key2", "key3", "key4"])
        self.assertEqual(length, 0)

    def test4(self) -> None:
        """
        One of the dict's values is a dict that should become a `Config`.
        """
        test_dict = {"key1": "value1", "key2": {"key3": "value2"}}
        test_config = cconfig.Config.from_dict(test_dict)
        act = str(test_config)
        exp = r"""
        key1: value1
        key2:
          key3: value2
        """
        # Compare expected vs. actual outputs.
        exp = hprint.dedent(exp)
        self.assert_equal(act, exp, fuzzy_match=False)
        # Check the the value type.
        check = isinstance(test_config["key2"], cconfig.Config)
        self.assertTrue(check)


# #############################################################################
# Test_to_pickleable_string
# #############################################################################


class Test_to_pickleable_string(hunitest.TestCase):
    def helper(
        self,
        value: Any,
        should_be_pickleable_before: bool,
        force_values_to_string: bool,
    ) -> str:
        # Set config.
        nested: Dict[str, Any] = {
            "key1": value,
            "key2": {"key3": {"key4": {}}},
        }
        config = cconfig.Config.from_dict(nested)
        # Check if config is pickle-able before.
        is_pickleable_before = hintros.is_pickleable(config["key1"])
        self.assertEqual(is_pickleable_before, should_be_pickleable_before)
        # Check if function was succesfully applied on config.
        actual = config.to_pickleable(force_values_to_string)
        is_pickleable_after = hintros.is_pickleable(actual["key1"])
        self.assertTrue(is_pickleable_after)
        # Convert `actual` to string since `assert_equal` comparing
        # within strings and bytes.
        actual = str(actual)
        return actual

    def test1(self) -> None:
        """
        Test when config is pickle-able before applying the function.
        """
        value = "val1"
        # TODO(Danya): Do we want to keep `mark_as_used` in pickleable strings?
        expected = r"""
        key1: val1
        key2:
          key3:
            key4:

        """
        should_be_pickleable_before = True
        force_values_to_string = True
        actual = self.helper(
            value,
            should_be_pickleable_before,
            force_values_to_string,
        )
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        """
        Test when config is not pickle-able before applying the function.
        """
        # Set non-pickle-able value.
        value = lambda x: x
        expected = r"""
        key1: <function Test_to_pickleable_string.test2.<locals>.<lambda>>
        key2:
          key3:
            key4:

        """
        should_be_pickleable_before = False
        force_values_to_string = True
        actual = self.helper(
            value,
            should_be_pickleable_before,
            force_values_to_string,
        )
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)


# #############################################################################
# Test_save_to_file
# #############################################################################


class Test_save_to_file(hunitest.TestCase):
    def helper(self, value: Optional[str]) -> None:
        # Set config.
        log_dir = self.get_scratch_space()
        tag = "system_config.input"
        nested: Dict[str, Any] = {
            "key1": value,
            "key2": {"key3": {"key4": {}}},
        }
        config = cconfig.Config.from_dict(nested)
        # Save config.
        config.save_to_file(log_dir, tag)
        # Set expected values.
        expected_txt_path = os.path.join(log_dir, f"{tag}.txt")
        expected_pkl_str_path = os.path.join(
            log_dir, f"{tag}.values_as_strings.pkl"
        )
        expected_pkl_path = os.path.join(
            log_dir, f"{tag}.all_values_picklable.pkl"
        )
        # Check that file paths exist.
        self.assertTrue(os.path.exists(expected_txt_path))
        self.assertTrue(os.path.exists(expected_pkl_str_path))
        self.assertTrue(os.path.exists(expected_pkl_path))

    def test1(self) -> None:
        """
        Test saving a Config that is pickle-able.
        """
        value = "value1"
        self.helper(value)

    def test2(self) -> None:
        """
        Test saving a Config that is not pickle-able.
        """
        # Set non-pickle-able value.
        value = lambda x: x
        self.helper(value)


# #############################################################################
# Test_to_string
# #############################################################################


def remove_line_numbers(actual_config: str):
    # Remove line numbers from shorthand representations, e.g.
    #  dataflow/system/system_builder_utils.py::***::get_config_template
    line_regex = r"(?<=::)(\d+)(?=::)"
    actual_config = re.sub(line_regex, "***", actual_config)
    return actual_config


class Test_to_string(hunitest.TestCase):
    def get_test_config(
        self,
        value: Any,
    ) -> str:
        # Set config.
        nested: Dict[str, Any] = {
            "key1": value,
            "key2": {"key3": {"key4": {}}},
        }
        config = cconfig.Config.from_dict(nested)
        return config

    def test1(self) -> None:
        """
        Test when a value is a DataFrame.
        """
        value = pd.DataFrame(data=[[1, 2, 3], [4, 5, 6]], columns=["a", "b", "c"])
        config = self.get_test_config(value)
        #
        mode = "verbose"
        actual = config.to_string(mode)
        #
        expected = r"""key1 (marked_as_used=False, writer=None, val_type=pandas.core.frame.DataFrame):
        index=[0, 1]
        columns=a,b,c
        shape=(2, 3)
        a b c
        0 1 2 3
        1 4 5 6
        key2 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key3 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key4 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test2(self) -> None:
        """
        Test when config contains functions.
        """
        # Set function value.
        value = lambda x: x
        config = self.get_test_config(value)
        #
        mode = "verbose"
        actual = config.to_string(mode)
        #
        expected = r"""
        key1 (marked_as_used=False, writer=None, val_type=function): <function Test_to_string.test2.<locals>.<lambda>>
        key2 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key3 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key4 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)

    def test3(self) -> None:
        """
        Test when config contains a multiline string.
        """
        # Set multiline string value.
        value = "This is a\ntest multiline string."
        config = self.get_test_config(value)
        #
        mode = "verbose"
        actual = config.to_string(mode)
        #
        expected = r"""key1 (marked_as_used=False, writer=None, val_type=str):
        This is a
        test multiline string.
        key2 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key3 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key4 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)

    def test4(self) -> None:
        """
        Test verbose mode with `marked_as_used` == True.
        """
        value = "value2"
        config = self.get_test_config(value)
        _ = config.get_and_mark_as_used("key1")
        #
        mode = "verbose"
        actual = config.to_string(mode)
        actual = remove_line_numbers(actual)
        #
        expected = r"""key1 (marked_as_used=True, writer=$GIT_ROOT/core/config/test/test_config.py::***::test4, val_type=str): value2
        key2 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key3 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key4 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)

    def test5(self) -> None:
        """
        Test debug mode with `marked_as_used` == False.
        """
        # Set multiline string value.
        value = "This is a\ntest multiline string."
        config = self.get_test_config(value)
        #
        mode = "debug"
        actual = config.to_string(mode)
        #
        expected = r"""key1 (marked_as_used=False, writer=None, val_type=str):
        This is a
        test multiline string.
        key2 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key3 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key4 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        """
        self.assert_equal(actual, expected, purify_text=True, fuzzy_match=True)

    def test6(self) -> None:
        """
        Test debug mode with `marked_as_used` == True.

        This is a smoketest since the output of stacktrace is unstable.
        """
        # Set multiline string value.
        value = "value2"
        config = self.get_test_config(value)
        #
        _ = config.get_and_mark_as_used("key1")
        # Convert to string with full stack trace and remove line numbers.
        mode = "debug"
        _ = config.to_string(mode)


# #############################################################################
# Test_mark_as_used1
# #############################################################################


class Test_mark_as_used1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test marking a config with scalar values.
        """
        test_dict = {"key1": 1, "key2": "value2"}
        test_config = cconfig.Config.from_dict(test_dict)
        #
        expected_value = "value2"
        actual_value = test_config.get_and_mark_as_used("key2")
        self.assert_equal(
            actual_value, expected_value, purify_text=True, fuzzy_match=True
        )
        #
        expected_config = r"""key1 (marked_as_used=False, writer=None, val_type=int): 1
        key2 (marked_as_used=True, writer=$GIT_ROOT/core/config/test/test_config.py::***::test1, val_type=str): value2"""
        self._helper(test_config, expected_config)

    def test2(self) -> None:
        """
        Test marking a value in a nested config.
        """
        test_nested_dict = {"key1": 1, "key2": {"key3": "value3"}}
        test_nested_config = cconfig.Config.from_dict(test_nested_dict)
        #
        # Test marking the subconfig.
        expected_value = r"key3: value3"
        actual_value = test_nested_config.get_and_mark_as_used("key2")
        self.assert_equal(
            str(actual_value), expected_value, purify_text=True, fuzzy_match=True
        )
        # Test marking the subconfig.
        expected_config = r"""key1 (marked_as_used=False, writer=None, val_type=int): 1
        key2 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key3 (marked_as_used=True, writer=$GIT_ROOT/core/config/test/test_config.py::***::test2, val_type=str): value3"""
        self._helper(test_nested_config, expected_config)
        self._helper(test_nested_config, expected_config)

    def test3(self) -> None:
        """
        Test marking a subconfig in a deeply nested config.
        """
        test_nested_dict = {"key1": 1, "key2": {"key3": {"key4": "value3"}}}
        test_nested_config = cconfig.Config.from_dict(test_nested_dict)
        #
        # Test marking the nested subconfig.
        expected_value = r"""key3:
        key4: value3"""
        actual_value = test_nested_config.get_and_mark_as_used("key2")
        self.assert_equal(
            str(actual_value), expected_value, purify_text=True, fuzzy_match=True
        )
        #
        expected_config = r"""key1 (marked_as_used=False, writer=None, val_type=int): 1
        key2 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key3 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key4 (marked_as_used=True, writer=$GIT_ROOT/core/config/test/test_config.py::***::test3, val_type=str): value3"""
        self._helper(test_nested_config, expected_config)

    def test4(self) -> None:
        """
        Test marking a config with iterable value.
        """
        test_dict = {"key1": 1, "key2": ["value2", 2]}
        test_config = cconfig.Config.from_dict(test_dict)
        #
        expected_value = "['value2', 2]"
        actual_value = test_config.get_and_mark_as_used("key2")
        self.assert_equal(
            str(actual_value), expected_value, purify_text=True, fuzzy_match=True
        )
        #
        expected_config = r"""key1 (marked_as_used=False, writer=None, val_type=int): 1
        key2 (marked_as_used=True, writer=$GIT_ROOT/core/config/test/test_config.py::***::test4, val_type=list): ['value2', 2]"""
        self._helper(test_config, expected_config)

    def _helper(self, actual_config: cconfig.Config, expected_config: str):
        """
        Remove line numbers from config string and compare to expected value.
        """
        actual_config = repr(actual_config)
        # Replace line numbers with '***', e.g.:
        #  dataflow/system/system_builder_utils.py::***::get_config_template
        line_regex = r"(?<=::)(\d+)(?=::)"
        actual_config = re.sub(line_regex, "***", actual_config)
        self.assert_equal(
            actual_config, expected_config, purify_text=True, fuzzy_match=True
        )


# #############################################################################
# Test_marked_as_used1
# #############################################################################


class Test_get_marked_as_used1(hunitest.TestCase):
    """
    Verify that marked_as_used parameter is displayed correctly.
    """

    def test1(self) -> None:
        config = {"key1": "value1", "key2": {"key3": {"key4": "value2"}}}
        config = cconfig.Config.from_dict(config)
        # Verify that marked_as_used for a single value is correctly marked as used.
        config.get_and_mark_as_used("key1")
        is_key1_marked = config.get_marked_as_used("key1")
        self.assertTrue(is_key1_marked)
        # Verify that marked_as_used for nested single value is correctly displayed.
        config.get_and_mark_as_used(("key2", "key3", "key4"))
        is_key4_marked = config.get_marked_as_used(("key2", "key3", "key4"))
        self.assertTrue(is_key4_marked)
        # Verify that marked_as_used for a subconfig is correctly displayed.
        config.get_and_mark_as_used("key2")
        is_key2_marked = config.get_marked_as_used("key2")
        self.assertFalse(is_key2_marked)


# #############################################################################
# Test_check_unused_variables1
# #############################################################################


class Test_check_unused_variables1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Verify that a single unused variable is correctly identified.
        """
        config = {"key1": "value1", "key2": "value2"}
        config = cconfig.Config.from_dict(config)
        config.get_and_mark_as_used("key1")
        unused_variables = config.check_unused_variables()
        expected = [("key2",)]
        self.assertListEqual(unused_variables, expected)

    def test2(self) -> None:
        """
        Verify that a nested unused variable is correctly identified.
        """
        config = {
            "key1": "value1",
            "key2": {"key3": {"key4": "value2", "key5": "value3"}},
        }
        config = cconfig.Config.from_dict(config)
        config.get_and_mark_as_used("key1")
        config.get_and_mark_as_used(("key2", "key3", "key5"))
        unused_variables = config.check_unused_variables()
        expected = [("key2", "key3", "key4")]
        self.assertListEqual(unused_variables, expected)

    def test3(self) -> None:
        """
        Verify that all unused variables are correctly identified.
        """
        config = {
            "key1": "value1",
            "key2": {"key3": {"key4": "value2", "key5": "value3"}},
        }
        config = cconfig.Config.from_dict(config)
        unused_variables = config.check_unused_variables()
        expected = [("key1",), ("key2", "key3", "key4"), ("key2", "key3", "key5")]
        self.assertListEqual(unused_variables, expected)


# #############################################################################
# _Config_execute_stmt_TestCase1
# #############################################################################


class _Config_execute_stmt_TestCase1(hunitest.TestCase):
    """
    A class to apply transformations to a Config one-by-one checking its
    result.
    """

    def execute_stmt(
        self, stmt: str, exp: Optional[str], mode: str, globals: Dict
    ) -> str:
        """
        - Execute statement stmt
        - Print the resulting config
        - Check that config is what's expected, if exp is not `None`
        """
        _LOG.debug("\n" + hprint.frame(stmt))
        exec(stmt, globals)  # pylint: disable=exec-used
        #
        if mode == "str":
            act = str(config)  # pylint: disable=undefined-variable
        elif mode == "repr":
            act = repr(config)  # pylint: disable=undefined-variable
        else:
            raise ValueError(f"Invalid mode={mode}")
        _LOG.debug("config=\n%s", act)
        if exp is not None:
            self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)
        # Package the output.
        act = hprint.frame(stmt) + "\n" + act
        return act

    def raise_stmt(
        self, stmt: str, assertion_type: Any, exp: Optional[str], globals_: Dict
    ) -> None:
        _LOG.debug("\n" + hprint.frame(stmt))
        with self.assertRaises(assertion_type) as cm:
            exec(stmt, globals_)  # pylint: disable=exec-used
        act = str(cm.exception)
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)

    def run_steps_assert_string(
        self, workload: List[Tuple[str, Optional[str]]], mode: str, globals_: Dict
    ) -> None:
        for data in workload:
            hdbg.dassert_eq(len(data), 2, "Invalid data='%s'", str(data))
            stmt, exp = data
            self.execute_stmt(stmt, exp, mode, globals_)

    def run_steps_check_string(
        self, workload: List[str], mode: str, globals_: Dict
    ) -> None:
        exp = None
        res = []
        for stmt in workload:
            res_tmp = self.execute_stmt(stmt, exp, mode, globals_)
            res.append(res_tmp)
        txt = "\n".join(res)
        self.check_string(txt, purify_text=True, fuzzy_match=True)


# #############################################################################
# Test_nested_config_set_execute_stmt1
# #############################################################################


class Test_nested_config_set_execute_stmt1(_Config_execute_stmt_TestCase1):
    """
    Test that _Config_execute_stmt_TestCase1 works properly.
    """

    def test_assert_string_str1(self) -> None:
        workload = []
        #
        stmt = "config = cconfig.Config()"
        exp = ""
        workload.append((stmt, exp))
        #
        stmt = 'config["nrows"] = 10000'
        exp = r"""
        nrows: 10000
        """
        workload.append((stmt, exp))
        #
        stmt = 'config.add_subconfig("read_data")'
        exp = r"""
        nrows: 10000
        read_data:
        """
        workload.append((stmt, exp))
        #
        mode = "str"
        self.run_steps_assert_string(workload, mode, globals())

    def test_assert_string_repr1(self) -> None:
        workload = []
        #
        stmt = "config = cconfig.Config()"
        exp = ""
        workload.append((stmt, exp))
        #
        stmt = 'config["nrows"] = 10000'
        exp = """
        nrows (marked_as_used=False, writer=None, val_type=int): 10000
        """
        workload.append((stmt, exp))
        #
        stmt = 'config.add_subconfig("read_data")'
        exp = r"""
        nrows (marked_as_used=False, writer=None, val_type=int): 10000
        read_data (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        """
        workload.append((stmt, exp))
        #
        mode = "repr"
        self.run_steps_assert_string(workload, mode, globals())

    # ////////////////////////////////////////////////////////////////////////////
    def check_string_helper1(self, mode: str) -> None:
        workload = []
        #
        stmt = "config = cconfig.Config()"
        workload.append(stmt)
        #
        stmt = 'config["nrows"] = 10000'
        workload.append(stmt)
        #
        stmt = 'config.add_subconfig("read_data")'
        workload.append(stmt)
        #
        self.run_steps_check_string(workload, mode, globals())

    def test_check_string_str1(self) -> None:
        mode = "str"
        self.check_string_helper1(mode)

    def test_check_string_repr1(self) -> None:
        mode = "repr"
        self.check_string_helper1(mode)


# #############################################################################
# Test_basic1
# #############################################################################


class Test_basic1(_Config_execute_stmt_TestCase1):
    def test1(self) -> None:
        """
        Various assignments and their representations.
        """
        mode = "repr"
        # Create a Config.
        update_mode = "overwrite"
        clobber_mode = "allow_write_after_use"
        stmt = f'config = cconfig.Config(update_mode="{update_mode}", clobber_mode="{clobber_mode}")'
        exp = ""
        self.execute_stmt(stmt, exp, mode, globals())
        # Assign with a flat key.
        stmt = 'config["key1"] = "hello.txt"'
        exp = r"""
        key1 (marked_as_used=False, writer=None, val_type=str): hello.txt
        """
        self.execute_stmt(stmt, exp, mode, globals())
        # Invalid access.
        stmt = 'config["key1"]["key2"] = "world.txt"'
        exp = """
        'str' object does not support item assignment
        """
        self.raise_stmt(stmt, TypeError, exp, globals())
        # Invalid access.
        stmt = 'config["key1", "key2"] = "world.txt"'
        exp = """
        * Failed assertion *
        Instance of 'hello.txt' is '<class 'str'>' instead of '<class 'core.config.config_.Config'>'
        """
        self.raise_stmt(stmt, AssertionError, exp, globals())

    def test2(self) -> None:
        """
        Various assignments and their representations.
        """
        mode = "repr"
        # Create a Config.
        update_mode = "overwrite"
        clobber_mode = "allow_write_after_use"
        stmt = f'config = cconfig.Config(update_mode="{update_mode}", clobber_mode="{clobber_mode}")'
        exp = ""
        self.execute_stmt(stmt, exp, mode, globals())
        # Assign with a compound key.
        stmt = 'config["key1", "key2"] = "hello.txt"'
        exp = r"""
        key1 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key2 (marked_as_used=False, writer=None, val_type=str): hello.txt
        """
        self.execute_stmt(stmt, exp, mode, globals())
        # Assign with a compound key.
        stmt = 'config["key1"]["key2"] = "hello2.txt"'
        exp = r"""
        key1 (marked_as_used=False, writer=None, val_type=core.config.config_.Config):
        key2 (marked_as_used=False, writer=None, val_type=str): hello2.txt
        """
        self.execute_stmt(stmt, exp, mode, globals())

    def test3(self) -> None:
        mode = "repr"
        # Create a Config.
        update_mode = "overwrite"
        clobber_mode = "assert_on_write_after_use"
        stmt = f'config = cconfig.Config(update_mode="{update_mode}", clobber_mode="{clobber_mode}")'
        exp = ""
        self.execute_stmt(stmt, exp, mode, globals())
        # Assign a value.
        stmt = 'config["key1"] = "hello.txt"'
        exp = r"""
        key1 (marked_as_used=False, writer=None, val_type=str): hello.txt
        """
        self.execute_stmt(stmt, exp, mode, globals())
