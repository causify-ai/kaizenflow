import datetime
import logging
import os
import pytest
from typing import Any, Optional

import pandas as pd

import core.config as cconfig
import helpers.hio as hio
import helpers.hplayback as hplayba
import helpers.hsystem as hsystem
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


# #############################################################################
# TestJsonRoundtrip1
# #############################################################################


class TestJsonRoundtrip1(hunitest.TestCase):
    """
    Test roundtrip conversion through jsonpickle for different types.
    """

    def test1(self) -> None:
        obj = 3
        #
        hplayba.round_trip_convert(obj, logging.DEBUG)

    def test2(self) -> None:
        obj = "hello"
        #
        hplayba.round_trip_convert(obj, logging.DEBUG)

    def test3(self) -> None:
        data = {
            "Product": ["Desktop Computer", "Tablet", "iPhone", "Laptop"],
            "Price": [700, 250, 800, 1200],
        }
        df = pd.DataFrame(data, columns=["Product", "Price"])
        df.index.name = "hello"
        #
        obj = df
        hplayba.round_trip_convert(obj, logging.DEBUG)

    def test4(self) -> None:
        obj = datetime.date(2015, 1, 1)
        #
        hplayba.round_trip_convert(obj, logging.DEBUG)


# #############################################################################
# TestPlaybackInputOutput1
# #############################################################################


class TestPlaybackInputOutput1(hunitest.TestCase):
    """
    Freeze the output of Playback.
    """

    def helper(self, mode: str, *args: Any, **kwargs: Any) -> None:

        # TODO(gp): Factor out the common code.
        # Define a function to generate a unit test for.
        def get_result_assert_equal(a: Any, b: Any) -> Any:
            p = hplayba.Playback("assert_equal")
            if isinstance(a, datetime.date) and isinstance(b, datetime.date):
                return p.run(abs(a - b))
            if isinstance(a, dict) and isinstance(b, dict):
                c = {}
                c.update(a)
                c.update(b)
                return p.run(c)
            if isinstance(a, cconfig.Config) and isinstance(b, cconfig.Config):
                c = cconfig.Config(update_mode="overwrite")
                c.update(a)
                c.update(b)
                return p.run(c)
            return p.run(a + b)

        def get_result_check_string(a: Any, b: Any) -> Any:
            p = hplayba.Playback("check_string")
            if isinstance(a, datetime.date) and isinstance(b, datetime.date):
                return p.run(abs(a - b))
            if isinstance(a, dict) and isinstance(b, dict):
                c = {}
                c.update(a)
                c.update(b)
                return p.run(c)
            if isinstance(a, cconfig.Config) and isinstance(b, cconfig.Config):
                c = cconfig.Config(update_mode="overwrite")
                c.update(a)
                c.update(b)
                return p.run(c)
            return p.run(a + b)

        def get_result_assert_equal_none() -> Any:
            p = hplayba.Playback("assert_equal")
            return p.run("Some string.")

        def get_result_check_string_none() -> Any:
            p = hplayba.Playback("check_string")
            return p.run("Some string")

        if mode == "assert_equal":
            if not args and not kwargs:
                code = get_result_assert_equal_none()
            else:
                code = get_result_assert_equal(*args, **kwargs)
        elif mode == "check_string":
            if not args and not kwargs:
                code = get_result_check_string_none()
            else:
                code = get_result_check_string(*args, **kwargs)
        else:
            raise ValueError("Invalid mode ")
        self.check_string(code, purify_text=True)
        _LOG.debug("Testing code:\n%s", code)
        exec(code, locals())  # pylint: disable=exec-used

    def test1(self) -> None:
        """
        Test for int inputs.
        """
        # Create inputs.
        a = 3
        b = 2
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test2(self) -> None:
        """
        Test for string inputs.
        """
        # Create inputs.
        a = "test"
        b = "case"
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test3(self) -> None:
        """
        Test for list inputs.
        """
        # Create inputs.
        a = [1, 2, 3]
        b = [4, 5, 6]
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test4(self) -> None:
        """
        Test for dict inputs.
        """
        # Create inputs.
        a = {"1": 2}
        b = {"3": 4}
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test5(self) -> None:
        """
        Test for pd.DataFrame inputs.
        """
        # Create inputs.
        a = pd.DataFrame({"Price": [700, 250, 800, 1200]})
        b = pd.DataFrame({"Price": [1, 1, 1, 1]})
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test6(self) -> None:
        """
        Test for datetime.date inputs (using `jsonpickle`).
        """
        # Create inputs.
        a = datetime.date(2015, 1, 1)
        b = datetime.date(2012, 1, 1)
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test7(self) -> None:
        """
        Test for int inputs with check_string.
        """
        # Create inputs.
        a = 3
        b = 2
        # Generate, freeze and execute a unit test.
        self.helper("check_string", a=a, b=b)

    def test8(self) -> None:
        """
        Test for string inputs with check_string.
        """
        # Create inputs.
        a = "test"
        b = "case"
        # Generate, freeze and execute a unit test.
        self.helper("check_string", a=a, b=b)

    def test9(self) -> None:
        """
        Test for list inputs with check_string.
        """
        # Create inputs.
        a = [1, 2, 3]
        b = [4, 5, 6]
        # Generate, freeze and execute a unit test.
        self.helper("check_string", a=a, b=b)

    def test10(self) -> None:
        """
        Test for dict inputs with check_string.
        """
        # Create inputs.
        a = {"1": 2}
        b = {"3": 4}
        # Generate, freeze and execute a unit test.
        self.helper("check_string", a=a, b=b)

    def test11(self) -> None:
        """
        Test for pd.DataFrame inputs with check_string.
        """
        # Create inputs.
        a = pd.DataFrame({"Price": [700, 250, 800, 1200]})
        b = pd.DataFrame({"Price": [1, 1, 1, 1]})
        # Generate, freeze and execute a unit test.
        self.helper("check_string", a=a, b=b)

    def test12(self) -> None:
        """
        Test for dict inputs with data structures recursion.
        """
        # Create inputs.
        a = {"1": ["a", 2]}
        b = {"3": pd.DataFrame({"Price": [700, 250, 800, 1200]}), "4": {"5": 6}}
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test13(self) -> None:
        """
        Test for pd.Series inputs with check_string.
        """
        # Create inputs.
        a = pd.Series([10, 20, 15], name="N Numbers")
        b = pd.Series([10.0, 0.0, 5.5], name="Z Numbers")
        # Generate, freeze and execute a unit test.
        self.helper("check_string", a=a, b=b)

    def test14(self) -> None:
        """
        Test for pd.Series inputs with assert_equal.
        """
        # Create inputs.
        a = pd.Series([10, 20, 15], name="N Numbers")
        b = pd.Series([10.0, 0.0, 5.5], name="Z Numbers")
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test15(self) -> None:
        """
        Test for cconfig.Config inputs with check_string.
        """
        # Create inputs.
        a = cconfig.Config([("meta", "meta value 1"), ("list", [1, 2])])
        b = cconfig.Config([("meta", "meta value 2")])
        # Generate, freeze and execute a unit test.
        self.helper("check_string", a=a, b=b)

    def test16(self) -> None:
        """
        Test for cconfig.Config inputs with assert_equal.
        """
        # Create inputs.
        a = cconfig.Config([("meta", "meta value 1"), ("list", [1, 2])])
        b = cconfig.Config([("meta", "meta value 2")])
        # Generate, freeze and execute a unit test.
        self.helper("assert_equal", a=a, b=b)

    def test17(self) -> None:
        """
        Test if testing function has no args with check_string.
        """
        self.helper("check_string")

    def test18(self) -> None:
        """
        Test if testing function has no args with assert_equal.
        """
        self.helper("assert_equal")


# #############################################################################
# TestToPythonCode1
# #############################################################################


class TestToPythonCode1(hunitest.TestCase):
    """
    Test to_python_code() for different types.
    """

    def test_float1(self) -> None:
        """
        Test float without first zero.
        """
        self._check(0.1, "0.1")

    def test_float2(self) -> None:
        """
        Test positive float.
        """
        self._check(1.0, "1.0")

    def test_float3(self) -> None:
        """
        Test negative float.
        """
        self._check(-1.1, "-1.1")

    def test_int1(self) -> None:
        """
        Test zero.
        """
        self._check(0, "0")

    def test_int2(self) -> None:
        """
        Test positive int.
        """
        self._check(10, "10")

    def test_int3(self) -> None:
        """
        Test negative int.
        """
        self._check(-10, "-10")

    def test_str1(self) -> None:
        """
        Test str simple.
        """
        self._check("a", '"a"')

    def test_str2(self) -> None:
        """
        Test str with double quotes.
        """
        self._check('"b"', '"\\"b\\""')

    def test_str3(self) -> None:
        """
        Test str with single quotes.
        """
        self._check("'c'", "\"'c'\"")

    def test_list1(self) -> None:
        """
        Test List.
        """
        self._check([1, 0.2, "3"], '[1, 0.2, "3"]')

    def test_dict1(self) -> None:
        """
        Test Dist.
        """
        self._check({"a": 0.2, 3: "b"}, '{"a": 0.2, 3: "b"}')

    def test_df1(self) -> None:
        """
        Test pd.DataFrame (single quotes expected in field names)
        """
        self._check(
            pd.DataFrame.from_dict({"a": [0.2, 0.1]}),
            "pd.DataFrame.from_dict({'a': [0.2, 0.1]})",
        )

    def test_dataseries1(self) -> None:
        """
        Test pd.Series.
        """
        self._check(
            pd.Series([0.2, 0.1], name="a"),
            "pd.Series(data=[0.2, 0.1], index=RangeIndex(start=0, stop=2, step=1), "
            'name="a", dtype=float64)',
        )

    def test_config1(self) -> None:
        """
        Test cconfig.Config.
        """
        config = cconfig.Config()
        config["var1"] = "val1"
        config["var2"] = cconfig.Config([("var3", 10), ("var4", "val4")])
        self._check(
            config,
            "cconfig.Config.from_python(\"Config([('var1', 'val1'), "
            "('var2', Config([('var3', 10), ('var4', 'val4')]))])\")",
        )

    def _check(self, input_obj: Any, expected: str) -> None:
        res = hplayba.to_python_code(input_obj)
        self.assert_equal(res, expected)


# #############################################################################
# TestPlaybackFilePath1
# #############################################################################


class TestPlaybackFilePath1(hunitest.TestCase):
    """
    Test file mode correctness.
    """

    def test1(self) -> None:
        """
        Test writing to file when number of tests is more than generated (10).
        """
        test_file = hplayba.Playback._get_test_file_name("./path/to/somewhere.py")
        self.assert_equal(
            test_file, "./path/to/test/test_by_playback_somewhere.py"
        )


# #############################################################################
# TestPlaybackFileMode1
# #############################################################################


class TestPlaybackFileMode1(hunitest.TestCase):
    """
    Test file mode correctness.
    """

    def get_code(self, max_tests: Optional[int] = None) -> str:
        """
        Return a code for executable file to run.
        """
        max_tests_str = "" if max_tests is None else f", max_tests={max_tests}"
        code = (
            "\n".join(
                [
                    "import helpers.hplayback as hplayba",
                    "def plbck_sum(a: int, b: int) -> int:",
                    '    hplayba.Playback("check_string", to_file=True%s).run(None)',
                    "    return a + b",
                    "",
                    "[plbck_sum(i, i + 1) for i in range(4)]",
                ]
            )
            % max_tests_str
        )
        return code

    def helper(self, max_tests: Optional[int] = None) -> Any:
        """
        Return generated by playback code.
        """
        # Get file paths.
        tmp_dir = self.get_scratch_space()
        # File with code.
        code_basename = "code_.py"
        tmp_py_file = os.path.join(tmp_dir, code_basename)
        # File with test.
        tmp_test_file = os.path.join(
            tmp_dir, "test", "test_by_playback_" + code_basename
        )
        # Save the code to the file.
        hio.to_file(tmp_py_file, self.get_code(max_tests))
        # Executes the code.
        hsystem.system(f"python {tmp_py_file}")
        playback_code = hio.from_file(tmp_test_file)
        return playback_code

    @pytest.mark.requires_ck_infra
    def test1(self) -> None:
        """
        Test writing to file when number of tests is more than generated.
        """
        max_tests = 100
        self.check_string(self.helper(max_tests))

    @pytest.mark.requires_ck_infra
    def test2(self) -> None:
        """
        Test writing to file when number of tests is default.
        """
        self.check_string(self.helper())

    @pytest.mark.requires_ck_infra
    def test3(self) -> None:
        """
        Test writing to file when number of tests is lower than generated.
        """
        max_tests = 2
        self.check_string(self.helper(max_tests))
