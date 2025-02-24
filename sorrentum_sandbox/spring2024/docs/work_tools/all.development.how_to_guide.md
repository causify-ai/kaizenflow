

<!-- toc -->

- [Setting up Git credentials](#setting-up-git-credentials)
  * [Preamble](#preamble)
  * [Check Git credentials](#check-git-credentials)
  * [Setting Git credentials](#setting-git-credentials)
  * [Enforcing Git credentials](#enforcing-git-credentials)
- [Create the env](#create-the-env)
- [Playback](#playback)
- [Publish a notebook](#publish-a-notebook)
  * [Detailed instructions](#detailed-instructions)
  * [Publish notebooks](#publish-notebooks)
  * [Open a published notebook](#open-a-published-notebook)
    + [Start a server](#start-a-server)
    + [Using the dev box](#using-the-dev-box)
    + [Using Windows browser](#using-windows-browser)
- [How to create a private fork](#how-to-create-a-private-fork)
- [Integrate public to private: `amp` -> `cmamp`](#integrate-public-to-private-amp---cmamp)
  * [Set-up](#set-up)
  * [Ours vs theirs](#ours-vs-theirs)
  * [Sync the repos (after double integration)](#sync-the-repos-after-double-integration)
  * [Updated sync](#updated-sync)
  * [Check that things are fine](#check-that-things-are-fine)
  * [Integrate private to public: `cmamp` -> `amp`](#integrate-private-to-public-cmamp---amp)
  * [Squash commit of everything in the branch](#squash-commit-of-everything-in-the-branch)
- [Double integration `cmamp` `amp`](#double-integration-cmamp--amp)
  * [Script set-up](#script-set-up)
  * [Manual set-up branches](#manual-set-up-branches)
  * [High-level plan](#high-level-plan)
  * [Sync `im` `cmamp` -> `amp`](#sync-im-cmamp---amp)
  * [Sync everything](#sync-everything)
  * [Files that need to be different](#files-that-need-to-be-different)
    + [Testing](#testing)

<!-- tocstop -->

# Setting up Git credentials

## Preamble

- Git allows setting credentials at different "levels":
  - System (set for all the users in `/etc/git`)
  - Global (set for a single user in `$HOME/.gitconfig` or
    `$HOME/.config/git/config`)
  - Local (set on a per client basis in `.git/config` in the repo root)
  - Git uses a hierarchical config approach in which settings of a broader scope
    are inherited if not overridden.
- Refs:
  - How to customize Git:
    https://git-scm.com/book/en/v2/Customizing-Git-Git-Configuration
  - Details on `git config`: https://git-scm.com/docs/git-config

## Check Git credentials

- You can check the Git credentials that will be used to commit in a client by
  running:
  ```bash
  > git config -l | grep user
  user.name=saggese
  user.email=saggese@gmail.com
  github.user=gpsaggese
  ```
- To know at which level each variable is defined, run
  ```bash
  > git config --show-origin user.name
  file:/Users/saggese/.gitconfig saggese
  ```
- You can see all the `Authors` in a Git repo history with:
  ```bash
  > git log | grep -i Author | sort | uniq
  ...
  ```
- Git doesn't do any validation of `user.name` and `user.email` but it just uses
  these values to compose a commit message like:

  ```bash
  > git log -2
  commit 31052d05c226b1c9834d954e0c3d5586ed35f41e (HEAD ->
  AmpTask1290_Avoid_committing_to_master_by_mistake)
  Author: saggese <saggese@gmail.com>
  Date: Mon Jun 21 16:22:25 2021

  Update hooks
  ```

## Setting Git credentials

- To keep things simple and avoid variability, our convention is to use:
  - As `user.name` our Linux user name on the local computer we are using to
    commit which is returned by `whoami` (e.g., `user.name=saggese`)
  - As `user.email` the email that corresponds to that user (e.g,.
    `user.email=saggese@gmail.com`)
- To accomplish the set-up above you can:
  - Use in `/Users/saggese/.gitconfig` the values for our open-source account,
    so that they are used by default
  ```bash
  > git config --global user.name $(whoami)
  > git config --global user.email YOUR_EMAIL
  ```
- Use the correct user / email in the repos that are not open-source
  ```bash
  > cd $GIT_ROOT
  > git config --local user.name $(whoami)
  > git config --local user.email YOUR_EMAIL
  ```
- Note that you need to set these local values on each Git client that you have
  cloned, since Git doesn't version control these values

## Enforcing Git credentials

- We use Git hooks to enforce that certain emails are used for certain repos
  (e.g., we should commit to our open-source repos only using our personal
  non-corporate email).
- You need to install the hooks in each Git client that you use. Conceptually
  this step is part of `git clone`: every time you clone a repo locally you need
  to set the hooks.
- TODO(gp): We could create a script to automate cloning a repo and setting it
  up.

  ```bash
  > cd //amp
  > ./dev_scripts/git/git_hooks/install_hooks.py --action install
  > cd //lem
  > ./amp/dev_scripts/git/git_hooks/install_hooks.py --action install
  ```

- This procedure creates some links from `.git/hook` to the scripts in the repo.
- You can also use the action `status` to see the status and `remove` to the
  hooks.

# Create the env

- You can follow the
  ```bash
  # Build the client env
  > dev_scripts/client_setup/build.sh
  > source dev_scripts/setenv_amp.sh
  ```

# Playback

# Publish a notebook

- `publish_notebook.py` is a little tool that allows to:
  1. Opening a notebook in your browser (useful for read-only mode)
     - E.g., without having to use Jupyter notebook (which modifies the file in
       your client) or github preview (which is slow or fails when the notebook
       is too large)
  2. Sharing a notebook with others in a simple way
  3. Pointing to detailed documentation in your analysis Google docs
  4. Reviewing someone's notebook
  5. Comparing multiple notebooks against each other in different browser
     windows
  6. Taking a snapshot / checkpoint of a notebook as a backup or before making
     changes
     - This is a lightweight alternative to "unit testing" to capture the
       desired behavior of a notebook
     - One can take a snapshot and visually compare multiple notebooks
       side-by-side for changes

## Detailed instructions

- You can get details by running:

  ```bash
  > dev_scripts/notebooks/publish_notebook.py -h
  ```

- Plug-in for Chrome
  [my-s3-browser](https://chrome.google.com/webstore/detail/my-s3-browser/lgkbddebikceepncgppakonioaopmbkk?hl=en)

## Publish notebooks

- Make sure that your environment is set up properly

  ```bash
  > more ~/.aws/credentials
  [am]
  aws_access_key_id=**
  aws_secret_access_key=**
  aws_s3_bucket=alphamatic-data

  > printenv | grep AM_
  AM_AWS_PROFILE=am
  ```

- If you don't have them, you need to re-run `source dev_scripts/setenv.sh` in
  all the shells. It might be easier to kill that tmux session and restart it

  ```bash
  > tmux kill-session --t limeXYZ

  > ~/go_lem.sh XYZ
  ```

- Inside or outside a Docker bash run

  ```bash
  > publish_notebook.py --file http://127.0.0.1:2908/notebooks/notebooks/Task40_Optimizer.ipynb --action publish_on_s3
  ```

- The file is copied to S3

  ```bash
  Copying './Task40_Optimizer.20210717_010806.html' to
  's3://alphamatic-data/notebooks/Task40_Optimizer.20210717_010806.html'
  ```

- You can also save the data locally:

  ```bash
  > publish_notebook.py --file
  amp/oms/notebooks/Master_forecast_processor_reader.ipynb --action publish_on_s3
  --aws_profile saml-spm-sasm
  ```

- You can also use a different path or profile by specifying it directly

  ```bash
  > publish_notebook.py \
  --file http://127.0.0.1:2908/notebooks/notebooks/Task40_Optimizer.ipynb \
  --action publish_on_s3 \
  --s3_path s3://alphamatic-data/notebooks \
  --aws_profile am
  ```

## Open a published notebook

### Start a server

- `(cd /local/home/share/html/published_notebooks; python3 -m http.server 8000)`

- Go to the page in the local browser

### Using the dev box

- To open a notebook saved on S3, \*outside\* a Docker container run:

  ```bash
  > publish_notebook.py --action open --file
  s3://alphamatic-data/notebooks/Task40_Optimizer.20210717_010806.html
  ```

- This opens a Chrome window through X-windows.
- To open files faster you can open a Chrome window in background with

  ```bash
  > google-chrome
  ```

- And then navigate to the path (e.g.,
  `/local/home/share/html/published_notebooks/Master_forecast_processor_reader.20220810-112328.html`)

### Using Windows browser

- Another approach is:

  ```bash
  > aws s3 presign --expires-in 36000
  s3://alphamatic-data/notebooks/Task40_Optimizer.20210716_194400.html | xclip
  ```

- Open the link saved in the clipboard in the Windows browser
- For some reason, Chrome saves the link instead of opening, so you need to
  click on the saved link

# How to create a private fork

- https://stackoverflow.com/questions/10065526/github-how-to-make-a-fork-of-public-repository-private
- From
  https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/creating-a-repository-on-github/duplicating-a-repository

  ```bash
  > git clone --bare git@github.com:alphamatic/amp.git amp_bare

  > git push --mirror https://github.com/cryptomtc/cmamp.git
  ```

- It worked only as cryptomtc, but not using my key

# Integrate public to private: `amp` -> `cmamp`

## Set-up

```bash
> git remote add public git@github.com:alphamatic/amp

# Go to cmamp
> cd /data/saggese/src/cmamp1
> cd /Users/saggese/src/cmamp1

# Add the remote
# git remote add public https://github.com/exampleuser/public-repo.git
> git remote add public git@github.com:alphamatic/amp

> git remote -v
origin https://github.com/cryptomtc/cmamp.git (fetch)
origin https://github.com/cryptomtc/cmamp.git (push)
public git@github.com:alphamatic/amp (fetch)
public git@github.com:alphamatic/amp(push)
```

## Ours vs theirs

- From
  https://stackoverflow.com/questions/25576415/what-is-the-precise-meaning-of-ours-and-theirs-in-git/25576672

- When merging:
  - Ours = branch checked out (git checkout \*ours\*)
  - Theirs = branch being merged (git merge \*theirs\*)
- When rebasing the role is swapped
  - Ours = branch being rebased onto (e.g., master)
  - Theirs = branch being rebased (e.g., feature)

## Sync the repos (after double integration)

```bash
> git fetch origin; git fetch public

# Pull from both repos

> git pull public master -X ours

# You might want to use `git pull -X theirs` or `ours`

> git pull -X theirs

> git pull public master -s recursive -X ours

# When there is a file added it is better to add

> git diff --name-status --diff-filter=U | awk '{print $2}'

im/ccxt/db/test/test_ccxt_db_utils.py

# Merge branch

> gs
+ git status
On branch AmpTask1786_Integrate_20211128_02 Your branch and 'origin/AmpTask1786_Integrate_20211128_02' have diverged, and have 861 and 489
different commits each, respectively. (use "git pull" to merge the remote branch into yours)

You are in a sparse checkout with 100% of tracked files present.

nothing to commit, working tree clean

> git pull -X ours

## Make sure it's synced at ToT

> rsync --delete -r /Users/saggese/src/cmamp2/ /Users/saggese/src/cmamp1
--exclude='.git/'

> diff -r --brief /Users/saggese/src/cmamp1 /Users/saggese/src/cmamp2 | grep -v \.git
```

## Updated sync

```bash
> git fetch origin; git fetch public
```

## Check that things are fine

```bash
> git diff origin/master... >patch.txt

> cd /Users/saggese/src/cmamp2

# Create a branch

> git checkout -b Cmamp114_Integrate_amp_cmamp_20210928
> git apply patch.txt

# Compare branch with references

> dev_scripts/diff_to_vimdiff.py --dir1 /Users/saggese/src/cmamp1/im --dir2
/Users/saggese/src/cmamp2/im

> diff -r --brief /Users/saggese/src/lemonade3/amp \~/src/cmamp2 | grep -v "/im"

# Creates a merge commit
> git push origin master
```

## Integrate private to public: `cmamp` -> `amp`

```bash
> cd /data/saggese/src/cmamp1
> tar cvzf patch.tgz $(git diff --name-onlyorigin/master public/master | grep -v repo_config.py)

> cd /Users/saggese/src/amp1 git remote add cmamp
> git@github.com:cryptomtc/cmamp.git

> GIT_SSH_COMMAND="ssh -i \~/.ssh/cryptomatic/id_rsa.cryptomtc.github" git fetch
> git@github.com:cryptomtc/cmamp.git

> git checkout -b Integrate_20210928

> GIT_SSH_COMMAND="ssh -i \~/.ssh/cryptomatic/id_rsa.cryptomtc.github" git pull
> cmamp master -X ours
```

## Squash commit of everything in the branch

- From
  https://stackoverflow.com/questions/25356810/git-how-to-squash-all-commits-on-branch

  ```bash
  > git checkout yourBranch
  > git reset $(git merge-base master $(git branch
  --show-current))
  > git add -A
  > git commit -m "Squash"
  > git push --force
  ```

# Double integration `cmamp` < -- > `amp`

- The bug is https://github.com/alphamatic/amp/issues/1786

## Script set-up

```bash
> vi /Users/saggese/src/amp1/dev_scripts/integrate_repos/setup.sh
Update the date

> vi /Users/saggese/src/amp1/dev_scripts/integrate_repos/*

> cd \~/src/amp1
> source /Users/saggese/src/amp1/dev_scripts/integrate_repos/setup.sh

> cd \~/src/cmamp1
> source /Users/saggese/src/amp1/dev_scripts/integrate_repos/setup.sh
```

## Manual set-up branches

```bash
# Go to cmamp1
> go_amp.sh cmamp 1

# Set up the env vars in both clients
> export AMP_DIR=/Users/saggese/src/amp1; export
CMAMP_DIR=/Users/saggese/src/cmamp1; echo "$AMP_DIR"; ls
$AMP_DIR; echo "$CMAMP_DIR"; ls $CMAMP_DIR

# Create two branches
> export BRANCH_NAME=AmpTask1786_Integrate_20211010 export BRANCH_NAME=AmpTask1786_Integrate_2021117
...
> cd $AMP_DIR

# Create automatically
> i git_create_branch -b $BRANCH_NAME

# Create manually
> git checkout -b $BRANCH_NAME
> git push --set-upstream origin $BRANCH_NAME

> cd $CMAMP_DIR
> i git_create_branch -b $BRANCH_NAME
```

## High-level plan

- SUBDIR=im
  - Typically `cmamp` is copied on top of `amp`
- SUBDIR=devops
  - `cmamp` and `amp` need to be different (until we unify the Docker flow)
- Everything else
  - Typically `amp` -> `cmamp`

## Sync `im` `cmamp` -> `amp`

```bash
SUBDIR=im

# Check different files
> diff -r --brief $AMP_DIR/$SUBDIR $CMAMP_DIR/$SUBDIR | grep -v .git

# Diff the entire dirs with vimdiff
> dev_scripts/diff_to_vimdiff.py --dir1 $AMP_DIR/$SUBDIR --dir2 $CMAMP_DIR/$SUBDIR

# Find different files
> find $AMP_DIR/$SUBDIR -name "*"; find $CMAMP_DIR/$SUBDIR -name "*" sdiff
/tmp/dir1 /tmp/dir2

# Copy cmamp -> amp
> rsync --delete -au $CMAMP_DIR/$SUBDIR/ $AMP_DIR/$SUBDIR
-a = archive
-u = ignore newer

# Add all the untracked files
> cd $AMP_DIR/$SUBDIR && git add $(git ls-files -o --exclude-standard)

# Check that there are no differences after copying
> dev_scripts/diff_to_vimdiff.py --dir1 $AMP_DIR/$SUBDIR --dir2 $CMAMP_DIR/$SUBDIR

==========

> rsync --delete -rtu $AMP_DIR/$SUBDIR/ $CMAMP_DIR/$SUBDIR

> rsync --dry-run -rtui --delete $AMP_DIR/$SUBDIR/ $CMAMP_DIR/$SUBDIR/ .d..t.... ./
> f..t.... __init__.py
cd+++++++ features/
> f+++++++ features/__init__.py
> f+++++++ features/pipeline.py
cd+++++++ features/test/
> f+++++++ features/test/test_feature_pipeline.py
cd+++++++ features/test/TestFeaturePipeline.test1/
cd+++++++ features/test/TestFeaturePipeline.test1/output/
> f+++++++ features/test/TestFeaturePipeline.test1/output/test.txt
.d..t.... price/
.d..t.... real_time/
> f..t.... real_time/__init__.py
.d..t.... real_time/notebooks/
> f..t.... real_time/notebooks/Implement_RT_interface.ipynb
> f..t.... real_time/notebooks/Implement_RT_interface.py
.d..t.... real_time/test/
cd+++++++ real_time/test/TestRealTimeReturnPipeline1.test1/
cd+++++++ real_time/test/TestRealTimeReturnPipeline1.test1/output/
> f+++++++ real_time/test/TestRealTimeReturnPipeline1.test1/output/test.txt
.d..t.... returns/
> f..t.... returns/__init__.py
> f..t.... returns/pipeline.py
.d..t.... returns/test/
> f..t.... returns/test/test_returns_pipeline.py
.d..t.... returns/test/TestReturnsBuilder.test_equities1/
.d..t.... returns/test/TestReturnsBuilder.test_equities1/output/
.d..t.... returns/test/TestReturnsBuilder.test_futures1/
.d..t.... returns/test/TestReturnsBuilder.test_futures1/output/

> rsync --dry-run -rtui --delete $CMAMP_DIR/$SUBDIR/ $AMP_DIR/$SUBDIR/
> f..t.... price/__init__.py
> f..t.... price/pipeline.py
> f..t.... real_time/pipeline.py
> f..t.... real_time/test/test_dataflow_amp_real_time_pipeline.py
> f..t.... returns/test/TestReturnsBuilder.test_equities1/output/test.txt
> f..t.... returns/test/TestReturnsBuilder.test_futures1/output/test.txt
```

## Sync everything

```bash
# Check if there is anything in cmamp more recent than amp
> rsync -au --exclude='.git' --exclude='devops' $CMAMP_DIR/ $AMP_DIR

# vimdiff
> dev_scripts/diff_to_vimdiff.py --dir1 $AMP_DIR --dir2
$CMAMP_DIR

F1: skip
F9: choose left (i.e., amp)
F10: choose right (i.e,. cmamp)

# Copy

> rsync -au --delete --exclude='.git' --exclude='devops' --exclude='im'
$AMP_DIR/
$CMAMP_DIR

# Add all the untracked files

> (cd $CMAMP_DIR/$SUBDIR && git add $(git ls-files -o --exclude-standard))

> diff -r --brief $AMP_DIR $CMAMP_DIR | grep -v .git | grep Only
```

## Files that need to be different

- `amp` needs an `if False` `helpers/lib_tasks.py`

- `amp` needs two tests disabled `im/ccxt/data/load/test/test_loader.py`

  `im/ccxt/data/load/test/test_loader.py`

TODO(gp): How to copy files in vimdiff including last line?

- Have a script to remove all the last lines
- Some files end with an `0x0a`
- `tr -d '\\r'`

  ```bash
  > find . -name "\*.txt" | xargs perl -pi -e 's/\\r\\n/\\n/g'
  # Remove `No newline at end of file`
  > find . -name "\*.txt" | xargs perl -pi -e 'chomp if eof'
  ```

### Testing

- Run `amp` on my laptop (or on the server)
- IN PROGRESS: Get `amp` PR to pass on GH
- IN PROGRESS: Run lemonade on my laptop
- Run `cmamp` on the dev server
- Get `cmamp` PR to pass on GH
- Run dev_tools on the dev server
