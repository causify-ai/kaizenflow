import logging

import core.config as cconfig
import helpers.hdict as hdict
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_get_nested_dict_iterator(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test basic case with no nesting.
        """
        dict_ = {"key0": "value0", "key1": "value1"}
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [(("key0",), "value0"), (("key1",), "value1")]
        self.assertListEqual(actual_result, expected_result)

    def test2(self) -> None:
        """
        Test simple nested case.
        """
        dict_ = {
            "key0": {"key00": "value00", "key01": "value01"},
            "key1": "value1",
        }
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [
            (("key0", "key00"), "value00"),
            (("key0", "key01"), "value01"),
            (("key1",), "value1"),
        ]
        self.assertListEqual(actual_result, expected_result)

    def test3(self) -> None:
        """
        Test multilevel nested case.
        """
        dict_ = {"key0": {"key00": {"key000": "value000"}}, "key1": "value1"}
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [
            (("key0", "key00", "key000"), "value000"),
            (("key1",), "value1"),
        ]
        self.assertListEqual(actual_result, expected_result)

    def test4(self) -> None:
        """
        Test flat case with `None` value.
        """
        dict_ = {"key0": "value0", "key1": None}
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [(("key0",), "value0"), (("key1",), None)]
        self.assertListEqual(actual_result, expected_result)

    def test5(self) -> None:
        """
        Test nested case with `None` value.
        """
        dict_ = {"key0": {"key00": None}, "key1": "value1"}
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [(("key0", "key00"), None), (("key1",), "value1")]
        self.assertListEqual(actual_result, expected_result)

    def test6(self) -> None:
        """
        Test flat case with empty dict value.
        """
        dict_ = {"key0": {}, "key1": "value1"}
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [(("key0",), {}), (("key1",), "value1")]
        self.assertListEqual(actual_result, expected_result)

    def test7(self) -> None:
        """
        Test nested case with empty dict value.
        """
        dict_ = {"key0": {"key00": {}}, "key1": "value1"}
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [(("key0", "key00"), {}), (("key1",), "value1")]
        self.assertListEqual(actual_result, expected_result)

    def test8(self) -> None:
        """
        Test flat case with empty Config value.
        """
        config = cconfig.Config()
        dict_ = {"key0": config, "key1": "value1"}
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [(("key0",), config), (("key1",), "value1")]
        self.assertListEqual(actual_result, expected_result)

    def test9(self) -> None:
        """
        Test nexted case with empty Config value.
        """
        config = cconfig.Config()
        dict_ = {"key0": {"key00": config}, "key1": "value1"}
        actual_result = list(hdict.get_nested_dict_iterator(dict_))
        expected_result = [(("key0", "key00"), config), (("key1",), "value1")]
        self.assertListEqual(actual_result, expected_result)
