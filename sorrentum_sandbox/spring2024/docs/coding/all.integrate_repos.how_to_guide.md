# How to integrate repos

<!-- toc -->

- [Concepts](#concepts)
- [Invariants for the integration workflows](#invariants-for-the-integration-workflows)
- [Integration process](#integration-process)
  * [Preparation](#preparation)
  * [Integration](#integration)
  * [Double-check the integration](#double-check-the-integration)
  * [Run tests](#run-tests)

<!-- tocstop -->

# Concepts

- We have two dirs storing two forks of the same repo
  - Files are touched (e.g., added, modified, deleted) in each forks
  - The most problematic files are the files that are modified in both forks
  - Files that are added or deleted in one fork, should be added / deleted also
    in the other fork
- Often we can integrate "by directory", i.e., finding entire directories that
  were touched in one branch but not in the other
  - In this case we can simply copy the entire dir from one dir to the other
- Other times we need to integrate "by file"

- There are various interesting Git reference points:
  1. The branch point for each fork, at which the integration branch was started
  2. The last integration point for each fork, at which the repos are the same,
     or at least aligned

# Invariants for the integration workflows

- The user runs commands in an abs dir, e.g., `/Users/saggese/src/{amp1,cmamp1}`
- The user refers in the command line to `dir_basename`, which is the basename
  of the integration directories (e.g., `amp1`, `cmamp1`, `kaizenflow1`)
  - The `src_dir_basename` is the one where the command is issued
  - The `dst_dir_basename` is assumed to be parallel to the `src_dir_basename`
- The dirs are then transformed in absolute dirs `abs_src_dir`

# Integration process

## Preparation

- Pull master

- Crete the integration branches

  ```bash
  > cd cmamp1
  > git checkout master
  > i integrate_create_branch --dir-basename cmamp1
  > cd kaizenflow1
  > git checkout master
  > i integrate_create_branch --dir-basename kaizenflow1
  ```

- In one line

  ```bash
  cd $HOME/cmamp1 && \
    git checkout master && \
    i integrate_create_branch --dir-basename cmamp1 && \
    cd $HOME/kaizenflow1 && \
    git checkout master && \
    i integrate_create_branch --dir-basename kaizenflow1
  ```

- Remove white spaces from both source and destination repos:

  ```bash
  > dev_scripts/clean_up_text_files.sh
  > git commit -am "Remove white spaces"; git push
  ```
  - One should still run the regressions out of paranoia since some golden
    outcomes can be changed
    ```
    > i gh_create_pr --no-draft
    > i gh_workflow_list
    ```

- Remove empty files:

  ```bash
  > find . -type f -empty -print | grep -v .git | grep -v __init__ | grep -v ".log$" | grep -v ".txt$" | xargs git rm
  ```
  - TODO(gp): Add this step to `dev_scripts/clean_up_text_files.sh`

- Align `lib_tasks.py`:

  ```bash
  > vimdiff ~/src/{cmamp1, kaizenflow1}/tasks.py; diff_to_vimdiff.py --dir1 ~/src/cmamp1 --dir2 ~/src/kaizenflow1 --subdir helpers
  ```

- Lint both dirs:

  ```bash
  > cd amp1
  > i lint --dir-name . --only-format
  > cd cmamp1
  > i lint --dir-name . --only-format
  ```

  or at least the files touched by both repos:

  ```bash
  > i integrate_files --file-direction only_files_in_src
  > cat tmp.integrate_find_files_touched_since_last_integration.cmamp1.txt tmp.integrate_find_files_touched_since_last_integration.amp1.txt | sort | uniq >files.txt
  > FILES=$(cat files.txt)
  > i lint --only-format -f "$FILES"
  ```
  - This should be done as a single separated PR to be reviewed separately

- Align `lib_tasks.py`:
  ```bash
  > vimdiff ~/src/{amp1,cmamp1}/tasks.py; diff_to_vimdiff.py --dir1 ~/src/amp1 --dir2 ~/src/cmamp1 --subdir helpers
  ```

## Integration

- Create the integration branches:

  ```bash
  > cd amp1
  > i integrate_create_branch --dir-basename amp1
  > i integrate_create_branch --dir-basename kaizenflow1
  > cd cmamp1
  > i integrate_create_branch --dir-basename cmamp1
  ```

- Check what files were modified in each fork since the last integration:

  ```bash
  > i integrate_files --file-direction common_files
  > i integrate_files --file-direction common_files --src-dir-basename cmamp1 --dst-dir-basename kaizenflow1

  > i integrate_files --file-direction only_files_in_src
  > i integrate_files --file-direction only_files_in_dst
  ```

- Look for directory touched on only one branch:
  ```bash
  > i integrate_files --file-direction common_files --mode "print_dirs"
  > i integrate_files --file-direction only_files_in_src --mode "print_dirs"
  > i integrate_files --file-direction only_files_in_dst --mode "print_dirs"
  ```
- If we find dirs that are touched in one branch but not in the other we can
  copy / merge without running risks

  ```bash
  > i integrate_diff_dirs --subdir $SUBDIR -c
  ```

- Check which change was made in each side since the last integration

  ```bash
  # Find the integration point:
  > i integrate_files --file-direction common_files
  ...
  last_integration_hash='813c7e763'

  # Diff the changes in each side from the integration point:
  > i git_branch_diff_with -t hash -h 813c7e763 -f ...
  > git difftool 813c7e763 ...
  ```

- Check which files are different between the dirs:

  ```bash
  > i integrate_diff_dirs
  ```

- Diff dir by dir

  ```bash
  > i integrate_diff_dirs --subdir dataflow/system
  ```

- Copy by dir

  ```bash
  > i integrate_diff_dirs --subdir market_data -c
  ```

- Sync a dir to handle moved files
- Assume that there is a dir where files were moved
  ```bash
  > invoke integrate_diff_dirs
  ...
  ... Only in .../cmamp1/.../alpha_numeric_data_snapshots: alpha
  ... Only in .../amp1/.../alpha_numeric_data_snapshots: latest
  ```
- You can accept one side with:
  ```bash
  > invoke integrate_rsync $(pwd)/marketing
  ```
- This corresponds to:
  ```bash
  > rsync --delete -a -r {src_dir}/ {dst_dir}/
  ```

## Double-check the integration

- Check that the regressions are passing on GH

  ```bash
  > i gh_create_pr --no-draft
  ```

- Check the files that were changed in both branches (i.e., the "problematic
  ones") since the last integration and compare them to the base in each branch

  ```bash
  > cd amp1
  > i integrate_diff_overlapping_files --src-dir-basename "amp1" --dst-dir-basename "cmamp1"
  > cd cmamp1
  > i integrate_diff_overlapping_files --src-dir-basename "cmamp1" --dst-dir-basename "amp1"
  ```

- Read the changes to Python files:

  ```bash
  > cd amp1
  > i git_branch_diff_with -t base --keep-extensions py
  > cd cmamp1
  > i git_branch_diff_with -t base --keep-extensions py
  ```

- Quickly scan all the changes in the branch compared to the base:
  ```
  > cd amp1
  > i git_branch_diff_with -t base
  > cd cmamp1
  > i git_branch_diff_with -t base
  ```

## Run tests

- Check `amp` / `cmamp` using GH actions:

  ```bash
  > i gh_create_pr --no-draft
  > i pytest_collect_only
  > i gh_workflow_list
  ```

- Check `lem` on dev1

  ```bash
  # Clean everything.
  > git reset --hard; git clean -fd; git pull; (cd amp; git reset --hard; git clean -fd; git pull)

  > i git_pull

  > AM_BRANCH=AmpTask1786_Integrate_20220916
  > (cd amp; gco $AM_BRANCH)

  > i pytest_collect_only
  > i pytest_buildmeister

  > i git_branch_create -b $AM_BRANCH
  ```

- Check `lime` on dev4

- Check `orange` on dev1

- Check `dev_tools` on dev1
