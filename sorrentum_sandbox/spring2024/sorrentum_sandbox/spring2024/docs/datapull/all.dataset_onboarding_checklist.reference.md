

<!-- toc -->

- [Dataset onboarding checklist](#dataset-onboarding-checklist)
  * [Preparation and exploratory analysis](#preparation-and-exploratory-analysis)
  * [Implement historical downloader](#implement-historical-downloader)
  * [Automatic downloader](#automatic-downloader)
  * [QA historical downloader](#qa-historical-downloader)

<!-- tocstop -->

# Dataset onboarding checklist

We follow a standard flow when onboarding a new dataset.

Create a GH issue and paste the following checklist in the issue specification
whenever a request for a new dataset is made. The structure is pre-formatted as
a markdown checklist.

## Preparation and exploratory analysis

- [ ] Decide on the timeline
  - E.g., is this a high-priority dataset or a nice-to-have?
- [ ] Decide on the course of action
  - E.g., do we download only historical bulk data and/or also prepare a
    real-time downloader?
- [ ] Review existing code
  - Is there any downloader that is similar to the new one, in terms of
    interface, frequency, etc?
  - What code already existing can be generalized to accomplish the task at
    hand?
  - What needs to be implemented from scratch?
- [ ] Create an exploratory notebook that includes:
  - Description of the data type, if this is the first time downloading a
    certain data type
  - Example code to obtain a snippet of historical/real-time data
  - If we are interested in historical data, e.g.,
    - How far in the past the data source goes?
    - How far in the past we need the data to be?
- [ ] Create example code to obtain data in realtime
  - Is there any already clear issue with the realtime data?
    - E.g., throttling, issues with APIs, unreliability
- [ ] Perform initial QA on the data sample, e.g.,
  - Compute some statistics in terms of missing data, outliers
  - Does real-time and historical data match at first sight in terms of schema
    and content

## Implement historical downloader

- [ ] Decide what's the name of the data set according to `dataset_schema/`
      conventions
- [ ] Implement the code to perform the historical downloader
  - TODO(Juraj): Add a pointer to examples and docs
- [ ] Test the flow to download a snippet of data locally in the test stage
  - Apply QA to confirm data is being downloaded correctly
- [ ] Perform a bulk download for historical datasets
  - Manually via executing a script, if the history is short or the volume of
    data is low
  - Via an Airflow DAG if the volume of the data is too large for downloading
    manually
    - E.g.,
      `im_v2/airflow/dags/test.download_bulk_data_fargate_example_guide.py`

## Automatic downloader

- [ ] Setup automatic download of data in pre-production:
  - Since pre-prod runs with code from the master branch (updated twice a day
    automatically), make sure to merge any PRs related to the dataset onboarding
    first
  - For historical datasets:
    - To provide a single S3 location to access the entire dataset, move the
      bulk history from the test bucket to the pre-prod bucket (source and
      destination path should be identical)
    - Add a daily download Airflow task to get data from a previous day and
      append it to the existing bulk dataset
  - For real-time datasets:
    - Add a real-time download Airflow task to get data continuously 24/7

12. [ ] For some real-time datasets, an archival flow needs to be added in order
        not to overwhelm the storage
    - Consult with the team leader if it's needed for a particular dataset
    - Example Airflow DAG is
      `amp/im_v2/airflow/dags/preprod.postgres_data_archival_to_s3_fargate_new.py`

- [ ] Add an entry into the
  - [Monster dataset matrix](https://docs.google.com/spreadsheets/d/13Vyrxs9Eg-C6y91XIogLHi4A1_AFK7_KCF2KEnnxYv0/edit#gid=1908921737)
  - TODO(Juraj): Is this updated? Is there a new flow?
- Once the download is enabled in production, update the
  [Master_raw_data_gallery](https://github.com/cryptokaizen/cmamp/blob/master/im_v2/common/notebooks/Master_raw_data_gallery.ipynb)

## QA historical downloader

- [ ] If a QA flow for a similar data type exists, evaluate if it is sufficient
      and, in that case, re-use it in later steps. If it's insufficient, file an
      issue to add a new QA flow (using a Jupyter Notebook)
- [ ] Schedule the QA flow to Airflow by choosing one of the following options:
  - Creating a new DAG
  - Extending existing DAG to include a new task (preferred, if no large
    modifications are needed)
