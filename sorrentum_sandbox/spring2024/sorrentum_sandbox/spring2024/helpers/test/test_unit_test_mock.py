import logging
import unittest.mock as umock
from typing import Any

import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def _check(self: Any, str_to_eval: str, exp_val: str) -> None:
    """
    Evaluate `str_to_eval` and compare it to expected value `exp_val`.
    """
    # The variable lives 3 levels in the stack trace from here.
    act_val = hprint.to_str(str_to_eval, frame_lev=3)
    _LOG.debug("%s", act_val)
    self.assert_equal(act_val, exp_val, purify_text=True)


class _Class:
    def __init__(self) -> None:
        self.a = 3
        self.b = 14

    def get_a(self) -> int:
        return self.a

    def get_b(self) -> int:
        return self.b


class _TestCase(hunitest.TestCase):
    def check(self, *args, **kwargs):
        _check(self, *args, **kwargs)


# #############################################################################
# Test_Mock1
# #############################################################################


# References
# - https://docs.python.org/3/library/unittest.mock.html
# - https://realpython.com/python-mock-library/
#
# - Mocks are used to imitate objects in the code base and need to have the same
#   interface of objects they are replacing
# - `Mock` and `MagicMock` objects
#   - avoid to create stubs by creating attributes and methods as they are
#     accessed
#   - accessing the same attribute returns the same mock
#   - can be configured to specify return values
#   - store details of how they have been used
# - After execution, one can make assertions about how mocks have been used

# umock.Mockspec
# :param spec: specification for the mock object, e.g., using a class to create
#   the proper interface


class Test_Mock1(_TestCase):
    """
    - A `Mock` creates attributes / methods as you access them
    - The return value of a mocked attribute / method is also a `Mock`
    """

    def test_lazy_attributes1(self) -> None:
        """
        Assigning a class attribute on a Mock creates a Mock.
        """
        obj = umock.Mock()
        # obj is a Mock object.
        self.check("obj", "obj=<Mock id='xxx'>")
        # Calling an attribute creates a Mock.
        self.check("obj.a", "obj.a=<Mock name='mock.a' id='xxx'>")
        # Assigning an attribute in the mock creates an attribute.
        obj.a = 3
        self.check("obj.a", "obj.a=3")

    def test_lazy_methods1(self) -> None:
        """
        Calling a method on a Mock creates a Mock.
        """
        # Mock json module `import json`.
        json = umock.Mock()
        self.check("json", "json=<Mock id='xxx'>")
        # Create a function on the fly that returns a mock.
        v = json.dumps()
        self.assertTrue(isinstance(v, umock.Mock))
        self.check("json.dumps", "json.dumps=<Mock name='mock.dumps' id='xxx'>")
        # The mocked function and the returned value from a mock function are
        # different mocks.
        self.check("v", "v=<Mock name='mock.dumps()' id='xxx'>")
        self.check("type(v)", "type(v)=<class 'unittest.mock.Mock'>")
        self.check(
            "json.dumps()", "json.dumps()=<Mock name='mock.dumps()' id='xxx'>"
        )
        self.assertTrue(isinstance(json.dumps, umock.Mock))
        self.assertNotEqual(id(v), id(json.dumps))

    def test_assert1(self) -> None:
        """
        Check what function was called.
        """
        json = umock.Mock()
        json.loads("hello")
        # Check that the mocked function was called as expected.
        json.loads.assert_called()
        json.loads.assert_called_once()
        json.loads.assert_called_with("hello")
        self.assertEqual(json.loads.call_count, 1)

    def test_str1(self) -> None:
        mock = umock.Mock()
        # Calling `str()` on a mock creates a mock on the fly.
        self.check("str(mock)", "str(mock)=\"<Mock id='xxx'>\"")
        # Assign a mocked function returning "hello" to mock.__str__.
        mock.__str__ = umock.Mock(return_value="hello")
        self.assertEqual(str(mock), "hello")
        # One can't assign the return value, like one would do with a MagicMock.
        # mock.__str__.return_value = "hello"

    def test_spec1(self) -> None:
        # Create a Mock based on the class `_Class`.
        mock = umock.Mock(spec=_Class)
        #
        self.assertTrue(isinstance(mock, _Class))
        mock.get_a = umock.Mock(return_value=3)
        self.assertEqual(mock.get_a(), 3)


# #############################################################################
# Test_MagicMock1
# #############################################################################


class Test_MagicMock1(_TestCase):
    """
    A `MagicMock` is a subclass of `Mock` with some magic methods already
    created.
    """

    def test_get1(self) -> None:
        """
        Assign a MagicMock using array notation.
        """
        mock = umock.MagicMock()
        # MagicMock automatically infer `__get_item__()`.
        mock[3] = "fish"
        # Check.
        mock.__setitem__.assert_called_with(3, "fish")

    def test_get2(self) -> None:
        mock = umock.MagicMock()
        mock.__getitem__.return_value = "result"

    def test_str1(self) -> None:
        """
        Mock `str()` method.
        """
        mock = umock.MagicMock()
        # Mock `str()`.
        mock.__str__.return_value = "foobar"
        # Check.
        self.assertEqual(str(mock), "foobar")
        mock.__str__.assert_called_with()


# #############################################################################
# Test_Mock_Class1
# #############################################################################


class Test_Mock_Class1(_TestCase):
    def test_without_mock1(self) -> None:
        obj = _Class()
        self.assertEqual(obj.get_a(), 3)
        self.assertEqual(obj.get_b(), 14)

    def test_with_mock1(self) -> None:
        obj = _Class()
        # Mock method `get_a()`.
        obj.get_a = umock.MagicMock(return_value=4)
        # Check.
        self.assertEqual(obj.get_a(), 4)
        obj.get_a.assert_called()

    def test_with_mock2(self) -> None:
        obj = _Class()
        # Mock method `get_a()`.
        obj.get_a = umock.MagicMock(side_effect=KeyError("foo"))
        # Check.
        with self.assertRaises(KeyError) as cm:
            obj.get_a()
        #
        act = str(cm.exception)
        exp = "'foo'"
        self.assert_equal(act, exp)
        obj.get_a.assert_called()


# #############################################################################
# Test_Mock_Class_with_decorator1
# #############################################################################

# `umock.patch()`
# - replaces classes in a particular module with a Mock object
# - by default creates a MagicMock

# `umock.patch.object(target, attribute)` patches the named member "attribute"
# on the object "target" with a mock object.


class Test_Mock_Class_with_decorator1(_TestCase):
    @umock.patch.object(_Class, "get_a", return_value=4)
    def test1(self, mock_method: umock.MagicMock) -> None:
        """
        Patch method of an object using a decorator.
        """
        obj = _Class()
        # Check.
        # self.assertIs(mock_method, umock.MagicMock)
        self.check("mock_method", "mock_method=<MagicMock name='get_a' id='xxx'>")
        self.assertEqual(obj.get_a(), 4)
        mock_method.assert_called()
        obj.get_a.assert_called()


# #############################################################################
# Test_Mock_Class_with_context_manager1
# #############################################################################


class Test_Mock_Class_with_context_manager1(_TestCase):
    def test1(self) -> None:
        """
        Patch an object method using a context manager.
        """
        # Inside the context manager, the method is mocked.
        with umock.patch.object(_Class, "get_a", return_value=4):
            obj = _Class()
            # Check.
            self.check("obj.get_a", "obj.get_a=<MagicMock name='get_a' id='xxx'>")
            self.assertEqual(obj.get_a(), 4)
            obj.get_a.assert_called()
        # Outside the context manager everything is normal.
        obj = _Class()
        # Check.
        self.check(
            "obj.get_a",
            "obj.get_a=<bound method _Class.get_a of <helpers.test.test_unit_test_mock._Class object at 0x>>",
        )
        self.assertEqual(obj.get_a(), 3)

    def test_dict1(self) -> None:
        """
        Patch a dictionary.
        """
        foo = {"key": "value"}
        with umock.patch.dict(foo, {"key": "new_value"}, clear=True):
            self.assertEqual(foo["key"], "new_value")
        # Outside the context manager everything is normal.
        self.assertEqual(foo["key"], "value")
