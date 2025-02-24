

<!-- toc -->

- [What it is about](#what-it-is-about)
- [Opening a notebook](#opening-a-notebook)
- [What has changed](#what-has-changed)

<!-- tocstop -->

## What it is about

- `publish_notebook.py` is a little tool that allows to:
  1. Opening a notebook in your browser (useful for read-only mode)
     - E.g., without having to use Jupyter notebook (which modifies the file in
       your client) or github preview (which is slow or fails when the notebook
       is too large)
  2. Sharing a notebook with others in a simple way
  3. Pointing to detailed documentation in your analysis Google docs
  4. Reviewing someone's notebook
  5. Comparing multiple notebooks against each other in different browser
     windows
  6. Taking a snapshot / checkpoint of a notebook as a backup or before making
     changes
     - This is a lightweight alternative to "unit testing" to capture the
       desired behavior of a notebook
     - One can take a snapshot and visually compare multiple notebooks
       side-by-side for changes

You can get details by running: `dev_scripts/notebooks/publish_notebook.py -h`

## Opening a notebook

- Inside the dev container
  ```
  docker> FILE=im_v2/common/universe/notebooks/Master_universe_analysis.ipynb; publish_notebook.py --file $FILE --action convert
  ```
- This converts the `ipynb` file into a `HTML`
- Then you can open it from outside your container
  ```
  > open Master_universe_analysis.20231214-081257.html
  ```
  or pointing the browser to it

## What has changed

We've deployed the new service for storing notebooks in HTML format

- From now on `publish_notebook.py` will work from the Docker container. The new
  version of `publish_notebook.py` works using HTTP protocol and does not
  require ssh key authorization as it was before
- We've synchronized all documents. So all old docs already available on the new
  service
