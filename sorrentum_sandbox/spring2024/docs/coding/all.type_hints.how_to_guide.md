# Type hints

<!-- toc -->

   - [Why we use type hints](#why-we-use-type-hints)
   - [What to annotate with type hints](#what-to-annotate-with-type-hints)
   - [Conventions](#conventions)
      * [Empty return](#empty-return)
      * [Invoke tasks](#invoke-tasks)
      * [Annotation for kwargs](#annotation-for-kwargs)
      * [Any](#any)
      * [np.array and np.ndarray](#nparray-and-npndarray)
   - [Handling the annoying Incompatible types in assignment](#handling-the-annoying-incompatible-types-in-assignment)
   - [Handling the annoying "None" has no attribute](#handling-the-annoying-none-has-no-attribute)
   - [Disabling mypy errors](#disabling-mypy-errors)
   - [What to do when you don't know what to do](#what-to-do-when-you-dont-know-what-to-do)
   - [Library without types](#library-without-types)
   - [Inferring types using unit tests](#inferring-types-using-unit-tests)

<!-- tocstop -->

# Why we use type hints

- We use Python 3 type hints to:

  - Improve documentation
  - Allow mypy to perform static checking of the code, looking for bugs
  - Enforce the type checks at run-time, through automatic assertions (not implemented yet)

# What to annotate with type hints

- We expect all new library code (i.e., that is not in a notebook) to have type
  annotations
- We annotate the function signature
- We don't annotate the variables inside a function unless mypy reports that it
  can't infer the type
- We strive to get no errors / warnings from the linter, including mypy

# Conventions

## Empty return

- Return `-> None` if your function doesn't return

  - Pros:
    - `mypy` checks functions only when there is at least an annotation: so using
      `-> None` enables mypy to do type checking
    - It reminds us that we need to use type hints
  - Cons:
    - `None` is the default value and so it might seem redundant

## Invoke tasks

- For some reason `invoke` does not like type hints, so we

  - Omit type hints for `invoke` tasks, i.e. functions with the `@task` decorator
  - Put `# type: ignore` so that `mypy` does not complain

- Example:
  ```python
  @task 
  def run_qa_tests( # type: ignore 
    ctx, 
    stage="dev", 
    version="", 
  ):  
  ```

## Annotation for `kwargs`

- We use `kwargs: Any` and not `kwargs: Dict[str, Any]`
- `*` always binds to a `Tuple`, and `**` always binds to a `Dict[str, Any]`.
  Because of this restriction, type hints only need you to define the types of
  the contained arguments. The type checker automatically adds the
  `Tuple[_, ...]` and `Dict[str, _]` container types.
- [Reference article](https://adamj.eu/tech/2021/05/11/python-type-hints-args-and-kwargs/)

## `Any`

- `Any` type hint = no type hint
- We try to avoid it everywhere when possible

## `np.array` and `np.ndarray`

- If you get something like the following lint:
  ```bash
  dataflow/core/nodes/sklearn_models.py:537:[amp_mypy] error: Function "numpy.core.multiarray.array" is not valid as a type [valid-type]  
  ```
- Then the problem is probably that a parameter that the lint is related to
  has been typed as `np.array` while it should be typed as `np.ndarray`:
  ```python
  `x_vals: np.array` -> `x_vals: np.ndarray`
  ```

# Handling the annoying `Incompatible types in assignment`

- `mypy` assigns a single type to each variable for its entire scope
- The problem is in common idioms where we use the same variable to store
  different representations of the same data
  ```python
  output : str = ...
  output = output.split("\n")
  ...
  # Process output.
  ...
  output = "\n".join(output)
  ```
- Unfortunately the proper solution is to use different variables
  ```python
  output : str = ...
  output_as_array = output.split("\n")
  ...
  # Process output.
  ...
  output = "\n".join(output_as_array)
  ```
- Another case could be:
  ```python
  from typing import Optional
  def test_func(arg: bool):
  ...
  var: Optional[bool] = ...
  dbg.dassert_is_not(var, None)
  test_func(arg=var)
  ```
- Sometimes `mypy` doesn't pick up the `None` check, and warns that the function
  expects a `bool` rather than an `Optional[bool]`. In that case, the solution
  is to explicitly use `typing.cast` on the argument when passing it in, note
  that `typing.cast` has no runtime effects and is purely for type checking.
- Here're the relevant [docs](https://mypy.readthedocs.io/en/stable/casts.html)
- So the solution would be:
  ```python
  from typing import cast ...
  ...
  test_func(arg=cast(bool, var))
  ```

# Handling the annoying `"None" has no attribute`

- In some model classes `self._model` parameter is being assigned to `None` in
  ctor and being set after calling `set_fit_state` method
- The problem is that statically it's not possible to understand that someone
  will call `set_fit_state` before using `self._model`, so when a model's method
  is applied:
  ```python
  self._model = self._model.fit(...)
  ```
  the following lint appears:
  ```bash
  dataflow/core/nodes/sklearn_models.py:155:[amp_mypy] error: "None" has no attribute "fit"
  ```
- A solution is to
  - Type hint when assigning the model parameter in ctor:
     ```python
     self._model: Optional[sklearn.base.BaseEstimator] = None
     ```
  - Cast a type to the model parameter after asserting that it is not `None`:
     ```python
     hdbg.dassert_is_not(self._model, None)
     self._model = cast(sklearn.base.BaseEstimator, self._model)
     ```

# Disabling `mypy` errors

- If `mypy` reports an error and you don't understand why, please ping one of
  the python experts asking for help
- If you are sure that you understand why `mypy` reports and error and that you
  can override it, you disable this `error`
- When you want to disable an error reported by `mypy`:
  - Add a comment reporting the `mypy` error
  - Explain why this is not a problem
  - Add `# type: ignore` with two spaces as usual for the inline comment
  - Example
    ```python
    # mypy: Cannot find module named 'pyannotate_runtime'
    # pyannotate is not always installed
    from pyannotate_runtime import collect_types # type: ignore
    ```

# What to do when you don't know what to do

- Go to the [`mypy` official cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- Use `reveal_type`
  - To find out what type `mypy` infers for an expression anywhere in your
    program, wrap it in `reveal_type()`
  - `mypy` will print an error message with the type; remove it again before
    running the code
  - See [the official `mypy` documentation](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html#when-you-re-puzzled-or-when-things-are-complicated)

# Library without types

- `mypy` is unhappy when a library doesn't have types
- Lots of libraries are starting to add type hints now that python 2 has been
  deprecated
  ```bash
  *.py:14: error: No library stub file for module 'sklearn.model_selection' [mypy]
  ```
- You can go in `mypy.ini` and add the library (following the alphabetical
  order) to the list
- Note that you need to ensure that different copies of `mypy.ini` in different
  sub projects are equal
  ```bash
  > vimdiff mypy.ini amp/mypy.ini
  or
  > cp mypy.ini amp/mypy.ini
  ```

# Inferring types using unit tests

- Sometimes it is possible to infer types directly from unit tests. We have used
this flow to annotate the code when we switched to Python3 and it worked fine
although there were various mistakes. We still prefer to annotate by hand based
on what the code is intended to do, rather than automatically infer it from how
the code behaves.

  - Install `pyannotate`
    ```bash
    > pip install pyannotate
    ```
  - To enable collecting type hints run
    ```bash
    > export PYANNOTATE=True
    ```
  - Run `pytest`, e.g., on a subset of unit tests:
  - Run `pytest`, e.g., on a subset of unit tests like `helpers`:
    ```bash
    > pytest helpers
    ```
  - A file `type_info.json` is generated
  - Annotate the code with the inferred types:
    ```bash
    > pyannotate -w --type-info type_info.json . --py3
    ```
