import abc
import logging
from typing import Any, Callable, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hobject as hobject
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# Note that we can't derive this class from `hunitest.TestCase` otherwise the
# unit test framework will try to run the tests in this class.
class _Obj_to_str_TestCase(abc.ABC):
    """
    Test case for testing `obj_to_str()` and `obj_to_repr()`.
    """

    @abc.abstractmethod
    def get_object(self) -> Any:
        """
        Build object to test.
        """
        ...

    def helper(self, *, exp: Optional[str] = None, **kwargs: Any) -> None:
        obj = self.get_object()
        hdbg.dassert_is_not(obj, None)
        #
        txt: List[str] = []
        # Get `str()`.
        txt.append(hprint.frame("str:"))
        txt.append(hobject.obj_to_str(obj, **kwargs))
        # Get `repr()`.
        txt.append(hprint.frame("repr:"))
        txt.append(hobject.obj_to_repr(obj, **kwargs))
        # Concat.
        txt = "\n".join(txt)
        # Check.
        if exp is None:
            self.check_string(txt, purify_text=True)
        else:
            hdbg.dassert_isinstance(exp, str)
            self.assert_equal(txt, exp, purify_text=True, fuzzy_match=True)

    def test1(self, exp: str) -> None:
        """
        Use `__dict__` to extract the attributes.
        """
        self.helper(exp=exp, attr_mode="__dict__")

    def test2(self, exp: str) -> None:
        """
        Use `dir` to extract the attributes.
        """
        self.helper(exp=exp, attr_mode="dir")

    def test3(self, exp: str) -> None:
        """
        Use `__dict__` and print the type of the attributes.
        """
        self.helper(exp=exp, print_type=True)

    def test4(self) -> None:
        """
        Print only callable attributes.
        """
        self.helper(callable_mode="all")

    def test5(self) -> None:
        """
        Print only private attributes.
        """
        self.helper(private_mode="all")

    def test6(self) -> None:
        """
        Print only dunder attributes.
        """
        self.helper(dunder_mode="all")


# #############################################################################
# Test_obj_to_str1
# #############################################################################


class _Object1:
    """
    Object storing only scalar members and not other nested objects.
    """

    def __init__(self) -> None:
        self.a = False
        self.b = "hello"
        self.c = 3.14
        self._hello = "under"
        self.__hello = "double_dunder"
        self.hello = lambda x: x + 1


class Test_obj_to_str1(hunitest.TestCase, _Obj_to_str_TestCase):
    def get_object(self) -> Any:
        obj = _Object1()
        return obj

    def test1(self) -> None:
        exp = r"""
        ################################################################################
        str:
        ################################################################################
        _Object1 at 0x=(a=False, b=hello, c=3.14)
        ################################################################################
        repr:
        ################################################################################
        <helpers.test.test_hobject._Object1 at 0x>:
          a='False'
          b='hello'
          c='3.14'
        """
        super().test1(exp)

    def test2(self) -> None:
        exp = r"""
        ################################################################################
        str:
        ################################################################################
        _Object1 at 0x=(a=False, b=hello, c=3.14)
        ################################################################################
        repr:
        ################################################################################
        <helpers.test.test_hobject._Object1 at 0x>:
          a='False'
          b='hello'
          c='3.14'
        """
        super().test2(exp)

    def test3(self) -> None:
        exp = r"""
        ################################################################################
        str:
        ################################################################################
        _Object1 at 0x=(a=False <bool>, b=hello <str>, c=3.14 <float>)
        ################################################################################
        repr:
        ################################################################################
        <helpers.test.test_hobject._Object1 at 0x>:
          a='False' <bool>
          b='hello' <str>
          c='3.14' <float>
        """
        super().test3(exp)


# #############################################################################
# Test_obj_to_str2
# #############################################################################


class _Object2:
    """
    Object using a `obj_to_str()` as repr.
    """

    def __init__(self) -> None:
        self.x = True
        self.y = "world"
        self.z = 6.28
        self._hello = "under"
        self.__hello = "double_dunder"
        self.hello = lambda x: x + 1

    def __repr__(self) -> str:
        return hobject.obj_to_str(self)


class _Object3:
    """
    Object storing another object.
    """

    def __init__(self) -> None:
        self.p = "p"
        self.q = "q"
        self.object2 = _Object2()


class Test_obj_to_str2(hunitest.TestCase, _Obj_to_str_TestCase):
    def get_object(self) -> Any:
        obj = _Object3()
        return obj

    def test1(self) -> None:
        # TODO(gp): object2 in repr should be printed recursively as repr, but
        # it's not.
        exp = r"""
        ################################################################################
        str:
        ################################################################################
        _Object3 at 0x=(p=p, q=q, object2=_Object2 at 0x=(x=True, y=world, z=6.28))
        ################################################################################
        repr:
        ################################################################################
        <helpers.test.test_hobject._Object3 at 0x>:
          p='p'
          q='q'
          object2='_Object2 at 0x=(x=True, y=world, z=6.28)'
        """
        super().test1(exp)

    def test2(self) -> None:
        exp = r"""
        ################################################################################
        str:
        ################################################################################
        _Object3 at 0x=(object2=_Object2 at 0x=(x=True, y=world, z=6.28), p=p, q=q)
        ################################################################################
        repr:
        ################################################################################
        <helpers.test.test_hobject._Object3 at 0x>:
          object2='_Object2 at 0x=(x=True, y=world, z=6.28)'
          p='p'
          q='q'
        """
        super().test2(exp)

    def test3(self) -> None:
        exp = r"""
        ################################################################################
        str:
        ################################################################################
        _Object3 at 0x=(p=p <str>, q=q <str>, object2=_Object2 at 0x=(x=True, y=world, z=6.28) <helpers.test.test_hobject._Object2>)
        ################################################################################
        repr:
        ################################################################################
        <helpers.test.test_hobject._Object3 at 0x>:
          p='p' <str>
          q='q' <str>
          object2='_Object2 at 0x=(x=True, y=world, z=6.28)' <helpers.test.test_hobject._Object2>
        """
        super().test3(exp)


# #############################################################################
# Test_PrintableMixin_to_config_str
# #############################################################################


class _Abstract_ClassA(abc.ABC, hobject.PrintableMixin):
    """
    Abstract class descending from `PrintableMixin`.
    """

    def __init__(self) -> None:
        self._arg0 = 0
        self._arg1 = "one"
        self._arg2 = 2

    @staticmethod
    def get_config_attributes() -> List[str]:
        return ["_arg1", "_arg2"]


class _ClassB(hobject.PrintableMixin):
    """
    Class descending from `PrintableMixin`.
    """

    def __init__(self, get_wall_clock_time: Callable) -> None:
        self._arg5 = {"key1": "five", "key2": 5}
        self._arg6 = "abc"
        self._get_wall_clock_time = get_wall_clock_time

    @staticmethod
    def get_config_attributes() -> List[str]:
        return ["_arg5", "_get_wall_clock_time"]

    def get_wall_clock_time(self) -> pd.Timestamp:
        """
        Return wall clock time in the timezone specified in the ctor.

        Initially wall clock time can be in any timezone, but cannot be
        timezone-naive.
        """
        wall_clock_time = self._get_wall_clock_time()
        return wall_clock_time


class _ClassA(_Abstract_ClassA):
    """
    Class descending from `_AbstractClassA` and embedding `_ClassB`.
    """

    def __init__(self) -> None:
        super().__init__()
        self._arg3 = [3, 3, 3]
        get_wall_clock_time = lambda: pd.Timestamp(
            "2022-04-23", tz="America/New_York"
        )
        helper_class = _ClassB(get_wall_clock_time)
        self._arg4 = helper_class
        self._arg10 = {
            "key": 1,
            "get_wall_clock_time": helper_class.get_wall_clock_time,
        }

    def get_config_attributes(self) -> List[str]:
        config_attributes = super().get_config_attributes()
        child_class_attributes = ["_arg3", "_arg4", "_arg10"]
        config_attributes.extend(child_class_attributes)
        return config_attributes


class Test_PrintableMixin_to_config_str(hunitest.TestCase):
    def check_test_class_str(self, test_class: Any, exp: str) -> None:
        act = test_class.to_config_str()
        act = hunitest.purify_txt_from_client(act)
        self.assert_equal(act, exp, fuzzy_match=True)

    def test1(self) -> None:
        """
        Print `_Abstract_ClassA`.
        """
        test_class = _Abstract_ClassA()
        exp = r"""
        <helpers.test.test_hobject._Abstract_ClassA at 0x>:
            _arg1='one' <str>
            _arg2='2' <int>
        """
        self.check_test_class_str(test_class, exp)

    def test2(self) -> None:
        """
        Print `_ClassA`.
        """
        test_class = _ClassA()
        exp = r"""
        <helpers.test.test_hobject._ClassA at 0x>:
            _arg1='one' <str>
            _arg2='2' <int>
            _arg3='[3, 3, 3]' <list>
            _arg4=<helpers.test.test_hobject._ClassB at 0x>:
                _arg5='{'key1': 'five', 'key2': 5}' <dict>
                _get_wall_clock_time='<function _ClassA.__init__.<locals>.<lambda> at 0x>' <function>
            _arg10= <dict>
                {'get_wall_clock_time': <bound method _ClassB.get_wall_clock_time of <helpers.test.test_hobject._ClassB at 0x>:
                    _arg5='{'key1': 'five', 'key2': 5}' <dict>
                    _arg6='abc' <str>>,
                    'key': 1}
        """
        self.check_test_class_str(test_class, exp)
