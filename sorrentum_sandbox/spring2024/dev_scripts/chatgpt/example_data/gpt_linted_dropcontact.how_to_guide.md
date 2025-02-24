

<!-- toc -->

- [How to extract data from DropContact](#how-to-extract-data-from-dropcontact)
  * [Locations](#locations)
  * [Dataflow](#dataflow)
    + [Input](#input)
    + [Output](#output)
  * [Usage](#usage)

<!-- tocstop -->

# How to extract data from DropContact

## Locations

- The module is located at `marketing/dropcontact`
- An example notebook is at
  `marketing/notebooks/SorrTask606_Get_email_from_dropcontact.ipynb`
- It contains a full process for extracting data using the `DropContact` API and
  adding it to an existing Google sheet

## Dataflow

### Input

- Three sequences representing `First Name`, `Last Name`, and `Company Name`
- API key for DropContact

### Output

- DataFrame containing all data available from DropContact API
- An empty string is set for data not present

## Usage

- Import the module using `import marketing.dropcontact as mrkdrop`
- The module provides a single function for the extraction of data from the
  `DropContact` API
- It takes three sequences of data (can be a Python list, pandas column, etc.)
  and an API key for DropContact
- The processing time is approximately 50 requests per minute
- In any notebook, run the following script to get a pandas dataframe
  representing the data returned from DropContact:

  ```python
  import marketing.dropcontact as mrkdrop

  API_KEY = <DropContact_API_KEY>
  first_names = <First Name Sequence>
  last_names = <Last Name Sequence>
  company_names = <Company Name Sequence>
  dropcontact_dataframe = mrkdrop.get_email_from_dropcontact(first_names, last_names, company_names, API_KEY)
  ```
