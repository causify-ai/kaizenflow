

<!-- toc -->

- [Introduction](#introduction)
  * [Listing all the tasks](#listing-all-the-tasks)
  * [Getting help for a specific workflow](#getting-help-for-a-specific-workflow)
  * [Implementation details](#implementation-details)
- [Git](#git)
  * [Merge master in the current branch](#merge-master-in-the-current-branch)
- [GitHub](#github)
  * [Create a PR](#create-a-pr)
  * [Extract a PR from a larger one](#extract-a-pr-from-a-larger-one)
    + [Example](#example)
    + [Using git](#using-git)
  * [Systematic code transformation](#systematic-code-transformation)
  * [Generate a local `amp` Docker image](#generate-a-local-amp-docker-image)
  * [Update the dev `amp` Docker image](#update-the-dev-amp-docker-image)
  * [Experiment in a local image](#experiment-in-a-local-image)
- [GitHub Actions (CI)](#github-actions-ci)
- [pytest](#pytest)
  * [Run with coverage](#run-with-coverage)
  * [Capture output of a pytest](#capture-output-of-a-pytest)
  * [Run only one test based on its name](#run-only-one-test-based-on-its-name)
  * [Iterate on stacktrace of failing test](#iterate-on-stacktrace-of-failing-test)
  * [Iterating on a failing regression test](#iterating-on-a-failing-regression-test)
  * [Detect mismatches with golden test outcomes](#detect-mismatches-with-golden-test-outcomes)
- [Lint](#lint)
  * [Lint everything](#lint-everything)

<!-- tocstop -->

# Introduction

- We use `invoke` to implement workflows (aka "tasks") similar to Makefile
  targets, but using Python
- The official documentation for `invoke` is
  [here](https://docs.pyinvoke.org/en/0.11.1/index.html)

- We use `invoke` to automate tasks and package workflows for:
  - Docker: `docker_*`
  - Git: `git_*`
  - GitHub (relying on `gh` integration): `gh_*`
  - Running tests: `run_*`
  - Branch integration: `integrate_*`
  - Releasing tools and Docker images: `docker_*`
  - Lint: `lint_*`
  - Pytest:
- Each set of commands starts with the name of the corresponding topic:
  - E.g., `docker_*` for all the tasks related to Docker
- The best approach to getting familiar with the tasks is to browse the list and
  then check the output of the help
- `i` is the shortcut for the `invoke` command

  ```bash
  > invoke --help command
  > i -h gh_issue_title
  Usage: inv[oke] [--core-opts] gh_issue_title [--options] [other tasks here ...]

  Docstring:
  Print the title that corresponds to the given issue and repo_short_name.
  E.g., AmpTask1251_Update_GH_actions_for_amp.

  :param pbcopy: save the result into the system clipboard (only on macOS)

  Options:
  -i STRING, --issue-id=STRING
  -p, --[no-]pbcopy
  -r STRING, --repo-short-name=STRING
  ```

- We can guarantee you a 2x improvement in performance if you master the
  workflows, but it takes some time and patience

- `TAB` completion available for all the tasks, e.g.,

  ```bash
  > i gh_<TAB>
  gh_create_pr      gh_issue_title    gh_login          gh_workflow_list  gh_workflow_run
  ```
  - Tabbing after typing a dash (-) or double dash (--) will display valid
    options/flags for the current context.

## Listing all the tasks

- New commands are always being added, but a list of valid tasks is below

  ```bash
  > invoke --list
  INFO: > cmd='/Users/saggese/src/venv/amp.client_venv/bin/invoke --list'
  Available tasks:

  check_python_files Compile and execute Python files checking for errors.
  docker_bash Start a bash shell inside the container corresponding to a stage.
  docker_build_local_image Build a local image (i.e., a release candidate "dev"
  image).
  docker_build_prod_image (ONLY CI/CD) Build a prod image.
  docker_cmd Execute the command `cmd` inside a container corresponding to a
  stage.
  docker_images_ls_repo List images in the logged in repo_short_name.
  docker_jupyter Run jupyter notebook server.
  docker_kill Kill the last Docker container started.
  docker_login Log in the AM Docker repo_short_name on AWS.
  docker_ps List all the running containers.
  docker_pull Pull latest dev image corresponding to the current repo from the
  registry.
  docker_pull_dev_tools Pull latest prod image of `dev_tools` from the registry.
  docker_push_dev_image (ONLY CI/CD) Push the "dev" image to ECR.
  docker_push_prod_image (ONLY CI/CD) Push the "prod" image to ECR.
  docker_release_all (ONLY CI/CD) Release both dev and prod image to ECR.
  docker_release_dev_image (ONLY CI/CD) Build, test, and release to ECR the latest
  "dev" image.
  docker_release_prod_image (ONLY CI/CD) Build, test, and release to ECR the prod
  image.
  docker_rollback_dev_image Rollback the version of the dev image.
  docker_rollback_prod_image Rollback the version of the prod image.
  docker_stats Report last started Docker container stats, e.g., CPU, RAM.
  docker_tag_local_image_as_dev (ONLY CI/CD) Mark the "local" image as "dev".
  find_check_string_output Find output of check_string() in the test running
  find_test_class Report test files containing `class_name` in a format compatible
  with
  find_test_decorator Report test files containing `class_name` in pytest format.
  fix_perms :param action:
  gh_create_pr Create a draft PR for the current branch in the corresponding
  gh_issue_title Print the title that corresponds to the given issue and
  repo_short_name.
  gh_workflow_list Report the status of the GH workflows.
  gh_workflow_run Run GH workflows in a branch.
  git_add_all_untracked Add all untracked files to Git.
  git_branch_copy Create a new branch with the same content of the current branch.
  git_branch_diff_with_base Diff files of the current branch with master at the
  branching point.
  git_branch_files Report which files were added, changed, and modified in the
  current branch
  git_branch_next_name Return a name derived from the branch so that the branch
  does not exist.
  git_clean Clean the repo_short_name and its submodules from artifacts.
  git_create_branch Create and push upstream branch `branch_name` or the one
  corresponding to
  git_create_patch Create a patch file for the entire repo_short_name client from
  the base
  git_delete_merged_branches Remove (both local and remote) branches that have
  been merged into master.
  git_files Report which files are changed in the current branch with respect to
  git_last_commit_files Print the status of the files in the previous commit.
  git_merge_master Merge `origin/master` into the current branch.
  git_pull Pull all the repos.
  git_fetch_master Pull master without changing branch.
  git_rename_branch Rename current branch both locally and remotely.
  integrate_compare_branch_with_base Compare the files modified in both the
  branches in src_dir and dst_dir to
  integrate_copy_dirs Copy dir `subdir` from dir `src_dir` to `dst_dir`.
  integrate_create_branch Create the branch for integration in the current dir.
  integrate_diff_dirs Integrate repos from dir `src_dir` to `dst_dir`.
  lint Lint files.
  lint_create_branch Create the branch for linting in the current dir.
  print_setup Print some configuration variables.
  print_tasks Print all the available tasks in `lib_tasks.py`.
  pytest_clean Clean pytest artifacts.
  pytest_compare Compare the output of two runs of `pytest -s --dbg` removing
  irrelevant
  pytest_failed Process the list of failed tests from a pytest run.
  pytest_failed_freeze_test_list Copy last list of failed tests to not overwrite
  with successive pytest
  run_blank_tests (ONLY CI/CD) Test that pytest in the container works.
  run_coverage_report
  run_fast_slow_tests Run fast and slow tests independently.
  run_fast_tests Run fast tests.
  run_qa_tests Run QA tests independently.
  run_slow_tests Run slow tests.
  run_superslow_tests Run superslow tests.
  traceback Parse the traceback from Pytest and navigate it with vim.
  ```

## Getting help for a specific workflow

- You can get a more detailed help with

  ```bash
  > invoke --help run_fast_tests
  Usage: inv[oke] [--core-opts] run_fast_tests [--options] [other tasks here ...]

  Docstring:
  Run fast tests.

  :param stage: select a specific stage for the Docker image
  :param pytest_opts: option for pytest
  :param pytest_mark: test list to select as `@pytest.mark.XYZ`
  :param dir_name: dir to start searching for tests
  :param skip_submodules: ignore all the dir inside a submodule
  :param coverage: enable coverage computation
  :param collect_only: do not run tests but show what will be executed

  Options:
  -c, --coverage
  -d STRING, --dir-name=STRING
  -k, --skip-submodules
  -o, --collect-only
  -p STRING, --pytest-opts=STRING
  -s STRING, --stage=STRING
  -y STRING, --pytest-mark=STRING
  ```

## Implementation details

- By convention all invoke targets are in `*_lib_tasks.py`, e.g.,
  - `helpers/lib_tasks.py` - tasks to be run in `cmamp`
  - `optimizer/opt_lib_tasks.py` - tasks to be run in `cmamp/optimizer`
- All invoke tasks are functions with the `@task` decorator, e.g.,

  ```python
  from invoke import task

  @task
  def invoke_task(...):
    ...
  ```

- To run a task we use `context.run(...)`, see
  [the official docs](https://docs.pyinvoke.org/en/0.11.1/concepts/context.html)
- To be able to run a specified invoke task one should import it in `tasks.py`
  - E.g., see `cmamp/tasks.py`
- A task can be run only in a dir where it is imported in a corresponding
  `tasks.py`, e.g.,
  - `invoke_task1` is imported in `cmamp/tasks.py` so it can be run only from
    `cmamp`
  - `invoke_task2` is imported in `cmamp/optimizer/tasks.py` so it can be run
    only from `cmamp/optimizer`
    - In other words one should do `cd cmamp/optimizer` before doing
      `i invoke_task2 ...`

# Git

## Merge master in the current branch

```bash
> i git_merge_master
```

# GitHub

- Get the official branch name corresponding to an Issue

  ```bash
  > i gh_issue_title -i 256
  ## gh_issue_title: issue_id='256', repo_short_name='current'

  # Copied to system clipboard:
  AmpTask256_Part_task2236_jenkins_cleanup_split_scripts:
  https://github.com/alphamatic/amp/pull/256
  ```

## Create a PR

TODO(gp): Describe

## Extract a PR from a larger one

- When having a PR which is really big we prefer to brake it into smaller
  mergeable PRs using `i git_branch_copy`

### Example

- In my workflow there is a feature branch (e.g. `CmTask5874_Document_PR_flow`
  that I am developing in.
- When a piece of code is ready to be merged rather than merging the main PR we
  will create a child PR and merge that into `master`:
  - Step 1: Make sure your branch is up to date with origin

  ```bash
  # First switch to your feature branch
  > git checkout CmTask5874_Document_PR_flow

  # Make sure that the branch is up-to-date with master
  > i git_merge_master

  # Commit and push the changes that you have made to the branch
  > git commit -m “Initial Changes”
  > git push origin CmTask5874_Document_PR_flow

  # You can check the git diff between your branch and master using the following command:
  > i git_branch_diff_with -t base --only-print-files
  # Output:
  INFO: > cmd='/data/sameepp/src/venv/amp.client_venv/bin/invoke git_branch_diff_with -t base --only-print-files'
  04:58:35 - INFO  lib_tasks_git.py _git_diff_with_branch:726
  ###############################################################################
  # files=3
  ###############################################################################
  04:58:35 - INFO  lib_tasks_git.py _git_diff_with_branch:727
  ./figs/development/Fig1.png
  ./figs/development/Fig2.png
  docs/work_tools/all.development.how_to_guide.md
  04:58:35 - WARN  lib_tasks_git.py _git_diff_with_branch:732             Exiting as per user request with --only-print-files
  ```

  As we can see above I have made changes to 3 files. Lets say I just want to
  partially merge this PR and still keep working on the main branch (e.g. merge
  only the .png files).
  - Step 2: create a new branch (e.g., `CmTask5874_Document_PR_flow_02`) derived
    from our feature branch `CmTask5874_Document_PR_flow` using the command
    `i git_branch_copy`.

  ```bash
  # Create a derived branch from the feature branch.
  > i git_branch_copy

  # Output:
  INFO: > cmd='/data/sameepp/src/venv/amp.client_venv/bin/invoke git_branch_copy'
  git clean -fd
  invoke git_merge_master --ff-only
  From github.com:cryptokaizen/cmamp
    e59affd79..d6e6ed8e4  master     -> master
  INFO: > cmd='/data/sameepp/src/venv/amp.client_venv/bin/invoke git_merge_master --ff-only'
  ## git_merge_master:
  ## git_fetch_master:
  git fetch origin master:master
  git submodule foreach 'git fetch origin master:master'
  git merge master --ff-only
  Already up to date.
  07:04:46 - INFO  lib_tasks_git.py git_branch_copy:599                   new_branch_name='CmTask5874_Document_PR_flow_2'
  git checkout master && invoke git_branch_create -b 'CmTask5874_Document_PR_flow_2'
  Switched to branch 'master'
  Your branch is up to date with 'origin/master'.
  INFO: > cmd='/data/sameepp/src/venv/amp.client_venv/bin/invoke git_branch_create -b CmTask5874_Document_PR_flow_2'
  ## git_branch_create:
  07:05:00 - INFO  lib_tasks_git.py git_branch_create:413                 branch_name='CmTask5874_Document_PR_flow_2'
  git pull --autostash --rebase
  Current branch master is up to date.
  Switched to a new branch 'CmTask5874_Document_PR_flow_2'
  remote:
  remote: Create a pull request for 'CmTask5874_Document_PR_flow_2' on GitHub by visiting:
  remote:      https://github.com/cryptokaizen/cmamp/pull/new/CmTask5874_Document_PR_flow_2
  remote:
  To github.com:cryptokaizen/cmamp.git
  [new branch] CmTask5874_Document_PR_flow_2 ->
  CmTask5874_Document_PR_flow_2 git checkout -b CmTask5874_Document_PR_flow_2
  git push --set-upstream origin CmTask5874_Document_PR_flow_2 Branch
  'CmTask5874_Document_PR_flow_2' set up to track remote branch
  'CmTask5874_Document_PR_flow_2' from 'origin'. git merge --squash --ff
  CmTask5874_Document_PR_flow && git reset HEAD Updating d6e6ed8e4..a264a6f30
  Fast-forward Squash commit -- not updating HEAD
  docs/work_tools/figs/development/Fig1.png | Bin 27415 -> 0 bytes
  docs/work_tools/figs/development/Fig2.png | Bin 35534 -> 0 bytes 2 files
  changed, 0 insertions(+), 0 deletions(-) delete mode 100644
  docs/work_tools/figs/development/Fig1.png delete mode 100644
  docs/work_tools/figs/development/Fig2.png Unstaged changes after reset: D
  docs/work_tools/figs/development/Fig1.png D
  docs/work_tools/figs/development/Fig2.png
  ```
  - Step 3: Once the command is completed you can see that there is a new branch
    `CmTask5874_Document_PR_flow_2`with the same changes from feature branch
    ready to be staged. Hence finally you can just commit the desired files and
    merge the changes to master.

  ```bash
  > git status
  #Output:
  On branch CmTask5874_Document_PR_flow_2
  Your branch is up to date with 'origin/CmTask5874_Document_PR_flow_2'.

  Untracked files:
  (use "git add <file>..." to include in what will be committed)
        ./figs/development/Fig1.png
        ./figs/development/Fig2.png
        docs/work_tools/all.invoke_workflows.how_to_guide.md

  # Add, commit and push ont the required files.
  > git add ./figs/development/Fig1.png ./figs/development/Fig2.png
  > git commit -m "Checkpoint"
  > git push origin CmTask5874_Document_PR_flow_2
  ```

- Go to a fresh Git client (I have 2-3 Git clients separated from the one in
  which I develop for this kind of operations) or go to master in the same Git
  client

  ```bash
  # Go to master
  > git checkout master

  # Apply the patch from the run of `git_create_patch`

  > git apply
  > /Users/saggese/src/lemonade1/amp/patch.amp.8f9cda97.20210609_080439.patch

  # This patch should apply cleanly and with no errors from git, otherwise it means
  that your feature branch does not have the latest master

  # Remove what you don't want to commit.

  # Do not change anything or run the linter otherwise your feature branch will not
  merge easily.
  > git diff
  > git checkout master -- ...
  ...
  > git commit; git push

  # Create a PR (non-draft so that GH can start running the tests)
  > i gh_create_pr --no-draft

  # Regress the branch
  > i run_fast_tests ...

  # Merge the PR into master

  # Go back to your feature branch and merge master
  > gco ${feature_branch}
  > git pull

  # Now one piece of your feature branch has been merged and you can repeat until
  all the code is merged.
  ```

### Using git

```bash
> git checkout `dst_branch`
> git merge --squash --ff `src_branch`
> git reset HEAD
```

## Systematic code transformation

- See the help of `amp/dev_scripts/replace_text.py`

## Generate a local `amp` Docker image

- This is a manual flow used to test and debug images before releasing them to
  the team.
- The flow is similar to the dev image, but by default tests are not run and the
  image is not released.

  ```bash
  # Build the local image (and update Poetry dependencies, if needed).

  > i docker_build_local_image --update-poetry
  ...
  docker image ls 665840871993.dkr.ecr.us-east-1.amazonaws.com/amp:local

  REPOSITORY TAG IMAGE ID CREATED SIZE
  665840871993.dkr.ecr.us-east-1.amazonaws.com/amp local 9b3f8f103a2c 1 second ago 1.72GB

  # Test the new "local" image
  > i docker_bash --stage "local" python -c "import async_solipsism" python -c
  > "import async_solipsism; print(async_solipsism.**version**)"

  # Run the tests with local image
  # Make sure the new image is used: e.g., add an import and trigger the tests.
  > i run_fast_tests --stage "local" --pytest-opts core/dataflow/test/test_real_time.py
  > i run_fast_slow_tests --stage "local"

  # Promote a local image to dev.
  > i docker_tag_local_image_as_dev
  > i docker_push_dev_image
  ```

  ## Update the dev `amp` Docker image

- To implement the entire Docker QA process of a dev image

  ```bash
  # Clean all the Docker images locally, to make sure there is no hidden state.
  > docker system prune --all

  # Update the needed packages.
  > devops/docker_build/pyproject.toml

  # Visually inspect the updated packages.
  > git diff devops/docker_build/poetry.lock

  # Run entire release process.
  > i docker_release_dev_image
  ```

  ## Experiment in a local image

- To install packages in an image, do `i docker_bash`

  ```bash
  # Switch to root and install package.
  > sudo su -
  > source /venv/bin/activate
  > pip install <package>

  # Switch back to user.
  > exit
  ```

- You should test that the package is installed for your user, e.g.,
  ```bash
  > source /venv/bin/activate python -c "import foobar; print(foobar);print(foobar.__version__)"
  ```
- You can now use the package in this container. Note that if you exit the
  container, the modified image is lost, so you need to install it again.
- You can save the modified image, tagging the new image as local, while the
  container is still running.
- Copy your Container ID. You can find it
  - In the docker bash session, e.g., if the command line in the container
    starts with `user_1011@da8f3bb8f53b:/app$`, your Container ID is
    `da8f3bb8f53b`
  - By listing running containers, e.g., run `docker ps` outside the container
- Commit image
  ```bash
  > docker commit <Container ID> <IMAGE>/cmamp:local-$USER
  ```
  - E.g.
    `docker commit da8f3bb8f53b 665840871993.dkr.ecr.us-east-1.amazonaws.com/cmamp:local-julias`
- If you are running inside a notebook using `i docker_jupyter` you can install
  packages using a one liner `! sudo su -; source ...; `

# GitHub Actions (CI)

```bash
## Running a single test in GH Actions

Create a branch

Change .github/workflows/fast_tests.yml

run: invoke run_fast_tests
--pytest-opts="helpers/test/test_git.py::Test_git_modified_files1::test_get_modified_files_in_branch1
-s --dbg"
# In the current implementation (where we try to not run for branches) to run in a branch
```

# pytest

- From https://gist.github.com/kwmiebach/3fd49612ef7a52b5ce3a

- More details on running unit tests with `invoke` is
  [/docs/coding/all.run_unit_tests.how_to_guide.md](/docs/coding/all.run_unit_tests.how_to_guide.md)

## Run with coverage

```bash
> i run_fast_tests --pytest-opts="core/test/test_finance.py" --coverage
```

## Capture output of a pytest

- Inside the `dev` container (i.e., docker bash)
  ```bash
  docker> pytest_log ...
  ```

## Run only one test based on its name

- Outside the `dev` container

  ```bash
  > i find_test_class Test_obj_to_str1
  INFO: > cmd='/Users/saggese/src/venv/amp.client_venv/bin/invoke find_test_class Test_obj_to_str1'
  ## find_test_class: class_name abs_dir pbcopy
  10:18:42 - INFO  lib_tasks_find.py _find_test_files:44                  Searching from '.'

  # Copied to system clipboard:
  ./helpers/test/test_hobject.py::Test_obj_to_str1
  ```

## Iterate on stacktrace of failing test

- Inside docker bash
  ```bash
  docker> pytest ...
  ```
- The test fails: switch to using `pytest_log` to save the stacktrace to a file

  ```bash
  > pytest_log dataflow/model/test/test_tiled_flows.py::Test_evaluate_weighted_forecasts::test_combine_two_signals
  ...
  =================================== FAILURES ===================================
  __________ Test_evaluate_weighted_forecasts.test_combine_two_signals ___________
  Traceback (most recent call last):
    File "/app/dataflow/model/test/test_tiled_flows.py", line 78, in test_combine_two_signals
      bar_metrics = dtfmotiflo.evaluate_weighted_forecasts(
    File "/app/dataflow/model/tiled_flows.py", line 265, in evaluate_weighted_forecasts
      weighted_sum = hpandas.compute_weighted_sum(
  TypeError: compute_weighted_sum() got an unexpected keyword argument 'index_mode'
  ============================= slowest 3 durations ==============================
  2.18s call     dataflow/model/test/test_tiled_flows.py::Test_evaluate_weighted_forecasts::test_combine_two_signals
  0.01s setup    dataflow/model/test/test_tiled_flows.py::Test_evaluate_weighted_forecasts::test_combine_two_signals
  0.00s teardown dataflow/model/test/test_tiled_flows.py::Test_evaluate_weighted_forecasts::test_combine_two_signals
  ```

- Then from outside `dev` container launch `vim` in quickfix mode

  ```bash
  > invoke traceback
  ```

- The short form is `it`

## Iterating on a failing regression test

- The workflow is:

  ```bash
  # Run a lot of tests, e.g., the entire regression suite.
  > pytest ...
  # Some tests fail.

  # Run the `pytest_repro` to summarize test failures and to generate commands to reproduce them.
  > invoke pytest_repro
  ```

## Detect mismatches with golden test outcomes

- The command is

  ```bash
  > i pytest_find_unused_goldens
  ```

- The specific dir to check can be specified with the `dir_name` parameter.
- The invoke detects and logs mismatches between the tests and the golden
  outcome files.
  - When goldens are required by the tests but the corresponding files do not
    exist
    - This usually happens if the tests are skipped or commented out.
    - Sometimes it's a FP hit (e.g. the method doesn't actually call
      `check_string` but instead has it in a string, or `check_string` is called
      on a missing file on purpose to verify that an exception is raised).
  - When the existing golden files are not actually required by the
    corresponding tests.
    - In most cases it means the files are outdated and can be deleted.
    - Alternatively, it can be a FN hit: the test method A, which the golden
      outcome corresponds to, doesn't call `check_string` directly, but the
      test's class inherits from a different class, which in turn has a method B
      that calls `check_string`, and this method B is called in the test method
      A.
- For more details see
  [CmTask528](https://github.com/cryptokaizen/cmamp/issues/528).

# Lint

## Lint everything

```bash
> i lint --phases="amp_isort amp_class_method_order amp_normalize_import
amp_format_separating_line amp_black" --files='$(find . -name "\*.py")'
```
