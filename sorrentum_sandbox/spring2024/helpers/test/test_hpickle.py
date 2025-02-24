import logging

import helpers.hpickle as hpickle
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestToPickleable(hunitest.TestCase):
    def test_list1(self) -> None:
        """
        Test that a list is converted to a pickleable correctly.

        force_values_to_string = False
        """
        _obj = [1, "2", [3, 0.4], (5, None)]
        force_values_to_string = False
        actual = hpickle.to_pickleable(_obj, force_values_to_string)
        expected = [1, "2", [3, 0.4], (5, None)]
        self.assertEqual(actual, expected)

    def test_list2(self) -> None:
        """
        Test that a list is converted to a pickleable correctly.

        force_values_to_string = True
        """
        _obj = [1, "2", [3, 0.4], (5, None)]
        force_values_to_string = True
        actual = hpickle.to_pickleable(_obj, force_values_to_string)
        expected = ["1", "2", ["3", "0.4"], ("5", "None")]
        self.assertEqual(actual, expected)

    def test_tuple1(self) -> None:
        """
        Test that a tuple is converted to a pickleable correctly.

        force_values_to_string = False
        """
        _obj = (1, "2", [3, 0.4], (5, None))
        force_values_to_string = False
        actual = hpickle.to_pickleable(_obj, force_values_to_string)
        expected = (1, "2", [3, 0.4], (5, None))
        self.assertEqual(actual, expected)

    def test_dict1(self) -> None:
        """
        Test that a dict is converted to a pickleable correctly.

        force_values_to_string = False
        """
        _obj = {"a": 1, 2: ["b", 3], "c": {0.4: None}}
        force_values_to_string = False
        actual = hpickle.to_pickleable(_obj, force_values_to_string)
        expected = {"a": 1, 2: ["b", 3], "c": {0.4: None}}
        self.assertEqual(actual, expected)

    def test_iterable1(self) -> None:
        """
        Test that an iterable is converted to a pickleable correctly.

        force_values_to_string = False
        """
        _obj = {1, 2, 3}
        force_values_to_string = False
        actual = hpickle.to_pickleable(_obj, force_values_to_string)
        expected = [1, 2, 3]
        self.assertEqual(actual, expected)

    def test_unpickleable1(self) -> None:
        """
        Test that an unpickleable object is converted to a string.

        force_values_to_string = False
        """
        _obj = lambda x: x
        force_values_to_string = False
        actual = hpickle.to_pickleable(_obj, force_values_to_string)
        expected = "<function TestToPickleable.test_unpickleable1.<locals>.<lambda> at 0x>"
        self.assert_equal(actual, expected, purify_text=True)

    def test_unpickleable2(self) -> None:
        """
        Test that an unpickleable object is converted to a string.

        force_values_to_string = True
        """
        _obj = lambda x: x
        force_values_to_string = True
        actual = hpickle.to_pickleable(_obj, force_values_to_string)
        expected = "<function TestToPickleable.test_unpickleable2.<locals>.<lambda> at 0x>"
        self.assert_equal(actual, expected, purify_text=True)
