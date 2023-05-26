# **Structure of a notebook**


## 
**Always add a description for a notebook**

- A notebook can be used for various goals:


    - Tutorial / gallery


        - Show how some code works (e.g., functions in `signal_processing.py` or `data_encyclopedia.ipynb`)


        - The code should always work


        - We might want to add unit tests for it


    - Prototyping / one-off


        - E.g.,


            - We prototype some code, before it becomes library code


            - We did some one-off analysis


    - Analysis


        - Aka "master" notebooks


        - The notebook should always work so we need to treat it as part of the code base


        - We might want to add unit tests for it

Indicate a notebook's goal and what it does in its description, e.g.,

 
	## Description
		This notebook was used for prototyping / debugging code that was moved in the file `abc.py`



## General format of a notebook

●      Typically we use as first cells the following ones:


## Description

●      At the top of the notebook add a markdown cell explaining what this notebook does, e.g.,




### Imports
    - Import the needed libraries: it's better to put all the imports in one cell:

 


## Imports

```
%load_ext autoreload
%autoreload 2


# Standard imports.
import logging
import os


# Third-party imports.
import matplotlib.pyplot as plt
import pandas as pd


# Local imports.
import helpers.dbg as dbg
import helpers.env as env
import helpers.printing as prnt
import core.explore as exp
import core.signal_processing as sigp
...
```


●  	In this way executing one cell is enough to configure the notebook


## Configuration

	● You can configure the notebooks with some utils, logging, and report info on how the notebook was executed (e.g., Git commit, libs, etc.) by using the following cell:


# Print system signature.
```
print(env.get_system_signature()[0])


# Configure the notebook style.
prnt.config_notebook()


# Configure logger.
dbg.init_logger(verbosity=logging.INFO)
_LOG = logging.getLogger(__name__)
```



The output of the cell looks like:


```
# Packages

python: 3.7.3
joblib: 0.14.0
numpy: 1.17.3
pandas: 0.25.2
pyarrow: 0.15.0
scipy: 1.3.1
seaborn: 0.9.0
sklearn: 0.21.3
statsmodels: 0.10.1

# Last commits:
* 3c11dd7 Julia PTask461: Add correlation and autocorrelation analysis (
  22 hours ago) Thu Oct 31 14:31:14 2019 (HEAD ->
  PTask461_PRICE_Familiarize_with_target_commodities,
  origin/PTask461_PRICE_Familiarize_with_target_commodities)
* 99417bc Julia PTask418: Address a TODO in \_normalize_1_min() ( 2 days
  ago) Wed Oct 30 07:48:34 2019
* 6ad45a8 saggese More docs and lint ( 3 days ago) Tue Oct 29 21:31:55 2019
  WARNING: Running in Jupyter
```



## Make the notebook flow clear

-  	Each notebook needs to follow a clear and logical flow

-  	E.g.,


	-  	Load data


	-  	Compute stats, show some results


	-  	Clean data


	-  	Compute stats, show some results


	-  	Do analysis


	-  	Show results

The flow should be highlighted using headings in markdown:


```
# Level 1
## Level 2
### Level 3
```



●Use the extension for navigating the notebook (see our suggestions for Jupyter plug-ins)

●Keep related code and analysis close together so:
	- Readers can understand the logical flow
	- One could "easily" split the notebook in parts (e.g., when it becomes too big)
	- You can collapse the cells and don't scroll back and forth too much

## General


## 
**Keep together in a cell code that belongs together**

●  	It's often useful to keep in a cell computation that needs to be always executed together


        ○  	E.g., compute something and then print results

●  	In this way a single cell execution computes all data together

●      Often computation starts in multiple cells, e.g., to inline debugging, and once we are more confident that it works correctly we can merge it in a cell (or even better in a function)


## 
**Write beautiful code, even in notebooks**

●  	Follow the conventions and suggestions for Python code


        ○  	E.g., `code_style.md`, `design_philosophy.md`

●  	When prototyping with a notebook, the code can be of lower quality than code, but still needs to be readable and robust

●      In our opinion it's just better to always do write robust and readable code: it doesn't buy much time to cut corners


## 
**Show how data is transformed as you go**

●      Print a few lines of data structures (e.g., `df.head(3)`) so one can see how data is transformed through the cells


## 
**Use keyboard shortcuts**

●  	Learn the default keyboard shortcuts to edit efficiently

●      You can use the vim plug-in (see below) and become 3x more ninja


## 
**Strive for simplicity**

●  	Always make the notebook easy to be understood and run by somebody else

●  	Explain what happens

●  	Organize the code in a logical way

●  	Use decent variable names

●      Comment the results, when possible / needed


## 
**Dependencies among cells**

●  	Try to avoid dependencies between cells

●  	Even better avoid any dependency between cells

●  	E.g.,


- Put all the imports in one cell at the beginning, so with one cell execution you can make sure that all the imports are done
- Compare this approach with the case where the imports are randomly sprinkled in the notebook, then you need to go execute them one by one if you re-initialize the notebook

●      For the same reason group functions in one cell that you can easily re-execute


## 
**Re-execute from scratch**

● Once in a while (e.g., once a day)

● Commit your changes

● Make sure you can re-execute everything from the top with `Kernel -> Restart & Clean output` and then `Kernel -> Run all`

● Visually verify that the results didn't change, so that there is no weird state or dependency in the code

● Before a commit (and definitively before a PR) do a clean run


## 
**Add comments for complex cells**

● When a cell is too long, explain in a comment what a cell does, e.g.,

 
##
**Count stocks with all nans.**

num_nans = np.isnan(rets).sum(axis=0)
num_nans /= rets.shape[0]
num_nans.sort_values(ascending=False, inplace=True)
num_stocks_with_no_nans = (num_nans == 0.0).sum()
print("num_stocks_with_no_nans=%s" % perc(num_stocks_with_no_nans, rets.shape[1]))


●  	Another approach is to factor out the code in functions with clear names and simplify the flow


## 
**Do not cut & paste code**

●  	Cutting + paste + modify is _NEVER_ a good idea

●  	It takes more time to clean up cut & paste code than doing right in the first place

●      Just make a function out of the code and call it!


## 
**Avoid "wall-of-code" cell**

●      Obvious


## 
**Avoid data biases**

●  	Try to compute statistics on the entire data set so that results are representative and not dependent on a particular slice of the data

●  	You can sample the data and check stability of the results

●      If it takes too long to compute the statistics on the entire data set, report the problem and we can think of how to speed it up


## 
**Avoid hardwired constants**

●  	Don't use hardwired constants

●      Try to parametrize the code


## 
**Explain where data is coming from**

●  	If you are using data from a file (e.g., `/data/wd/RP_1yr_13_companies.pkl`), explain in a comment how the file was generated


    - Ideally report a command line to regenerate the data

●   The goal is for other people to be able to re-run the notebook from scratch


## 
**Use ET times**

●  	Although we store timestamps in UTC to make it canonical, try to use Eastern Times (ET) since typically financial data refers to New York time: \
 `datetime_ET = df.tz_localize(pytz.timezone('UTC')).tz_convert('US/Eastern')`

●      If you don't use timezone info `tzinfo` clarify in the variable name what timezone is used (e.g., `datetime_ET` instead of `datetime`)


## 
**Fix warnings**

●  	Like infra / dev code, a notebook should run without warnings

●      Warnings can't be ignored since they indicate that:

The code is relying on a feature that will change in the future, e.g.,


```
/utils.py:73: FutureWarning: Sorting because non-concatenation axis is
not aligned. A future version of pandas will change to not sort by
default.
To accept the future behavior, pass 'sort=False'.
To retain the current behavior and silence the warning, pass 'sort=True'.
```


- If we don't fix the issue now, the next time we create a conda environment the code might either break or (even worse) have a different behavior, i.e., silent failure


- It's better to fix the warning now that we can verify that the code does what we want to do, instead of fixing it later when we don't remember anymore what exactly we were doing

We are doing something that might have side effects, e.g., \
 `.../pandas/core/indexing.py:189: SettingWithCopyWarning:`


```
A value is trying to be set on a copy of a slice from a DataFrame
See the caveats in the documentation: http://pandas.pydata.org/pandas-docs/stable/indexing.html#indexing-view-versus-copy
```

- self._setitem_with_indexer(indexer, value)`


- This is a typical pandas warning telling us that we created a view on a dataframe (e.g., by slicing) and we are modifying the underlying data through the view


- This is dangerous since it can create unexpected side effects and coupling between pieces of code that can be painful to debug and fix

●  	If you have warnings in your code or notebook you can't be sure that the code is doing exactly what you think it is doing


- For what we know your code might be deleting your hard-disk, moving money from your account to mine, starting World War 3, ...


- You don't ever want to program by coincidence

●  	Typically the warnings are informative and tell us what's the issue and how to fix it, so please fix your code


●   If it's not obvious how to interpret or fix a warning file a bug, file a bug reporting clearly a repro case and the error message


## 
**Make cells idempotent**

●  	Try to make a notebook cell able of being executed multiple times without changing its output value, e.g.,

●  	_Bad \
 `df["id"] = df["id"] + 1`_


This computation is not idempotent, since if you execute it multiple times is going to increment the column `id` at every iteration

●  	_Good_


A better approach is to always create a new "copy", e.g.,

●      `df["incremented_df"] = df["id"] + 1`

For data frames and variables is a good idea to create copies of the data along the way: \
 `df_without1s = df[df["id"] != 1].copy()`


    ●  	`df_without1s_multipliedBy2 = df * 2`

●  	_Bad \
 `tmp = normalize(tmp)`_

●  	_Good \
 `tmp_after_normalize = normalize(tmp)`_


-In this way it's easy to add another stage in the pipeline without changing everything


-Of course the names `tmp_1`, `tmp_2` are a horrible idea since they are not self-explanatory and adding a new stage screws up the numbering


## 
**Always look at the discarded data**

●Filtering the data is a risky operation since once the data is dropped, nobody is going to go back and double check what exactly happened

●Everything downstream (e.g., all the results, all the conclusions, all the decisions based on those conclusions) rely on the filtering being correct

Any time there is a `dropna` or a filtering / masking operation, e.g., \
 `compu_data.dropna(subset=['CIK'], inplace=True)`


```


selected_metrics = [...]
compu_data = compu_data[compu_data['item'].apply(lambda x : x in selected_metrics)]
compu_data = compu_data[compu_data['datadate'].apply(date_is_quarter_end)]

```



Always count what percentage of the rows you dropped (e.g., do a back of the envelope check that you are dropping what you would expect) \
 `import helpers.printing as print_`


```
...
n_rows = compu_form_df.shape[0]
compu_form_df = compu_form_df.drop_duplicates()
n_rows_after = compu_form_df.shape[0]
```



    ●  	`_LOG.debug("After dropping duplicates kept: %s", print_.perc(n_rows_after, n_rows))`

●  	Make absolutely sure you are not dropping important data


        ○  	E.g., is the distribution of the data changed in the way you would expect?


## 
**Use a progress bar**

●      Always use progress bars (even in notebooks) so that user can see how long it will take for a certain computation

It is also possible to let `tqdm` automatically choose between console or notebook versions by using: \
 `from tqdm.autonotebook import tqdm`

# 
**Notebooks and libraries**

●  	It's ok to use functions in notebooks when building the analysis to leverage notebook interactivity

●      Once the notebook is "stable", often it's better to move the code in a library, i.e., a python file.


## 
**Pros**

●  	The same notebook code can be used for different notebooks


     -E.g., the function to read the data from disk is an obvious example

●  	More people can reuse the same code for different analyses

●  	If one changes the code in a library, Git can help tracking changes and merging, while notebooks are difficult to diff / merge

●  	Cleaning up / commenting / untangling the code can help reason carefully about the assumptions to find issues

●  	The notebook becomes more streamlined and easy to understand since now it's a sequence of functions `do_this_and_that` and presenting the results

●  	One can speed up / parallelize analyses with multiprocessing


-Notebooks are not great for this

-E.g., when one does the analyses on a small subset of the data and then wants to run on the entire large dataset

●      The exploratory analysis can be moved towards modeling and then production


## 
**Cons**

●      One disadvantage is that changes that were immediate in the notebook are not immediate anymore

That's actually not true, since using: \
 `%load_ext autoreload`


●  	`%autoreload 2 \
 `the notebook reads the changes automatically and you don't even need to execute the cell with the change

●      One doesn't have to scroll back and forth to execute the cell with the functions with all the possible mistakes


# 
**Plots**


## 
**Use the proper y-scale**

●      E.g., if one quantity can vary from -1.0 to 1.0 force the y-scale between those limits so that the values are absolutes, unless this would squash the plot


## 
**Make each plot self-explanatory**

●  	Make sure that each plot has a descriptive title, x and y label

●  	Explain the set-up of a plot / analysis


    - E.g., what is the universe of stocks used? What is the period of time?


    - Add this information also to the plots


## 
**Avoid wall-of-text tables**

●      Try to use plots summarizing the results besides the raw results in a table


## 
**Use common axes to allow visual comparisons**

●  	Try to use same axes for multiple graphs when possible to allow visual comparison between graphs

●      If that's not possible or convenient make individual plots with different scales and add a plot with multiple graphs inside on the same axis (e.g., with y-log)


## 
**Use the right plot**

●  	Pick the right type of graph to make your point


    -`pandas`, `seaborn`, `matplotlib` are your friends


# 
**Useful plugins**

●  	You can access the extensions menu:


    -`Edit -> nbextensions config`


    -`http://localhost:XYZ/nbextensions/`


## 
**Vim bindings**

●     [ VIM binding](https://github.com/lambdalisue/jupyter-vim-binding/wiki/Installation) will change your life


## 
**Table of content (2)**

●      To see the entire logical flow of the notebook, when you use the headers properly


## 
**ExecuteTime**

●      To see how long each cell takes to execute


## 
**Spellchecker**

●      To improve your English!


## 
**AutoSaveTime**

●      To save the code automatically every minute


## 
**Notify**

●      Show a browser notification when kernel becomes idle


## 
**Jupytext**

●  	We use Jupytext as standard part of our development flow

●      See `documentation/general/jupytext.md`
