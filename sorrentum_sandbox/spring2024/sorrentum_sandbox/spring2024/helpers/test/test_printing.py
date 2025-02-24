import logging
import pprint

import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_printing1(hunitest.TestCase):

    def test_color_highlight1(self) -> None:
        for c in hprint._COLOR_MAP:
            _LOG.debug(hprint.color_highlight(c, c))


# #############################################################################


class Test_to_str1(hunitest.TestCase):

    def test1(self) -> None:
        x = 1
        # To disable linter complaints.
        _ = x
        act = hprint.to_str("x")
        exp = "x=1"
        self.assertEqual(act, exp)

    def test2(self) -> None:
        x = "hello world"
        # To disable linter complaints.
        _ = x
        act = hprint.to_str("x")
        exp = "x='hello world'"
        self.assertEqual(act, exp)

    def test3(self) -> None:
        x = 2
        # To disable linter complaints.
        _ = x
        act = hprint.to_str("x*2")
        exp = "x*2=4"
        self.assertEqual(act, exp)

    def test4(self) -> None:
        """
        Test printing multiple values separated by space.
        """
        x = 1
        y = "hello"
        # To disable linter complaints.
        _ = x, y
        act = hprint.to_str("x y")
        exp = "x=1, y='hello'"
        self.assertEqual(act, exp)

    def test5(self) -> None:
        """
        Test printing multiple strings separated by space.
        """
        x = "1"
        y = "hello"
        # To disable linter complaints.
        _ = x, y
        act = hprint.to_str("x y")
        exp = "x='1', y='hello'"
        self.assertEqual(act, exp)

    def test6(self) -> None:
        """
        Test printing a list.
        """
        x = [1, "hello", "world"]
        # To disable linter complaints.
        _ = x
        act = hprint.to_str("x")
        exp = "x=[1, 'hello', 'world']"
        self.assertEqual(act, exp)


class Test_to_str2(hunitest.TestCase):

    def test1(self) -> None:
        """
        Test printing arguments that are declared on the different than
        function call line.
        """
        x = [1, "hello", "world"]
        y = "Hello"
        z = "world"
        # fmt: off
        act = hprint.to_str2(
            x, y, z
        )
        # fmt: off
        exp = "x=[1, 'hello', 'world'], y=Hello, z=world"
        self.assert_equal(act, exp)

    def test2(self) -> None:
        """
        Test printing arguments which are declared on the different lines.
        """
        x = [1, "hello", "world"]
        y = "Hello"
        z = "world"
        # fmt: off
        act = hprint.to_str2(x,
                             y,
                             z)
        # fmt: on
        exp = "x=[1, 'hello', 'world'], y=Hello, z=world"
        self.assert_equal(act, exp)

    def test3(self) -> None:
        """
        Test printing arguments from a function called from line which contains
        call of another function.
        """

        def string_wrapper(line: str) -> str:
            return line

        x = [1, "hello", "world"]
        y = "Hello"
        z = "world"
        act = string_wrapper(hprint.to_str2(x, y, z))
        exp = "x=[1, 'hello', 'world'], y=Hello, z=world"
        self.assert_equal(act, exp)


# #############################################################################


class Test_log(hunitest.TestCase):

    def test2(self) -> None:
        x = 1
        # To disable linter complaints.
        _ = x
        for verb in [logging.DEBUG, logging.INFO]:
            hprint.log(_LOG, verb, "x")

    def test3(self) -> None:
        x = 1
        y = "hello"
        # To disable linter complaints.
        _ = x, y
        for verb in [logging.DEBUG, logging.INFO]:
            hprint.log(_LOG, verb, "x y")

    def test4(self) -> None:
        """
        The command:

        > pytest -k Test_log::test4  -o log_cli=true --dbg_verbosity DEBUG

        should print something like:

        DEBUG    test_printing:printing.py:315 x=1, y='hello', z=['cruel', 'world']
        INFO     test_printing:printing.py:315 x=1, y='hello', z=['cruel', 'world']
        """
        x = 1
        y = "hello"
        z = ["cruel", "world"]
        # To disable linter complaints.
        _ = x, y, z
        for verb in [logging.DEBUG, logging.INFO]:
            hprint.log(_LOG, verb, "x y z")


# #############################################################################


class Test_sort_dictionary(hunitest.TestCase):

    def test1(self) -> None:
        dict_ = {
            "tool": {
                "poetry": {
                    "name": "lm",
                    "version": "0.1.0",
                    "description": "",
                    "authors": [""],
                    "dependencies": {
                        "awscli": "*",
                        "boto3": "*",
                        "flaky": "*",
                        "fsspec": "*",
                        "gluonts": "*",
                        "invoke": "*",
                        "jupyter": "*",
                        "matplotlib": "*",
                        "mxnet": "*",
                        "networkx": "*",
                        "pandas": "^1.1.0",
                        "psycopg2": "*",
                        "pyarrow": "*",
                        "pytest": "^6.0.0",
                        "pytest-cov": "*",
                        "pytest-instafail": "*",
                        "pytest-xdist": "*",
                        "python": "^3.7",
                        "pywavelets": "*",
                        "s3fs": "*",
                        "seaborn": "*",
                        "sklearn": "*",
                        "statsmodels": "*",
                        "bs4": "*",
                        "jsonpickle": "*",
                        "lxml": "*",
                        "tqdm": "*",
                        "requests": "*",
                    },
                    "dev-dependencies": {},
                }
            },
            "build-system": {
                "requires": ["poetry>=0.12"],
                "build-backend": "poetry.masonry.api",
            },
        }
        act = hprint.sort_dictionary(dict_)
        self.check_string(pprint.pformat(act))


# #############################################################################


class Test_indent1(hunitest.TestCase):

    def test1(self) -> None:
        txt = """foo

class TestHelloWorld(hunitest.TestCase):
    bar
"""
        num_spaces = 2
        act = hprint.indent(txt, num_spaces=num_spaces)
        exp = """  foo

  class TestHelloWorld(hunitest.TestCase):
      bar
"""
        self.assert_equal(act, exp, fuzzy_match=False)


# #############################################################################


class Test_dedent1(hunitest.TestCase):

    def test1(self) -> None:
        txt = """
        foo

        class TestHelloWorld(hunitest.TestCase):
            bar
"""
        act = hprint.dedent(txt)
        exp = """foo

class TestHelloWorld(hunitest.TestCase):
    bar"""
        self.assert_equal(act, exp, fuzzy_match=False)

    def test2(self) -> None:
        txt = r"""
        read_data:
          file_name: foo_bar.txt
          nrows: 999
        single_val: hello
        zscore:
          style: gaz
          com: 28"""
        act = hprint.dedent(txt)
        exp = """read_data:
  file_name: foo_bar.txt
  nrows: 999
single_val: hello
zscore:
  style: gaz
  com: 28"""
        self.assert_equal(act, exp, fuzzy_match=False)

    def test_roundtrip1(self) -> None:
        """
        Verify that `indent` and `dedent` are inverse of each other.
        """
        txt1 = """foo

class TestHelloWorld(hunitest.TestCase):
    bar"""
        num_spaces = 3
        txt2 = hprint.indent(txt1, num_spaces=num_spaces)
        txt3 = hprint.dedent(txt2)
        self.assert_equal(txt1, txt3, fuzzy_match=False)


# #############################################################################


class Test_align_on_left1(hunitest.TestCase):

    def test1(self) -> None:
        txt = """foo

class TestHelloWorld(hunitest.TestCase):
    bar
"""
        act = hprint.align_on_left(txt)
        exp = """foo

class TestHelloWorld(hunitest.TestCase):
bar
"""
        self.assert_equal(act, exp, fuzzy_match=False)


# #############################################################################


class Test_logging1(hunitest.TestCase):

    def test_log_frame1(self) -> None:
        hprint.log_frame(_LOG, "%s %s", "hello", "world")

    def test_log_frame2(self) -> None:
        hprint.log_frame(_LOG, "%s", "hello", level=1)

    def test_log_frame3(self) -> None:
        hprint.log_frame(_LOG, "%s", "hello", level=2, verbosity=logging.INFO)
