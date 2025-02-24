# KaizenFlow - Python Style Guide

<!-- toc -->

- [Meta](#meta)
- [Disclaimer](#disclaimer)
* [References](#references)
- [High-Level Principles](#high-level-principles)
  - [Follow the DRY principle](#follow-the-dry-principle)
  - [The writer is the reader](#the-writer-is-the-reader)
  - [Encapsulate what changes](#encapsulate-what-changes)
  - [Least surprise principle](#least-surprise-principle)
  - [Pay the technical debt](#pay-the-technical-debt)
  - [End-to-end first](#end-to-end-first)
  - [Unit test everything](#unit-test-everything)
  - [Don't get attached to code](#dont-get-attached-to-code)
  - [Always plan before writing code](#always-plan-before-writing-code)
  - [Think hard about naming](#think-hard-about-naming)
  - [Look for inconsistencies](#look-for-inconsistencies)
  - [No ugly hacks](#no-ugly-hacks)
- [Our coding suggestions](#our-coding-suggestions)
* [Being careful with naming](#being-careful-with-naming)
  - [Follow the conventions](#follow-the-conventions)
  - [Follow spelling rules](#follow-spelling-rules)
  - [Search good names, avoid bad names](#search-good-names-avoid-bad-names)
    - [General naming rules](#general-naming-rules)
    - [Do not be stingy](#do-not-be-stingy)
    - [Do not abbreviate just to save characters](#do-not-abbreviate-just-to-save-characters)
    - [When to use abbreviations](#when-to-use-abbreviations)
  - [Avoid code stutter](#avoid-code-stutter)
* [Comments and docstrings](#comments-and-docstrings)
  - [General conventions](#general-conventions)
  - [Descriptive vs imperative style](#descriptive-vs-imperative-style)
  - [Docstrings style](#docstrings-style)
  - [Comments style](#comments-style)
  - [Replace empty lines in code with comments](#replace-empty-lines-in-code-with-comments)
  - [Referring to an object in code comments](#referring-to-an-object-in-code-comments)
  - [Avoid distracting comments](#avoid-distracting-comments)
  - [Commenting out code](#commenting-out-code)
  - [Use type hints](#use-type-hints)
  - [Interval notation](#interval-notation)
  - [If you find a bug or obsolete docstring/TODO in the code](#if-you-find-a-bug-or-obsolete-docstringtodo-in-the-code)
* [Linter](#linter)
  - [Remove linter messages](#remove-linter-messages)
  - [When to disable linter messages](#when-to-disable-linter-messages)
  - [Prefer non-inlined linter comments](#prefer-non-inlined-linter-comments)
  - [Don't mix real changes with linter changes](#dont-mix-real-changes-with-linter-changes)
* [Logging](#logging)
  - [Always use logging instead of prints](#always-use-logging-instead-of-prints)
  - [Our logging idiom](#our-logging-idiom)
  - [Logging level](#logging-level)
  - [Use positional args when logging](#use-positional-args-when-logging)
  - [Exceptions don't allow positional args](#exceptions-dont-allow-positional-args)
  - [Report warnings](#report-warnings)
* [Assertions](#assertions)
  - [Validate values before an assignment](#validate-values-before-an-assignment)
  - [Encode the assumptions using assertions](#encode-the-assumptions-using-assertions)
  - [Use positional args when asserting](#use-positional-args-when-asserting)
  - [Report as much information as possible in an assertion](#report-as-much-information-as-possible-in-an-assertion)
* [Imports](#imports)
  - [Don't use evil `import *`](#dont-use-evil-import-)
  - [Cleaning up the evil `import *`](#cleaning-up-the-evil-import-)
  - [Avoid `from ... import ...`](#avoid-from--import-)
  - [Exceptions to the import style](#exceptions-to-the-import-style)
  - [Always import with a full path from the root of the repo / submodule](#always-import-with-a-full-path-from-the-root-of-the-repo--submodule)
  - [Baptizing module import](#baptizing-module-import)
  - [Examples of imports](#examples-of-imports)
* [Scripts](#scripts)
  - [Use Python and not bash for scripting](#use-python-and-not-bash-for-scripting)
  - [Skeleton for a script](#skeleton-for-a-script)
  - [Some useful patterns](#some-useful-patterns)
  - [Use scripts and not notebooks for long-running jobs](#use-scripts-and-not-notebooks-for-long-running-jobs)
  - [Follow the same structure](#follow-the-same-structure)
  - [Use clear names for the scripts](#use-clear-names-for-the-scripts)
* [Functions](#functions)
  - [Avoid using non-exclusive `bool` arguments](#avoid-using-non-exclusive-bool-arguments)
  - [Try to make functions work on multiple types](#try-to-make-functions-work-on-multiple-types)
  - [Avoid hard-wired column name dependencies](#avoid-hard-wired-column-name-dependencies)
  - [Single exit point from a function](#single-exit-point-from-a-function)
  - [Order of function parameters](#order-of-function-parameters)
    - [Problem](#problem)
    - [Decision](#decision)
  - [Consistency of ordering of function parameters](#consistency-of-ordering-of-function-parameters)
  - [Style for default parameter](#style-for-default-parameter)
    - [Problem](#problem-1)
    - [Decision](#decision-1)
    - [Rationale](#rationale)
  - [Calling functions with default parameters](#calling-functions-with-default-parameters)
    - [Problem](#problem-2)
    - [Decision](#decision-2)
    - [Rationale](#rationale-1)
  - [Don't repeat non-default parameters](#dont-repeat-non-default-parameters)
    - [Problem](#problem-3)
    - [Decision](#decision-3)
    - [Rationale](#rationale-2)
* [Writing clear beautiful code](#writing-clear-beautiful-code)
  - [Keep related code close](#keep-related-code-close)
  - [Order functions in topological order](#order-functions-in-topological-order)
  - [Distinguish public and private functions](#distinguish-public-and-private-functions)
  - [Keep public functions organized in a logical order](#keep-public-functions-organized-in-a-logical-order)
  - [Do not make tiny wrappers](#do-not-make-tiny-wrappers)
  - [Regex](#regex)
  - [Do not introduce another “concept” unless really needed](#do-not-introduce-another-concept-unless-really-needed)
  - [Return `None` or keep one type](#return-none-or-keep-one-type)
  - [Avoid wall-of-text functions](#avoid-wall-of-text-functions)
* [Writing robust code](#writing-robust-code)
  - [Don’t let your functions catch the default-itis](#dont-let-your-functions-catch-the-default-itis)
  - [Explicitly bind default parameters](#explicitly-bind-default-parameters)
  - [Don’t hardwire params in a function call](#dont-hardwire-params-in-a-function-call)
  - [Make `if-elif-else` complete](#make-if-elif-else-complete)
  - [Add TODOs when needed](#add-todos-when-needed)
* [Common Python mistakes](#common-python-mistakes)
  - [`==` vs `is`](#-vs-is)
  - [`type()` vs `isinstance()`](#type-vs-isinstance)
* [Unit tests](#unit-tests)
* [Refactoring](#refactoring)
  - [When moving / refactoring code](#when-moving--refactoring-code)
  - [Write script for renamings](#write-script-for-renamings)
* [Architectural and design pattern](#architectural-and-design-pattern)
  - [Research quality vs production quality](#research-quality-vs-production-quality)
  - [Always separate what changes from what stays the same](#always-separate-what-changes-from-what-stays-the-same)
  - [Organize scripts as pipelines](#organize-scripts-as-pipelines)
  - [Make filename unique](#make-filename-unique)
  - [Incremental behavior](#incremental-behavior)
  - [Run end-to-end](#run-end-to-end)
  - [Think about scalability](#think-about-scalability)
  - [Use command line for reproducibility](#use-command-line-for-reproducibility)
  - [Structure the code in terms of filters](#structure-the-code-in-terms-of-filters)
* [Code style for different languages](#code-style-for-different-languages)
  - [SQL](#sql)
- [Conventions (Addendum)](#conventions-addendum)
* [Be patient](#be-patient)
* [Goal](#goal)
* [Keep the rules simple](#keep-the-rules-simple)
* [Allow turning off the automatic tools](#allow-turning-off-the-automatic-tools)
* [Make the spell-checker happy](#make-the-spell-checker-happy)

<!-- tocstop -->

# Meta

- What we call "rules" are actually just a convention
- The "rules"
  - Are optimized for the common case
  - Are not the absolute best way of doing something in all possible cases
  - Can become cumbersome or weird to follow for some corner cases
- We prefer simple rather than optimal rules so that they can be applied in most
  of the cases, without thinking or going to check the documentation
- The rules are striving to achieve consistency and robustness
  - We prefer to care about consistency rather than arguing about which approach
    is better in each case
  - E.g., see the futile "tab vs space" flame-war from the 90s
- The rules are optimized for the average developer / data scientist and not for
  power users
- The rules try to minimize the maintenance burden
  - We want to minimize the propagation of a change
- Rules are not fixed in stone
  - Rules evolve based on what we discuss through the reviews

# Disclaimer

- This document was forked from
  [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html),
  therefore, the numbering of chapters sets off where the Style Guide ends. Make
  sure to familiarize yourself with it before proceeding to the rest of the doc,
  since it is the basis of our team’s code style.
- Another important source is
  [The Pragmatic Programmer](https://drive.google.com/file/d/1g0vjtaBVq0dt32thNprBRJpeHJsJSe-Z/view?usp=sharing)
  by David Thomas and Andrew Hunt. While not Python-specific, it provides an
  invaluable set of general principles by which any person working with code
  (software developer, DevOps or data scientist) should abide. Read it on long
  commutes, during lunch, and treat yourself to a physical copy on Christmas.
  The book is summarized
  [here](https://github.com/cryptokaizen/cmamp/blob/master/docs/coding/all.code_like_pragmatic_programmer.how_to_guide.md),
  but do not deprive yourself of the engaging manner in which Thomas & Hunt
  elaborate on these points -- on top of it all, it is a very, very enjoyable
  read.

## References

- Coding
  - [Google Python Style Guide (GPSG)](https://google.github.io/styleguide/pyguide.html)
  - [](https://google.github.io/styleguide/pyguide.html)[Code convention from PEP8](https://www.python.org/dev/peps/pep-0008/)[](https://www.python.org/dev/peps/pep-0008/)
- [](https://www.python.org/dev/peps/pep-0008/)Documentation
  - [Docstring convention from PEP257](https://github.com/google/styleguide/blob/gh-pages/docguide/best_practices.md)
  - [Google documentation best practices](https://github.com/google/styleguide/blob/gh-pages/docguide/best_practices.md)
- Commenting style
  - [Sphinx](https://www.sphinx-doc.org/en/master/)
- [Sphinx tutorial](https://thomas-cokelaer.info/tutorials/sphinx/index.html)
- Design
  - [Google philosophical stuff](https://github.com/google/styleguide/blob/gh-pages/docguide/philosophy.md)
  - [Unix rules (although a bit cryptic sometimes)](https://en.wikipedia.org/wiki/Unix_philosophy#Eric_Raymond%E2%80%99s_17_Unix_Rules)

# High-Level Principles

- In this paragraph we summarize the high-level principles that we follow for
  designing and implementing code and research. We should be careful in adding
  principles here. Ideally principles should be non-overlapping and generating
  all the other lower level principles we follow (like a basis for a vector
  space)

### Follow the [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself) principle

### The writer is the reader

- Make code easy to read even if it is more difficult to write
- Code is written 1x and read 100x
- Remember that even if things are perfectly clear now to the person that wrote
  the code, in a couple of months the code will look foreign to whoever wrote
  the code.
- So make your future-self's life easier by following the conventions and erring
  on the side of documenting for the reader.

### Encapsulate what changes

- Separate what changes from what stays the same

### [Least surprise principle](https://en.wikipedia.org/wiki/Principle_of_least_astonishment)

- Try to make sure that the reader is not surprised

### Pay the technical debt

- Any unpaid debt is guaranteed to bite you when you don't expect it
- Still some debt is inevitable: try to find the right trade-off

### End-to-end first

- Always focus on implementing things end-to-end, then improve each block
- Remember the analogy of building the car through the skateboard, the bike,
  etc.
  - Compare this approach to building wheels, chassis, with a big-bang
    integration at the end

### Unit test everything

- Code that matters needs to be unit tested
- Code that doesn't matter should not be checked in the repo
- The logical implication is: all code checked in the repo should be unit tested

### Don't get attached to code

- It's ok to delete, discard, retire code that is not useful any more
- Don't take it personally when people suggest changes or simplification

### Always plan before writing code

- File a GitHub issue
- Think about what to do and how to do it
- Ask for help or for a review
- The best code is the one that we avoid to write through a clever mental
  kung-fu move

### Think hard about naming

- Finding a name for a code object, notebook, is extremely difficult but very
  important to build a mental map
- Spend the needed time on it

### Look for inconsistencies

- Stop for a second after you have, before sending out:
  - Implemented code or a notebook
  - Written documentation
  - Written an e-mail
  - ...
- Reset your mind and look at everything with fresh eyes like if it was the
  first time you saw it
  - Does everything make sense to someone that sees this for the first time?
  - Can (and should) it be improved?
  - Do you see inconsistencies, potential issues?
- It will take less and less time to become good at this

### No ugly hacks

- We don't tolerate "ugly hacks", i.e., hacks that require lots of work to be
  undone (much more than the effort to do it right in the first place)
  - Especially an ugly design hack, e.g., a Singleton, or some unnecessary
    dependency between distant pieces of code
  - Ugly hacks spreads everywhere in the code base

# Our coding suggestions

## Being careful with naming

### Follow the conventions

- Name executable files (scripts) and library functions using verbs (e.g.,
  `download.py`, `download_data()`)
- Name classes and (non-executable) files using nouns (e.g., `Downloader()`,
  `downloader.py`)
- For decorators we don't use a verb as we do for normal functions, but rather
  an adjective or a past tense verb, e.g.,
  ```python
  def timed(f):
      """
      Add a timer decorator around a specified function.
      """
      …
  ```

### Follow spelling rules

- We spell commands in lower-case, and programs with initial upper case:
  - "Git" (as program), "git" (as the command)
- We distinguish "research" (not "default", "base") vs "production"
- We use different names for indicating the same concept, e.g., `dir`, `path`,
  `folder`
  - Preferred term is `dir`
- Name of columns
  - The name of columns should be `..._col` and not `..._col_name` or `_column`
- Timestamp
  - We spell `timestamp`, we do not abbreviate it as `ts`
  - We prefer timestamp to `datetime`
    - E.g., `start_timestamp` instead of `start_datetime`
- Abbreviations
  - JSON, CSV, DB, etc., are abbreviations and thus should be capitalized in
    comments and docstrings, and treated as abbreviations in code when it
    doesn't conflict with other rules
    - E.g., `convert_to_CSV`, but `csv_file_name` as a variable name that is not
      global
  - Profit-and-loss: PnL instead of pnl or PNL

### Search good names, avoid bad names

#### General naming rules

- Naming things properly is one of the most difficult task of a programmer /
  data scientist
  - The name needs to be (possibly) short and memorable
    - However, don't be afraid to use long names, if needed, e.g.,
      `process_text_with_full_pipeline_twitter_v1`
    - Сlarity is more important than number of bytes used
  - The name should capture what the object represents, without reference to
    things that can change or to details that are not important
  - The name should refer to what objects do (i.e., mechanisms), rather than how
    we use them (i.e., policies)
  - The name needs to be non-controversial: people need to be able to map the
    name in their mental model
  - The name needs to sound good in English
    - _Bad_: `AdapterSequential` sounds bad
    - _Good_: `SequentialAdapter` sounds good
- Some examples of how NOT to do naming:
  - `raw_df` is a terrible name
    - "raw" with respect to what?
    - Cooked?
    - Read-After-Write race condition?
  - `person_dict` is bad
    - What if we switch from a dictionary to an object?
      - Then we need to change the name everywhere!
    - The name should capture what the data structure represents (its semantics)
      and not how it is implemented

#### Do not be stingy

- Why calling an object `TimeSeriesMinStudy` instead of `TimeSeriesMinuteStudy`?
  - Saving 3 letters is not worth
  - The reader might interpret `Min` as `Minimal` (or `Miniature`, `Minnie`,
    `Minotaur`)
- If you don't like to type, we suggest you get a better keyboard, e.g.,
  [this](https://kinesis-ergo.com/shop/advantage2/)

#### Do not abbreviate just to save characters

- Abbreviations just to save space are rarely beneficial to the reader. E.g.,
  - Fwd (forward)
  - Bwd (backward)
  - Act (actual)
  - Exp (expected)

#### When to use abbreviations

- We could relax this rule for short lived functions and variables in order to
  save some visual noise.
- Sometimes an abbreviation is so short and common that it's ok to leave it
  E.g.,
  - Df (dataframe)
  - Srs (series)
  - Idx (index)
  - Id (identifier)
  - Val (value)
  - Var (variable)
  - Args (arguments)
  - Kwargs (keyword arguments)
  - Col (column)
  - Vol (volatility) while volume is always spelled out

### Avoid code stutter

- An example of code stutter: you want to add a function that returns `git` root
  path in a module `git`
- _Bad_
  - Name is `get_git_root_path()`

    ```python
    import helpers.git as git

    ... git.get_git_root_path()
    ```
  - You see that the module is already specifying we are talking about Git

- _Good_
  - Name is `get_root_path()`

    ```python
    import helpers.git as git

    ... git.get_root_path()
    ```
  - This is not only aesthetic reason but a bit related to a weak form of DRY

## Comments and docstrings

### General conventions

- Code needs to be properly commented
- We follow python standard [PEP 257](https://www.python.org/dev/peps/pep-0257/)
  for commenting
  - PEP 257 standardizes what comments should express and how they should do it
    (e.g., use triple quotes for commenting a function), but does not specify
    what markup syntax should be used to describe comments
- Different conventions have been developed for documenting interfaces
  - ReST
  - Google (which is cross-language, e.g., C++, python, ...)
  - Epytext
  - Numpydoc

### Descriptive vs imperative style

- We decided to use imperative style for our comments and docstrings
  - Pylint and other python QA tools favor an imperative style
  - From [PEP 257](https://www.python.org/dev/peps/pep-0257/)
    ```
    The docstring is a phrase ending in a period. It prescribes the function or
    method's effect as a command ("Do this", "Return that"), not as a description;
    e.g. don't write "Returns the pathname ...".
    ```

### Docstrings style

- We follow ReST (aka re-Structured Text) style for docstrings which is:
  - The most widely supported in the python community
  - Supported by all doc generation tools (e.g., epydoc, sphinx)
  - Default in Pycharm
  - Default in pyment
  - Supported by pydocstyle (which does not support Google style as explained
    [here](https://github.com/PyCQA/pydocstyle/issues/275))
- Example of a function definition with ReST styled docstring:

  ```python
    def my_function(param1: str) -> str:
        """
        A one-line description of what the function does.

        A longer description (possibly on multiple lines) with a more detailed
        explanation of what the function does, trying to not be redundant with
        the parameter / return description below. The focus is on the interface
        and what the user should know to use the function and not how the
        function is implemented.

        :param param1: this is a first param
        :return: this is a description of what is returned
        """
  ```
  - We pick lowercase after `:param XYZ: ...` unless the first word is a proper
    noun or type
  - A full ReST docstring styling also requires to specify params and return
    types, however type hinting makes it redundant so you should use only type
    hinting

- Put docstrings in triple quotation marks
  - _Bad_
    ```python
    Generate "random returns".
    ```
  - _Good_
    ```python
    """
    Generate "random returns".
    """
    ```
- Sometimes functions are small enough so we just use a 1-liner docstring
  without detailed params and return descriptions. Just do not put text and
  docstring brackets in one line
  - _Bad_
    ```python
    """This is not our approach."""
    ```
  - _Good_
    ```python
    """
    This is our approach.
    """
    ```
- [More examples of and discussions on python docstrings](https://stackoverflow.com/questions/3898572)

### Comments style

- Comments follow the same style of docstrings, e.g., imperative style with
  period `.` at the end
  - _Bad_
    ```python
    # This comment is not imperative and has no period at the end
    ```
  - _Good_
    ```python
    # Make comments imperative and end them with a period.
    ```
- Always place comments above the lines that they are referring to. Avoid
  writing comments on the same line as code since they require extra maintenance
  (e.g., when the line becomes too long)
  - _Bad_
    ```python
    print("hello world")      # Introduce yourself.
    ```
  - _Good_
    ```python
    # Introduce yourself.
    print("hello world")
    ```
- The only exception is commenting `if-elif-else` statments: we comment them
  underneath the each statement in order to explain the code that belongs to the
  each statement particularly
  - _Bad_
    ```python
    # Set remapping based on the run type.
    if is_prod:
        ...
    else:
        ...
    ```
  - _Good_
    ```python
    #
    if is_prod:
        # Set remapping for database data used in production.
        ...
    else:
        # Set remapping for file system data used in simulation.
        ...
    ```
    - If you want to separate an `if` statement from a bunch of code preceeding
      it, you can leave an empty comment before it

### Replace empty lines in code with comments

- If you feel that you need an empty line in the code, it probably means that a
  specific chunk of code is a logical piece of code performing a cohesive
  function

  ```python
  ...
  end_y = end_dt.year

  paths = list()
  ...
  ```

- Instead of putting an empty line, you should put a comment describing at high
  level what the code does.
  ```python
  ...
  end_y = end_dt.year
  # Generate a list of file paths for Parquet dataset.
  paths = list()
  ...
  ```
- If you don't want to add comments, just comment the empty line.
  ```python
  ...
  end_y = end_dt.year
  #
  paths = list()
  ...
  ```
- The problem with empty lines is that they are visually confusing since one
  empty line is used also to separate functions. For this reason we suggest
  using an empty comment

### Referring to an object in code comments

- In general, **avoid** this whenever possible
- Code object names (e.g., function, class, params) are often subject to change,
  so we need to take care of them everywhere. It is very hard to track all of
  them in comments so replace the names with their actual meaning
  - _Bad_
    ```python
    # Generate a list of file paths for `ParquetDataset`.
    ```
  - _Good_
    ```python
    # Generate a list of file paths for Parquet dataset.
    ```
- However, sometimes it is necessary. In this case refer to objects in the code
  using Markdown. This is useful for distinguishing the object code from the
  real-life object
  - _Bad_
    ```python
    # The dataframe df_tmp is used for ...
    ```
  - _Good_
    ```python
    # The dataframe `df_tmp` is used for ...
    ```

### Avoid distracting comments

- Use comments to explain the high level logic / goal of a piece of code and not
  the details, e.g., do not comment things that are obvious
  - _Bad_
    ```python
    # Print results.
    _LOG.info("Results are %s", ...)
    ```

### Commenting out code

- When we comment out code, we should explain why it is no longer relevant
  - _Bad_
    ```python
    is_alive = pd.Series(True, index=metadata.index)
    # is_alive = kgutils.annotate_alive(metadata, self.alive_cutoff)
    ```
  - _Good_
    ```python
    # TODO(*): As discussed in PTask5047 for now we set all timeseries to be alive.
    # is_alive = kgutils.annotate_alive(metadata, self.alive_cutoff)
    is_alive = pd.Series(True, index=metadata.index)
    ```

### Use type hints

- We expect new code to use type hints whenever possible
  - See [PEP 484](https://www.python.org/dev/peps/pep-0484/)
  - [Type hints cheat sheet](https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html)
- At some point we will start adding type hints to old code
- We plan to start using static analyzers (e.g., `mypy`) to check for bugs from
  type mistakes and to enforce type hints at run-time, whenever possible

### Interval notation

- Intervals are represented with `[a, b), (a, b], (a, b), [a, b]`
- We don't use the other style `[a, b[`

### If you find a bug or obsolete docstring/TODO in the code

- The process is:
  - Do a `git blame` to find who wrote the code
  - If it's an easy bug, you can fix it and ask for a review from the author
  - You can comment on a PR (if there is one)
  - You can file a bug on Github with
    - Clear info on the problem
    - How to reproduce it, ideally a unit test
    - Stacktrace

## Linter

- The linter is in charge of reformatting the code according to our conventions
  and reporting potential problems
- You can find instructions on how to run linter at the
  [First review process](First_review_process.md) doc

### Remove linter messages

- When the linter reports a problem:
  - We assume that linter messages are correct, until the linter is proven wrong
  - We try to understand what is the rationale for the linter's complaints
  - We then change the code to follow the linter's suggestion and remove the
    lint
- If you think a message is too pedantic, please file a bug with the example and
  as a team we will consider whether to exclude that message from our list of
  linter suggestions
- If you think the message is a false positive, then try to change the code to
  make the linter happy
  - E.g., if the code depends on some run-time behavior that the linter can't
    infer, then you should question whether that behavior is really needed
  - A human reader would probably be as confused as the linter is

### When to disable linter messages

- If you really believe you should override the linter in this particular case,
  then use something like:
  ```python
  # pylint: disable=some-message,another-one
  ```
  - You then need to explain in a comment why you are overriding the linter.
  - Don't use linter code numbers, but the
    [symbolic name](https://github.com/josherickson/pylint-symbolic-names)
    whenever possible:
    - _Bad_
      ```python
      # pylint: disable=W0611
      import config.logging_settings
      ```
    - _Good_
      ```python
      # pylint: disable=unused-import
      # This is needed when evaluating code at run-time that depends from
      # this import.
      import config.logging_settings
      ```

### Prefer non-inlined linter comments

- As for the general comments, we prefer make linter comments non-inlined
- However, sometimes there is no other choice than an inlined comment to get the
  linter to understand which line we are referring to, so in rare cases it is
  OK:
  - _Bad_ but ok if needed
    ```python
    import config.logging_settings  # pylint: disable=unused-import
    ```
  - _Good_
    ```python
    # pylint: disable=line-too-long
      expected_df_as_str = """# df=
                                  asset_id   last_price            start_datetime              timestamp_db
      end_datetime
      2000-01-01 09:31:00-05:00      1000   999.874540 2000-01-01 09:30:00-05:00 2000-01-01 09:31:00-05:00
      2000-01-01 09:32:00-05:00      1000  1000.325254 2000-01-01 09:31:00-05:00 2000-01-01 09:32:00-05:00
      2000-01-01 09:33:00-05:00      1000  1000.557248 2000-01-01 09:32:00-05:00 2000-01-01 09:33:00-05:00"""
      # pylint: enable=line-too-long
    ```

### Don't mix real changes with linter changes

- We don't commit changes that modify the code together with linter
  reformatting, unless the linting is applied to the changes we just made
  - The reason for not mixing real and linter changes is that for a PR or to
    just read the code it is difficult to understand what really changed vs what
    was just a cosmetic modification
- If you are worried the linter might change your code in a way you don't like,
  e.g.,
  - Screwing up some formatting you care about for some reason, or
  - Suggesting changes that you are worried might introduce bugs you can commit
    your code and then do a "lint commit" with a message "CMTaskXYZ: Lint"
  - In this way you have a backup state that you can rollback to, if you want
- If you run the linter and see that the linter is reformatting / modifying
  pieces of code you din't change, it means that our team mate forgot to lint
  their code
  - `git blame` can figure out the culprit
  - You can send him / her a ping to remind her to lint, so you don't have to
    clean after him / her
  - In this case, the suggested approach is:
    - Commit your change to a branch / stash
    - Run the linter by itself on the files that need to be cleaned, without any
      change
    - Run the unit tests to make sure nothing is breaking
    - You can fix lints or just do formatting: it's up to you
    - You can make this change directly on `master` or do a PR if you want to be
      extra sure: your call

## Logging

### Always use logging instead of prints

- Always use `logging` and never `print()` to monitor the execution

### Our logging idiom

- In order to use our logging framework (e.g., `-v` from command lines, and much
  more) use:

  ```python
  import helpers.hdbg as hdbg

  _LOG = logging.getLogger(__name__)

  hdbg.init_logger(verbosity=logging.DEBUG)

  _LOG.debug("I am a debug function about %s", a)
  ```

- In this way one can decide how much debug info is needed (see Unix rule of
  silence)
  - E.g., when there is a bug one can run with `-v DEBUG` and see what's
    happening right before the bug

### Logging level

- Use `_LOG.warning` for messages to the final user related to something
  unexpected where the code is making a decision that might be controversial
  - E.g., processing a dir that is supposed to contain only `.csv` files the
    code finds a non-`.csv` file and decides to skip it, instead of breaking
- Use `_LOG.info` to communicate to the final user, e.g.,
  - When the script is started
  - Where the script is saving its results
  - A progress bar indicating the amount of work completed
- Use `_LOG.debug` to communicate information related to the internal behavior
  of code
  - Do not pollute the output with information a regular user does not care
    about
- Make sure the script prints when the work is terminated, e.g., "DONE" or
  "Results written to ..."
  - This is useful to indicate that the script did not die in the middle:
    sometimes this happens silently and it is reported only from the OS return
    code

### How to pick the level for a logging statement

- If all the debug info was printed at `INFO` level, the output will be too slow
  by default
- So we separate what needs to be always printed (i.e., `INFO`) and what is
  needed only if there is a problem to debug (i.e., `DEBUG`)
  - Only who writes the code should decide what is `DEBUG`, since they know what
    is needed to debug
  - In fact many loggers use multiple levels of debugging level depending of how
    much detailed debugging info are needed
- `logging` has ways to enable logging on a per module basis
   - So in prod mode you need to know which part you want to debug, since
     printing everything at `INFO` level is not possible

### Use positional args when logging

- _Bad_
  ```python
  _LOG.debug("cmd=%s %s %s" % (cmd1, cmd2, cmd3))
  _LOG.debug("cmd=%s %s %s".format(cmd1, cmd2, cmd3))
  _LOG.debug("cmd={cmd1} {cmd2} {cmd3}")
  ```
- _Good_
  ```python
  _LOG.debug("cmd=%s %s %s", cmd1, cmd2, cmd3)
  ```
- All the statements are equivalent from the functional point of view
- The reason is that in the second case the string is not built unless the
  logging is actually performed, which limits time overhead from logging

### Exceptions don't allow positional args

- For some reason people tend to believe that using the `logging` / `dassert`
  approach of positional param to exceptions
  - _Bad_ (use positional args)
    ```python
    raise ValueError("Invalid server_name='%s'", server_name)
    ```
  - _Good_ (use string interpolation)
    ```python
    raise ValueError("Invalid server_name='%s'" % server_name)
    ```
  - _Best_ (use string format)
    ```python
    raise ValueError(f"Invalid server_name='{server_name}'")
    ```
- The constructor of an exception accepts a string
- Using the string f-format is best since
  - It's more readable
  - There is little time overhead since if you get to the exception probably the
    code is going to terminate, and it's not in a hot loop

### Report warnings

- If there is a something that is suspicious but you don't feel like it's
  worthwhile to assert, report a warning with:
  ```python
  _LOG.warning(...)
  ```
- If you know that if there is a warning then there are going to be many many
  warnings
  - Print the first warning
  - Send the rest to warnings.log
  - At the end of the run, reports "there are warnings in warnings.log"

## Assertions

### Validate values before an assignment

- We consider this as an extension of a pre-condition ("only assign values that
  are correct") rather than a postcondition
- Often is more compact since it doesn't have reference to `self`
  - _Bad_
    ```python
    self._tau = tau
    hdbg.dassert_lte(self._tau, 0)
    ```
  - _Good_
    ```python
    hdbg.dassert_lte(tau, 0)
    self._tau = tau
    ```
  - _Exceptions_

    When we handle a default assignment, it's more natural to implement a
    post-condition:

    ```python
    col_rename_func = col_rename_func or (lambda x: x)
    hdbg.dassert_isinstance(col_rename_func, collections.Callable)
    ```

### Encode the assumptions using assertions

- If your code makes an assumption don’t just write a comment, but implement an
  assertion so the code can’t be executed if the assertion is not verified
  (instead of failing silently)
  ```python
  hdbg.dassert_lt(start_date, end_date)
  ```

### Use positional args when asserting

- `dassert_*` is modeled after logging so for the same reasons one should use
  positional args
- _Bad_
  ```python
  hdbg.dassert_eq(a, 1, "No info for %s" % method)
  ```
  Good
  ```python
  hdbg.dassert_eq(a, 1, "No info for %s", method)
  ```

### Report as much information as possible in an assertion

- When using a `dassert_*` you want to give to the user as much information as
  possible to fix the problem
  - E.g., if you get an assertion after 8 hours of computation you don't want to
    have to add some logging and run for 8 hours to just know what happened
- A `dassert_*` typically prints as much info as possible, but it can't report
  information that is not visible to it:
  - _Bad_
    ```python
    hdbg.dassert(string.startswith("hello"))
    ```
    - You don't know what is value of `string` is
  - _Good_
    ```python
    hdbg.dassert(string.startswith("hello"), "string='%s'", string)
    ```
    - Note that often is useful to add `'` (single quotation mark) to fight
      pesky spaces that make the value unclear, or to make the error as readable
      as possible

## Imports

### Don't use evil `import *`

- Do not use in notebooks or code the evil `import *`
  - _Bad_
    ```python
    from helpers.sql import *
    ```
  - _Good_
    ```python
    import helpers.sql as hsql
    ```
- The `from ... import *`:
  - Pollutes the namespace with the symbols and spreads over everywhere, making
    it painful to clean up
  - Obscures where each function is coming from, removing the context that comes
    with the namespace
  - [Is evil in many other ways](https://stackoverflow.com/questions/2386714/why-is-import-bad)

### Cleaning up the evil `import *`

- To clean up the mess you can:
  - For notebooks
    - Find & replace (e.g., using jupytext and Pycharm)
    - Change the import and run one cell at the time
  - For code
    - Change the import and use linter on file to find all the problematic spots
- One of the few spots where the evil `import *` is ok is in the `__init__.py`
  to tweak the path of symbols exported by a library
  - This is an advanced topic and you should rarely use it

### Avoid `from ... import ...`

- Import should always start from `import`:
  ```python
  import library as short_name
  import library.sublibrary as short_name
  ```
- This rule applies to imports of third party libraries and our library
- Because of this rule we have to always specify a short import of a parent lib
  before every code object that does not belong to the file:
  - _Bad_
    ```python
    from helpers.sql import get_connection, get_connection_from_env_vars, \
        DBConnection, wait_connection_from_db, execute_insert_query
    ```
  - _Good_
    ```python
    import helpers.sql as hsql
    ...
    ... hsql.get_connection()
    ```
- The problem with the `from ... import ...` is that it:
  - Creates lots of maintenance effort
    - E.g., anytime you want a new function you need to update the import
      statement
  - Creates potential collisions of the same name
    - E.g., lots of modules have a `read_data()` function
  - Impairs debugging
    - Importing directly in the namespace loses information about the module
    - E.g.,`read_documents()` is not clear: what documents?
    - `np.read_documents()` at least gives information of which packages is it
      coming from and enables us to track it down to the code

### Exceptions to the import style

- We try to minimize the exceptions to this rule to avoid to keep this rule
  simple, rather than discussing about
- The current agreed upon exceptions are:
  - For `typing` it is ok to do:
    ```python
    from typing import Iterable, List
    ```
    in order to avoid typing everywhere, since we want to use type hints as much
    as possible

### Always import with a full path from the root of the repo / submodule

- _Bad_
  ```python
  import exchange_class
  ```
- _Good_
  ```python
  import im_v2.ccxt.data.extract.exchange_class
  ```
  - In this way your code can run without depending upon your current dir

### Baptizing module import

- Each module that can be imported should have a docstring at the very beginning
  (before any code) describing how it should be imported

  ```python
  """
  Import as:

  import im_v2.ccxt.data.client.ccxt_clients as imvcdccccl
  """
  ```

- The import abbreviations are called 'short imports' and usually consist of 7-9
  first letters of all the words that comprise path to file
- **DO NOT** simply give a random short import name
  - Run linter to generate short import for a file automatically
- For some most files we specify short imorts by hand so thay may contain less
  symbols, e.g., `hdbg`
- The goal is to have always the same imports so it's easy to move code around,
  without collisions

### Examples of imports

- Example 1
  - _Bad_
    ```python
    from im_v2.ccxt.data.client import ccxt_clients as ccxtcl
    ```
  - _Good_
    ```python
    import im_v2.ccxt.data.client.ccxt_clients as imvcdccccl
    ```
- Example 2
  - _Bad_
    ```python
    from edgar.shared import headers_extractor as he
    ```
  - _Good_
    ```python
    import edgar.shared.headers_extractor as eshheext
    ```
- Example 3
  - _Bad_
    ```python
    from helpers import hdbg
    ```
  - _Good_
    ```python
    import helpers.hdbg as hdbg
    ```

## Scripts

### Use Python and not bash for scripting

- We prefer to use python instead of bash scripts with very few exceptions
  - E.g., scripts that need to modify the environment by setting env vars, like
    `setenv.sh`
- The problem with bash scripts is that it's too easy to put together a sequence
  of commands to automate a workflow
- Quickly things always become more complicated than what you thought, e.g.,
  - You might want to interrupt if one command in the script fails
  - You want to use command line options
  - You want to use logging to see what's going on inside the script
  - You want to do a loop with a regex check inside
- Thus you need to use the more complex features of bash scripting and bash
  scripting is absolutely horrible, much worse than perl (e.g., just think of
  `if [ ... ]` vs `if [[ ... ]]`)
- Our approach is to make simple to create scripts in python that are equivalent
  to sequencing shell commands, so that can evolve in complex scripts

### Skeleton for a script

- The ingredients are:
  - `dev_scripts/script_skeleton.py`: a template to write simple scripts you can
    copy and modify it
  - `helpers/hsystem.py`: a set of utilities that make simple to run shell
    commands (e.g., capturing their output, breaking on error or not, tee-ing to
    file, logging, ...)
  - `helpers` has lots of useful libraries
- The official reference for a script is `dev_scripts/script_skeleton.py`
  - You can copy this file and change it
  - A simple example is: `dev_scripts/git/gup.py`
  - A complex example is: `dev_scripts/replace_text.py`

### Some useful patterns

- Some useful patterns / idioms that are supported by the framework are:
  - Incremental mode: you skip an action if its outcome is already present
    (e.g., skipping creating a dir, if it already exists and it contains all the
    results)
  - Non-incremental mode: clean and execute everything from scratch
  - Dry-run mode: the commands are written to screen instead of being executed

### Use scripts and not notebooks for long-running jobs

- We prefer to use scripts to execute code that might take long time (e.g.,
  hours) to run, instead of notebooks
- Pros of script
  - All the parameters are completely specified by a command line
  - Reproducible and re-runnable
- Cons of notebooks
  - Tend to crash / hang for long jobs
  - Not easy to understand if the notebook is doing progress
  - Not easy to get debug output
- Notebooks are designed for interactive computing / debugging and not batch
  jobs
  - You can experiment with notebooks, move the code into a library, and wrap it
    in a script

### Follow the same structure

- All python scripts that are meant to be executed directly should:

  1. Be marked as executable files with:
     ```
     > chmod +x foo_bar.py
     ```
  2. Have the python code should start with the standard Unix shebang notation:
     ```python
     #!/usr/bin/env python
     ```
  - This line tells the shell to use the `python` defined in the environment
  - In this way you can execute directly without prepending with python

  3. Have a:
     ```python
     if __name__ == "__main__":
         ...
     ```
  4. Ideally use `argparse` to have a minimum of customization

### Use clear names for the scripts

- In general scripts (like functions) should have a name like "action_verb".
  - _Bad_
    - Examples of bad script names are `timestamp_extractor.py` and
      `timestamp_extractor_v2.py`
      - Which timestamp data set are we talking about?
      - What type of timestamps are we extracting?
      - What is the difference about these two scripts?
- We need to give names to scripts that help people understand what they do and
  the context in which they operate
- We can add a reference to the task that originated the work (to give more
  context)
  - _Good_
    - E.g., for a script generating a dataset there should be an (umbrella) bug
      for this dataset, that we refer in the bug name, e.g.,
      `TaskXYZ_edgar_timestamp_dataset_extractor.py`
- Also where the script is located should give some clue of what is related to

## Functions

### Avoid using non-exclusive `bool` arguments

- While a simple `True`/`False` switch may suffice for today's needs, very often
  more flexibility is eventually needed
- If more flexibility is needed for a `bool` argument, you are faced with the
  choice:
  - Adding another parameter (then parameter combinations grow exponentially and
    may not all make sense)
  - Changing the parameter type to something else
- Either way, you have to change the function interface
- To maintain flexibility from the start, opt for a `str` parameter "mode",
  which is allowed to take a small well-defined set of values.
- If an implicit default is desirable, consider making the default value of the
  parameter `None`. This is only a good route if the default operation is
  non-controversial / intuitively obvious.

### Try to make functions work on multiple types

- We encourage implementing functions that can work on multiple related types:
  - _Bad_: implement `demean_series()`, `demean_dataframe()`
  - _Good_: implement a function `demean(obj)` that can work with `pd.Series`
    and `pd.DataFrame`
    - One convention is to call `obj` the variable whose type is not known until
      run-time
- In this way we take full advantage of duck typing to achieve something similar
  to C++ function overloading (actually even more expressive)
- Try to return the same type of the input, if possible
  - E.g., the function called on a `pd.Series` returns a `pd.Series`

### Avoid hard-wired column name dependencies

- When working with dataframes, we often want need handle certain columns
  differently, or perform an operation on a strict subset of columns
- In these cases, it is tempting to assume that the special columns will have
  specific names, e.g., `"datetime"`
- The problem is that column names are
  - Rarely obvious (e.g., compare `"datetime"` vs `"timestamp"` vs `"Datetime"`)
  - Tied to specific use cases
    - The function you are writing may be written for a specific use case today,
      but what if it is more general
    - If someone wants to reuse your function in a different setting where
      different column names make sense, why should they have to conform to your
      specific use case's needs?
  - May overwrite existing column names
    - For example, you may decided to call a column `"output"`, but what if the
      dataframe already has a column with that name?
- To get around this, allow the caller to communicate to the function the names
  of any special columns
  - _Good_
    ```python
    def func(datetime_col: str):
        ...
    ```
- Make sure that you require column names only if they are actually used by the
  function
- If you must use hard-write column names internally or for some application,
  define the column name in the library file as a global variable, like
  ```python
  DATETIME_COL = "datetime"
  ```
  - Users of the library can now access the column name through imports
  - This prevents hidden column name dependencies from spreading like a virus
    throughout the codebase

### Single exit point from a function

- Consider the following _Bad_ function
  ```python
  def _get_zero_element(list_: List):
        if not list_:
            return None
        else:
            return list_[0]
  ```
  - Linter message is
    ```
    im.kibot/utils.py:394: [R1705(no-else-return), ExpiryContractMapper.extract_contract_expiry] Unnecessary "else" after "return"
    [pylint]
    ```
- Try to have a single exit point from a function, since this guarantees that
  the return value is always the same
- In general returning different data structures from the same function (e.g., a
  list in one case and a float in another) is indication of bad design
  - There are exceptions like a function that works on different types (e.g.,
    accepts a dataframe or a series and then returns a dataframe or a series,
    but the input and output is the same)
  - Returning different types (e.g., float and string) is also bad
  - Returning a type or `None` is typically ok
- Try to return values that are consistent so that the client doesn't have to
  switch statement, using `isinstance(...)`
  - E.g., return a `float` and if the value can't be computed return `np.nan`
    (instead of `None`) so that the client can use the return value in a uniform
    way
- Function examples with single exit point
  ```python
  def _get_zero_element(list_: List):
      if not list_:
          ret = np.nan
      else:
          ret = list_[0]
      return ret
  ```
  or
  ```python
  def _get_zero_element(list_: List):
      ret = np.nan if not list_ else list_[0]
      return ret
  ```
- However in rare cases it is OK to have functions like:
  ```python
  def ...(...):
      # Handle simple cases.
      ...
      if ...:
          return
      # lots of code
      ...
      return
  ```

### Order of function parameters

#### Problem

- We want to have a standard, simple, and logical order for specifying the
  arguments of a function

#### Decision

- The preferred order is:
  - Input parameters
  - Output parameters
  - In-out parameters
  - Default parameters

### Consistency of ordering of function parameters

- Try to:
  - Keep related variables close to each other
  - Keep the order of parameters similar across functions that have similar
    interface
- Enforcing these rules is based on best effort
- Pycharm is helpful when changing order of parameters
- Use linter to check consistency of types between function definition and
  invocation

### Style for default parameter

#### Problem

- How to assign default parameters in a function to make them clear and
  distinguishable?

#### Decision

- We make all the default parameters keyword-only
  - This means that we should always specify default parameters using a keyword
  - When building a function, always put default parameters after `*`
- It's ok to use a default parameter in the interface as long as it is a Python
  scalar (which is immutable by definition)
  - _Good_
    ```python
    def function(
      value: int = 5,
      *,
      dir_name: str = "hello_world",
    ):
    ```
- You should not use list, maps, objects, etc. as the default value but pass
  `None` and then initialize the default param inside the function
  - _Bad_
    ```python
    def function(
      *,
      obj: Object = Object(),
      list_: List[int] = [],
    ):
    ```
  - _Good_
    ```python
    def function(
      *,
      obj: Optional[Object] = None,
      list_: Optional[List[int]] = None,
    ):
      if obj is None:
        obj = Object()
      if list_ is None:
        list_ = []
    ```
- We use a `None` default value when a function needs to be wrapped and the
  default parameter needs to be propagated
  - _Good_

    ```python
    def function1(
      ...,
      *,
      dir_name: Optional[str] = None,
    ):
      dir_name = dir_name or "/very_long_path"

    def function2(
      ...,
      *,
      dir_name: Optional[str] = None,
    ):
      function1(..., dir_name=dir_name)
    ```

#### Rationale

- Pros of the _Good_ vs _Bad_ style
  - When you wrap multiple functions, each function needs to propagate the
    default parameters, which: - violates DRY; and - adds maintenance burden (if
    you change the innermost default parameter, you need to change all of them!)
    - With the proposed approach, all the functions use `None`, until the
      innermost function resolves the parameters to the default values
  - The interface is cleaner
  - Implementation details are hidden (e.g., why should the caller know what is
    the default path?)
  - Mutable parameters can not be passed through (see
    [here](https://stackoverflow.com/questions/1132941/least-astonishment-and-the-mutable-default-argument)))
- Cons:
  - One needs to add `Optional` to the type hint

### Calling functions with default parameters

#### Problem

- You have a function
  ```python
  def func(
    task_name : str,
    dataset_dir : str,
    *,
    clobber : bool = clobber,
  ):
  ...
  ```
- How should it be invoked?

#### Decision

- We prefer to
  - Assign directly the positional parameters
  - Bind explicitly the parameters with a default value using their name
  - Do not put actual parameter values to the function call but specify them
    right before
  - _Bad_
    ```python
    func("some_task_name", "/dir/subdir", clobber=False)
    ```
  - _Good_
    ```python
    task_name = "some_task_name"
    dataset_dir = "/dir/subdir"
    clobber = False
    func(task_name, dataset_dir, clobber=clobber)
    ```

#### Rationale

- Pros of _Good_ vs _Bad_ style
  - If a new parameter with a default value is added to the function `func`
    before `clobber`:
    - The _Good_ idiom doesn't need to be changed
    - All instances of the _Bad_ idiom need to be updated
      - The _Bad_ idiom might keep working but with silent failures
      - Of course `mypy` and `Pycharm` might point this out
  - The _Good_ style highlights which default parameters are being overwritten,
    by using the name of the parameter
    - Overwriting a default parameter is an exceptional situation that should be
      explicitly commented
- Cons:
  - None

### Don't repeat non-default parameters

#### Problem

- Given a function with the following interface:
  ```python
  def mult_and_sum(multiplier_1, multiplier_2, sum_):
      return multiplier_1 * multiplier_2 + sum_
  ```
  how to invoke it?

#### Decision

- Positional arguments are not default, so not keyword-only for consistency
  - _Bad_
    ```python
    a = 1
    b = 2
    c = 3
    mult_and_sum(multiplier_1=a,
                 multiplier_2=b,
                 sum_=c)
    ```
  - _Good_
    ```python
    a = 1
    b = 2
    c = 3
    mult_and_sum(a, b, c)
    ```

#### Rationale

- Pros of _Good_ vs _Bad_
  - Non-default parameters in Python require all the successive parameters to be
    name-assigned
    - This causes maintenance burden
  - The _Bad_ approach is in contrast with our rule for the default parameters
    - We want to highlight which parameters are overriding the default
  - The _Bad_ approach in practice requires all positional parameters to be
    assigned explicitly causing:
    - Repetition in violation of DRY (e.g., you need to repeat the same
      parameter everywhere); and
    - Maintainance burden (e.g., if you change the name of a function parameter
      you need to change all the invocations)
  - The _Bad_ style is a convention used in no language (e.g., C, C++, Java)
    - All languages allow binding by parameter position
    - Only some languages allow binding by parameter name
  - The _Bad_ makes the code very wide, creating problems with our 80 columns
    rule
- Cons of _Good_ vs _Bad_
  - One could argue that the _Bad_ form is clearer
    - IMO the problem is in the names of the variables, which are uninformative,
      e.g., a better naming achieves the same goal of clarity
      ```python
      mul1 = 1
      mul2 = 2
      sum_ = 3
      mult_and_sum(mul1, mul2, sum_)
      ```

## Writing clear beautiful code

### Keep related code close

- E.g., keep code that computes data close to the code that uses it.
- This holds also for notebooks: do not compute all the data structure and then
  analyze them.
- It’s better to keep the section that “reads data” close to the section that
  “processes it”. In this way it’s easier to see “blocks” of code that are
  dependent from each other, and run only a cluster of cells.

### Order functions in topological order

- Order functions / classes in topological order so that the ones at the top of
  the files are the "innermost" and the ones at the end of the files are the
  "outermost"
  - In this way, reading the code top to bottom one should not find a forward
    reference that requires skipping back and forth
- Linter reorders functions and classes in the topological order so make sure
  you run it after adding new ones

### Distinguish public and private functions

- The public functions `foo_bar()` (not starting with `_`) are the ones that
  make up the interface of a module and that are called from other modules and
  from notebooks
- Use private functions like `_foo_bar()` when a function is a helper of another
  private or public function
- Also follow the “keep related code close” close by keeping the private
  functions close to the functions (private or public) that are using them
- Some references:
  - [StackOverflow](https://stackoverflow.com/questions/1641219/does-python-have-private-variables-in-classes?noredirect=1&lq=1)

### Keep public functions organized in a logical order

- Keep the public functions in an order related to the use representing the
  typical flow of use, e.g.,
  - Common functions, used by all other functions
  - Read data
  - Process data
  - Save data
- You can use banners to separate layers of the code. Use the banner long 80
  cols (e.g., I have a vim macro to create banners that always look the same)
  and be consistent with empty lines before / empty and so on.
- The banner is a way of saying “all these functions belong together”.

  ```python
  # #############################################################################
  # Read data.
  # #############################################################################

  def _helper1_to_func1():
  ...
  def _helper2_to_func1():
  ...
  def func1_read_data1():
      _helper1_to_func1()
      ...
      _helper2_to_func2()

  # #############################################################################
  # Process data.
  # #############################################################################
  ...
  # #############################################################################
  # Save data.
  # #############################################################################
  ...
  ```

- Ideally each section of code should use only sections above, and be used by
  sections below (aka “Unix layer approach”).
- If you find yourself using too many banners this is in indication that code
  might need to be split into different classes or files
  - Although we don’t have agreed upon rules, it might be ok to have large files
    as long as they are well organized. E.g., in pandas code base, all the code
    for DataFrame is in a single file long many thousands of lines (!), but it
    is nicely separated in sections that make easy to navigate the code
  - Too many files can become problematic, since one needs to start jumping
    across many files: in other words it is possible to organize the code too
    much (e.g. what if each function is in a single module?)
  - Let’s try to find the right balance.
- It might be a good idea to use classes to split the code, but also OOP can
  have a dark side
  - E.g., using OOP only to reorganize the code instead of introducing
    “concepts”
  - IMO the worst issue is that they don’t play super-well with Jupyter
    autoreload

### Do not make tiny wrappers

- Examples of horrible functions:
  - How many characters do we really saved? If typing is a problem, learn to
    touch type.
    ```python
    def is_exists(path: str) -> None:
        return os.path.exists(path)
    ```
    or
    ```python
    def make_dirs(path: str) -> List[str]:
        os.makedirs(path)
    ```
  - This one can be simply replaced by `os.path.dirname`
    ```python
    def folder_name(f_name: str) -> str:
        if f_name[-1] != "/":
            return f_name + "/"
        return f_name
    ```

### Regex

- The rule of thumb is to compile a regex expression, e.g.,
  ```python
  backslash_regex = re.compile(r"\\")
  ```
  only if it's called more than once, otherwise the overhead of compilation and
  creating another var is not justified

### Do not introduce another “concept” unless really needed

- We want to introduce degrees of freedom and indirection only when we think
  this can be useful to make the code easy to maintain, read, and expand.
- If we add degrees of freedom everywhere just because we think that at some
  point in the future this might be useful, then there is very little advantage
  and large overhead.
- Introducing a new variable, function, class introduces a new concept that one
  needs to keep in mind. People that read the code, needs to go back and forth
  in the code to see what each concept means.
- Think about the trade-offs and be consistent.
- Example 1
  ```python
  def fancy_print(txt):
      print "fancy: ", txt
  ```
  - Then people that change the code need to be aware that there is a function
    that prints in a special way. The only reason to add this shallow wrapper is
    that, in the future, we believe we want to change all these calls in the
    code.
- Example 2
  ```python
  SNAPSHOT_ID = "SnapshotId"
  ```
  - Another example is parametrizing a value used in a single function.
  - If multiple functions need to use the same value, then this practice can be
    a good idea. If there is a single function using this, one should at least
    keep it local to the function.
  - Still note that introducing a new concept can also create confusion. What if
    we need to change the code to:
    ```python
    SNAPSHOT_ID = "TigerId"
    ```
    then the variable and its value are in contrast.

### Return `None` or keep one type

- Functions that return different types can make things complicated downstream,
  since the callers need to be aware of all of it and handle different cases.
  This also complicates the docstring, since one needs to explicitly explain
  what the special values mean, all the types and so on.
- In general returning multiple types is an indication that there is a problem.
- Of course this is a trade-off between flexibility and making the code robust
  and easy to understand, e.g.,
- In the following example it is better to either return `None` (to clarify that
  something special happened) or an empty dataframe `pd.DataFrame(None)` to
  allow the caller code being indifferent to what is returned.
  - _Bad_
    ```python
    if "Tags" not in df.columns:
        df["Name"] = np.nan
    else:
        df["Name"] = df["Tags"].apply(extract_name)
    ```
  - _Good_
    ```python
    if "Tags" not in df.columns:
        df["Name"] = None
    else:
        df["Name"] = df["Tags"].apply(extract_name)
    ```

### Avoid wall-of-text functions

- _Bad_
  ```python
  def get_timestamp_data(raw_df: pd.DataFrame) -> pd.DataFrame:
      timestamp_df = get_raw_timestamp(raw_df)
      documents_series = raw_df.progress_apply(he.extract_documents_v2, axis=1)
      documents_df = pd.concat(documents_series.values.tolist())
      documents_df.set_index(api.cfg.INDEX_COLUMN, drop=True, inplace=True)
      documents_df = documents_df[
          documents_df[api.cfg.DOCUMENTS_DOC_TYPE_COL] != ""]
      types = documents_df.groupby(
          api.cfg.DOCUMENTS_IDX_COL)[api.cfg.DOCUMENTS_DOC_TYPE_COL].unique()
      timestamp_df[api.cfg.TIMESTAMP_DOC_TYPES_COL] = types
      is_xbrl_series = raw_df[api.cfg.DATA_COLUMN].apply(he.check_xbrl)
      timestamp_df[api.cfg.TIMESTAMP_DOC_ISXBRL_COL] = is_xbrl_series
      timestamp_df[api.cfg.TIMESTAMP_DOC_EX99_COL] = timestamp_df[
          api.cfg.TIMESTAMP_DOC_TYPES_COL].apply(
              lambda x: any(['ex-99' in t.lower() for t in x]))
      timestamp_df = timestamp_df.rename(columns=api.cfg.TIMESTAMP_COLUMN_RENAMES)
      return timestamp_df
  ```
  - This function is correct but it has few problems (e.g., lack of a docstring,
    lots of unclear concepts, abuse of constants).
- _Good_

  ```python
  def get_timestamp_data(raw_df: pd.DataFrame) -> pd.DataFrame:
      """
      Get data containing timestamp information.

      :param raw_df: input non-processed data
      :return: timestamp data
      """
      # Get data containing raw timestamp information.
      timestamp_df = get_raw_timestamp(raw_df)
      # Extract the documents with data type information.
      documents_series = raw_df.progress_apply(he.extract_documents_v2, axis=1)
      documents_df = pd.concat(documents_series.values.tolist())
      documents_df.set_index(api.cfg.INDEX_COLUMN, drop=True, inplace=True)
      documents_df = documents_df[
          documents_df[api.cfg.DOCUMENTS_DOC_TYPE_COL] != ""
      ]
      types = documents_df.groupby(
          api.cfg.DOCUMENTS_IDX_COL
      )[api.cfg.DOCUMENTS_DOC_TYPE_COL].unique()
      # Set columns about types of information contained.
      timestamp_df[api.cfg.TIMESTAMP_DOC_TYPES_COL] = types
      is_xbrl_series = raw_df[api.cfg.DATA_COLUMN].apply(he.check_xbrl)
      timestamp_df[api.cfg.TIMESTAMP_DOC_ISXBRL_COL] = is_xbrl_series
      timestamp_df[api.cfg.TIMESTAMP_DOC_EX99_COL] = timestamp_df[
          api.cfg.TIMESTAMP_DOC_TYPES_COL
      ].apply(lambda x: any(["ex-99" in t.lower() for t in x]))
      # Rename columns to canonical representation.
      timestamp_df = timestamp_df.rename(columns=api.cfg.TIMESTAMP_COLUMN_RENAMES)
      return timestamp_df
  ```
  - You should at least split the functions in chunks using `#` or even better
    comment what each chunk of code does.

## Writing robust code

### Don’t let your functions catch the default-itis

- Default-itis is a disease of a function that manifests itself by getting too
  many default parameters.
- Default params should be used only for parameters that 99% of the time are
  constant.
- In general we require the caller to be clear and specify all the params.
- Functions catch defaultitis when the programmer is lazy and wants to change
  the behavior of a function without changing all the callers and unit tests.
  Resist this urge! `grep` is friend. Pycharm does this refactoring
  automatically.

### Explicitly bind default parameters

- It’s best to explicitly bind functions with the default params so that if the
  function signature changes, your functions doesn’t confuse a default param was
  a positional one.
  - _Bad_
    ```python
    hdbg.dassert(
        args.form or args.form_list,
        "You must specify one of the parameters: --form or --form_list",
    )
    ```
  - _Good_
    ```python
    hdbg.dassert(
        args.form or args.form_list,
        msg="You must specify one of the parameters: --form or --form_list",
    )
    ```

### Don’t hardwire params in a function call

- _Bad_
  ```python
  esa_df = universe.get_esa_universe_mapped(False, True)
  ```
  - It is difficult to read and understand without looking for the invoked
    function (aka write-only code) and it’s brittle since a change in the
    function params goes unnoticed.
- _Good_
  ```python
  gvkey = False
  cik = True
  esa_df = universe.get_esa_universe_mapped(gvkey, cik)
  ```
  - It’s better to be explicit (as usual)
  - This solution is robust since it will work as long as gvkey and cik are the
    only needed params, which is as much as we can require from the called
    function.

### Make `if-elif-else` complete

- In general all the `if-elif-else` statements should to be complete, so that
  the code is robust.
- _Bad_
  ```python
  hdbg.dassert_in(
      frequency,
      ["D", "T"]
      "Only daily ('D') and minutely ('T') frequencies are supported.",
  )
  if frequency == "T":
      ...
  if frequency == "D":
      ...
  ```
- _Good_
  ```python
  if frequency == "T":
      ...
  elif frequency == "D":
      ...
  else:
      raise ValueError("The %s frequency is not supported" % frequency)
  ```
  - This code is robust and correct
  - Still the `if-elif-else` is enough and the assertion is not needed
    - DRY here wins: you don't want to have to keep two pieces of code in sync
    - The last line is a catch-all that makes sure even if we modify the
      previous
  - It makes sense to check early only when you want to fail before doing more
    work
  - E.g., sanity checking the parameters of a long running function, so that it
    doesn't run for 1 hr and then crash because the name of the file is
    incorrect

### Add TODOs when needed

- When there is something that you know you should have done, but you didn’t
  have time to do, add a TODO, possibly using your github name e.g.,
  ```python
  # TODO(gp): …
  ```
  - In this way it’s easy to grep for your TODOs, which becomes complicated when
    using different names.
- Be clear on the meaning of TODO
  - A `TODO(Batman): clean this up` can be interpreted as
    1. "Batman suggested to clean this up"
    2. "Batman should clean this up"
    3. "Batman has the most context to explain this problem or fix it"
  - On the one hand, `git blame` will report who created the TODO, so the first
    meaning is redundant.
  - On the other hand, since we follow a shared ownership of the code, the
    second meaning should be quite infrequent. In fact the code has mostly
    `TODO(*)` todos, where `*` relates to all the team members
  - Given pros and cons, the proposal is to use the first meaning.
  - This is also what Google style guide suggests
    [here](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#312-todo-comments)
- If the TODO is associated with a Github issue, you can simply put the issue
  number and description inside the TODO, e.g.,
  ```python
  # TODO(Grisha): "Handle missing tiles" CmTask #1775.
  ```
- You can create a TODO for somebody else, or you can create a Upsource comment
  / review or Github bug, depending on how important the issue is
- If the TODO is general, e.g., anybody can fix it, then you can avoid to put a
  name. This should not be abused since it creates a culture when people don’t
  take responsibility for their mistakes.
- You can use P1, P2 to indicate if the issue is critical or not. E.g., P0 is
  the default for saying this is important, P1 is more of a “nice to have”.
  ```python
  # TODO(Sergey): P1 This can be implemented in pandas using a range generation.
  ```

## Common Python mistakes

### `==` vs `is`

- `is` checks whether two variables point to the same object (aka reference
  equality), while `==` checks if the two pointed objects are equivalent (value
  equality).
- For checking against types like `None` we want to use `is`, `is not`
  - _Bad_
    ```python
    if var == None:
    ```
  - \_Good\_\_
    ```python
    if var is None:
    ```
- For checking against values we want to use `==`
  - _Bad_
    ```python
    if unit is "minute":
    ```
  - \_Good\_\_
    ```python
    if unit == "minute":
    ```
- For more info checks
  [here](https://stackoverflow.com/questions/132988/is-there-a-difference-between-and-is-in-python)

### `type()` vs `isinstance()`

- `type(obj) == list` is worse since we want to test for reference equality (the
  type of object is a list) and not the type of obj is equivalent to a list.
- `isinstance` caters for inheritance (an instance of a derived class is an
  instance of a base class, too), while checking for equality of type does not
  (it demands identity of types and rejects instances of subtypes, AKA
  subclasses).
  - _Bad_
    ```python
    if type(obj) is list:
    ```
  - \_Good\_\_
    ```python
    if isinstance(obj, list):
    ```
- For more info check
  [here](https://stackoverflow.com/questions/1549801/what-are-the-differences-between-type-and-isinstance)

## Unit tests

- Provide a minimal end-to-end unit testing (which creates a conda environment
  and then run a few unit tests)
- Use
  - Pytest <https://docs.pytest.org/en/latest/>
  - `unittest` library
- Usually we are happy with
  - Lightly testing the tricky functions
  - Some end-to-end test to make sure the code is working
- Use your common sense
  - E.g., no reason to test code that will be used only once
- To run unit tests in a single file
  ```
  > pytest datetime_utils_test.py -x -s
  ```
- For more information on our testing conventions and guidelines, see
  `docs/coding/all.unit_tests.how_to_guide.md`

## Refactoring

### When moving / refactoring code

- If you move files, refactor code, move functions around make sure that:
  - Code and notebook work (e.g., imports and caller of the functions)
  - Documentation is updated (this is difficult, so best effort is enough)
- For code find all the places that have been modified
  ```
  > grep -r "create_dataframe" *
  edgar/form_4/notebooks/Task252_EDG4_Coverage_of_our_universe_from_Forms4.ipynb:    "documents, transactions = edu.create_dataframes(\n",
  edgar/form_4/notebooks/Task313_EDG4_Understand_Form_4_amendments.ipynb:    "documents, transactions = edu.create_dataframes(\n",
  edgar/form_4/notebooks/Task193_EDG4_Compare_form4_against_Whale_Wisdom_and_TR.ipynb:    "documents, transactions, owners, footnotes = edu.create_dataframes(\n",
  ```
- Or if you use mighty Pycharm, Ctrl + Mouse Left Click (Shows you all places
  where this function or variable was used) and try to fix them, at least to
  give your best shot at making things work
  - You can edit directly the notebooks without opening, or open and fix it.
- Good examples how you can safely rename anything for Pycharm users:
  <https://www.jetbrains.com/help/Pycharm/rename-refactorings.html>
- But remember, you must know how to do it without fancy IDE like Pycharm.
- If it’s important code:
  - Run unit tests
  - Run notebooks (see
    [here](https://n-xovwktmtjsnaxyc2mwes2xu7pohqedmdm6zjw5q-0lu-script.googleusercontent.com/userCodeAppPanel#))

### Write script for renamings

- When you need to rename any code object that is being used in many files, use
  `dev_scripts/replace_text.py` to write a script that will implement your task
  - Read the script docstring for detailed information about how to use it
- You DO NOT use `replace_text.py` directly. Instead, create an executable `.sh`
  script that uses `replace_text.py`
  - Look for examples at `dev_scripts/cleanup_scripts`
  - Commit the created script to the mentioned folder so then your team members
    can use it to implement renaming in other libs

## Architectural and design pattern

### Research quality vs production quality

- Code belonging to top level libraries (e.g., `//amp/core`, `//amp/helpers`)
  and production (e.g., `//.../db`, `vendors`) needs to meet high quality
  standards, e.g.,
  - Well commented
  - Following our style guide
  - Thoroughly reviewed
  - Good design
  - Comprehensive unit tests
- Research code in notebook and python can follow slightly looser standards,
  e.g.,
  - Sprinkled with some TODOs
  - Not perfectly general
- The reason is that:
  - Research code is still evolving and we want to keep the structure flexible
  - We don't want to invest the time in making it perfect if the research
    doesn't pan out
- Note that research code still needs to be:
  - Understandable / usable by not authors
  - Well commented
  - Follow the style guide
  - Somehow unit tested
- We should be able to raise the quality of a piece of research code to
  production quality when that research goes into production

### Always separate what changes from what stays the same

- In both main code and unit test it's not a good idea to repeat the same code
- _Bad_
  - Copy-paste-modify
- _Good_
  - Refactor the common part in a function and then change the parameters used
    to call the function
- Example:
  - What code is clearer to you, VersionA or VersionB?
  - Can you spot the difference between the 2 pieces of code?
    - Version A

      ```python
      stopwords = nlp_ut.read_stopwords_json(_STOPWORDS_PATH)
      texts = ["a", "an", "the"]
      stop_words = nlp_ut.get_stopwords(
          categories=["articles"], stopwords=stopwords
      )
      actual_result = nlp_ut.remove_tokens(texts, stop_words=stop_words)
      expected_result = []
      self.assertEqual(actual_result, expected_result)

      ...
      texts = ["do", "does", "is", "am", "are", "be", "been", "'s", "'m", "'re"]
      stop_words = nlp_ut.get_stopwords(
          categories=["auxiliary_verbs"], stopwords=stopwords,
      )
      actual_result = nlp_ut.remove_tokens(texts, stop_words=stop_words)
      expected_result = []
      self.assertEqual(actual_result, expected_result)
      ```
    - Version B

      ```python
      def _helper(texts, categories, expected_result):
          stopwords = nlp_ut.read_stopwords_json(_STOPWORDS_PATH)
          stop_words = nlp_ut.get_stopwords(
              categories=categories, stopwords=stopwords
          )
          actual_result = nlp_ut.remove_tokens(texts, stop_words=stop_words)
          expected_result = []
          self.assertEqual(actual_result, expected_result)

      texts = ["a", "an", "the"]
      categories = ["articles"]
      expected_result = []
      _helper(texts, categories, expected_result)
      ...

      texts = ["do", "does", "is", "am", "are", "be", "been", "'s", "'m", "'re"]
      categories = ["auxiliary_verbs"]
      expected_result = []
      _helper(texts, categories, expected_result)
      ```
    - Yes, Version A is _Bad_ and Version B is _Good_

### Organize scripts as pipelines

- One can organize complex computations in stages of a pipeline
  - E.g., to parse EDGAR forms
    - Download -> (raw data) -> header parser -> (pq data) -> XBLR / XML / XLS
      parser -> (pq data) -> custom transformation
- One should be able to run the entire pipeline or just a piece
  - E.g., one can run the header parser from the raw data, save the result to
    file, then read this file back, and run the XBLR parser
- Ideally one would always prefer to run the pipeline from scratch, but
  sometimes the stages are too expensive to compute over and over, so using
  chunks of the pipeline is better
- This can also mixed with the “incremental mode”, so that if one stage has
  already been run and the intermediate data has been generated, that stage is
  skipped
  - Each stage can save files in a `tmp_dir/stage_name`
- The code should be organized to allow these different modes of operations, but
  there is not always need to be super exhaustive in terms of command line
  options
  - E.g., I implement the various chunks of the pipeline in a library,
    separating functions that read / save data after a stage and then assemble
    the pieces into a throw-away script where I hardwire the file names and so
    on

### Make filename unique

- _Problem_
  - We have a lot of structure / boilerplate in our project around RH
    hypotheses.
    - E.g., there are corresponding files for all the RH like:
      - `RHxyz/configs.py`
      - `RHxyz/pipeline.py`
  - It is not clear if it's better to make filenames completely unique by
    repeating the `RH`, e.g., `RH1E_configs.py`, or let the directories
    disambiguate.
  - Note that we are not referring to other common files like `utils.py`, which
    are made unique by their position in the file system and by the automatic
    shortening of the imports.
- _Decision_
  - Invoking the principle of 'explicit is better than implicit', the proposal
    is to repeat the prefix.
    - _Bad_: `RH1E/configs.py`
    - _Good_: `RH1E/RH1E_configs.py`
- _Rationale_
  - Pros of the repetition (e.g., `RH1E/RH1E_configs.py`):
    - The filename is unique so there is no dependency on where you are
    - Since pytest requires all files to be unique, we need to repeat the prefix
      for the test names and the rule is "always make the names of the files
      unique"
    - We are going to have lots of these files and we want to minimize the risk
      of making mistakes
  - Cons of the repetition:
    - Stuttering
    - What happens if there are multiple nested dirs? Do we repeat all the
      prefixes?
      - This seems to be an infrequent case

### Incremental behavior

- Often we need to run the same code over and over
  - E.g., because the code fails on an unexpected point and then we need to
    re-run from the beginning
- We use options like:
  ```
  --incremental
  --force
  --start_date
  --end_date
  --output_file
  ```
- Check existence output file before start function (or a thread when using
  parallelism) which handle data of the corresponding period
  - If `--incremental` is set and output file already exists then skip the
    computation and report
    - Log.info(“Skipping processing file %s as requested”, …)
  - If `--incremental` is not set
    - If output file exists then we issue a log.warn and abort the process
    - If output file exists and param `--force`, then report a log.warn and
      rewrite output file

### Run end-to-end

- Try to run things end-to-end (and from scratch) so we can catch these
  unexpected issues and code defensively
  - E.g., we found out that TR data is malformed sometimes and only running
    end-to-end we can catch all the weird cases
  - This also helps with scalability issues, since if takes 1 hr for 1 month of
    data and we have 10 years of data is going to take 120 hours (=5 days) to
    run on the entire data set

### Think about scalability

- Do experiments to try to understand if a code solution can scale to the
  dimension of the data we have to deal with
  - E.g., inserting data by doing SQL inserts of single rows are not scalable
    for pushing 100GB of data
- Remember that typically we need to run the same scripts multiple times (e.g.,
  for debug and / or production)

### Use command line for reproducibility

- Try to pass params through command line options when possible
  - In this way a command line contains all the set-up to run an experiment

### Structure the code in terms of filters

- Focus on build a set of "filters" split into different functions, rather than
  a monolithic flow
- Organize the code in terms of a sequence of transformations that can be run in
  sequence, e.g.,
  1. Create SQL tables
  2. Convert json data to csv
  3. Normalize tables
  4. Load csv files into SQL
  5. Sanity check the SQL (e.g., mismatching TR codes, missing dates)
  6. Patch up SQL (e.g., inserting missing TR codes and reporting them to us so
     we can check with TR)

## Code style for different languages

### SQL

- You can use the package https://github.com/andialbrecht/sqlparse to format SQL
  queries
- There is also an on-line version of the same formatter at
  https://sqlformat.org

# Conventions (Addendum)

## Be patient

- For some reason talking about conventions makes people defensive and
  uncomfortable, sometimes.
- Conventions are not a matter of being right or wrong, but to consider pros and
  cons of different approaches, and make the decision only once instead of
  discussing the same problem every time. In this way we can focus on achieving
  the Ultimate Goal.
- If you are unsure or indifferent to a choice, be flexible and let other
  persons that seem to be less flexible decide.

## Goal

- The goal of the conventions is to simplify our job by removing ambiguity
- There is no right or wrong: that's why it's a convention and not a law of
  nature
  - On the flip-side, if there is a right and wrong, then what we are discussing
    probably shouldn’t be considered as a convention
- We don't want to spend time discussing inconsequential points
- We don't want reviewers to pick lints instead of focusing on architectural
  issues and potential bugs
- Remove cognitive burden of being distracted by "this is an annoying lint" (or
  at least perceived lint)
- Once a convention is stable, we would like to automate enforcing it by the
  linter
  - Ideally the linter should fix our mistakes so we don't even have to think
    about them, and reviewers don't have to be distracted with pointing out the
    lints

## Keep the rules simple

- E.g., assume that we accepted the following rules:
  - Git is capitalized if it refers to the tool and it's not capitalized when it
    refers to the command (this is what Git documentation suggests)
  - Python is written capitalized (this is what Python documentation suggests)
  - `pandas` is written lowercase, unless it is a beginning of the line in which
    case it's capitalized, but it's better to try to avoid to start a sentence
    with it (this is what pandas + English convention seems to suggest)
  - Any other library could suggest a different convention based on the
    preference of its author, who tries to finally force people to follow his /
    her convention …)
- All these rules require mental energy to be followed and readers will spend
  time checking that these rules are enforced, rather than focusing on bugs and
  architecture.
- In this case we want to leverage the ambiguity of "it's unclear what is the
  correct approach" by simplifying the rule
  - E.g., every name of tools or library is always capitalized
  - This is simple to remember and automatically enforce

## Allow turning off the automatic tools

- We understand that tools can't always understand the context and the
  subtleties of human thoughts, and therefore they yield inevitably to false
  positives.
- Then we always want to permit disabling the automatic checks / fixes e.g., by
  using directives in comments or special syntax (e.g., anything in a `...` or
  `…` block should be leaved untouched)
- It can be tricky determining when an exception is really needed and when
  overriding the tool becomes a slippery slope for ignoring the rules.
- Patience and flexibility is advised here.

## Make the spell-checker happy

- The spell-checker is not always right: false positives are often very annoying
- We prefer to find a way to make the spell-checker happy rather than argue that
  the spell-checker is wrong and ignore it
- The risk with overriding the spell-checker (and any other tool) is that the
  decision is not binary anymore correct / not-correct and can't be automated
  and requires mental energy to see if the flagged error is real or not.
  - E.g., `insample` is flagged as erroneous, so we convert it into `in-sample`.
- The solution for the obvious cases of missing a word (e.g., a technical word)
  is to add words to the vocabulary. This still needs to be done by everyone,
  until we find a way to centralize the vocabulary.
  - E.g., untradable is a valid English word, but Pycharm's spell-checker
    doesn't recognize it.
- TODO(\*): Should we add it to the dictionary or write it as "un-tradable"?
- Still we don't want to override the spell-checker when an alternative
  lower-cost solution is available. E.g.,
  - `in-sample` instead of `insample`
  - `out-of-sample` instead of `oos`
- We decided that `hyper-parameter` can be written without hyphen:
  `hyperparameter`
