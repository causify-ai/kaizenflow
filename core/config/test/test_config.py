import collections
import datetime
import logging
import pprint
from typing import Any, Dict

import pytest

import core.config as cconfig
import core.config.config_ as cconconf
import helpers.hprint as hprint
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################
# Utils
# #############################################################################


def _get_flat_config1() -> cconfig.Config:
    """
    Build a flat (i.e., non-nested) config, that looks like:
        ```
        nrows: 10000
        nrows2: hello
        ```
    """
    config = cconfig.Config()
    config["hello"] = "world"
    config["foo"] = [1, 2, 3]
    #
    _LOG.debug("config=\n%s", config)
    return config


# #############################################################################


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


# #############################################################################
# TestFlatConfigSet1
# #############################################################################


class TestFlatConfigSet1(hunitest.TestCase):
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
        config = _get_flat_config1()
        #
        act = _check_roundtrip_transformation(self, config)
        exp = r"""
        # config=
        hello: world
        foo: [1, 2, 3]
        # code=
        Config([('hello', 'world'), ('foo', [1, 2, 3])])
        """.lstrip().rstrip()
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


def _get_flat_config2(self_: Any) -> cconfig.Config:
    """
    Build a flat (i.e., non-nested) config, that looks like:
        ```
        nrows: 10000
        nrows2: hello
        ```
    """
    config = cconfig.Config()
    config["nrows"] = 10000
    config["nrows2"] = "hello"
    #
    _LOG.debug("config=\n%s", config)
    exp = r"""
    nrows: 10000
    nrows2: hello
    """
    self_.assert_equal(str(config), exp, fuzzy_match=True)
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
        #
        with self.assertRaises(KeyError) as cm:
            config.get("nrows_tmp")
        act = str(cm.exception)
        exp = r'''"key='nrows_tmp' not in '['nrows', 'nrows2']'"'''
        self.assert_equal(act, exp)

    def test_non_existing_key3(self) -> None:
        """
        Look up a non-existent multiple key, not passing a default value.
        """
        config = _get_flat_config2(self)
        #
        with self.assertRaises(KeyError) as cm:
            config.get(("nrows2", "nrows_tmp"))
        act = str(cm.exception)
        exp = r'''"tail_key='('nrows_tmp',)' not in 'hello'"'''
        self.assert_equal(act, exp)

    def test_non_existing_key4(self) -> None:
        """
        Look up a non-existent multiple key, not passing a default value.
        """
        config = _get_flat_config2(self)
        #
        with self.assertRaises(KeyError) as cm:
            config.get(("nrows2", "hello"))
        act = str(cm.exception)
        exp = r'''"tail_key='('hello',)' not in 'hello'"'''
        self.assert_equal(act, exp)

    # /////////////////////////////////////////////////////////////////////////////

    def test_existing_key_with_type1(self) -> None:
        """
        nrows exists, so the default value is not used.
        """
        config = _get_flat_config2(self)
        self.assertEqual(config.get("nrows", None, int), 10000)
        self.assertEqual(config.get("nrows", "hello", int), 10000)

    def test_existing_key_with_type2(self) -> None:
        """
        nrows3 is missing so the default value is used.
        """
        config = _get_flat_config2(self)
        self.assertEqual(config.get("nrows3", 5, int), 5)
        self.assertEqual(config.get("nrows3", "hello", str), "hello")

    def test_existing_key_with_type3(self) -> None:
        """
        nrows exists, so the default value is not used but the type is checked.
        """
        config = _get_flat_config2(self)
        with self.assertRaises(AssertionError) as cm:
            self.assertEqual(config.get("nrows", None, str), 10000)
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        Instance '10000' of class 'int' is not a subclass of '<class 'str'>'
        """
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)

    def test_non_existing_key_with_type1(self) -> None:
        """
        nrows exists (so the default value is not used) but it's int and not
        str.
        """
        config = _get_flat_config2(self)
        with self.assertRaises(AssertionError) as cm:
            self.assertEqual(config.get("nrows", "hello", str), 10000)
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        Instance '10000' of class 'int' is not a subclass of '<class 'str'>'
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
# TestNestedConfigGet1
# #############################################################################


def _get_nested_config1(self_: Any) -> cconfig.Config:
    """
    Build a nested config, that looks like:
        ```
        nrows: 10000
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
        ```
    """
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
    #
    _LOG.debug("config=\n%s", config)
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
    self_.assert_equal(str(config), exp, fuzzy_match=True)
    return config


class TestNestedConfigGet1(hunitest.TestCase):
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
        exp = r'''"key='read_data2' not in '['nrows', 'read_data', 'single_val', 'zscore']'"'''
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
        exp = r'''"key='file_name2' not in '['file_name', 'nrows']'"'''
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_non_existing_key3(self) -> None:
        """
        Check a non-existent key at the second level.
        """
        config = _get_nested_config1(self)
        #
        with self.assertRaises(KeyError) as cm:
            _ = config["read_data2"]["file_name2"]
        act = str(cm.exception)
        exp = r'''"key='read_data2' not in '['nrows', 'read_data', 'single_val', 'zscore']'"'''
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# TestNestedConfigSet1
# #############################################################################


class TestNestedConfigSet1(hunitest.TestCase):
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
# TestNestedConfigMisc1
# #############################################################################


def _get_nested_config2() -> cconfig.Config:
    """
    Build a nested config, that looks like:
        ```
        nrows: 10000
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        ```
    """
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
    #
    _LOG.debug("config=\n%s", config)
    return config


def _get_nested_config3() -> cconfig.Config:
    """
    Build a nested config, that looks like:
        ```
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28
        ```
    """
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
    #
    _LOG.debug("config=\n%s", config)
    return config


def _get_nested_config4() -> cconfig.Config:
    """
    Build a nested config, that looks like:
        ```
        write_data:
          file_name: baz.txt
          nrows: 999
        single_val2: goodbye
        zscore2:
          style: gaz
          com: 28
        ```
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
    #
    _LOG.debug("config=\n%s", config)
    return config


def _get_nested_config5() -> cconfig.Config:
    """
    Build a nested config, that looks like:
        ```
        read_data:
          file_name: baz.txt
          nrows: 999
        single_val: goodbye
        zscore:
          style: super
        extra_zscore:
          style: universal
          tau: 32
        ```
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
    #
    _LOG.debug("config=\n%s", config)
    return config


class TestNestedConfigMisc1(hunitest.TestCase):
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
        """.lstrip().rstrip()
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
        """.lstrip().rstrip()
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
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_config1(self) -> None:
        """
        Compare two different styles of building a nested config.
        """
        config1 = _get_nested_config1(self)
        config2 = _get_nested_config2()
        #
        self.assert_equal(str(config1), str(config2))


# #############################################################################
# TestNestedConfigIn1
# #############################################################################


class TestNestedConfigIn1(hunitest.TestCase):
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
        """.lstrip().rstrip()
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
# TestNestedConfigUpdate1
# #############################################################################


class TestNestedConfigUpdate1(hunitest.TestCase):
    def test_update1(self) -> None:
        config1 = _get_nested_config3()
        config2 = _get_nested_config4()
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
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_update2(self) -> None:
        config1 = _get_nested_config3()
        config2 = _get_nested_config5()
        #
        config1.update(config2)
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
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_update3(self) -> None:
        """
        Generate a config of `{"key1": {"key0": }}` structure.
        """
        config = cconfig.Config()
        config_tmp = config.add_subconfig("key1")
        #
        subconfig = cconfig.Config()
        subconfig.add_subconfig("key0")
        #
        config_tmp.update(subconfig)
        #
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
# TestNestedConfigFlatten1
# #############################################################################


class TestNestedConfigFlatten1(hunitest.TestCase):
    def test_flatten1(self) -> None:
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
        #
        flattened = config.flatten()
        act = pprint.pformat(flattened)
        exp = r"""
        OrderedDict([(('read_data', 'file_name'), 'foo_bar.txt'),
             (('read_data', 'nrows'), 999),
             (('single_val',), 'hello'),
             (('zscore', 'style'), 'gaz'),
             (('zscore', 'com'), 28)])
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_flatten2(self) -> None:
        config = cconfig.Config()
        #
        config_tmp = config.add_subconfig("read_data")
        config_tmp["file_name"] = "foo_bar.txt"
        config_tmp["nrows"] = 999
        #
        config["single_val"] = "hello"
        #
        config.add_subconfig("zscore")
        #
        flattened = config.flatten()
        act = pprint.pformat(flattened)
        exp = r"""
        OrderedDict([(('read_data', 'file_name'), 'foo_bar.txt'),
             (('read_data', 'nrows'), 999),
             (('single_val',), 'hello'),
             (('zscore',), )])
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# TestSubtractConfig1
# #############################################################################


class TestSubtractConfig1(hunitest.TestCase):
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
        """.lstrip().rstrip()
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
        """.lstrip().rstrip()
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################
# TestDassertIsSerializable1
# #############################################################################


class TestDassertIsSerializable1(hunitest.TestCase):
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
# TestFromEnvVar1
# #############################################################################


class TestFromEnvVar1(hunitest.TestCase):
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
        Show that setting a value on a read-only config raises.
        """
        config = _get_nested_config1(self)
        _LOG.debug("config=\n%s", config)
        # Assign the value.
        self.assertEqual(config["zscore", "style"], "gaz")
        config["zscore", "style"] = "gasoline"
        self.assertEqual(config["zscore", "style"], "gasoline")
        # Mark as read-only.
        config.mark_read_only()
        # Try to assign an existing key and check it raises an error.
        with self.assertRaises(RuntimeError) as cm:
            config["zscore", "style"] = "oil"
        act = str(cm.exception)
        exp = r"""Trying to set key='('zscore', 'style')' to val='oil' in read-only config
        'nrows: 10000
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gasoline
          com: 28'
        """
        self.assert_equal(act, exp, fuzzy_match=True)
        # Try to assign a new key and check it raises an error.
        self.assertEqual(config["zscore", "style"], "gasoline")
        with self.assertRaises(RuntimeError) as cm:
            config["zscore2"] = "gasoline"
        act = str(cm.exception)
        exp = r"""Trying to set key='zscore2' to val='gasoline' in read-only config
        'nrows: 10000
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gasoline
          com: 28'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_set2(self) -> None:
        """
        Show that updating a read-only config raises.
        """
        config1 = _get_nested_config3()
        config2 = _get_nested_config4()
        config1.update(config2)
        #
        # Mark as read-only.
        config1.mark_read_only()
        with self.assertRaises(RuntimeError) as cm:
            config1.update(config2)
        act = str(cm.exception)
        exp = r"""Trying to set key='('write_data', 'file_name')' to val='baz.txt' in read-only config
        'read_data:
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
          com: 28'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_set3(self) -> None:
        """
        Show that by setting `value=False` config can be updated.
        """
        config = _get_nested_config1(self)
        _LOG.debug("config=\n%s", config)
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
                # An empty dict becomes an empty config when converting to `Config`
                # further.
                "param3": collections.OrderedDict(),
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


# TODO(gp): Unit tests all the functions.


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