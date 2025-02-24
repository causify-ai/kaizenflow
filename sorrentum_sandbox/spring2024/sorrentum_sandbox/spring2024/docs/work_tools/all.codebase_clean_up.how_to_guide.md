

<!-- toc -->

- [Codebase clean-up scripts](#codebase-clean-up-scripts)
  * [Problem](#problem)
  * [Solution: script approach](#solution-script-approach)
  * [Using the script approach](#using-the-script-approach)
- [How to use `replace_text.py`](#how-to-use-replace_textpy)
  * [Rename a file](#rename-a-file)
  * [Replace an import with a new one](#replace-an-import-with-a-new-one)
  * [Replace text in a specific directory](#replace-text-in-a-specific-directory)
  * [Revert all files but this one](#revert-all-files-but-this-one)
  * [Custom flows](#custom-flows)
- [Usage examples](#usage-examples)
  * [Instructions for the PR author](#instructions-for-the-pr-author)
    + [Example](#example)
  * [Instructions for the subrepo integrator](#instructions-for-the-subrepo-integrator)

<!-- tocstop -->

# Codebase clean-up scripts

## Problem

1. Since we have multiple repos, we can't always easily replace code in one repo
   (e.g., with PyCharm) and have all the other repos work properly
2. Sometimes it is required to rename files and replace text in files at the
   same time (e.g., when renaming an import)
3. While developing a change for the entire repo, we want to be able to "reset"
   the work and apply the change from scratch

- E.g., during the review of the PR applying lots of text replaces:
  - The code in master might be changing creating conflicts
  - The reviewers might ask some changes
  - This creates a lot of manual changes

## Solution: script approach

- Create a shell `sh` script that applies the correct changes to all the repos
  using [/dev_scripts/replace_text.py](/dev_scripts/replace_text.py)
- For more complex problems we can extend `replace_text.py` with custom
  regex-based operations

- The script approach solves all the problems above

1. We apply the script to all the repos
2. The script can rename text and files at the same time
3. We can check out a clean master, run the script to apply the changes
   automatically, regress and merge

## Using the script approach

- We want to apply clean-up changes to the code base with a script

- Ideally we would like to apply all the changes automatically through the
  script
  - E.g., in [SorrTask258](https://github.com/kaizen-ai/kaizenflow/issues/258) a
    script that replaces `pytest.raises` with `self.assertRaises` everywhere in
    the code
- We are ok to make the vast majority (like 95%) of the changes automatically,
  and the rest manually

- We want to keep together in a single PR
  - The script performing automatically the changes; and
  - The manual changes from the outcome of the script

- We want to create a separate PR to communicate with the reviewers the output
  of running the script
  - The author/reviewers should run the script on all the repos, run the unit
    tests, and merge (through a PR as usual)

# How to use `replace_text.py`

- See `-h` for updated list of options

- Replace an instance of text in the content of all the files with extensions:
  `.py`, `.ipynb`, `.txt`, `.md`
- `--old`: regular expression or string that should be replaced with `--new`
- `--new`: regular expression or string that should replace `--old`
- `--preview`: see script result without making actual changes
- `--only_dirs`: provide space-separated list of directories to process only
- `--only_files`: provide space-separated list of files to process only
- `--exclude_files`: provide space-separated list of files to exclude from
  replacements
- `--exclude_dirs`: provide space-separated list of dir to exclude from
  replacements
- `--ext`: process files with specified extensions
  - Defaults are `py, ipynb, txt, sh`
  - Use `_all_` for all files

- The goal of the script is to replace an instance of text in the content of all
  the files with extensions `.py`, `.ipynb`, `.txt`, `.md` and to do a `git mv`
  for files based on certain criteria

## Rename a file

- Preview the change
  ```bash
  > replace_text.py \
      --old research_backtest_utils \
      --new backtest_api \
      --preview
  ```
- Then you can look at the changes to be performed with `vic` /
  `vim -c "cfile cfile"`
- If you are satisfied you can re-run the command with `--preview` to apply the
  change
- Rename file
  ```bash
  > git mv ./dataflow/backtest/{research_backtest_utils.py,backtest_api.py}
  ```

## Replace an import with a new one

```bash
> replace_text.py \
    --old "import core.fin" \
    --new "import core.finance"
```

## Replace text in a specific directory

```bash
> replace_text.py \
    --old "exec " \
    --new "execute " \
    --preview \
    --dirs dev_scripts \
    --exts None
```

## Revert all files but this one

- There is an option `--revert_all` to apply this before the script
  ```bash
  > gs -s | \
      grep -v dev_scripts/replace_text.py | \
      grep -v "\?" | \
      awk '{print $2}' | \
      xargs git checkout --
  ```

## Custom flows

```bash
> replace_text.py --custom_flow _custom1
```

- Custom flow for AmpTask14
  ```bash
  > replace_text.py --custom_flow _custom2 --revert_all
  ```

# Usage examples

- See [SorrIssue259](https://github.com/kaizen-ai/kaizenflow/issues/259) and the
  related [PR](https://github.com/kaizen-ai/kaizenflow/pull/336) for reference
  - We wanted to make `_to_multiline_cmd()` from `helpers/lib_tasks_utils.py` a
    public function
  - This would require to rename `_to_multiline_cmd()` to `to_multiline_cmd()`
    with the script
  - This
    [script](https://github.com/cryptokaizen/cmamp/blob/master/dev_scripts/cleanup_scripts/SorrTask259_Make_to_multi_line_cmd_public.sh)
    will make the replacement smoothly everywhere in the code except for the
    dirs specified `--exclude_dirs` flag.

- See [SorrIssue258](https://github.com/kaizen-ai/kaizenflow/issues/258) and the
  related [PR](https://github.com/kaizen-ai/kaizenflow/pull/350) for reference
  - We wanted to replace `pytest.raises` with `self.assertRaises`
  - This
    [script](https://github.com/kaizen-ai/kaizenflow/blob/master/dev_scripts/cleanup_scripts/SorrTask258_Replace_pytest_raises_with_self_assertraises.sh)
    will replace it everywhere in the code
  - Note the use of `--ext` flag to specify the file extentions the script
    should work on
- Of course the changes need to be applied in one repo and then propagated to
  all the other repos if the tests are successful

## Instructions for the PR author

- Create a local branch called `...TaskXYZ_..._script` containing:
  - The code that needs to be changed manually
    - E.g.: Replacing `pytest.raises` with `self.assertRaises`
  - More contextual changes
    - E.g.: Adding unit tests to the new functions
  - The script for the replacement of the caller named after the GH issue
    - The script should:
      - Prepare the target Git client
      - Merge this `script` branch with the manual changes
      - Make the automated changes
        - E.g.: Rename a function or replace certain word in comments /
          docstring
  - Notes in the files that need to be changed manually after the automatic
    script
- Run from scratch the script getting the regression to pass
  - Any time there is a change needed by hand, the change should be added to the
    script branch
  - The goal is to be able to run the script
- File a PR of the `...TaskXYZ_..._script`
- (Optional) Create a PR with the result of the script
  - The author can request a review on this PR, but still the goal is to
    automate as much as possible
- Finally, the PR author merges the PR with the results of the script

### Example

- The name of script should be related to the task. E.g:
  `SorrTask259_Make_to_multi_line_cmd_public.sh`
- The script should have a system call to `replace_text.py` to execute the
  required functionality as provided in the above examples
- Create a PR only with the script and the changes

## Instructions for the subrepo integrator

- Do a `git checkout` of the `...TaskXYZ_..._script`
- Run the script
- Review carefully the changes to make sure we are not screwing things up
- Run the regressions
- Merge the resulting `...TaskXYZ...` PR
- Ensure that the `...TaskXYZ_..._script` is merged in `master`
- Delete the `...TaskXYZ_..._script`
