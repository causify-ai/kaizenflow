

<!-- toc -->

- [Adding a table of contents to a notebook](#adding-a-table-of-contents-to-a-notebook)
  * [Problem](#problem)
  * [Solution](#solution)
    + [How it works](#how-it-works)
    + [How to use](#how-to-use)
  * [Limitations](#limitations)

<!-- tocstop -->

# Adding a table of contents to a notebook

## Problem

- The Jupyter Notebook's extension that adds a table of contents (TOC) to a
  notebook only works on the Jupyter server. When the notebook is published as
  HTML or rendered on GitHub, the TOC added by this extension is not displayed
- We want to be able to add a TOC to a notebook in a way that is also visible in
  these environments

## Solution

- Create a custom script that adds a TOC to a notebook by parsing its contents
- The script:
  [/dev_scripts/notebooks/add_toc_to_notebook.py](/dev_scripts/notebooks/add_toc_to_notebook.py)

### How it works

- Parse the JSON representation of the notebook's contents
- Identify cells that contain headings
  - Headings are located in Markdown-type cells, start at the beginning of a
    line and consist of one or more hash signs, followed by at least one
    whitespace and then the heading text
  - E.g., "# First heading"
- Add HTML anchors to the cells where headings were found
  - E.g.,
  ```html
  <a name="first-heading"></a>
  ```
- Compose a TOC from the extracted headings, using anchors to create internal
  links to the notebook cells
- Add the TOC to the first cell of the notebook
  - If there is already a TOC in that cell, replace it with the new one to
    ensure the TOC is up-to-date

- The flow of the script resembles
  [this 3rd-party solution](https://github.com/gerbaudo/python-scripts/blob/master/various/add_toc.py).
  The principal difference is that we are not using the `nbformat` library and
  instead parse the JSON representation of the notebook's code directly
- The reason is that we prioritize transparency in parsing and prefer not to
  rely on external libraries that may unexpectedly change their behavior in the
  future

### How to use

- Run on one or more notebooks:

```bash
> dev_scripts/notebooks/add_toc_to_notebook.py \
    --input_files dir1/file1.ipynb dir2/file2.ipynb
```

- Run on a directory to process all the notebooks in it:

```bash
> dev_scripts/notebooks/add_toc_to_notebook.py \
    --input_dir dir1/
```

## Limitations

- If a notebook with the TOC added by the script is rendered on GitHub, the TOC
  is displayed but its links are broken (they do not lead to the cells with the
  corresponding headings)
- This is due to a known issue with how GitHub renders notebooks, see, for
  example, discussions
  [here](https://stackoverflow.com/questions/55065972/table-of-contents-in-jupyter-notebooks-on-github/62457712#62457712)
  and
  [here](https://stackoverflow.com/questions/38132862/html-anchors-in-a-jupyter-notebook-on-github/59254017#59254017)
- If the notebook is published as HTML, the TOC is displayed and its links work
  as expected
