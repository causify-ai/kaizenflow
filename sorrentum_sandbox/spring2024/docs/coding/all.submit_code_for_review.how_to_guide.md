# First Review Process

<!-- toc -->

- [Read Python Style Guide](#read-python-style-guide)
- [Run linter](#run-linter)
- [Compare your code to example code](#compare-your-code-to-example-code)
- [Save Reviewer time](#save-reviewer-time)
  * [Assign Reviewers](#assign-reviewers)
  * [Mention the issue](#mention-the-issue)
  * [Resolve conversations](#resolve-conversations)
  * [Merge master to your branch](#merge-master-to-your-branch)
  * [Ask for reviews](#ask-for-reviews)
  * [Do not use screenshots](#do-not-use-screenshots)
  * [Report bugs correctly](#report-bugs-correctly)
- [Talk through code and not GitHub](#talk-through-code-and-not-github)
- [Look at examples of the first reviews](#look-at-examples-of-the-first-reviews)

<!-- tocstop -->

We understand that receiving feedback on your code can be a difficult process,
but it is an important part of our development workflow. Here we have gathered
some helpful tips and resources to guide you through your first review.

## Read Python Style Guide

- Before submitting your code for review, we highly recommend that you read the
  [Python Style Guide](all.coding_style.how_to_guide.md), which outlines the
  major conventions and best practices for writing Python code.
- Adhering to these standards will help ensure that your code is easy to read,
  maintain, and understand for other members of the team.

## Run linter

- Linter is a tool that checks (and tries to fix automatically) your code for
  syntax errors, style violations, and other issues.
- Run it on all the changed files to automatically catch any code issues before
  filing any PR or before requesting a review!
- To be able to run the linter, you need to you need to set up your client first
  since you're outside Docker:
  - The instructions are available at
    [KaizenFlow_development_setup.md](/docs/onboarding/kaizenflow.set_up_development_environment.how_to_guide.md)
  - In practice you need to have run
    ```
    > source dev_scripts/setenv_amp.sh
    ```
- Run the linter with `invoke` command (which is abbreviated as `i`) and pass
  all the files you need to lint in brackets after the `--files` option,
  separated by a space:
  ```
  > i lint --files "defi/tulip/implementation/order.py defi/tulip/implementation/order_matching.py"
  ```
  - Output example:
    ```
    defi/tulip/implementation/order_matching.py:14: error: Cannot find implementation or library stub for module named 'defi.dao_cross'  [import]
    defi/tulip/implementation/order_matching.py:69: error: Need type annotation for 'buy_heap' (hint: "buy_heap: List[<type>] = ...")  [var-annotated]
    defi/tulip/implementation/order_matching.py:70: error: Need type annotation for 'sell_heap' (hint: "sell_heap: List[<type>] = ...")  [var-annotated]
    ...
    ```
  - `i lint` has options for many workflows. E.g., you can automatically lint
    all the files that you touched in your PR with `--branch`, the files in the
    last commit with `--last-commit`. You can look at all the options with:
    ```
    > i lint --help
    ```
- Fix the lints
  - No need to obsessively fix all of them - just crucial and obvious ones
  - Post unresolved lints in your PR so Reviewer could see them and know which
    should be fixed and which are not
- If we see that people didn't run the linter, we should do a quick PR just
  running the linter. This type of PR can be merged even without review.
- If the linter introduces extensive changes in a PR, causing difficulty in
  reading the diff, a new pull request should be created exclusively for the
  linter changes, based on the branch of the original PR.

## Compare your code to example code

- To get an idea of what well-formatted and well-organized code looks like, we
  suggest taking a look at some examples of code that adhere to our standards.
- We try to maintain universal approaches to all the parts of the code, so when
  looking at a code example, check for:
  - Code style
  - Docstrings and comments
  - Type hints
  - Containing directory structure
- Here are some links to example code:
  - Classes and functions:
    - `defi/tulip/implementation/order.py`
    - `defi/tulip/implementation/order_matching.py`
  - Unit tests:
    - `defi/tulip/test/test_order_matching.py`
    - `defi/tulip/test/test_optimize.py`
  - Scripts:
    - `dev_scripts/replace_text.py`
    - `dev_scripts/lint_md.sh`

## Save Reviewer time

### Assign Reviewers

- Make sure to select a Reviewer in a corresponding GitHub field so he/she gets
  notified
  - <img width="313" alt="" src="https://github.com/kaizen-ai/kaizenflow/assets/31514660/f8534c49-bff6-4d59-9037-d70dc03d5ff9">
  - Junior contributors should assign Team Leaders (e.g., Grisha, DanY, Samarth,
    ...) to review their PR
    - Team Leaders will assign integrators (GP & Paul) themselves after all
      their comments are implemented
  - Ping the assigned Reviewer in the issue if nothing happens in 24 hours
  - If you want to keep someone notified about changes in the PR but do not want
    to make him/her a Reviewer, type `FYI @github_name` in a comment section

### Mention the issue

- Mention the corresponding issue in the PR description to ease the navigation
  - E.g., see an
    [example](https://github.com/kaizen-ai/kaizenflow/pull/288#issue-1729654983)
    - <img width="505" alt="" src="https://github.com/kaizen-ai/kaizenflow/assets/31514660/69fbabec-300c-4f7c-94fc-45c5da5a6817">

### Resolve conversations

- When you've implemented a comment from a Reviewer, press
  `Resolve conversation` button so the Reviewer knows that you actually took
  care of it
  - <img width="328" alt="" src="https://github.com/kaizen-ai/kaizenflow/assets/31514660/a4c79d73-62bd-419b-b3cf-e8011621ba3c">

### Merge master to your branch

- Before any PR review request do `i git_merge_master` in order to keep the code
  updated
  - Resolve conflicts if there are any
  - Do not forget to push it since this action is a commit itself
- Actually, a useful practice is to merge master to your branch every time you
  to get back to work on it
  - This way you make sure that your branch is always using a relevant code and
    avoid huge merge conflicts
- **NEVER** press `Squash and merge` button yourself
  - You need to merge master branch to your branch - not vice verca!
  - This is a strictly Team Leaders and Integrators responsibility

### Ask for reviews

- When you've implemented all the comments and need another round of review:
  - Press the circling arrows sign next to the Reviewer for the ping
    - <img width="280" alt="" src="https://github.com/kaizen-ai/kaizenflow/assets/31514660/4f924f4f-abab-40be-975d-a4fa81d9af3b">
  - Remove `PR_for_authors` and add `PR_for_reviewers` label (labels
    [desc](/docs/work_organization/all.use_github_and_zenhub.how_to_guide.md#pr-labels))
    - <img width="271" alt="" src="https://github.com/kaizen-ai/kaizenflow/assets/31514660/3580bf34-dcba-431b-af5c-5ae65f7597c3">

### Do not use screenshots

- Stack trace and logs are much more convenient to use for debugging
- Screenshots are often too small to capture both input and return logs while
  consuming a lot of basically useless memory
- The exceptions are plots and non-code information
- Examples:
  - _Bad_

    <img width="677" alt="scree" src="https://github.com/kaizen-ai/kaizenflow/assets/31514660/699cd1c5-53d2-403b-a0d7-96c66d4360ce">
  - _Good_

    Input:
    ```
    type_ = "supply"
    supply_curve1 = ddcrsede.get_supply_demand_discrete_curve(
        type_, supply_orders_df1
    )
    supply_curve1
    ```

    Error:
    ```
    ---------------------------------------------------------------------------
    NameError                                 Traceback (most recent call last)
    Cell In [5], line 2
          1 type_ = "supply"
    ----> 2 supply_curve1 = ddcrsede.get_supply_demand_discrete_curve(
          3     type_, supply_orders_df1
          4 )
          5 supply_curve1

    NameError: name 'ddcrsede' is not defined
    ```

### Report bugs correctly

- Whenever you face any errors put as much information about the issue as
  possible, e.g.,:
  - What you are trying to achieve
  - Command line you ran, e.g.,
    ```
    > i lint -f defi/tulip/test/test_dao_cross_sol.py
    ```
  - **Copy-paste** the error and the stack trace from the cmd line, **no
    screenshots**, e.g.,
    ```
    Traceback (most recent call last):
      File "/venv/bin/invoke", line 8, in <module>
        sys.exit(program.run())
      File "/venv/lib/python3.8/site-packages/invoke/program.py", line 373, in run
        self.parse_collection()
    ValueError: One and only one set-up config should be true:
    ```
  - The log of the run
    - Maybe the same run using `-v DEBUG` to get more info on the problem
  - What the problem is
  - Why the outcome is different from what you expected
  - E.g. on how to report any issues
    - https://github.com/kaizen-ai/kaizenflow/issues/370#issue-1782574355

## Talk through code and not GitHub

- Authors of the PR should not initiate talking to reviewers through GitHub but
  only through code
  - E.g., if there is something you want to explain to the reviewers, you should
    not comment your own PR, but should add comments or improve the code
  - Everything in GitHub is lost once the PR is closed, so all knowledge needs
    to go inside the code or the documentation
- Of course it's ok to respond to questions in GitHub

## Look at examples of the first reviews

- It can be helpful to review some examples of previous first reviews to get an
  idea of what common issues are and how to address them.
- Here are some links to a few "painful" first reviews:
  - Adding unit tests:
    - https://github.com/kaizen-ai/kaizenflow/pull/166
    - https://github.com/kaizen-ai/kaizenflow/pull/186
  - Writing scripts:
    - https://github.com/kaizen-ai/kaizenflow/pull/267
    - https://github.com/kaizen-ai/kaizenflow/pull/276
