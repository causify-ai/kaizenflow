# Linter Github Action Workflow Explanation

<!-- toc -->

- [Overview](#overview)
- [How it works](#how-it-works)
  * [Fetch master branch](#fetch-master-branch)
  * [Run the linter and check the linter results](#run-the-linter-and-check-the-linter-results)

<!-- tocstop -->

# Overview

- We want to use linter for all the new code that needs to be merged into the
  `master` branch
- This is implemented by running the GitHub Actions workflow, `linter.yml`,
  which is executed against the changed or added files in the branch
- If the linter detects changes in the new files, it indicates that the linter
  did not run before.
- In this case, the workflow will fail, and will not allow the PR to be merged

# How it works

## Fetch master branch

In order to compare the changed files in the PR with the latest master branch,
fetch the latest master, e.g.,

```bash
invoke git_fetch_master
```

## Run the linter and check the linter results

- Run the linter against the changed files in the PR branch

```bash
invoke lint --branch
```

- Check if the git client is clean

```bash
git status
```

- If the git client is not clean, abort the execution and the workflow will fail
- If the git client is clean, the workflow will exit successfully

Invoke task for this action is:

```bash
invoke lint_check_if_it_was_run
```
