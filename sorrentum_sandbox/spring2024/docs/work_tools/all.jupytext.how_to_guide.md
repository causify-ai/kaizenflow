

<!-- toc -->

- [Jupytext](#jupytext)
  * [Why Jupytext?](#why-jupytext)
  * [Reference documentation](#reference-documentation)
  * [Installation](#installation)
  * [Using Jupytext](#using-jupytext)
  * [Example of uses](#example-of-uses)
    + [Test that the conversion works {#test-that-the-conversion-works}](#test-that-the-conversion-works-%23test-that-the-conversion-works)
    + [Manual sync](#manual-sync)
    + [Automatic syncing when using the Jupyter server](#automatic-syncing-when-using-the-jupyter-server)
    + [Convert a notebook to script](#convert-a-notebook-to-script)
    + [Convert a script into a notebook](#convert-a-script-into-a-notebook)
    + [Remove metadata from a notebook](#remove-metadata-from-a-notebook)
    + [Linter](#linter)
    + [Refresh all the scripts](#refresh-all-the-scripts)

<!-- tocstop -->

# Jupytext

## Why Jupytext?

- In few words [Jupytext](https://github.com/mwouts/jupytext) associates a
  Python representation to a notebook, which is kept in sync with the notebook
  in a sensible way

- Jupytext allows to:
  - Edit notebooks with your favorite editor (hopefully) vi or PyCharm
  - Use a Python version of your notebook to run long computations from shell
    instead of using a notebook
  - Do a code review, diff changes, resolve conflicts using the Python code

## Reference documentation

- [https://github.com/mwouts/jupytext](https://github.com/mwouts/jupytext)
- [https://jupytext.readthedocs.io/en/latest/](https://jupytext.readthedocs.io/en/latest/)
- [https://jupytext.readthedocs.io/en/latest/faq.html](https://jupytext.readthedocs.io/en/latest/faq.html)

## Installation

- Check what version you have:

  ```bash
  > jupytext --version
  1.2.1
  ```

- Check if you have a Jupyter config:

  ```bash
  > ls ~/.jupyter/jupyter_notebook_config.py
  ```

- If you don't have a config, generate it with:

  ```bash
  > jupyter notebook --generate-config
  ```

- Edit `~/.jupyter/jupyter_notebook_config.py` and append the following:

  ```python
  #------------------------------------------------------------------------------
  # Jupytext
  #------------------------------------------------------------------------------
  c.NotebookApp.contents_manager_class = "jupytext.TextFileContentsManager"
  # Always pair ipynb notebooks to py files
  c.ContentsManager.default_jupytext_formats = "ipynb,py"
  # Use the percent format when saving as py
  c.ContentsManager.preferred_jupytext_formats_save = "py:percent"
  c.ContentsManager.outdated_text_notebook_margin = float("inf")
  ```

- Now you need to restart the notebook server to pick up Jupytext
- We use the "percent" format where cells are delimited by a `%%` comment
  - Pycharm, black, and other tools understand / respect that this is a
    delimiter for jupyter cells

## Using Jupytext

- Now when you `git add` a `.ipynb` file you always need to add also the paired
  `.py` file
- Same thing if you rename with `git mv` or delete a notebook
  - You need to explicitly take care of renaming and deleting also the `.py`
    file

## Example of uses

### Test that the conversion works {#test-that-the-conversion-works}

- Jupytext keeps a notebook and the paired `.py` file in sync
  ```bash
  > jupytext Task22.ipynb --test --to py:percent --stop
  > jupytext Task22.ipynb --test-strict --to py:percent
  ```

### Manual sync

    ```bash
    > jupytext --sync --to py:percent XYZ.ipynb
    ```

### Automatic syncing when using the Jupyter server

- After you have installed the jupytext extension, open a notebook with your
  Jupyter server
  - You should see that there is a `.py` file close to the `.ipynb` file you
    opened
  - Open the `.py` file
  - You can see that there is the code in the cells separated by `%%`

- Changes to the notebook are reflected in the file:
  - Modify the notebook and save the notebook
  - Open the `.py`
  - Note that the cell that you modified in the notebook has changed in the
    `.py` file

- Changes to the file are reflected in the notebook:
  - Modify the `.py` file, e.g., changing one cell
  - Go to the jupyter notebook and reload it
  - The cell you modified has changed!

### Convert a notebook to script

    ```bash
    > jupytext --to py:percent XYZ.ipynb
    ```

### Convert a script into a notebook

```bash
> jupytext --to notebook XYZ.py
```

### Remove metadata from a notebook

- This is equivalent to transforming the paired `.py` file in a notebook
  ```bash
  > jupytext --to notebook XYZ.py
  ```

### Linter

- The linter automatically reformats the `.py` files and then updates the
  `.ipynb` without losing the formatting
  ```bash
  > linter.py --file XYZ.py
  > jupytext --sync --to py:percent XYZ.py
  ```

### Refresh all the scripts

- The script `dev_scripts/notebooks/process_jupytext.py` automates some of the
  workflow in Jupytext (see the help)

- The script `dev_scripts/notebooks/process_all_jupytext.sh` applies
  `process_jupytext.py` to all the `ipynb` files
  ```bash
  > dev_scripts/notebooks/process_all_jupytext.sh <ACTION>
  ```
