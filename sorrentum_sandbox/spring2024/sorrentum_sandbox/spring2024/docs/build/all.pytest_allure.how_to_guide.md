# Pytest Allure How to Guide

<!-- toc -->

- [How to run the flow end-to-end via GH actions](#how-to-run-the-flow-end-to-end-via-gh-actions)
- [How to generate allure-pytest results](#how-to-generate-allure-pytest-results)
- [How to backup the Allure results](#how-to-backup-the-allure-results)
- [How to generate Allure HTML-report](#how-to-generate-allure-html-report)
  * [Keep the history of test runs](#keep-the-history-of-test-runs)
- [How to publish the Allure-HTML report](#how-to-publish-the-allure-html-report)

<!-- tocstop -->

# How to run the flow end-to-end via GH actions

Considering that we run the tests on the `cmamp` repo with the fast `tests`
group

**Important note**: Unlike usual test run, we don't stop the execution on failure.
For this we use the `continue-on-error: true` in the GitHub action step.

Here is the link to the [GitHub action file](../.github/workflows/DISABLED.allure.fast_test.yml).

# How to generate allure-pytest results

To save Allure results after a test run, append `--allure-dir` parameter to a
`pytest` cmd, e.g.,

```bash
i run_fast_tests ... --allure-dir ./allure_results
```

where `allure-dir` is the directory where the Allure results will be stored.

# How to backup the Allure results

To backup the Allure results, copy the `allure_results` directory to a AWS S3
bucket, e.g.,

```bash
aws s3 cp allure_results s3://cryptokaizen-unit-test/allure_test/cmamp/fast/results.20231120_102030 --recursive
```

where:

- `allure_results` is the directory where the Allure results are stored
- `20231120_102030` is the date and time with the mask `%Y%m%d_%H%M%S`
- `cmamp` is the name of the GitHub repo
- `fast` is the name of the tests group

# How to generate Allure HTML-report

- Whenever Allure generates a test report in a specified directory i.e.
  `allure-report` (refer to the
  ["How it works"](pytest_allure.explanation.md#how-it-works) section), it
  concurrently produces data inside the history subdirectory
- The JSON files within the history subdirectory preserve all the necessary
  information for Allure to use the data from this test report into the next
  test report, see
  [History files](https://allurereport.org/docs/how-it-works-history-files/)

To install the Allure CLI utility, refer to the
[official docs](https://allurereport.org/docs/gettingstarted-installation/).

In order to generate the HTML report, run the following command:

```
allure generate allure_results -o allure_report
```

where:

- `allure_results` is the directory where the Allure results are stored
- `allure_report` is the directory where the Allure HTML-report will be stored

TODO(Vlad): Come up with a clean-up strategy for the S3 bucket.

## Keep the history of test runs

- To activate the features related to history, copy the history subdirectory
  from the previous report into the latest test results directory before
  generating the subsequent test report
- Here is an example of how to do it, assuming that your project is configured
  to use `allure-results` and `allure-report` directories:

  - Make sure you have the previous report generated in the `allure-report`
    directory
  - Remove the `allure-results` directory
  - Run the tests with the option `--allure-dir allure_results`
  - Copy the `allure-report/history` subdirectory to `allure-results/history`
  - Generate the new report

To copy the history subdirectory from the previous run to the `allure_results`:
```bash
aws s3 cp s3://cryptokaizen-html/allure_reports/cmamp/fast/report.20231120_102030/history allure_results/history --recursive
```

# How to publish the Allure-HTML report

To publish the Allure report, copy the `allure_report` directory to a AWS S3
bucket, e.g.,

```bash
aws s3 cp allure_report s3://cryptokaizen-html/allure_reports/cmamp/fast/report.20231120_102030 --recursive
```

where:

- `allure_report` is the directory where the Allure HTML-report will be stored
- `20231120_102030` is the date and time with the mask `%Y%m%d_%H%M%S`
- `cmamp` is the name of the GitHub repo
- `fast` is the name of the tests group

For e.g., to access the HTML-report open this link on a browser:
[http://172.30.2.44/allure_reports/cmamp/fast/report.20231120_102030](http://172.30.2.44/allure_reports/cmamp/fast/report.20231120_102030)
