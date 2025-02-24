# Git workflow and best practices

<!-- toc -->

- [Before you start](#before-you-start)
  * [Readings](#readings)
- [Workflow](#workflow)
- [Best Practices](#best-practices)
  * [Do not check in large data files](#do-not-check-in-large-data-files)
  * [Branch workflow best practices](#branch-workflow-best-practices)
    + [Branches are cheap](#branches-are-cheap)
    + [`master` is sacred](#master-is-sacred)
    + [Always work in a branch](#always-work-in-a-branch)
    + [Keep different changes in separate branches](#keep-different-changes-in-separate-branches)
  * [Pull request (PR) best practices](#pull-request-pr-best-practices)
  * [Workflow diagram](#workflow-diagram)
  * [Deleting a branch](#deleting-a-branch)
- [How-to and troubleshooting](#how-to-and-troubleshooting)
  * [Do not mess up your branch](#do-not-mess-up-your-branch)
  * [Analyzing commits](#analyzing-commits)
    + [Show files modified in a commit](#show-files-modified-in-a-commit)
  * [Conflicts](#conflicts)
    + [Getting the conflicting files](#getting-the-conflicting-files)
    + [Accepting "theirs"](#accepting-theirs)
  * [How to get out of a messy/un-mergeable branch](#how-to-get-out-of-a-messyun-mergeable-branch)
  * [Reverting](#reverting)
    + [Reverting the last local commit](#reverting-the-last-local-commit)
  * [Branching](#branching)
    + [Checking what work has been done in a branch](#checking-what-work-has-been-done-in-a-branch)
    + [Checking if you need to merge `master` into your feature branch](#checking-if-you-need-to-merge-master-into-your-feature-branch)
    + [Comparing the difference of a directory among branches](#comparing-the-difference-of-a-directory-among-branches)
  * [Merging `master`](#merging-master)
  * [Rebasing](#rebasing)
  * [Merging pull requests](#merging-pull-requests)
- [Submodules](#submodules)
  * [Adding a submodule](#adding-a-submodule)
  * [Working in a submodule](#working-in-a-submodule)
  * [Updating a submodule to the latest commit](#updating-a-submodule-to-the-latest-commit)
  * [To check if supermodule and amp are in sync](#to-check-if-supermodule-and-amp-are-in-sync)
  * [Roll forward git submodules pointers:](#roll-forward-git-submodules-pointers)
  * [To clean all the repos](#to-clean-all-the-repos)
  * [Pull a branch without checkout](#pull-a-branch-without-checkout)
  * [To force updating all the submodules](#to-force-updating-all-the-submodules)

<!-- tocstop -->

# Before you start

- GitHub is the place where we keep our code
- `git` is the tool (program) for version control
- We interact with GitHub via `git`
- Use public key for authorization
  - You can add a new public key here
    [GH -> Personal settings -> SSH keys](https://github.com/settings/keys)
  - More details about what is public key you can find in
    [all.ssh.how_to_guide.md](https://github.com/cryptokaizen/cmamp/blob/master/docs/work_tools/all.ssh.how_to_guide.md)

## Readings

- Read at least the first 3 chapters of
  [Git book](https://git-scm.com/book/en/v2)
- Read about
  [Git Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
  - We use Git submodules to compose and share code about repos

# Workflow

- Run `git fetch`
  ```
  # Fetch all the data from origin.
  > git fetch

  # List all the branches.
  > git branch -r
  origin/HEAD -> origin/master
  origin/PTask274
  ...
  ```

- Checkout master and pull
  - You want to branch from the latest version of master to avoid a merge:
    ```
    # Checkout the `master` branch.
    > git checkout master

    # Make sure your local `master` is in sync with the remote.
    > git pull --rebase
    ```
  - Alternatively, and especially if you have local changes to move to a new
    branch, run
    ```
    > git checkout master
    > i git_pull
    ```

- Name a branch after its corresponding issue
  - The canonical name for a new feature branch is obtained by running
    `i gh_issue_title`:
    ```
    > i gh_issue_title -i 274
    INFO: > cmd='/Users/saggese/src/venv/amp.client_venv/bin/invoke gh_issue_title -i 274'
    report_memory_usage=False report_cpu_usage=False
    ## gh_issue_title: issue_id='274', repo_short_name='current'
    ## gh_login:
    07:35:54 - INFO  lib_tasks_gh.py gh_login:48                            account='kaizenflow'
    export GIT_SSH_COMMAND='ssh -i /Users/saggese/.ssh/id_rsa.kaizenflow.github'
    gh auth login --with-token </Users/saggese/.ssh/github_pat.kaizenflow.txt

    # Copied to system clipboard:
    CmTask274_Update_names: https://github.com/kaizen-ai/kaizenflow/pull/274
    ```
    - Before running verify that GitHub cli `gh` works
      ```
      > gh --version
      gh version 2.29.0 (2023-05-10)
      https://github.com/cli/cli/releases/tag/v2.29.0
      ```
  - The name is `CmTask274_Update_names`
  - To use multiple branches for a given task, append a numeral to the name,
    e.g., `CmTask274_Update_names_v02`

- Create and checkout the branch
  ```
  > git branch my_feature
  > git checkout my_feature
  ```
  - Alternatively, you can create and checkout in one command with
    ```
    > git checkout -b my_feature
    ```
  - From this point on, you commit only in the branch and changes to master will
    not affect your branch
  - If the branch already exists, check out the branch by executing
    ```
    > git checkout my_feature
    ```
- Commit your work early and often
  - Commits on your feature branch do not affect master. Checkpoint your work
    regularly by committing:
    ```
    > git status On branch my_feature
    > git add ...
    > git commit
    [my_feature 820b296] My feature is awesome!
    ```
  - Commits stay local (not seen on GitHub) until you explicitly tell git to
    "upload" the commits through git push (see next)
- Push your feature branch changes upstream
  - When you commit, commits are local (not seen on GitHub)
  - When you want your code to be pushed to the server (e.g., to back up or to
    share the changes with someone else), you need to push the branch upstream
    ```
    > git push -u origin my_feature
    ...
    30194fc..820b296  my_feature -> my_feature
    Branch 'my_feature' set up to track remote branch 'my_feature' from 'origin'.
    ```
  - Note that `-u` tells git to set the upstream of this branch to origin
  - This operation is needed only the first time you create the branch and not
    for each `git push`
- Merge `master` into your feature branch regularly
  - Merge `master` into your feature branch at least once a day, if the branch
    stays around that long:
    ```
    # Get the .git from the server
    > git fetch
    # Make your master up to origin/master.
    > git checkout master
    > git pull
    # Merge master into my_feature branch.
    > git checkout my_feature
    > git merge master
    ```
  - A simpler flow which should be equivalent
    - TODO(gp): Verify that
      ```
      # Get the .git from the server
      > git fetch
      # Merge master into my_feature branch.
      > git checkout my_feature
      > git merge origin/master
      ```
- Repeat Steps 4-7 as needed
- Request a review of your work by making a pull request (PR)
  - Verify that your work is ready for a review by going through this checklist:
    - The PR is self-contained
    - The latest `master` has been merged into the feature branch
    - All files in the PR have been linted with `linter.py`
    - All tests pass
  - If your work is ready for review, make a pull request
    - Use the GitHub UI (for now; we may replace with a script). Go to the
      branch on the web interface and push "Compare & pull request"
    - Make sure that GP and Paul are assigned as reviewers, as well as anyone
      else who may be interested
    - Make sure that GP and Paul are assigned as assignees
  - Follow up on all comments and mark as resolved any requested changes that
    you resolve

# Best Practices

## Do not check in large data files

- Avoid checking in large data files
  - The reason is that large files bloat the repo
  - Once a large file is checked in, it never goes away
  - Therefore, **DO NOT CHECK IN DATA FILES IN EXCESS OF 500K**
  - If in doubt (even on a branch), ask first!
- Sometimes is makes sense to check in some representative data for unit tests
- BUT, larger tests should obtain their data from s3 or MongoDB

## Branch workflow best practices

### Branches are cheap

- One of the advantages of working with Git is that branches are cheap

### `master` is sacred

- In an ideal world `master` branch is sacred (see Platinum rule of Git)
  - Development should never be done directly on master
  - Changes to master should only happen by pull-request or merge
  - One should avoid working in master except in rare cases, e.g., a simple
    urgent bug-fix needed to unblock people
  - `master` should be always never broken (all tests are passing and it is
    deployable)

### Always work in a branch

- Generally it is best to be the sole contributor to your branch
  - If you need to collaborate with somebody on a branch, remember that the
    golden rule of rebase still applies to this "public" branch: "do not rebase
    pushed commits"
- It is ok to open multiple branches for a given task if needed
  - E.g., if you have multiple chunks of work or multiple people are working on
    orthogonal changes
  - It might be that the task is too big and needs to be broken in smaller bugs
- All the rules that apply to `master` apply also to a branch
  - E.g., commit often, use meaningful commit messages.
  - We are ok with a little looser attitude in your branch
  - E.g., it might be ok to not run unit tests before each commit, but be
    careful!
- Use a branch even if working on a research notebook
  - Try to avoid modifying notebooks in multiple branches simultaneously, since
    notebook merges can be painful
  - Working in a branch in this case facilitates review
  - Working in a branch protects the codebase from accidental pushes of code
    changes outside of the notebook (e.g., hacks to get the notebook working
    that need to be cleaned up)

### Keep different changes in separate branches

- It is easier for you to keep work sane and separated
- Cons of multiple conceptual changes in the same branches
- You are testing / debugging all at once which might make your life more
  difficult
- Reviewing unrelated changes slows down the review process
- Packaging unrelated changes together that means no change gets merged until
  all of the changes are accepted

## Pull request (PR) best practices

- Make sure your PR is coherent
  - It may not need to do everything the Task requires, but the PR should be
    self-contained and not break anything
- If you absolutely need changes under review to keep going, create the new
  branch from the old branch rather than from master (less ideal)
  - Try to avoid branching from branches
    - This creates also dependencies on the order of committing branches
    - You end up with a spiderweb of branches
- Frequent small PRs are easier to review
  - You will also experience faster review turnaround
  - Reviewers like working on smaller changes more than working on larger ones
  - PR review time does not scale linearly with lines changed (may be more like
    exponential)
- Merging changes frequently means other people can more easily see how the code
  is progressing earlier on in the process, and give you feedback
  - E.g., "here it is a much simpler way of doing this", or even better "you
    don't need to write any code, just do &lt;this_and_that>"
- Merged changes are tested in the Jenkins build

## Workflow diagram

## Deleting a branch

- You can run the script `dev_scripts/git/git_branch.sh` to get all the branches
  together with some information, e.g., last commit and creator
- E.g., let's assume we believe that `PTask354_INFRA_Populate_S3_bucket` is
  obsolete and we want to delete it:
  - Get `master` up to date
    ```
    > git checkout master
    > git fetch
    > git pull
    ```
  - Merge `master` into the target branch
  - Pull and merge
    ```
    > git checkout PTask354_INFRA_Populate_S3_bucket
    > git pull
    > git merge master
    ```
  - Resolve conflicts
    ```
    > git commit
    > git pull
    ```
  - Ask Git if the branch is merged
    - One approach is to ask Git if all the changes in master are also in the
      branch
      ```
      > git branch `PTask354_INFRA_Populate_S3_bucket` --no-merged PTask354_INFRA_Populate_S3_bucket
      ```
    - Note that Git is very strict here, e.g.,
      `PTask354_INFRA_Populate_S3_bucket` is not completely merged since I've
      moved code "manually" (not only through `git cherry-pick, git merge`)
    - One approach is to just merge `PTask354_INFRA_Populate_S3_bucket` into
      master and run `git branch` again
  - Manually check if there is any textual difference
    - Another approach is to check what the differences are between the branch
      and `origin/master`
      ```
      > git log master..HEAD
      6465b0c saggese, 25 seconds ago : Merge branch 'master' into PTask354_INFRA_Populate_S3_bucket  (HEAD -> PTask354_INFRA_Populate_S3_bucket, origin/PTask354_INFRA_Populate_S3_bucket)
      > git log HEAD..master
      ```
    - Here we see that there are no textual differences
    - So we can either merge the branch into `master` or just kill directly
  - Kill-kill-kill!
    - To delete both the local and remote branch you can do
      ```
      > git branch -d PTask354_INFRA_Populate_S3_bucket
      > git push origin --delete PTask354_INFRA_Populate_S3_bucket
      ```

# How-to and troubleshooting

## Do not mess up your branch

- If you are working in a branch, before doing `git push` make sure the branch
  is not broken (e.g., from a mistake in merge / rebase mess)
- A way to check that the branch is sane is the following:
  - Make sure that you don't have extra commits in your branch:
    - The difference between your branch and master
      `bash > git fetch > git checkout &lt;BRANCH> > git log origin/master..HEAD`
      shows only commits made by you or, if you are not the only one working on
      the branch, only commits belonging to the branch with the same `PTaskXYZ`
    - E.g., if George is working on `PTask275` and sees that something funny is
      going on:
      ```
      a379826 Ringo, 3 weeks ago : LemTask54: finish dataflow through
      cross-validation
      33a46b2 George, 2 weeks ago : PTask275 Move class attributes docstrings to init, change logging
      ```
  - Make sure the files modified in your branch are only the file you expect to
    be modified
    ```
    > git fetch
    > git checkout &lt;BRANCH>
    > git diff --name-only master..HEAD
    ```
  - If you see that there is a problem, don't push upstream (because the branch
    will be broken for everybody) and ask a Git expert

## Analyzing commits

### Show files modified in a commit

- You can see the files modified in a given commit hash with:
  ```
  > git show --name-only $HASH
  ```
- E.g.,
  ```
  > git show --name-only 39a9e335298a3fe604896fa19296d20829801cf2

  commit 39a9e335298a3fe604896fa19296d20829801cf2
  Author: Julia &lt;julia@...>
  Date:   Fri Sep 27 11:43:41 2019

  PTask274 lint

  vendors/cme/utils.py
  vendors/first_rate/utils.py
  ```

## Conflicts

### Getting the conflicting files

- To see the files in conflicts
  ```
  git diff --name-only --diff-filter=U
  ```
- This is what the script `git_conflict_files.sh` does

### Accepting "theirs"
```
> git checkout --theirs $FILES
> git add $FILES
```

- TODO(gp): Fix this ours and theirs. The first option represents the current
  branch from which you executed the command before getting the conflicts, and
  the second option refers to the branch where the changes are coming from.
  ```
  > git show :1:README
  > git show :2:README
  > git show :3:README
  ```
- Stage #1 is the common ancestor of the files, stage #2 is the target-branch
  version, and stage #3 is the version you are merging from.

## How to get out of a messy/un-mergeable branch

- If one screws up a branch:
  - Rebase to master
  - Resolve the conflicts
    - E.g., pick the `master` version when needed:
      ```
      git checkout --theirs ...; git add ...
      ```
  - Diff the changes in the branch vs another client at `master`
    ```
    > diff_to_vimdiff.py --dir1 $DIR1/amp --dir2 $DIR2/amp --skip_vim
    Saving log to file '/Users/saggese/src/...2/amp/dev_scripts/diff_to_vimdiff.py.log'
    10-06_15:22 INFO : _parse_diff_output:36  : Reading '/tmp/tmp.diff_to_vimdiff.txt'
    #       DIFF: README.md
    #       DIFF: core/dataflow.py
    #       DIFF: core/dataflow_core.py
    #       DIFF: core/test/test_core.py
    #       DIFF: dev_scripts/diff_to_vimdiff.py
    #       ONLY: diff_to_vimdiff.py.log in $DIR1/dev_scripts
    #       DIFF: dev_scripts/grc
    #       ONLY: code_style.txt in $DIR2/docs/notes
    ...
    #       DIFF: vendors/test/test_vendors.py
    ```
  - Diff / merge manually the files that are different
    ```
    > diff_to_vimdiff.py --dir1 $DIR1/...2/amp --dir2 $DIR2/...3/amp --skip_vim
    > --only_diff_content
    #       DIFF: README.md
    #       DIFF: core/dataflow.py
    #       DIFF: core/dataflow_core.py
    #       DIFF: core/test/test_core.py
    ...
    ```

## Reverting

### Reverting the last local commit
```
> git reset --soft HEAD~
```

## Branching

### Checking what work has been done in a branch

- Look at all the branches available:
  ```
  # Fetch all the data from origin.
  > git fetch
  # List all the branches.
  > git branch -r
  origin/HEAD -> origin/master
  origin/PTask274
  ...
  ```
- Go to the branch:
  ```
  > git checkout PTask274
  ```
- Check what are the commits that are in the current branch HEAD but not in
  `master`:
  ```
  > gll master..HEAD
  > git log master..HEAD
  eb12233 Julia PTask274 verify dataset integrity ( 13 hours ago) Sat Sep 28 18:55:12 2019 (HEAD -> PTask274, origin/PTask274) ...
  a637594 saggese PTask274: Add tag for review ( 3 days ago) Thu Sep 26 17:13:33 2019
  ```
- To see the actual changes in a branch you can't do (Bad) \
  `> git diff master..HEAD` since `git diff` compares two commits and not a range
  of commits like `git log` (yes, Git has a horrible API)
- What you need to do is to get the first commit in the branch and the last from
  `git log` and compare them:
  ```
  > git difftool a637594..eb12233
  > gd a637594..eb12233
  ```

### Checking if you need to merge `master` into your feature branch

- You can see what commits are in master but missing in your branch with:
  ```
  > gll ..master
  de51a7c saggese Improve script to help diffing trees in case of difficult merges. Add notes from reviews ( 5 hours ago) Sat Oct 5 11:24:11 2019 (origin/master, origin/HEAD, master)
  8acd60c saggese Add a basic end-to-end unit test for the linter ( 19 hours ago) Fri Oct 4 21:28:09 2019 …
  ```
- You want to `rebase` your feature branch onto `master`

### Comparing the difference of a directory among branches

- This is useful if we want to focus on changes on a single dir
  ```
  > git ll master..PTask274 vendors/cme
  39a9e33 Julia PTask274 lint ( 2 days ago) Fri Sep 27 11:43:41 2019
  c8e7e1a Julia PTask268 modify according to review16 ( 2 days ago) Fri Sep 27
  11:41:47 2019
  a637594 saggese PTask274: Add tag for review ( 3 days ago) Thu Sep 26 17:13:33
  2019
  ```
  ```
  > git diff --name-only a637594..33a46b2 -- vendors helpers
  helpers/csv.py
  vendors/cme/utils.py
  vendors/first_rate/Task274_verify_datasets.ipynb
  vendors/first_rate/Task274_verify_datasets.py
  vendors/first_rate/reader.py
  vendors/first_rate/utils.py
  vendors/test/test_vendors.py
  ```

## Merging `master`

- If your branch lives long, you want to apply changes made on master to show on
  your branch
- Merge flow
- Assume your branch is clean
  - E.g., everything is committed, or stashed
- Pull changes from `master` on the remote repo
  ```
  > git checkout master
  > git pull
  ```
- Checkout your feature branch
  ```
  > git checkout my_feature
  ```
- Merge stuff from `master` to `my_feature`
  ```
  > git merge master --no-ff
  ... editor will open a message for the merge commit ...
  ```
- In few informal words, the `--no-ff` option means that commits are not
  "inlined" (similar to rebase) even if possible, but a merge commit is always
  used
  - The problem is that if the commits are "inlined" then you can't revert the
    change in one shot like we would do for a merge commit, but you need to
    revert all the inlined changes

## Rebasing

- **For now, we suggest avoiding the rebase flow**
- The reason is that rebase makes things cleaner when used properly, but can get
  you into deep trouble if not used properly
- You can rebase onto `master`, i.e., you re-apply your changes to `master`
- Not the other way around: that would be a disaster!
  ```
  > git checkout my_feature
  # See that you have that master doesn't have.
  > git ll origin/master..
  # See that master has that you don't have.
  > git ll ..origin/master
  > git rebase master
  > git ll ..origin/master
  # Now you see that there is nothing in master you don't have
  > git ll origin/master..
  # You can see that you are ahead of master
  ```

## Merging pull requests

- The procedure for manual merges is as follows
- **Do not merge yourself unless explicitly requested by a reviewer**
- Pull changes from remote `master` branch
  ```
  > git checkout master
  > git pull
  ```
- Merge your branch into `master` without fast-forward
  ```
  > git merge --no-ff my_feature
  ```
- Push the newly merged master
  ```
  > git push
  ```
- Delete the branch, if you are done with it:
  ```
  > git branch -d my_feature
  ```

# Submodules

## Adding a submodule

- Following the instructions in
  [https://git-scm.com/book/en/v2/Git-Tools-Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)

## Working in a submodule

- When you work in a submodule, the flow should be like:
  - Create a branch in a submodule
  - Do your job
  - Push the submodule branch
  - Create a PR in the submodule when you are done

## Updating a submodule to the latest commit

- After the submodule PR is merged:
  - Checkout the submodule in the master branch and do `git pull`
  - In the main repo, create a branch like `PTask1234_update_submodule`
  - From the new branch do `git add &lt;submodule_name>`, e.g., `git add amp`
  - Commit changes, push
  - Create a PR

## To check if supermodule and amp are in sync

- Run the script:
  ```
  > dev_scripts/git/git_submodules_are_updated.sh
  ```

## Roll forward git submodules pointers:

- Run the script:
  ```
  > dev_scripts/git/git_submodules_roll_fwd.sh
  ```

## To clean all the repos
```
> git submodule foreach git clean -fd
```

## Pull a branch without checkout

- This is useful when merging `master` in a different branch and we don't want
  to checkout master just to pull
  ```
  > git fetch origin master:master
  ```

## To force updating all the submodules

- Run the script `> dev_scripts/git/git_submodules_pull.sh` or
  ```
  > git submodule update --init --recursive`
  > git submodule foreach git pull --autostash
  ```
