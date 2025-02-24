

<!-- toc -->

- [Connecting Google Sheets to Pandas](#connecting-google-sheets-to-pandas)
  * [Installing gspread-pandas](#installing-gspread-pandas)
  * [Configuring access to your Google Drive](#configuring-access-to-your-google-drive)
  * [OAuth Client](#oauth-client)
    + [Gotchas](#gotchas)
  * [Using `gspread` on the server](#using-gspread-on-the-server)
- [Using gspread-pandas](#using-gspread-pandas)

<!-- tocstop -->

# Connecting Google Sheets to Pandas

- In order to load a Google sheet into a Pandas dataframe or the other way
  around, you can use a library called `gspread-pandas`.
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

## Configuring access to your Google Drive

- `gspread-pandas` leverages `gspread` to access Google Drive
- The most updated instructions on how to create client credentials are
  [here](https://gspread-pandas.readthedocs.io/en/latest/getting_started.html#client-credentials)
- There are two ways to authenticate
  - OAuth Client ID
  - Service account key (preferred)

- More details are in
  - Https://gspread-pandas.readthedocs.io/en/latest/configuration.html
  - Https://docs.gspread.org/en/latest/oauth2.html

- The service account key looks like

  ```txt
  > more ~/Downloads/gspread-gp-94afb83adb02.json
  {
    "type": "service_account",
    "project_id": "gspread-gp",
    "private_key_id": "94afb83adb...",
    "private_key": "-----BEGIN PRIVATE KEY...",
    "client_email": "gp-gspread@gspread-gp.iam.gserviceaccount.com",
    "client_id": "101087234...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/gp-gspread%40gspread-gp.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
  }
  ```

- Cp ~/Downloads/gspread-gp-94afb83adb02.json
  helpers/.google_credentials/service.json

- You need to have a service account key that has access to the Google Drive for
  modification
  - Normally the default one `helpers/.google_credentials/service.json` would
    work.
  - If you need to modify a Google Drive space where the default service account
    does not have access to, follow the instruction
    [here](https://gspread-pandas.readthedocs.io/en/latest/getting_started.html#client-credentials)
    to get your own `your_service.json`, store it and use it as the service
    account key path in `hgoogle_file_api.py`.
  - The process is not complicated, but it's not obvious since you need to click
    around in the GUI
  - The credentials file is a JSON downloaded from Google.

## OAuth Client

- Follow the process in https://docs.gspread.org/en/latest/oauth2.html in the
  section "Enable API Access for Project"
- Go to the Google Developers Console
  https://console.cloud.google.com/apis/dashboard?pli=1&project=gspread-gp
- Create a project using a name like "gp_gspread"
- Search for "Drive API" and click on "Enable API"
- Search for "Sheets API" and click on "Enable API"
- Click on "Credentials" and select "OAuth client ID"
  - Name can be anything (e.g., "Desktop Client 1")
  - - You should see "Client ID", "Client secrets", ...
- Then you are going to get a pop up with "OAuth client created"
  - Click "Download JSON" at the bottom
  - The file downloaded is like
    "client_secret_42164...-00pdvmfnf3lrda....apps.googleusercontent.com.json"
- The downloaded file should look like
  ```txt
  > cat ~/Downloads/client_secret_421642061916-...apps.googleusercontent.com.json | python -m json.tool
  {
      "installed": {
          "client_id": "421642061916-00pdvm... .apps.googleusercontent.com",
          "project_id": "gspread-gp",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://oauth2.googleapis.com/token",
          "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
          "client_secret": "GOCSPX-8yJsZx...",
          "redirect_uris": [
              "http://localhost"
          ]
      }
  }
  ```

### Gotchas

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
