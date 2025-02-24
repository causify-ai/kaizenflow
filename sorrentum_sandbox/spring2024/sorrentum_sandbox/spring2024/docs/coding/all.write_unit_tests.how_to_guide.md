

<!-- toc -->

- [Guidelines about writing unit tests](#guidelines-about-writing-unit-tests)
    + [**What is a unit test?**](#what-is-a-unit-test)
    + [**Why is unit testing important?**](#why-is-unit-testing-important)
  * [Unit testing tips](#unit-testing-tips)
    + [Tip #1: Test one thing](#tip-%231-test-one-thing)
    + [Tip #2: Keep tests self-contained](#tip-%232-keep-tests-self-contained)
    + [Tip #3: Only specify data related to what is being tested](#tip-%233-only-specify-data-related-to-what-is-being-tested)
    + [Tip #4: Test realistic corner cases](#tip-%234-test-realistic-corner-cases)
    + [Tip #5: Test a typical scenario](#tip-%235-test-a-typical-scenario)
    + [Tip #6: Test executable scripts end-to-end](#tip-%236-test-executable-scripts-end-to-end)
  * [Conventions](#conventions)
    + [Naming and placement conventions](#naming-and-placement-conventions)
    + [Our framework to test using input / output data](#our-framework-to-test-using-input--output-data)
    + [Use text and not pickle files as input](#use-text-and-not-pickle-files-as-input)
    + [`check_string` vs `self.assertEqual`](#check_string-vs-selfassertequal)
    + [Use `self.assert_equal`](#use-selfassert_equal)
    + [How to split unit test code in files](#how-to-split-unit-test-code-in-files)
    + [Skeleton for unit test](#skeleton-for-unit-test)
    + [Hierarchical `TestCase` approach](#hierarchical-testcase-approach)
    + [Use the appropriate `self.assert*`](#use-the-appropriate-selfassert)
    + [Do not use `hdbg.dassert`](#do-not-use-hdbgdassert)
    + [Interesting testing functions](#interesting-testing-functions)
    + [Use set_up_test / tear_down_test](#use-set_up_test--tear_down_test)
      - [Nested set_up_test / tear_down_test](#nested-set_up_test--tear_down_test)
    + [Use setUpClass / tearDownClass](#use-setupclass--teardownclass)
- [Update test tags](#update-test-tags)
- [Mocking](#mocking)
  * [Refs](#refs)
  * [Common usage samples](#common-usage-samples)
  * [Philosophy about mocking](#philosophy-about-mocking)
  * [Some general suggestions about testing](#some-general-suggestions-about-testing)
    + [Test from the outside-in](#test-from-the-outside-in)
    + [We don't need to test all the assertions](#we-dont-need-to-test-all-the-assertions)
    + [Use strings to compare output instead of data structures](#use-strings-to-compare-output-instead-of-data-structures)
    + [Use `self.check_string()` for things that we care about not changing (or are too big to have as strings in the code)](#use-selfcheck_string-for-things-that-we-care-about-not-changing-or-are-too-big-to-have-as-strings-in-the-code)
    + [Each test method should test a single test case](#each-test-method-should-test-a-single-test-case)
    + [Each test should be crystal clear on how it is different from the others](#each-test-should-be-crystal-clear-on-how-it-is-different-from-the-others)
    + [In general, you want to budget the time to write unit tests](#in-general-you-want-to-budget-the-time-to-write-unit-tests)
    + [Write a skeleton of unit tests and ask for a review if you are not sure how what to test](#write-a-skeleton-of-unit-tests-and-ask-for-a-review-if-you-are-not-sure-how-what-to-test)
  * [Object patch with return value](#object-patch-with-return-value)
  * [Path patch with multiple return values](#path-patch-with-multiple-return-values)
  * [Ways of calling `patch` and `patch.object`](#ways-of-calling-patch-and-patchobject)
  * [Mock object state after test run](#mock-object-state-after-test-run)
  * [Mock common external calls in `hunitest.TestCase` class](#mock-common-external-calls-in-hunitesttestcase-class)
  * [Mocks with specs](#mocks-with-specs)
  * [Caveats](#caveats)

<!-- tocstop -->

# Guidelines about writing unit tests

### **What is a unit test?**

- A unit test is a small, self-contained test of a public function or public
  method of a library
- The test specifies the given inputs, any necessary state, and the expected
  output
- Running the test ensures that the actual output agrees with the expected
  output

### **Why is unit testing important?**

- Unit testing is an integral part of Pragmatic programming approach
- Some of the tips that relate to it are:
  - Design with Contracts
  - Refactor Early, Refactor Often
  - Test Your Software, or Your Users Will
  - Coding Ain't Done Till All the Tests Run
  - Test State Coverage, Not Code Coverage
  - You Can't Write Perfect Software
  - Crash Early
  - Design to Test
  - Test Early. Test Often. Test Automatically.
  - Use Saboteurs to Test Your Testing
  - Find Bugs Once
- Good unit testing improves software quality. It does this in part by
  - Eliminating bugs (obvious)
  - Clarifying code design and interfaces ("Design to Test")
  - Making refactoring safer and easier ("Refactor Early, Refactor Often")
  - Documenting expected behavior and usage

## Unit testing tips

### Tip #1: Test one thing

- A good unit test tests only one thing
- Testing one thing keeps the unit test simple, relatively easy to understand,
  and helps isolate the root cause when the test fails
- How do we test more than one thing? By having more than one unit test!

### Tip #2: Keep tests self-contained

- A unit test should be independent of all other unit tests
- Each test should be self-sufficient
- Additionally, one should never assume that unit tests will be executed in a
  particular order
- A corollary of keeping tests self-contained is to keep all information needed
  to understand the test within the test itself
- In other words, when possible, avoid calling helper functions to load data or
  state to initialize the test; instead, specify the data explicitly in the test
  where it is used
  - This makes the test easier to understand and easier to debug when it fails
  - If multiple unit tests use or can use the same initialization data, do not
    hesitate repeating it in each test (or consider using parameterized testing)

### Tip #3: Only specify data related to what is being tested

- If a function that is being tested supports optional arguments, but those
  optional arguments are not needed for a particular unit test, then do not
  specify them in the test
- Specify the minimum of what is required to test what is being tested.

### Tip #4: Test realistic corner cases

- Can your function receive an empty list?
- Can it return an empty Series?
- What happens if it receives a numerical value outside of an expected range?
- How should the function behave in those cases? Should it crash? Should it
  return a reasonable default value?
- Expect these questions to come up in practice and think through what the
  appropriate behavior should be. Then, test for it.

### Tip #5: Test a typical scenario

- In ensuring that corner cases are covered, do not overlook testing basic
  functionality for typical cases
- This is useful for verifying current behavior and to support refactoring.

### Tip #6: Test executable scripts end-to-end

- In some cases, like scripts, it is easy to get lost chasing the coverage %
  - E.g., covering every line of the original, including the parser
- This is not always necessary
  - If you can run a script with all arguments present, it means that the parser
    works correctly
  - So an end-to-end smoke test will also cover the parser
  - This saves a little time and reduces the bloat
- If you need to test the functionality, consider factoring out as much code as
  possible from `_main`
  - A good practice is to have a `_run` function that does all the job and
    `_main` only brings together the parser and the executable part

## Conventions

### Naming and placement conventions

- We follow the convention (that happen to be mostly the default to `pytest`):
- A directory `test` that contains all the test code and artifacts
  - The `test` directory contains all the `test_*.py` files and all inputs and
    outputs for the tests.
  - A unit test file should be close to the library / code it tests
- The test class should make clear reference to the code that is tested
  - To test a class `FooBar`, the corresponding test class is named
    `TestFooBar`, i.e. we use the CamelCase for the test classes
  - To test a function `generate_html_tables()`, the corresponding test class is
    named `Test_generate_html_tables`
  - To test a method `method_a()` of the class `FooBar`, the corresponding test
    class is named `TestFooBar` and the test method in this class is named
    `test_method_a`
  - To test a protected method `_gozilla()` of `FooBar`, the corresponding test
    method is named `test__gozilla` (note the double underscore). This is needed
    to distinguish testing the public method `FooBar.gozilla()` from
    `FooBar._gozilla()`
- Numbers can be used to differentiate between separate test cases clearly
  - A number can be added to the test class name, e.g., `TestFooBar1()`, if
    there are multiple test classes that are testing the code in different ways
    (e.g., with different set up and tear down actions)
  - We prefer to name classes `TestFooBar1` and methods `TestFooBar1.test1()`,
    even if there is a single class / method, to make it easier to add another
    test class, without having to rename class and `check_string` files.
  - We are OK with using suffixes like `01`, `02`, … , when we believe it's
    important that methods are tested in a certain order (e.g., from the
    simplest to the most complex)
- It's OK to have multiple test methods in a single class, e.g., for
  `FooBar.method_a()` and `FooBar.method_b()`, the test class contains the
  following methods:
  ```python
  class TestFooBar1(unittest2.TestCase):
      def test_method_a(self):
          ...
      def test_method_b(self):
          ...
  ```
- Split test classes and methods in a reasonable way so each one tests one
  single thing in the simplest possible way
- Remember that test code is not second-class citizen, although it's auxiliary
  to the code
  - Add comments and docstring explaining what the code is doing
  - If you change the name of a class, also the test should be changed
  - If you change the name of a file also the name of the file with the testing
    code should be changed

### Our framework to test using input / output data

- `helpers/unit_test.py` has some utilities to create input and output easily
  dirs storing data for unit tests
- `hut.TestCase` has various methods to help you create
  - `get_input_dir`: return the name of the dir used to store the inputs
  - `get_scratch_space`: return the name of a scratch dir to keep artifacts of
    the test
  - `get_output_dir`: probably not interesting for the user
- The directory structure enforced by the out `TestCase` is like:

  ```bash
  > tree -d edg/form_8/test/
  edg/form_8/test/
  └── TestExtractTables1.test1
      ├── input
      └── output
  ```

- The layout of test dir:
  ```bash
  > ls -1 helpers/test/
  Test_dassert1.test2
  Test_dassert1.test3
  Test_dassert1.test4
  ...
  Test_dassert_misc1.test6
  Test_dassert_misc1.test8
  Test_system1.test7
  test_dbg.py
  test_helpers.py
  test_system_interaction.py
  ```

### Use text and not pickle files as input

- The problem with pickle files is the usual ones
  - They are not stable across different versions of libraries
  - They are not human-readable
- Prefer to use text file
  - E.g., use a CSV file
- If the data used for testing is generated in a non-complicated way
  - Document how it was generated
  - Even better, add a test that generates the data
- Use a subset of the input data
  - The smaller, the better for everybody
    - Fast tests
    - Easier to debug
    - More targeted unit test
  - Do not check in 1 megabyte of test data!

### `check_string` vs `self.assertEqual`

- TODO(gp): Add

### Use `self.assert_equal`

- This is a function that helps you understand what the mismatches are
- It works on `str`

### How to split unit test code in files

- The two extreme approaches are:
  - All the test code for a directory goes in one file
    `foo/bar/test/test_$DIRNAME.py` (or `foo/bar/test/test_all.py`)
  - Each file `foo/bar/$FILENAME` with code gets its corresponding
    `foo/bar/test/test_$FILENAME.py`
    - It should also be named according to the library it tests
    - For example, if the library to test is called `pnl.py`, then a
      corresponding unit test should be called `test_pnl.py`
- Pros of 1) vs 2)
  - Less maintenance churn
    - It takes work to keep the code and the test files in sync, e.g.,
      - If you change the name of the code file, you don't have to change other
        file names
      - If you move one class from one file to another, you might not need to
        move test code
  - Fewer files opened in your editor
  - Avoid many files with a lot of boilerplate code
- Cons of 1) vs 2)
  - The single file can become huge!
- Compromise solution: Start with a single file
  `test_$DIRNAME.py`(or`test*dir_name.py`) \* In the large file add a framed
  comment like:
  ```python
  # ##################
  # Unit tests for …
  # ##################
  ```
  - So it's easy to find which file is tested were using grep
- Then split when it becomes too big using `test_$FILENAME.py`

### Skeleton for unit test

- Interesting unit tests are in `helpers/test`
- A unit test looks like:
  ```python
  import helpers.unit_test as hut
  class Test...(hut.TestCase):
      def test...(self):
          ...
  ```
- `pytest` will take care of running the code so you don't need:
  ```python
  if __name__ == '__main__':
  unittest.main()
  ```

### Hierarchical `TestCase` approach

- Whenever there is a hierarchy in classes, we also create a hierarchy of test
  classes
- A parent test class looks like:
  ```python
  import helpers.unit_test as hut
  class SomeClientTestCase(hut.TestCase):
      def _test...1(self):
          ...
      def _test...2(self):
          ...
  ```
- While a child test class looks like this, where test methods use the
  corresponding methods from the parent test class:
  ```python
  class TestSomeClient(SomeClientTestCase):
      def test...1(self):
          ...
      def test...2(self):
          ...
  ```
- Each `TestCase` tests a "behavior" like a set of related methods
- Each `TestCase` is under the test dir
- Each derived class should use the proper `TestCase` classes to reach a decent
  coverage
- It is OK to use non-private methods in test classes to ensure that the code is
  in order of dependency so that the reader doesn't have to jump back / forth
- We want to separate chunks of unit test code using:

  ```python
  # ########################################################################
  ```

  putting all the methods used by that chunk at the beginning and so on

- It is OK to skip a `TestCase` method if it is not meaningful, when coverage is
  enough
- As an example, see `im_v2/common/data/client/test/im_client_test_case.py` and
  `im_v2/ccxt/data/client/test/test_ccxt_clients.py`

### Use the appropriate `self.assert*`

- When you get a failure, you don't want to get something like "True is not
  False", rather an informative message like "5 is not < 4"
- Bad `self.assertTrue(a < b)`
- Good `self.assertLess(a, b)`

### Do not use `hdbg.dassert`

- `dassert`s are for checking the self-consistency of the code
- The invariant is that you can remove `dbg.dassert` without changing the code's
  behavior. Of course, you can't remove the assertion and get unit tests to work

### Interesting testing functions

- List of useful testing functions are:
  - [General python](https://docs.python.org/2/library/unittest.html#test-cases)
  - [Numpy](https://docs.scipy.org/doc/numpy-1.15.0/reference/routines.testing.html)
  - [Pandas](https://pandas.pydata.org/pandas-docs/version/0.21/api.html#testing-functions)

### Use set_up_test / tear_down_test

- If you have a lot of repeated code in your tests, you can make them shorter by
  moving this code to `set_up_test/tear_down_test` methods:
  - These methods are our preferred alternative to `setUp()` and `tearDown()`
    methods that are standardly used in the `unittest` framework. As a general
    rule, we should avoid defining custom `setUp()` and `tearDown()` methods in
    our test classes. The reason is that the `unittest`/`pytest` framework
    relies on its built-in `setUp()` and `tearDown()` methods, and if we
    introduce additional operations in these methods in the individual test
    classes (e.g., mocking, opening DBs), it can interfere with the inner
    workings of the framework.
  - Instead of `setUp()`, we define a `set_up_test()` method within the test
    class and then run it at the beginning of each test method.
  - Similarly, instead of `tearDown()`, we define `tear_down_test()` and run it
    at the end of each test method.
  - To make sure both `set_up_test()` and `tear_down_test()` run even if the
    test itself fails, we wrap them in a
    [pytest fixture](https://docs.pytest.org/en/6.2.x/fixture.html#yield-fixtures-recommended).

    **Bad**:

    ```python
    def setUp(self) -> None:
        super().setUp()
        ...
        ... # custom code
        ...

    def tearDown(self) -> None:
        ...
        ... # custom code
        ...
        super().tearDown()

    def test1(self) -> None:
        ...
    ```

    **Good**:

    ```python
    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        ...
        ... # custom code
        ...

    def tear_down_test(self) -> None:
        ...
        ... # custom code
        ...

    def test1(self) -> None:
        ...
    ```
  - If there is nothing left in `setUp()`/`tearDown()` after removing
    `super().setUp()`/`super.tearDown()`, then `setUp()`/`tearDown()` can be
    discarded completely.

#### Nested set_up_test / tear_down_test

- When a test class (e.g., TestChild) inherits from another test class (e.g.,
  TestParent), `setUp()`/`tearDown()` methods in the child class normally
  incorporate the corresponding methods from the parent class.
- We prioritize clarity and explicitness in the naming and usage of our methods.
  Therefore, the general rule is that we define
  `set_up_test()`/`tear_down_test()` in the parent class, and in the child class
  we define `set_up_test2()`/`tear_down_test2()`, which call the corresponding
  methods from the parent class.
  - If the child class itself is used as a parent for another class, then the
    deeper nested class's methods are named
    `set_up_test3()`/`tear_down_test3()`, and so on, with the numerical suffix
    increasing at each level.
- The following cases are possible with regard to the `setUp()`/`tearDown()`
  configuration:
  - Both of TestParent and TestChild have separate `setUp()`/`tearDown()`
    methods. Then, in TestParent, `setUp()`/`tearDown()` should be replaced by
    `set_up_test()`/`tear_down_test()` as described above; in TestChild,
    `setUp()`/`tearDown()` should be replaced by
    `set_up_test2()`/`tear_down_test2()`, which call
    `set_up_test()`/`tear_down_test()` from the parent class. For example:

  ```python
  class TestParent(hunitest.TestCase):
      def setUp(self) -> None:
          super().setUp()
          ...

      def tearDown(self) -> None:
          ...
          super().tearDown()

      def test1(self) -> None:
          ...

  class TestChild(TestParent):
      def setUp(self) -> None:
          super().setUp()
          ...

      def tearDown(self) -> None:
          ...
          super().tearDown()

      def test1(self) -> None:
          ...
  ```

  should be replaced by:

  ```python
  class TestParent(hunitest.TestCase):
      @pytest.fixture(autouse=True)
      def setup_teardown_test(self):
          # Run before each test.
          self.set_up_test()
          yield
          # Run after each test.
          self.tear_down_test()

      def set_up_test(self) -> None:
          ...

      def tear_down_test(self) -> None:
          ...

      def test1(self) -> None:
          ...

  class TestChild(TestParent):
      @pytest.fixture(autouse=True)
      def setup_teardown_test(self):
          # Run before each test.
          self.set_up_test2()
          yield
          # Run after each test.
          self.tear_down_test2()

      def set_up_test2(self) -> None:
          self.set_up_test()
          ...

      def tear_down_test2(self) -> None:
          ...
          self.tear_down_test()

      def test1(self) -> None:
          ...
  ```
  - TestParent has `setUp()` and `tearDown()`, while TestChild does not. Then,
    in TestParent, `setUp()`/`tearDown()` should be replaced by
    `set_up_test()`/`tear_down_test()` as described above; in TestChild,
    `set_up_test()`/`tear_down_test()` will run in the test methods
    automatically via the inherited fixture. For example:

  ```python
  class TestParent(hunitest.TestCase):
      def setUp(self) -> None:
          super().setUp()
          ...

      def tearDown(self) -> None:
          ...
          super().tearDown()

      def test1(self) -> None:
          ...

  class TestChild(TestParent):
      def test1(self) -> None:
          ...
  ```

  should be replaced by:

  ```python
  class TestParent(hunitest.TestCase):
      @pytest.fixture(autouse=True)
      def setup_teardown_test(self):
          # Run before each test.
          self.set_up_test()
          yield
          # Run after each test.
          self.tear_down_test()

      def set_up_test(self) -> None:
          ...

      def tear_down_test(self) -> None:
          ...

      def test1(self) -> None:
          ...

  class TestChild(TestParent):
      def test1(self) -> None:
          ...
  ```
  - If TestParent only has one of the two, either `setUp()` or `tearDown()`,
    then in both TestParent and TestChild, the test methods should run (from the
    fixture), respectively, either `set_up_test()` or `tear_down_test()`, e.g.:

        ```python
        class TestParent(hunitest.TestCase):
            @pytest.fixture(autouse=True)
            def setup_teardown_test(self):
                # Run before each test.
                self.set_up_test()
                yield

            def set_up_test(self) -> None:
                ...

            def test1(self) -> None:
                ...

        class TestChild(TestParent):
            def test1(self) -> None:
                ...
        ```
  - A combination of the previous two options: TestParent has `setUp()` and
    `tearDown()`, and TestChild has one of them but not the other. Then, in
    TestParent, `setUp()`/`tearDown()` should be replaced by
    `set_up_test()`/`tear_down_test()` as described above. In TestChild, the
    method that was present, `setUp()` or `tearDown()`, should be replaced by
    `set_up_test2()` or `tear_down_test2()`, which should call `set_up_test()`
    or `tear_down_test()` from TestParent; the other method from TestParent,
    which was absent in TestChild, should be added directly to TestChild's
    fixture to run in its test methods. For example, for the case when TestChild
    has `setUp()` but not `tearDown()`:

  ```python
  class TestParent(hunitest.TestCase):
      def setUp(self) -> None:
          super().setUp()
          ...

      def tearDown(self) -> None:
          ...
          super().tearDown()

      def test1(self) -> None:
          ...

  class TestChild(TestParent):
      def setUp(self) -> None:
          super().setUp()
          ...

      def test1(self) -> None:
          ...
  ```

  should be replaced by:

  ```python
  class TestParent(hunitest.TestCase):
      @pytest.fixture(autouse=True)
      def setup_teardown_test(self):
          # Run before each test.
          self.set_up_test()
          yield
          # Run after each test.
          self.tear_down_test()

      def set_up_test(self) -> None:
          ...

      def tear_down_test(self) -> None:
          ...

      def test1(self) -> None:
          ...

  class TestChild(TestParent):
      @pytest.fixture(autouse=True)
      def setup_teardown_test(self):
          # Run before each test.
          self.set_up_test2()
          yield
          # Run after each test.
          self.tear_down_test()

      def set_up_test2(self) -> None:
          self.set_up_test()
          ...

      def test1(self) -> None:
          ...
  ```
  - TestChild has `setUp()` and `tearDown()` (or just one of the two), while
    TestParent does not. Then, in TestChild, `setUp()`/`tearDown()` should be
    replaced by `set_up_test()`/`tear_down_test()` as described above;
    TestParent undergoes no changes. For example:

  ```python
  class TestParent(hunitest.TestCase):
      def test1(self) -> None:
          ...

  class TestChild(TestParent):
      def setUp(self) -> None:
          super().setUp()
          ...

      def tearDown(self) -> None:
          ...
          super().tearDown()

      def test1(self) -> None:
          ...
  ```

  should be replaced by:

  ```python
  class TestParent(hunitest.TestCase):
      def test1(self) -> None:
          ...

  class TestChild(TestParent):
      @pytest.fixture(autouse=True)
      def setup_teardown_test(self):
          # Run before each test.
          self.set_up_test()
          yield
          # Run after each test.
          self.tear_down_test()

      def set_up_test(self) -> None:
          ...

      def tear_down_test(self) -> None:
          ...

      def test1(self) -> None:
          ...
  ```

### Use setUpClass / tearDownClass

- If you need some expensive code parts to be done once for the whole test
  class, such as opening a database connection, opening a temporary file on the
  filesystem, loading a shared library for testing, etc., you can use
  `setUpClass/tearDownClass` methods:
  - `setUpClass()`

    A class method called before tests in an individual class are run.
    `setUpClass` is called with the class as the only argument and must be
    decorated as a
    [classmethod](https://docs.python.org/3/library/functions.html#classmethod):

    ```python
    @classmethod
    def setUpClass(cls):
        ...
    ```
  - `tearDownClass()`

    A class method called after tests in an individual class have run.
    `tearDownClass` is called with the class as the only argument and must be
    decorated as a
    [classmethod](https://docs.python.org/3/library/functions.html#classmethod):

    ```python
    @classmethod
    def tearDownClass(cls):
        ...
    ```

- For more information, see
  [official unittest docs](https://docs.python.org/3/library/unittest.html)

# Update test tags

- There are 2 files with the list of tests' tags:
  - `amp/pytest.ini`
  - `.../pytest.ini (if `amp` is a submodule)`
- In order to update the tags (do it in both files):
  - In the `markers` section, add a name of a new tag
  - After a `:` add a short description
  - Keep tags in the alphabetical order

# Mocking

## Refs

- Introductory article is
  [https://realpython.com/python-mock-library/ ](https://realpython.com/python-mock-library/)
- Official Python documentation for the mock package can be seen here
  [unit test mock](https://docs.python.org/3/library/unittest.mock.html)

## Common usage samples

It is best to apply on any part that is deemed unnecessary for specific test

- Complex functions
  - Mocked functions can be tested separately
- 3rd party provider calls
  - CCXT
  - AWS
    - S3
      - See `helpers/hmoto.py` in `cmamp` repo
    - Secrets
    - Etc...
- DB calls

- Many more possible combinations can be seen in the official documentation.
- Below are the most common ones for basic understanding.

## Philosophy about mocking

1. We want to mock the minimal surface of a class
   - E.g., assume there is a class that is interfacing with an external provider
     and our code places requests and gets values back
   - We want to replace the provider with an object that responds to the
     requests with the actual response of the provider
   - In this way, we can leave all the code of our class untouched and tested
2. We want to test public methods of our class (and a few private methods)
   - In other words, we want to test the end-to-end behavior and not how things
     are achieved
   - Rationale: if we start testing "how" things are done and not "what" is
     done, we can't change how we do things (even if it doesn't affect the
     interface and its behavior), without updating tons of methods
   - We want to test the minimal amount of behavior that enforces what we care
     about

## Some general suggestions about testing

### Test from the outside-in

- We want to start testing from the end-to-end methods towards the constructor
  of an object
- Rationale: often, we start testing the constructor very carefully and then we
  get tired / run out of time when we finally get to test the actual behavior
- Also, testing the important behavior automatically tests building the objects
- Use the code coverage to see what's left to test once you have tested the
  "most external" code

### We don't need to test all the assertions

- E.g., testing carefully that we can't pass a value to a constructor doesn't
  really test much besides the fact that `dassert` works (which, surprisingly
  works!)
- We don't care about line coverage or checking boxes for the sake of checking
  boxes

### Use strings to compare output instead of data structures

- Often, it's easier to do a check like:

  ```python
  # Better:
  expected = str(...)
  expected = pprint.pformat(...)

  # Worse:
  expected = ["a", "b", { ... }]
  ```

  rather than building the data structure

- Some purists might not like this, but
  - It's much faster to use a string (which is or should be one-to-one to the
    data structure), rather than the data structure itself
    - By extension, many of the more complex data structure have a built-in
      string representation
  - It is often more readable and easier to diff (e.g., `self.assertEqual` vs
    `self.assert_equal`)
  - In case of mismatch, it's easier to update the string with copy-paste rather
    than creating a data structure that matches what was created

### Use `self.check_string()` for things that we care about not changing (or are too big to have as strings in the code)

- Use `self.assert_equal()` for things that should not change (e.g., 1 + 1 = 2)
- When using `check_string` still try to add invariants that force the code to
  be correct
- E.g., if we want to check the PnL of a model, we can freeze the output with
  `check_string()`, but we want to add a constraint like there are more
  timestamps than 0 to avoid the situation where we update the string to
  something malformed

### Each test method should test a single test case

- Rationale: we want each test to be clear, simple, fast
- If there is repeated code we should factor it out (e.g., builders for objects)

### Each test should be crystal clear on how it is different from the others

- Often, you can factor out all the common logic into a helper method
- Copy-paste is not allowed in unit tests in the same way it's not allowed in
  production code

### In general, you want to budget the time to write unit tests

- E.g., "I'm going to spend 3 hours writing unit tests". This is going to help
  you focus on what's important to test and force you to use an iterative
  approach rather than incremental (remember the Monalisa)

  ![alt_image](figs/unit_tests/image_4.png)

### Write a skeleton of unit tests and ask for a review if you are not sure how what to test

- Aka "testing plan"

## Object patch with return value

```python
import unittest.mock as umock
import im_v2.ccxt.data.extract.extractor as ivcdexex

@umock.patch.object(ivcdexex.hsecret, "get_secret")
def test_function_call1(self, mock_get_secret: umock.MagicMock):
    mock_get_secret.return_value = "dummy"
```

- Function `get_secret` in `helpers/hsecret.py` is mocked
  - Pay attention on where is `get_secret` mocked:
    - It is mocked in im_v2.ccxt.data.extract.extractor as “get_secret” is
      called there in function that is being tested
  - `@umock.patch.object(hsecret, "get_secret")` will not work as mocks are
    applied after all modules are loaded, hence the reason for using exact
    location
    - If we import s module in test itself it will work as mock is applied
    - For modules outside of test function it is too late as they are loaded
      before mocks for test are applied
- On every call, it returns string "dummy"

## Path patch with multiple return values

```python
import unittest.mock as umock

@umock.patch("helpers.hsecret.get_secret")
def test_function_call1(self, mock_get_secret: umock.MagicMock):

mock_get_secret.side_effect = ["dummy", Exception]
```

- On first call, string `dummy` is returned
- On second, `Exception` is raised

## Ways of calling `patch` and `patch.object`

- Via decorator
  ```python
  @umock.patch("helpers.hsecret.get_secret")
  def test_function_call1(self, mock_get_secret: umock.MagicMock):
      pass
  ```
- In actual function
  ```python
  get_secret_patch = umock.patch("helpers.hsecret.get_secret")
  get_secret_mock = get_secret_patch.start()
  ```
  - This is the only approach in which you need to start/stop patch!
    - The actual mock is returned as the return value of `start()` method!
  - In other two approaches, start/stop is handled under the hood and we are
    always interacting with `MagicMock` object
- Via `with` statement (also in function)
  ```python
  with umock.patch(""helpers.hsecret.get_secret"") as get_secret_mock:
      pass
  ```
  - One of the use cases for this is if we are calling a different function
    inside a function that is being mocked
    - Mostly because it is easy for an eye if there are to much patches via
      decorator and we do not need to worry about reverting the patch changes as
      that is automatically done at the end of with statement

## Mock object state after test run

```python
@umock.patch.object(exchange_class._exchange, "fetch_ohlcv")
def test_function_call1(self, fetch_ohlcv_mock: umock.MagicMock):
    self.assertEqual(fetch_ohlcv_mock.call_count, 1)
    actual_args = tuple(fetch_ohlcv_mock.call_args)
    expected_args = (
            ("BTC/USDT",),
            {"limit": 2, "since": 1, "timeframe": "1m"},
    )
    self.assertEqual(actual_args, expected_args)
```

- After `fetch_ohlcv` is patched, `Mock` object is passed to test
  - In this case, it is `fetch_ohlcv_mock`
- From sample we can see that function is called once
  - First value in a tuple are positional args passed to `fetch_ohlcv` function
  - Second value in a tuple are keyword args passed to `fetch_ohlcv` function
  - As an alternative, `fetch_ohlcv_mock.call_args.args` and
    `fetch_ohlcv_mock.call_args.kwargs` can be called for separate results of
    args/kwargs

    ```python
    self.assertEqual(fetch_ohlcv_mock.call_count, 3)
    actual_args = str(fetch_ohlcv_mock.call_args_list)
    expected_args = r"""
    [call('BTC/USDT', since=1645660800000, bar_per_iteration=500),
    call('BTC/USDT', since=1645690800000, bar_per_iteration=500),
    call('BTC/USDT', since=1645720800000, bar_per_iteration=500)]
    """
    self.assert_equal(actual_args, expected_args, fuzzy_match=True)
    ```

- In sample above, that is continuation of previous sample,
  `fetch_ohlcv_mock.call_args_list` is called that returns all calls to mocked
  function regardless of how many times it is called
- Useful for verifying that args passed are changing as expected

## Mock common external calls in `hunitest.TestCase` class

```python
class TestCcxtExtractor1(hunitest.TestCase):
    # Mock calls to external providers.
    get_secret_patch = umock.patch.object(ivcdexex.hsecret, "get_secret")
    ccxt_patch = umock.patch.object(ivcdexex, "ccxt", spec=ivcdexex.ccxt)

    def set_up_test(self) -> None:
        self.get_secret_mock: umock.MagicMock = self.get_secret_patch.start()
        self.ccxt_mock: umock.MagicMock = self.ccxt_patch.start()
        # Set dummy credentials for all tests.
        self.get_secret_mock.return_value = {"apiKey": "test", "secret": "test"}

    def tear_down_test(self) -> None:
        self.get_secret_patch.stop()
        self.ccxt_patch.stop()
```

- For every unit test we want to isolate external calls and replace them with
  mocks
  - This way tests are much faster and not influenced by external factors we can
    not control
  - Mocking them in `set_up_test()` (which is run at the beginning of the test
    methods) will make the tests using this class simpler and ready out of the
    box
- In current sample we are mocking AWS secrets and `ccxt` library
  - `umock.patch.object` is creating `patch` object that is not yet activated
    - `patch.start()/stop()` is activating/deactivating patch for each test
      where `set_up_test()` and `tear_down_test()` are run
    - `patch.start()` is returning a standard `MagicMock` object we can use to
      check various states as mentioned in previous examples and control return
      values
      - Call_args, call_count, return_value, side_effect, etc.
- Note: Although patch initialization in static variables belongs to
  `set_up_test()`, when this code is moved there patch is created for each test
  separately. We want to avoid that and only start/stop same patch for each
  test.

## Mocks with specs

```python
# Regular mock and external library `ccxt` is replaced with `MagicMock`
@umock.patch.object(ivcdexex, "ccxt")
# Only `ccxt` is spec'd, not actual components that are "deeper" in the `ccxt` library.
@umock.patch.object(ivcdexex, "ccxt", spec=ivcdexex.ccxt)
# Everything is spec'd recursively , including returning values/instances of `ccxt`
# functions and returned values/instances of returned values/instances, etc.
@umock.patch.object(ivcdexex, "ccxt", autospec=True)
```

- First mock is not tied to any spec and we can call any attribute/function
  against the mock and the call will be memorized for inspection and the return
  value is new `MagicMock`.
  - `ccxt_mock.test(123)` returns new `MagicMock` and raises no error
- In second mock `ccxt.test(123)` would fail as such function does not exists
  - We can only call valid exchange such as `ccxt_mock.binance()` that will
    return `MagicMock`, as exchange is not part of the spec
- In third mock everything needs to be properly called
  - `ccxt_mock.binance()` will return `MagicMock` with `ccxt.Exchange` spec_id
    (in mock instance as meta)
    - As newly `exchange` instance is with spec, we can only call real
      functions/attributes of `ccxt.Exchange` class

## Caveats

```python
# `datetime.now` cannot be patched directly, as it is a built-in method.
# Error: "can't set attributes of built-in/extension type 'datetime.datetime'"
datetime_patch = umock.patch.object(imvcdeexut, "datetime", spec=imvcdeexut.datetime)
```

- Python built-in methods can not be patched

  ```python
  class TestExtractor1(hunitest.TestCase):
      # Mock `Extractor`'s abstract functions.
      abstract_methods_patch = umock.patch.object(
          imvcdexex.Extractor, "__abstractmethods__", new=set()
      )
      ohlcv_patch = umock.patch.object(
          imvcdexex.Extractor,
          "_download_ohlcv",
          spec=imvcdexex.Extractor._download_ohlcv,
      )
  ```

- Patching `__abstractmethods__` function of an abstract class enables us to
  instantiate and test abstract class as any regular class
