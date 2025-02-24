

<!-- toc -->

- [Qgrid](#qgrid)
  * [Some documentation](#some-documentation)
  * [Testing](#testing)

<!-- tocstop -->

# Qgrid

## Some documentation

- GitHub: <https://github.com/quantopian/qgrid>
- Official documentation: <https://qgrid.readthedocs.io/en/latest>
- Interesting demo:
  <https://mybinder.org/v2/gh/quantopian/qgrid-notebooks/master?filepath=index.ipynb>

## Testing

- Pandas >1.0 needs qgrid at least 1.3.0 which is installed in our

  ```python
  print(qgrid.__version__)
  1.3.0
  ```

- Go to the gallery notebook as in:
  <http://localhost:10002/notebooks/amp/core/notebooks/gallery_examples.ipynb#Qgrid>

- Make sure you can see the output of the cells

- If not you might need to apply the fix as per
  <https://github.com/quantopian/qgrid/issues/253>
  - Stop the notebook server
  - Execute

  ```bash
  > jupyter nbextension enable --py --sys-prefix qgrid
  /Users/saggese/.conda/envs/develop/bin/jupytext
  jupyter nbextension enable --py --sys-prefix widgetsnbextensionEnabling notebook extension qgrid/extension...
        - Validating: OK

  > jupyter nbextension enable --py --sys-prefix widgetsnbextension
  /Users/saggese/.conda/envs/develop/bin/jupytext
  Enabling notebook extension jupyter-js-widgets/extension...
        - Validating: OK
  ```
  - Restart the notebook
  - Test again with the gallery notebook
