# Imports and packages

<!-- toc -->

- [Goals of packages](#goals-of-packages)
  * [Circular dependency (aka import cycle, import loop)](#circular-dependency-aka-import-cycle-import-loop)
  * [Rules for imports](#rules-for-imports)
  * [How to import code from unit tests](#how-to-import-code-from-unit-tests)
    + [Common unit test code](#common-unit-test-code)
- [Package/lib hierarchy and cycle prevention](#packagelib-hierarchy-and-cycle-prevention)
- [Anatomy of a package](#anatomy-of-a-package)

<!-- tocstop -->

- TODO(gp): Consolidate here any other rule from other gdoc

# Goals of packages

- The goal of creating packages is to:

  - Simplify the import from clients
  - Hide in which file the actual code is, so that we can reorganize the code
    without having to change all the client code
  - Organize the code in related units
  - Make it simpler to avoid import loops by enforcing that there are no import
    loops in any module and no import loops among modules

- E.g., referring to package from a different package looks like
  ```python
  import dataflow.core as dtfcore
  dtfcore.ArmaGenerator(...)
  ```
- Importing the specific file:
  ```python
  import dataflow.system.source_nodes as dtfsysonod
  dtfsysonod.ArmaGenerator(...)
  ```

## Circular dependency (aka import cycle, import loop)

- The simplest case of circular import is a situation when in lib `A` we have
  `import B`, and in lib B we have `import A`
- The presence of circular imports can be checked with an invoke
  `i lint_detect_cycles`. By default, it will run on the whole repo, which takes
  a couple of minutes, but it will provide the most reliable and thorough check
  for circular imports

## Rules for imports

- We follow rules to avoid import loops:

  - Code inside a package should import directly a file in the same package and
    not use the package

    - E.g., `im_v2/common/data/client/data_frame_im_clients.py`

      - Good

        ```python
        import im_v2.common.data.client.abstract_im_clients as imvcdcaimcl
        ```

      - Bad
        ```python
        import im_v2.common.data.client as icdc
        ```

  - Code from a package should import other packages, instead of importing
    directly the file
  - We don't allow any import loop that can be detected statically (i.e., by
    inspecting the code without executing it)
    - This guarantees that there are no dynamic import loops, which are even
      more difficult to detect and disruptive
  - We allow only imports at the module level and not inside functions
    - We don't accept using local imports to break import loops, unless it's
      temporary to solve a more important problem
  - We allow nested packages
    - TODO(gp): Clarify the rules here
  - We don't want to abuse packaging by creating too many of them
    - Rationale:
      - There is overhead in organizing and maintaining code in packages and we
        want to pay the overhead only if we get enough benefit from this
  - We specify a short import in the `__init__.py` file for a package manually
    because the linter cannot do it automatically yet

    - We use the first letters to build a short import and try to keep it less
      than 8 chars long, e.g., `im_v2.talos.data.client` -> `itdcl`
    - We insert an import docstring in the `__init__.py` file manually and then
      we use the specified short import everywhere in the codebase. E.g.,

      ```python
      Import as:

      import im_v2.talos.data.client as itdcl
      ```

## How to import code from unit tests

- To avoid churning client code when code is moved among files, we allow unit
  tests to both:

  1. Import the package when testing code exported from the package
     - E.g., in `market_data/test/market_data_test_case.py` you can import the
       package even if it's included
       ```python
       import market_data as mdata
       … mdata.AbstractMarketData …
       ```
  2. Import the files directly with the code and not the package
     - E.g.,
       ```python
       import market_data.abstract_market_data as mdabmada
       … mdabmada.AbstractMarketData …
       ```

- To justify, one can argue that unit tests are clients of the code and should
  import packages like any other client
- To justify, one can interpret that unit tests are tied to specific files, so
  they should be kept in sync with the low-level code and not with the public
  interface. In fact, we already allow unit tests to call private functions,
  acknowledging that unit tests are not regular clients

- Given that both explanations are valid, we allow both styles

### Common unit test code

- Unit tests should not import from each other
  - If there is common code, it should go in libraries inside or outside `test`
    directories
    - E.g., we use `foobar_example.py` files containing builders for mocks and
      examples of objects to be used by tests
    - E.g., we use `test/foobar_test_case.py` or `test/foobar_utils.py`
  - In other terms, test files are always leaves of the import graph

# Package/lib hierarchy and cycle prevention

- Static import cycles can be detected by the invoke `lint_detect_cycles`
- To prevent import cycles, we want to enforce that certain packages don't
  depend on other packages
  - E.g., `helpers` should not depend on any other package, besides external
    libraries
  - `core` should only depend on `helpers`
  - `dataflow` should only depend on `core` and `helpers`
  - These constraints can be expressed in terms of "certain nodes of the import
    graph are sources" or "certain edges in the import graph are forbidden"
- We also want to enforce that certain libs don't import others within a single
  package. For example, in `helpers`, the following hierarchy should be
  respected:
  1. `hwarnings`, `hserver`, `hlogging`
  2. `hdbg`
  3. `hintrospection`, `hprint`
  4. `henv`, `hsystem`, `hio`, `hversio` (this is the base layer to access env
     vars and execute commands)
  5. `hgit` (Git requires accessing env vars and system calls)
- A library can only import libs that precede it or are on the same level in the
  hierarchy above.
  - E.g., `henv` can import `hdbg`, `hprint`, and `hio`, but it cannot import
    `hgit`
  - While importing a lib on the same level, make sure you are not creating an
    import cycle
- In addition, keep in mind the following rules to prevent import cycles:
  - Any import inside a function is just a temporary hack waiting to create
    problems
  - Any time we can break a file into smaller pieces, we should do that since
    this helps control the dependencies

# Anatomy of a package

- TODO(gp): Let's use `dataflow` as a running example
- A package has a special `__init__.py` exporting public methods
