# Jupyter notebook best practices

<!-- toc -->

- [When to use a Jupyter notebook](#when-to-use-a-jupyter-notebook)
- [General structure of a notebook](#general-structure-of-a-notebook)
  * [Description](#description)
  * [Imports](#imports)
  * [Configuration](#configuration)
- [Make the notebook flow clear](#make-the-notebook-flow-clear)
- [General best practices](#general-best-practices)
  * [Update calls only for Master/Gallery notebooks](#update-calls-only-for-mastergallery-notebooks)
    + [Convention:](#convention)
    + [Rationale:](#rationale)
  * [Keep code that belongs together in one cell](#keep-code-that-belongs-together-in-one-cell)
  * [Write beautiful code, even in notebooks](#write-beautiful-code-even-in-notebooks)
  * [Show how data is transformed as you go](#show-how-data-is-transformed-as-you-go)
  * [Use keyboard shortcuts](#use-keyboard-shortcuts)
  * [Strive for simplicity](#strive-for-simplicity)
  * [Dependencies among cells](#dependencies-among-cells)
  * [Re-execute from scratch](#re-execute-from-scratch)
  * [Add comments for complex cells](#add-comments-for-complex-cells)
  * [Do not cut & paste code](#do-not-cut--paste-code)
  * [Avoid "wall-of-code" cell](#avoid-wall-of-code-cell)
  * [Avoid data biases](#avoid-data-biases)
  * [Avoid hardwired constants](#avoid-hardwired-constants)
  * [Explain where data is coming from](#explain-where-data-is-coming-from)
  * [Fix warnings](#fix-warnings)
  * [Make cells idempotent](#make-cells-idempotent)
  * [Always look at the discarded data](#always-look-at-the-discarded-data)
  * [Use a progress bar](#use-a-progress-bar)
- [Notebooks and libraries](#notebooks-and-libraries)
  * [Pros](#pros)
  * [Cons](#cons)
- [Recommendations for plots](#recommendations-for-plots)
  * [Use the proper y-scale](#use-the-proper-y-scale)
  * [Make each plot self-explanatory](#make-each-plot-self-explanatory)
  * [Avoid wall-of-text tables](#avoid-wall-of-text-tables)
  * [Use common axes to allow visual comparisons](#use-common-axes-to-allow-visual-comparisons)
  * [Use the right plot](#use-the-right-plot)
- [Useful plugins](#useful-plugins)
  * [Vim bindings](#vim-bindings)
  * [Table of content](#table-of-content)
  * [ExecuteTime](#executetime)
  * [Spellchecker](#spellchecker)
  * [AutoSaveTime](#autosavetime)
  * [Notify](#notify)
  * [Jupytext](#jupytext)
  * [Gspread](#gspread)

<!-- tocstop -->

# When to use a Jupyter notebook

- A notebook can be used for various goals:
  - Tutorial / gallery
    - Show how some code works (e.g., functions in `signal_processing.py` or
      `data_encyclopedia.ipynb`)
    - The code should always work
    - We might want to add unit tests for it
  - Prototyping / one-off
    - E.g.,
      - We prototype some code, before it becomes library code
      - We did some one-off analysis
  - Analysis
    - Aka "master" notebooks
    - The notebook should always work so we need to treat it as part of the code
      base
    - We might want to add unit tests for it

# General structure of a notebook

## Description

- At the top of the notebook add a description section explaining a notebook's
  goal and what it does, e.g.,

  ```
  # Description

  This notebook was used for prototyping / debugging code that was moved in the file `abc.py`
  ```

- Convert section headers and cells with description text to a Markdown format
  by selecting a cell and then at Jupyter interface do
  `Cell -> Cell Type -> Markdown`

## Imports

- Add a code section importing the needed libraries
  - Autoreload modules to keep Jupyter and local code updated in real-time
  - Standard imports, e.g. `os`
  - Third-party imports, e.g. `pandas`
  - Local imports from our lib
- It's better to put all the imports in one cell and separate different import
  types by 1 empty line, e.g.:

  ```
  # Imports

  %load_ext autoreload
  %autoreload 2

  import logging
  import os

  import matplotlib.pyplot as plt
  import pandas as pd

  import helpers.dbg as dbg
  import helpers.env as env
  import helpers.printing as prnt
  import core.explore as exp
  import core.signal_processing as sigp
  ...
  ```

- In this way executing one cell is enough to configure the notebook

## Configuration

- You can configure the notebooks with some utils, logging, and report info on
  how the notebook was executed (e.g., Git commit, libs, etc.) by using the
  following cell:

  ```
  # Configure logger.
  hdbg.init_logger(verbosity=logging.INFO)
  _LOG = logging.getLogger(__name__)

  # Print system signature.
  _LOG.info("%s", henv.get_system_signature()[0])

  # Configure the notebook style.
  hprint.config_notebook()
  ```

- The output of the cell looks like:
  ```
  INFO: > cmd='/venv/lib/python3.8/site-packages/ipykernel_launcher.py -f /home/.local/share/jupyter/runtime/kernel-a48f60fd-0f96-48b4-82d8-879385f2be91.json'
  WARNING: Running in Jupyter
  DEBUG Effective logging level=10
  DEBUG Shut up 1 modules: asyncio
  DEBUG > (cd . && cd "$(git rev-parse --show-toplevel)/.." && (git rev-parse --is-inside-work-tree | grep -q true)) 2>&1
  DEBUG > (git rev-parse --show-toplevel) 2>&1
  ...
  # Packages
  python: 3.8.10
  cvxopt: 1.3.0
  cvxpy: 1.2.2
  gluonnlp: ?
  gluonts: 0.6.7
  joblib: 1.2.0
  mxnet: 1.9.1
  numpy: 1.23.4
  pandas: 1.5.1
  pyarrow: 10.0.0
  scipy: 1.9.3
  seaborn: 0.12.1
  sklearn: 1.1.3
  statsmodels: 0.13.5
  ```

# Make the notebook flow clear

- Each notebook needs to follow a clear and logical flow, e.g:
  - Load data
  - Compute stats
  - Clean data
  - Compute stats
  - Do analysis
  - Show results
- The flow should be highlighted using headings in markdown:
  ```
  # Level 1
  ## Level 2
  ### Level 3
  ```
- Use the extension for navigating the notebook (see our suggestions for Jupyter
  plug-ins)
- Keep related code and analysis close together so:
  - Readers can understand the logical flow
  - One could "easily" split the notebook in parts (e.g., when it becomes too
    big)
  - You can collapse the cells and don't scroll back and forth too much

# General best practices

## Update calls only for Master/Gallery notebooks

### Convention:

- We do our best to update the calls in the Master/Gallery notebooks but we
  don't guarantee that the fix is correct
- For other notebooks we either do the fix (e.g., changing a name of a function)
  and tweak the call to enforce the old behavior, or even not do anything if
  there are too many changes

### Rationale:

- We have dozens of ad-hoc research notebooks
- When a piece of code is updated (e.g., `ImClient`) the change should be
  propagated everywhere in the code base, including the notebooks
- This results in excessive amount of maintenance work which we want to avoid

## Keep code that belongs together in one cell

- It's often useful to keep in a cell computation that needs to be always
  executed together
  - E.g., compute something and then print results
- In this way a single cell execution computes all data together
- Often computation starts in multiple cells, e.g., to inline debugging, and
  once we are more confident that it works correctly we can merge it in a cell
  (or even better in a function)

## Write beautiful code, even in notebooks

- Follow the conventions and suggestions for
  [Python code style](Coding_Style_Guide.md)
- When prototyping with a notebook, the code can be of lower quality than code,
  but still needs to be readable and robust
- In our opinion it's just better to always do write robust and readable code:
  it doesn't buy much time to cut corners

## Show how data is transformed as you go

- Print a few lines of data structures (e.g., `df.head(3)`) so one can see how
  data is transformed through the cells

## Use keyboard shortcuts

- Learn the default keyboard shortcuts to edit efficiently
- You can use the vim plug-in (see below) and become 3x more ninja

## Strive for simplicity

- Always make the notebook easy to be understood and run by somebody else
- Explain what happens
- Organize the code in a logical way
- Use decent variable names
- Comment the results, when possible / needed

## Dependencies among cells

- Try to avoid dependencies between cells
- Even better avoid any dependency between cells, e.g.:
  - Put all the imports in one cell at the beginning, so with one cell execution
    you can make sure that all the imports are done
  - Compare this approach with the case where the imports are randomly sprinkled
    in the notebook, then you need to go execute them one by one if you
    re-initialize the notebook
- For the same reason group functions in one cell that you can easily re-execute

## Re-execute from scratch

- Once in a while (e.g., once a day)
- Commit your changes
- Make sure you can re-execute everything from the top with
  `Kernel -> Restart & Clean output` and then `Kernel -> Run all`
- Visually verify that the results didn't change, so that there is no weird
  state or dependency in the code
- Before a commit (and definitively before a PR) do a clean run

## Add comments for complex cells

- When a cell is too long, explain in a comment what a cell does, e.g.,
  ```
  ## Count stocks with all nans.
  num_nans = np.isnan(rets).sum(axis=0)
  num_nans /= rets.shape[0]
  num_nans = num_nans.sort_values(ascending=False)
  num_stocks_with_no_nans = (num_nans == 0.0).sum()
  print("num_stocks_with_no_nans=%s" % hprint.perc(num_stocks_with_no_nans, rets.shape[1]))
  ```
- Another approach is to factor out the code in functions with clear names and
  simplify the flow

## Do not cut & paste code

- Cutting + paste + modify is _NEVER_ a good idea
- It takes more time to clean up cut & paste code than doing right in the first
  place
- Just make a function out of the code and call it!

## Avoid "wall-of-code" cell

- Obvious

## Avoid data biases

- Try to compute statistics on the entire data set so that results are
  representative and not dependent on a particular slice of the data
- You can sample the data and check stability of the results
- If it takes too long to compute the statistics on the entire data set, report
  the problem and we can think of how to speed it up

## Avoid hardwired constants

- Don't use hardwired constants
- Try to parametrize the code

## Explain where data is coming from

- If you are using data from a file (e.g., `/data/wd/RP_1yr_13_companies.pkl`),
  explain in a comment how the file was generated
  - Ideally report a command line to regenerate the data
- The goal is for other people to be able to re-run the notebook from scratch

## Fix warnings

- A notebook should run without warnings
- Warnings can't be ignored since they indicate that the code is relying on a
  feature that will change in the future, e.g.,
  ```
  FutureWarning: Sorting because non-concatenation axis is
  not aligned. A future version of pandas will change to not sort by
  default.
  To accept the future behavior, pass 'sort=False'.
  To retain the current behavior and silence the warning, pass 'sort=True'.
  ```
- Another example: after a cell execution the following warning appears:
  ```
  A value is trying to be set on a copy of a slice from a DataFrame
  See the caveats in the documentation: http://pandas.pydata.org/pandas-docs/stable/indexing.html#indexing-view-versus-copy
  ```
  - This is a typical pandas warning telling us that we created a view on a
    dataframe (e.g., by slicing) and we are modifying the underlying data
    through the view
  - This is dangerous since it can create unexpected side effects and coupling
    between pieces of code that can be painful to debug and fix
- If we don't fix the issue now, the next time we create a conda environment the
  code might either break or (even worse) have a different behavior, i.e.,
  _silent failure_
- It's better to fix the warning now that we can verify that the code does what
  we want to do, instead of fixing it later when we don't remember anymore what
  exactly we were doing
- If you have warnings in your code or notebook you can't be sure that the code
  is doing exactly what you think it is doing
  - For what we know your code might be deleting your hard-disk, moving money
    from your account to mine, starting World War 3, ...
  - You don't ever want to program by coincidence
- Typically the warnings are informative and tell us what's the issue and how to
  fix it, so please fix your code
  - If it's not obvious how to interpret or fix a warning file a bug, file a bug
    reporting clearly a repro case and the error message

## Make cells idempotent

- Try to make a notebook cell able of being executed multiple times without
  changing its output value, e.g.,
  - _Bad_
    ```
    df["id"] = df["id"] + 1
    ```
    - This computation is not idempotent, since if you execute it multiple times
      is going to increment the column `id` at every iteration
  - _Good_
    ```
    df["incremented_df"] = df["id"] + 1
    ```
    - A better approach is to always create a new "copy"
- Another example:
  - _Bad_
    ```
    tmp = normalize(tmp)
    ```
  - _Good_
    ```
    tmp_after_normalize = normalize(tmp)
    ```
    - In this way it's easy to add another stage in the pipeline without
      changing everything
    - Of course the names `tmp_1`, `tmp_2` are a horrible idea since they are
      not self-explanatory and adding a new stage screws up the numbering
- For data frames and variables is a good idea to create copies of the data
  along the way:
  ```
  df_without_1s = df[df["id"] != 1].copy()
  ```

## Always look at the discarded data

- Filtering the data is a risky operation since once the data is dropped, nobody
  is going to go back and double check what exactly happened
- Everything downstream (e.g., all the results, all the conclusions, all the
  decisions based on those conclusions) rely on the filtering being correct
- Any time there is a `dropna` or a filtering / masking operation, e.g.:
  ```
  compu_data = compu_data.dropna(subset=["CIK"])
  ```
  or
  ```
  selected_metrics = [...]
  compu_data = compu_data[compu_data["item"].apply(lambda x : x in selected_metrics)]
  compu_data = compu_data[compu_data["datadate"].apply(date_is_quarter_end)]
  ```
- Always count what percentage of the rows you dropped (e.g., do a back of the
  envelope check that you are dropping what you would expect)
  ```
  import helpers.printing as hprint
  ...
  n_rows = compu_form_df.shape[0]
  compu_form_df = compu_form_df.drop_duplicates()
  n_rows_after = compu_form_df.shape[0]
  _LOG.debug("After dropping duplicates kept: %s", hprint.perc(n_rows_after, n_rows))
  ```
- Make absolutely sure you are not dropping important data
  - E.g., has the distribution of the data changed in the way you would expect?

## Use a progress bar

- Always use progress bars (even in notebooks) so that user can see how long it
  will take for a certain computation.
- It is also possible to let `tqdm` automatically choose between console or
  notebook versions by using
  ```
  from tqdm.autonotebook import tqdm
  ```

# Notebooks and libraries

- It's ok to use functions in notebooks when building the analysis to leverage
  notebook interactivity
- Once the notebook is "stable", often it's better to move the code in a
  library, i.e., a python file.
- Make sure you add autoreload modules in `Imports` section
  ```
  %load_ext autoreload
  %autoreload 2
  ```
  - Otherwise, if you change a function in the lib, the notebook will not pull
    this change and use the old version of the function

## Pros

- The same notebook code can be used for different notebooks
  - E.g., the function to read the data from disk is an obvious example
- More people can reuse the same code for different analyses
- If one changes the code in a library, Git can help tracking changes and
  merging, while notebooks are difficult to diff / merge
- Cleaning up / commenting / untangling the code can help reason carefully about
  the assumptions to find issues
- The notebook becomes more streamlined and easy to understand since now it's a
  sequence of functions `do_this_and_that` and presenting the results
- One can speed up / parallelize analyses with multiprocessing
  - Notebooks are not great for this
  - E.g., when one does the analyses on a small subset of the data and then
    wants to run on the entire large dataset
- The exploratory analysis can be moved towards modeling and then production

## Cons

- One have to scroll back and forth between notebook and the libraries to
  execute the cell with the functions and fix all the possible mistakes

# Recommendations for plots

## Use the proper y-scale

- If one value can vary from -1.0 to 1.0, force the y-scale between those limits
  so that the values are absolutes, unless this would squash the plot

## Make each plot self-explanatory

- Make sure that each plot has a descriptive title, x and y label
- Explain the set-up of a plot / analysis
  - E.g., what is the universe of stocks used? What is the period of time?
  - Add this information also to the plots

## Avoid wall-of-text tables

- Try to use plots summarizing the results besides the raw results in a table

## Use common axes to allow visual comparisons

- Try to use same axes for multiple graphs when possible to allow visual
  comparison between graphs
- If that's not possible or convenient make individual plots with different
  scales and add a plot with multiple graphs inside on the same axis (e.g., with
  y-log)

## Use the right plot

- Pick the right type of graph to make your point
  - `pandas`, `seaborn`, `matplotlib` are your friends

# Useful plugins

- You can access the extensions menu:
  - `Edit -> nbextensions config`
  - `http://localhost:XYZ/nbextensions/`

## Vim bindings

- [VIM binding](https://github.com/lambdalisue/jupyter-vim-binding/wiki/Installation)
  will change your life

## Table of content

- To see the entire logical flow of the notebook, when you use the headers
  properly

## ExecuteTime

- To see how long each cell takes to execute

## Spellchecker

- To improve your English!

## AutoSaveTime

- To save the code automatically every minute

## Notify

- Show a browser notification when kernel becomes idle

## Jupytext

- We use Jupytext as standard part of our development flow
- See `docs/work_tools/all.jupytext.how_to_guide.md`

## Gspread

- Allow to read g-sheets in Jupyter Notebook
- First, one needs to configure Google API, just follow the instructions from
  [here](https://docs.gspread.org/en/latest/oauth2.html#enable-api-access)
- Useful links:
  - [Examples of gspread Usage](https://docs.gspread.org/en/latest/user-guide.html#examples-of-gspread-usage)
  - [Enabling Gsheet API](https://stackoverflow.com/questions/68721853/how-to-fix-google-sheets-api-has-not-been-used-in-project)
  - [Adding service email if it’s not working](https://stackoverflow.com/questions/38949318/google-sheets-api-returns-the-caller-does-not-have-permission-when-using-serve)
