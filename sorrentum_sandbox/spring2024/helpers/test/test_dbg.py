import collections
import logging
from typing import List, Tuple

import helpers.hdbg as hdbg
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)

# TODO(gp): Make sure the coverage is 100%.

# #############################################################################


# TODO(gp): Use a self.assert_equal() instead of a check_string() since this
#  code needs to be stable.
class Test_dassert1(hunitest.TestCase):
    """
    Test `dassert()`.
    """

    def test1(self) -> None:
        """
        An assertion that is verified.
        """
        hdbg.dassert(True)

    def test2(self) -> None:
        """
        An assertion that is not verified.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert(False)
        self.check_string(str(cm.exception))

    def test3(self) -> None:
        """
        An assertion with a message.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert(False, msg="hello")
        self.check_string(str(cm.exception))

    def test4(self) -> None:
        """
        An assertion with a message to format.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert(False, "hello %s", "world")
        self.check_string(str(cm.exception))

    def test5(self) -> None:
        """
        Too many parameters.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert(False, "hello %s", "world", "too_many")
        self.check_string(str(cm.exception))

    def test6(self) -> None:
        """
        Not enough parameters.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert(False, "hello %s")
        self.check_string(str(cm.exception))

    def test7(self) -> None:
        """
        Common error of calling `dassert()` instead of `dassert_eq()`.

        According to the user's intention the assertion should trigger,
        but, because of using `dassert()` instead of `dassert_eq()`, the
        assertion will not trigger. We notice that the user passed a
        list instead of a string as `msg` and raise.
        """
        with self.assertRaises(AssertionError) as cm:
            y = ["world"]
            hdbg.dassert(y, ["hello"])
        self.check_string(str(cm.exception))


# #############################################################################


class Test_dassert_eq1(hunitest.TestCase):
    def test1(self) -> None:
        hdbg.dassert_eq(1, 1)

    def test2(self) -> None:
        hdbg.dassert_eq(1, 1, msg="hello world")

    def test3(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_eq(1, 2, msg="hello world")
        self.check_string(str(cm.exception))

    def test4(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_eq(1, 2, "hello %s", "world")
        self.check_string(str(cm.exception))

    def test5(self) -> None:
        """
        Raise assertion with incorrect message.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_eq(1, 2, "hello %s")
        self.check_string(str(cm.exception))


# #############################################################################


# TODO(gp): Break it in piece.
class Test_dassert_misc1(hunitest.TestCase):

    # dassert_in

    def test_in1(self) -> None:
        hdbg.dassert_in("a", "abc")

    def test_in2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_in("a", "xyz".split())
        self.check_string(str(cm.exception))

    # dassert_is

    def test_is1(self) -> None:
        a = None
        hdbg.dassert_is(a, None)

    def test_is2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_is("a", None)
        self.check_string(str(cm.exception))

    # dassert_isinstance

    def test_is_instance1(self) -> None:
        hdbg.dassert_isinstance("a", str)

    def test_is_instance2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_isinstance("a", int)
        self.check_string(str(cm.exception))

    def test_is_instance3(self) -> None:
        hdbg.dassert_isinstance("a", (str, int))

    def test_is_instance4(self) -> None:
        hdbg.dassert_isinstance(5.0, (float, int))

    def test_is_instance5(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_isinstance("a", (float, int))
        # TODO(gp): Replace all check_string with assert_equal
        self.check_string(str(cm.exception))

    # dassert_set_eq

    def test_set_eq1(self) -> None:
        a = [1, 2, 3]
        b = [2, 3, 1]
        hdbg.dassert_set_eq(a, b)

    def test_set_eq2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 3]
            b = [2, 2, 1]
            hdbg.dassert_set_eq(a, b)
        # Check.
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        val1 - val2=[3]
        val2 - val1=[]
        val1=[1, 2, 3]
        set eq
        val2=[1, 2]
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    # dassert_is_subset

    def test_is_subset1(self) -> None:
        a = [1, 2]
        b = [2, 1, 3]
        hdbg.dassert_is_subset(a, b)

    def test_is_subset2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 3]
            b = [4, 2, 1]
            hdbg.dassert_is_subset(a, b)
        # Check.
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        val1=[1, 2, 3]
        issubset
        val2=[1, 2, 4]
        val1 - val2=[3]
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    # dassert_not_intersection

    def test_not_intersection1(self) -> None:
        a = [1, 2, 3]
        b = [4, 5]
        hdbg.dassert_not_intersection(a, b)

    def test_not_intersection2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 3]
            b = [4, 2, 1]
            hdbg.dassert_not_intersection(a, b)
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        val1=[1, 2, 3]
        has no intersection
        val2=[1, 2, 4]
        val1.intersection(val2)=[1, 2]
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    # dassert_no_duplicates

    def test_no_duplicates1(self) -> None:
        a = [1, 2, 3]
        hdbg.dassert_no_duplicates(a)

    def test_no_duplicates2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 3, 3]
            hdbg.dassert_no_duplicates(a)
        self.check_string(str(cm.exception))

    # dassert_is_sorted

    def test_is_sorted1(self) -> None:
        a = [1, 2, 3]
        hdbg.dassert_is_sorted(a)

    def test_is_sorted2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 4, 3]
            hdbg.dassert_is_sorted(a)
        self.check_string(str(cm.exception))

    def test_is_sorted3(self) -> None:
        """
        Test an array that is sorted descending.
        """
        a = [3, 2, 2]
        hdbg.dassert_is_sorted(a, sort_kwargs={"reverse": True})

    def test_is_sorted4(self) -> None:
        """
        Test an array that is not sorted descending.
        """
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 4, 3]
            sort_kwargs = {"reverse": True}
            hdbg.dassert_is_sorted(a, sort_kwargs=sort_kwargs)
        self.check_string(str(cm.exception))

    # dassert_eq_all

    def test_eq_all1(self) -> None:
        a = [1, 2, 3]
        b = [1, 2, 3]
        hdbg.dassert_eq_all(a, b)

    def test_eq_all2(self) -> None:
        with self.assertRaises(AssertionError) as cm:
            a = [1, 2, 3]
            b = [1, 2, 4]
            hdbg.dassert_eq_all(a, b)
        self.check_string(str(cm.exception))


# #############################################################################


class Test_dassert_lgt1(hunitest.TestCase):
    def test1(self) -> None:
        """
        No assertion raised since `0 <= 0 <= 3`.
        """
        hdbg.dassert_lgt(
            0, 0, 3, lower_bound_closed=True, upper_bound_closed=True
        )

    def test2(self) -> None:
        """
        Raise assertion since it is not true that `0 < 0 <= 3`.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_lgt(
                0, 0, 3, lower_bound_closed=False, upper_bound_closed=True
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        0 < 0
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test3(self) -> None:
        """
        Raise assertion since it is not true that `0 < 100 <= 3`.

        The formatting of the assertion is correct.
        """
        with self.assertRaises(AssertionError) as cm:
            lower_bound_closed = False
            upper_bound_closed = True
            hdbg.dassert_lgt(
                0,
                100,
                3,
                lower_bound_closed,
                upper_bound_closed,
                "hello %s",
                "world",
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        100 <= 3
        hello world
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


class Test_dassert_is_proportion1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Passing assertion with correct message and format.
        """
        hdbg.dassert_is_proportion(0.1, "hello %s", "world")

    def test2(self) -> None:
        """
        Passing assertion with correct message and format.
        """
        hdbg.dassert_is_proportion(0.0, "hello %s", "world")

    def test3(self) -> None:
        """
        Passing assertion with correct message and format.
        """
        hdbg.dassert_is_proportion(1.0, "hello %s", "world")

    def test_assert1(self) -> None:
        """
        Failing assertion with correct message and format.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_is_proportion(1.01, "hello %s", "world")
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        1.01 <= 1
        hello world
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert2(self) -> None:
        """
        Failing assertion with correct message.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_is_proportion(1.01, "hello world")
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        1.01 <= 1
        hello world
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert3(self) -> None:
        """
        Failing assertion with incorrect message formatting.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_is_proportion(1.01, "hello", "world")
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        1.01 <= 1
        Caught assertion while formatting message:
        'not all arguments converted during string formatting'
        hello world
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert4(self) -> None:
        """
        Failing assertion with incorrect message formatting.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_is_proportion(1.01, "hello %s %s", "world")
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        1.01 <= 1
        Caught assertion while formatting message:
        'not enough arguments for format string'
        hello %s %s world
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


class Test_dassert_container_type1(hunitest.TestCase):
    def test1(self) -> None:
        list_ = "a b c".split()
        hdbg.dassert_container_type(list_, List, str)

    def test_assert1(self) -> None:
        """
        Check that assertion fails since a list is not a tuple.
        """
        list_ = "a b c".split()
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_container_type(list_, Tuple, str)
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        Instance of '['a', 'b', 'c']' is '<class 'list'>' instead of 'typing.Tuple'
        obj='['a', 'b', 'c']'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert2(self) -> None:
        """
        Check that assertion fails since a list contains strings and ints.
        """
        list_ = ["a", 2, "c", "d"]
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_container_type(list_, list, str)
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        Instance of '2' is '<class 'int'>' instead of '<class 'str'>'
        obj='['a', 2, 'c', 'd']'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test_assert3(self) -> None:
        """
        Like `test_assert3()` but with a message.
        """
        list_ = ["a", 2, "c", "d"]
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_container_type(
                list_, list, str, "list_ is %s homogeneous", "not"
            )
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        Instance of '2' is '<class 'int'>' instead of '<class 'str'>'
        list_ is not homogeneous
        obj='['a', 2, 'c', 'd']'
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


class _Animal:
    pass


class _Man(_Animal):
    pass


class _Vegetable:
    pass


class Test_dassert_issubclass1(hunitest.TestCase):
    def test_man1(self) -> None:
        """
        An instance of `_Man` descends from `_Animal`.
        """
        man = _Man()
        hdbg.dassert_issubclass(man, _Man)

    def test_man2(self) -> None:
        """
        An instance of `_Man` descends from object.
        """
        man = _Man()
        hdbg.dassert_issubclass(man, object)

    def test_man_fail1(self) -> None:
        """
        An instance of `_Man` doesn't descends from `_Vegetable`.
        """
        man = _Man()
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_issubclass(man, _Vegetable)
        # We need to purify from object references.
        self.check_string(str(cm.exception), purify_text=True)

    def test_man_fail2(self) -> None:
        """
        An instance of `_Man` doesn't descends from `int`.
        """
        man = _Man()
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_issubclass(man, int)
        self.check_string(str(cm.exception), purify_text=True)

    def test1(self) -> None:
        """
        In Python everything is an object.
        """
        hdbg.dassert_issubclass(5, object)
        hdbg.dassert_issubclass(int, object)
        hdbg.dassert_issubclass(int, (object, int))

    def test_fail1(self) -> None:
        """
        `issubclass` only accepts classes and not instances as second argument.
        """
        with self.assertRaises(Exception) as cm:
            hdbg.dassert_issubclass(int, 5.0)
        self.check_string(str(cm.exception), purify_text=True)


# #############################################################################


class Test_dassert_callable1(hunitest.TestCase):
    def test1(self) -> None:
        func = lambda x: x
        hdbg.dassert_callable(func)

    def test_fail1(self) -> None:
        func = 4
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_callable(func)
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        Obj '4' of type '<class 'int'>' is not callable
        """
        self.assert_equal(act, exp, fuzzy_match=True)


# #############################################################################


class Test_dassert_all_defined_or_all_None(hunitest.TestCase):
    def test1(self) -> None:
        """
        Verify that test passes when all the values are defined.
        """
        vals = [1, 2, 3]
        hdbg.dassert_all_defined_or_all_None(vals)

    def test2(self) -> None:
        """
        Verify that assertion is raised when at least one of the values is not
        defined.
        """
        vals = [1, 2, None, None]
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_all_defined_or_all_None(vals)
        act = str(cm.exception)
        exp = r"""
        * Failed assertion *
        Some values in list are defined and some are None: '[1, 2, None, None]'
        """
        self.assert_equal(act, exp, fuzzy_match=True)

    def test3(self) -> None:
        """
        Verify that test passes when all the values are not defined.
        """
        vals = [None, None, None]
        hdbg.dassert_all_defined_or_all_None(vals)


# #############################################################################


class Test_dassert_related_params1(hunitest.TestCase):
    def test1(self) -> None:
        obj = {"val1": 1, "val2": 1, "val3": "hello"}
        mode = "all_or_none_non_null"
        hdbg.dassert_related_params(obj, mode, "message %s", "'hello world'")

    def test2(self) -> None:
        obj = {"val1": 0, "val2": None, "val3": ""}
        mode = "all_or_none_non_null"
        hdbg.dassert_related_params(obj, mode, "message %s", "'hello world'")

    def test3(self) -> None:
        obj = {"val1": 1, "val2": 0, "val3": "hello"}
        with self.assertRaises(Exception) as cm:
            mode = "all_or_none_non_null"
            hdbg.dassert_related_params(obj, mode, "message %s", "'hello world'")
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        All or none parameter should be non-null:
        val2=0
        params={'val1': 1, 'val2': 0, 'val3': 'hello'}
        message 'hello world'
        """
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)


# #############################################################################


class Test_dassert_related_params2(hunitest.TestCase):
    def test1(self) -> None:
        obj = {"val1": 1, "val2": 1, "val3": "hello"}
        mode = "all_or_none_non_None"
        hdbg.dassert_related_params(obj, mode, "message %s", "'hello world'")

    def test2(self) -> None:
        obj = {
            "val1": None,
            "val2": None,
            "val3": None,
        }
        mode = "all_or_none_non_None"
        hdbg.dassert_related_params(obj, mode, "message %s", "'hello world'")

    def test3(self) -> None:
        obj = {"val1": None, "val2": None, "val3": "hello"}
        with self.assertRaises(Exception) as cm:
            mode = "all_or_none_non_None"
            hdbg.dassert_related_params(obj, mode, "message %s", "'hello world'")
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        All or none parameter should be non-None:
        val1=None
        params={'val1': None, 'val2': None, 'val3': 'hello'}
        message 'hello world'
        """
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)

# #############################################################################

class Test_dassert_all_attributes_are_same1(hunitest.TestCase):
    def test1(self) -> None:
        """
        Wrong type of object.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_all_attributes_are_same(5, "a")
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        Instance of '5' is '<class 'int'>' instead of '<class 'list'>'
        """
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)

    def test2(self) -> None:
        """
        Wrong type of attribute.
        """
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_all_attributes_are_same([1, 2, 3], 1)
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        Instance of '1' is '<class 'int'>' instead of '<class 'str'>'
        """
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)

    def test3(self) -> None:
        """
        Attribute with different values.
        """
        Obj = collections.namedtuple("Obj", ["a", "b"])
        list_ = [Obj(1, 2), Obj(1, 3)]
        with self.assertRaises(AssertionError) as cm:
            hdbg.dassert_all_attributes_are_same(list_, "b")
        act = str(cm.exception)
        exp = """
        * Failed assertion *
        Elements in the list have different values for
        attribute b:
        {2, 3}
        """
        self.assert_equal(act, exp, purify_text=True, fuzzy_match=True)

    def test4(self) -> None:
        """
        Attribute with same values.
        """
        Obj = collections.namedtuple("Obj", ["a", "b"])
        list_ = [Obj(1, 2), Obj(1, 2)]
        hdbg.dassert_all_attributes_are_same(list_, "b")
