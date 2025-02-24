# Buildmeister process

<!-- toc -->

- [General](#general)
- [Notification system](#notification-system)
- [Buildmeister instructions](#buildmeister-instructions)
    + [`update_amp_submodule` fails](#update_amp_submodule-fails)
- [Buildmeister dashboard](#buildmeister-dashboard)
- [Allure Reports Analysis](#allure-reports-analysis)
- [Post-mortem analysis (TBD)](#post-mortem-analysis-tbd)

<!-- tocstop -->

# General

- The Buildmeister rotates every 2 weeks
  - To see who is the Buildmeister now refer to
    [Buildmeister gsheet](https://docs.google.com/spreadsheets/d/1Ab6a3BVeLX1l1B3_A6rNY9pHRsofeoCw2ip2dkQ6SdA/edit#gid=0)
  - Each rotation should be confirmed by a 'handshake' between the outgoing
    Buildmeister and the new one in the related Telegram chat
- The Buildmeister is responsible for:
  - Check build status using the
    [buildmeister dashboard](#buildmeister-dashboard) everyday
  - Pushing team members to fix broken tests
  - Conducting post-mortem analysis
    - Why did the break happen?
    - How can we avoid the problem next time, through process and automation?
- Refer to `.github` dir in the repo for update schedule of GH actions
- Additional information about the
  [tests](/docs/coding/all.unit_tests.how_to_guide.md)

# Notification system

- `@CK_cmamp_buildbot` notifies the team about breaks via Telegram channel
  `CK build notifications`
- A notification contains:
  - Failing tests type: fast/slow/super-slow
  - Repo
  - Branch
  - Event
  - Link to a failing run

Example:

- <img src="figs/buildmeister/image1.png">

# Buildmeister instructions

- You receive a break notification from `@CK_cmamp_buildbot`
- Have a look at the message
  - Do it right away, this is always your highest priority task
- Notify the team
  - If the break happened in `lemonade` repo, ping GP or Paul, since they are
    the only ones with write access

- Post on the `CK build notifications` Telegram channel what tests broke, e.g.,
  `FAILED knowledge_graph/vendors/test/test_utils.py::TestClean::test_clean`
  - If unsure about the cause of failure (there is a chance that a failure is
    temporary):
    - Do a quick run locally for the failed test
    - If the test is specific and can not be run locally, rerun the regressions
  - Ask if somebody knows what is the problem
    - If you know who is in charge of that test (you can use `git blame`) ask
      directly
  - If the offender says that it's fixing the bug right away, let him/her do it
  - Otherwise, file a bug to track the issue

- File an Issue in GH / ZH to report the failing tests and the errors
  - Example:
    [https://github.com/cryptokaizen/cmamp/issues/4386](https://github.com/cryptokaizen/cmamp/issues/4386)
  - Issue title template `Build fail - {repo} {test type} ({run number})`
    - Example: `Build fail - Cmamp fast_tests (1442077107)`
  - Paste the URL of the failing run
    - Example:
      [https://github.com/alphamatic/dev_tools/actions/runs/1497955663](https://github.com/alphamatic/dev_tools/actions/runs/1497955663)
  - Provide as much information as possible to give an understanding of the
    problem
  - List all the tests with FAILED status in a GitHub run, e.g.,
    ```
    FAILED knowledge_graph/vendors/test/test_p1_utils.py::TestClean::test_clean
    FAILED knowledge_graph/vendors/nbsc/test/test_nbsc_utils.py::TestExposeNBSCMetadata::test_expose_nbsc_metadata
    ```
  - Stack trace or part of it (if it's too large)
    ```
    Traceback (most recent call last): File
    "/.../automl/hypotheses/test/test*rh_generator.py", line 104, in test1
    kg_metadata, * = p1ut.load_release(version="0.5.2") File
    "/.../knowledge_graph/vendors/utils.py", line 53, in load_release % version,
    File "/.../amp/helpers/dbg.py", line 335, in dassert_dir_exists \_dfatal(txt,
    msg, \*args) File "/.../amp/helpers/dbg.py", line 97, in \_dfatal
    dfatal(dfatal_txt) File "/.../amp/helpers/dbg.py", line 48, in dfatal raise
    assertion_type(ret) AssertionError:
    ##############################################################################
    Failed assertion \*
      dir='/fsx/research/data/kg/releases/timeseries_db/v0.5.2' doesn't exist or
      it's not a dir The requested version 0.5.2 has directory associated with it.
    ```
  - Add the issue to the
    [BUILD - Breaks](https://app.zenhub.com/workspaces/cm-615371012ed326001e044788/issues/cryptokaizen/cmamp/167)
    Epic so that we can track it
  - If the failures are not connected to each other, file separate issues for
    each of the potential root cause
  - Keep issues grouped according to the codebase organization

- Post the issue reference on Telegram channel CK build notifications
  - You can quickly discuss there who will take care of the broken tests, assign
    that person
  - Otherwise, assign it to the person who can reroute

- Our policy is "fix it or revert"
  - The build needs to go back to green within 1 hr
    - Either the person responsible for the break fixes the issue within 1 hour,
      or you need to push the responsible person to disable the test
    - Do not make the decision about disabling the test yourself!
    - First, check with the responsible person, and if he / she is ok with
      disabling, do it
    - IMPORTANT: Disabling a test is not the first choice, it's a measure of
      last resort!

- Regularly check issues that belong to the Epic
  [BUILD - Breaks](https://app.zenhub.com/workspaces/cm-615371012ed326001e044788/issues/cryptokaizen/cmamp/167).
  - You have to update the break issues if the problem was solved or partially
    solved.
  - Pay special attention to the failures which resulted in disabling tests

- When your time of the Buildmeister duties is over, confirm the rotation with
  the next responsible person in the related Telegram chat.

### `update_amp_submodule` fails

- When this happens, the first thing to do is attempt to update the `amp`
  pointer manually

- Instructions:
  ```
  > cd src/dev_tools1
  > git checkout master
  > git pull --recurse-submodules
  > cd amp
  > git checkout master
  > git pull origin master
  > cd ..
  > git add "amp"
  > git commit -m "Update amp pointer"
  ```

- There is also an invoke target `git_roll_amp_forward` that does an equivalent
  operation

# Buildmeister dashboard

The Buildmeister dashboard is a tool that provides a quick overview of the
current state of the results of all GitHub Actions workflows. See
[run and publish the buildmeister dashboard](/docs/infra/ck.gh_workflows.explanation.md#run-and-publish-the-buildmeister-dashboard)
for detailed information.

# Allure Reports Analysis

- For a background on Allure, refer to these docs
  - Detailed info can be found in the official
    [docs](https://allurereport.org/docs/)
  - [Allure Explanantion](/docs/infra/all.pytest_allure.explanation.md)
  - [Allure How to Guide](/docs/infra/all.pytest_allure.how_to_guide.md)

- For now, the Buildmeister can get the link to the Allure reports by navigating
  GitHub Actions page https://github.com/cryptokaizen/cmamp/actions
  - Select a particular workflow (Allure fast tests, Allure slow tests, Allure
    superslow tests) based on the test types
  - Click on the particular run for which to get the report. Latest is on the
    top
  - Access the report URL by clicking `Report URL` in the run link. For e.g.:
    https://github.com/cryptokaizen/cmamp/actions/runs/7210433549/job/19643566697
  - The report URL looks like:
    http://172.30.2.44/allure_reports/cmamp/fast/report.20231212_013147

- Once a week the Buildmeister manually inspects
  [graph](https://allurereport.org/docs/gettingstarted-graphs/) section of the
  report
  - The overall goal is to:
    - Monitor the amount of skipped, failed, and broken tests using the
      `Trend Chart`. It shows how a certain value changed over time. Each
      vertical line corresponds to a certain version of the test report, with
      the last line on the right corresponding to the current version

      <img src="figs/buildmeister/trend.png"/>
    - Monitor the `Duration Trend` to check the time taken to the run all tests
      comparing to historical trends

      <img src="figs/buildmeister/Duration trend.png"/>
    - Monitor the `Duration Distribution`, where all the tests are divided into
      groups based on how long it took to complete them, and manually compare
      with the last week results

      <img src="figs/buildmeister/Duration Distribution.png"/>
    - Monitor the `Retries Trend` to check the number of retries occured in a
      particular run

      <img src="figs/buildmeister/Reries.png"/>
    - The idea is to make sure it doesn't have drastic change in the values

- Steps to perform if a test fails, timeouts or breaks
  - When a particular test fails, timeouts or breaks, Buildmeister should look
    in report for
    - How long it was the case, e.g., did it occur in the past? Include this
      info when filing an issue
    - The very first run when it happened and add that info to the issue. This
      could be useful for debugging purposes
    - These info can be extracted by navigating the `Packages` section of the
      report for that test. Any particular test has `history` and `retries`
      section which shows the history of success and number of retries occured
      for that test
  - The goal here is to provide more context when filing an issue so that we can
    make better decisions

# Post-mortem analysis (TBD)

- We want to understand on why builds are broken so that we can improve the
  system to make it more robust
  - In order to do that, we need to understand the failure modes of the system
  - For this reason we keep a log of all the issues and what was the root cause

- After each break fill the
  [Buildmeister spreadsheet sheet "Post-mortem breaks analysis"](https://docs.google.com/spreadsheets/d/1AajgLnRQka9-W8mKOkobg8QOzaEVOnIMlDi8wWVATeA/edit#gid=1363431255)

- `Date` column:
  - Enter the date when the break took place
  - Keep the bug ordered in reverse chronological order (i.e., most recent dates
    first)

- `Repo` column:
  - Specify the repo where break occurred
    - `amp`
    - ...

- `Test type` column:
  - Specify the type of the failing tests
    - Fast
    - Slow
    - Super-slow

- `Link` column:
  - Provide a link to a failing run

- `Reason` column:
  - Specify the reason of the break
    - Merged a branch with broken tests
    - Master was not merged in a branch
    - Merged broken slow tests without knowing that
    - Underlying data changed

- `Issue` column:
  - Provide the link to the ZH issue with the break description

- `Solution` column:
  - Provide the solution description of the problem
    - Problem that led to the break was solved
    - Failing tests were disabled, i.e. problem was not solved
