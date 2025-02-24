

<!-- toc -->

- [Connecting Google Sheets to Pandas](#connecting-google-sheets-to-pandas)
  * [Installing gspread-pandas](#installing-gspread-pandas)
  * [Configuring gspread-pandas](#configuring-gspread-pandas)
  * [Using `gspread` on the server](#using-gspread-on-the-server)
- [Using gspread-pandas](#using-gspread-pandas)

<!-- tocstop -->

# Connecting Google Sheets to Pandas

- In order to load a Google sheet into a Pandas dataframe (or the other way
  around), you can use a library called `gspread-pandas`.
- Documentation for the package is
  [here](https://gspread-pandas.readthedocs.io/en/latest/index.html)

## Installing gspread-pandas

- The library should be automatically installed in the Dev container
- If not you can install it in the notebook with
  ```
  notebook> !pip install gspread-pandas
  ```
- Or in the Docker container with:

  ```
  docker> sudo /bin/bash -c "(source /venv/bin/activate; pip install gspread)"
  ```

- To check that the library is installed
  - In a notebook
  ```
  notebook> import gspread; print(gspread.__version__)
  ```
  - In the dev container
  ```
  docker> python -c "import gspread; print(gspread.__version__)"
  5.10.0
  ```

## Configuring gspread-pandas

- You need to have a service account key that has access to the Google drive
  space for modification
  - Normally the default one `helpers/.google_credentials/service.json` would
    work.
  - If you need to modify a Google Drive space where the default service account
    does not have access to, follow the instruction
    [here](https://gspread-pandas.readthedocs.io/en/latest/getting_started.html#client-credentials)
    to get your own `your_service.json`, store it and use it as the service
    account key path in `hgoogle_file_api.py`.
  - The process is not complicated but it's not obvious since you need to click
    around in the GUI
  - The credentials file is a JSON downloaded from Google.
- `gspread-pandas` leverages `gspread`
- Following the process in https://docs.gspread.org/en/latest/oauth2.html
- Create a project using a name like "gp_gspread"
- Search for "Drive API" and click on Enable API
- Search for "Sheets API" and click on Enable API
- On top click on "+ Create Credentials" and select OAuth client ID
- Then you are going to get a pop up with "OAuth client created"
  - Click "Download JSON" at the bottom
  - The file downloaded is like
    "client_secret_42164...-00pdvmfnf3lrda....apps.googleusercontent.com"
- Move the file to `helpers/.google_credentials/client_secrets.json` (Overwrite
  the existing placeholder file).

  ```
  > mv ~/Downloads/client_secret_421642061916-00pdvmfnf3lrdasoh2ccsnqb5akr4v9f.apps.googleusercontent.com.json ~/src/kaizenflow1/helpers/.google_credentials/client_secrets.json
  > chmod 600 ~/src/kaizenflow1/helpers/.google_credentials/client_secrets.json
  ```

- Some gotchas:
  - Make sure to act only under your `...` account.
  - `project/product/application` names don't really matter. It's convenient to
    pick a name connected to the project so that it's easy to find later.
  - Whenever you are given a choice of making something generally accessible or
    accessible only to the members of your organization, choose making it
    accessible only to the members of your organization.
  - When you are given a choice of time periods to create something for, choose
    the longest one.
  - When you are given a choice between `OAuth client ID` and `Service account`,
    choose `Service account`.

## Using `gspread` on the server

- TODO(gp): Check if this flow works
- To use the library on the server, the downloaded JSON with the credentials
  needs to be stored on the server
  ```bash
  > export SRC_FILE="~/Downloads/client_secret_4642711342-ib06g3lbv6pa4n622qusqrjk8j58o8k6.apps.googleusercontent.com.json"
  > export DST_DIR="~/.config/gspread_pandas"
  > export DST_FILE="$DST_DIR/google_secret.json"
  > mkdir -p $DST_DIR
  > mv $SRC_FILE $DST_FILE
  > chmod 600 $DST_FILE
  ```
  and copy that on the server, e.g.,
  ```bash
  > ssh research "mkdir -p $DST_DIR"
  > scp $SRC_FILE research:$DST_FILE
  > ssh research "chmod 600 $DST_FILE"
  ```

# Using gspread-pandas

- The notebook with the usage example is located at
  `amp/core/notebooks/gsheet_into_pandas_example.ipynb`.

- The official use documentation is provided
  [here](https://gspread-pandas.readthedocs.io/en/latest/using.html).

- **Don't feel stupid if you need multiple iterations to get this stuff
  working**
  - Clicking on GUI is always a recipe for low productivity
  - Go command line and vim!
