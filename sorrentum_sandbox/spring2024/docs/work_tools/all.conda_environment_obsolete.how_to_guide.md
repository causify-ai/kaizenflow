

<!-- toc -->

- [Conda flow](#conda-flow)
  * [(optional) Install anaconda](#optional-install-anaconda)
  * [Configure anaconda](#configure-anaconda)
  * [Create conda environment](#create-conda-environment)
  * [Check conda environment](#check-conda-environment)
  * [Configure conda environment](#configure-conda-environment)
  * [Delete / recreate environment](#delete--recreate-environment)
    + [Overwrite a conda environment with `create_conda.py`](#overwrite-a-conda-environment-with-create_condapy)
    + [Manually delete a conda environment](#manually-delete-a-conda-environment)
    + [To delete the entire conda installation (advanced users)](#to-delete-the-entire-conda-installation-advanced-users)
  * [Update anaconda](#update-anaconda)
  * [Configure user credentials](#configure-user-credentials)
  * [Be patient](#be-patient)
- [Conda bloat](#conda-bloat)
  * [Minimize conda bloat](#minimize-conda-bloat)
- [Conda environment lifecycle](#conda-environment-lifecycle)
  * [Experimental conda environment](#experimental-conda-environment)
  * [Releasing a new conda environment](#releasing-a-new-conda-environment)
- [Conda maintenance (only for admins)](#conda-maintenance-only-for-admins)
  * [Updating conda itself](#updating-conda-itself)
  * [Cleaning conda packages](#cleaning-conda-packages)

<!-- tocstop -->

_THIS IS OBSOLETE AFTER DOCKER DEV CONTAINER_

# Conda flow

## (optional) Install anaconda

- For the AWS machine there is already a central conda, so there is no need for
  users to install
- For a laptop you need to install it yourself
  - You need _anaconda3_

## Configure anaconda

- Configure anaconda for your shell using:
  ```bash
  > conda init bash
  ```
- Anaconda3 adds a snippet of code in your `.bashrc`

## Create conda environment

- This is needed to install all the packages that are required for development:
  ```bash
  > cd $DST_DIR
  > ./dev_scripts/create_conda.develop.sh
  ```
- This script takes 5 mins to run

- You need to create an environment for every server you use (e.g., for the AWS
  server `research`, for your laptop)
- You can reuse the same environment for multiple Git clients

## Check conda environment

- Check that your conda environment exists:
  ```bash
  > conda info --envs
  # conda environments:
  #
  base                     /anaconda3
  develop            *  /home/<USER>/.conda/envs/develop
  ```

## Configure conda environment

- Every time you open a shell you need to activate the development environment
  run:

  ```bash
  > source dev_scripts/setenv_....sh
  ```

- This script:
  - Activates the conda environment
  - Sets environment variables
  - Makes sure things are working properly

## Delete / recreate environment

### Overwrite a conda environment with `create_conda.py`

- You can use the option `--delete_env_if_exists` to overwrite a conda env,
  creating it from scratch
- This is the typical approach

- There are some pre-packaged command lines to create the standard environments,
  e.g., `./dev_scripts/create_conda.develop.sh`

- The `create_conda.py` help as some useful examples of command lines, see the
  help:
  ```bash
  > create_conda.py -h
  ```

### Manually delete a conda environment

- You can delete a conda environment by simply deleting the corresponding
  directory
- The conda command tries to be smart removing the packages and leaving the dir,
  but IMO it doesn't always work
- You look at the environments with:
  ```bash
  > conda info --envs
  # conda environments:
  #
  ...
  develop               *  /Users/<USER>/.conda/envs/develop
  ...
  ```
- Then you can delete with:
  ```bash
  > rm -rf /Users/<USER>/.conda/envs/develop
  ```
- It's a good idea to move it so you can resume it if something goes wrong:
  ```bash
  > mv /Users/<USER>/.conda/envs/develop > /Users/<USER>/.conda/envs/develop.OLD
  ```
  - Note that `develop.OLD` might not work anymore since all the links are
    broken by the move

### To delete the entire conda installation (advanced users)

- This is a dangerous operation, since it deletes the executable `conda`
  - You want to do this only when your environment is screwed up: a more expert
    team member can help you diagnose it
- If you want to delete your conda installation, find the base env
  ```bash
  > conda info --envs
  base                     /anaconda3
  ...
  ```
- Run `rm -rf /anaconda3`
- A good idea is to move it so you can resume the state

## Update anaconda

- To update anaconda (i.e., the framework that manages conda packages and
  `conda` executable)

  ```bash
  > conda activate base
  # Remove index cache, lock files, tarballs, unused cache packages, and source
  # cache.
  > conda clean --all
  > conda update conda
  > conda update anaconda
  > conda -V
  conda 4.7.12
  ```

- You can try to activate one environment
  ```bash
  > conda activate amp_develop
  > which python
  /Users/saggese/.conda/envs/amp_develop/bin/python
  ```

## Configure user credentials

- For now this topic is obsolete. All development with AWS is running on a
  server side (or locally) in a docker container. Here you can find the
  documentation
  [the link](https://github.com/cryptokaizen/cmamp/blob/master/docs/work_tools/all.docker.how_to_guide.md)

- Update the user credential files in `amp/helpers/user_credentials.py`
  - Commit this so all your clients are configured
- Typically you can just copy-paste a portion of the configuration of another
  user

## Be patient

- The `create_conda.py` flow is designed to make our projects portable across:
  - Platforms (e.g., macOS, Linux)
  - Different installation of OSes (e.g., GP's laptop vs Paul's laptop) with all
    the peculiar ways we install and manage servers and laptops
  - Different versions of conda
  - Different versions of python 3.x
  - Different versions of python packages

- There is no easy way to make sure that `create_conda.py` works for everybody
  - We can only make sure that Jenkins builds the environment correctly in its
    set-up by following the process described above
  - Try to follow the steps one by one, using a clean shell, cutting and pasting
    commands
  - If you hit a problem, be patient, ping GP / Paul, and we will extend the
    script to handle the quirks of your set-up

# Conda bloat

- "Conda bloat" refers to the situation when there are more packages in the
  conda recipe than what strictly needed to allow us to make progress.

- The effects of conda bloat are:
  - Longer time for `conda` to solve the dependencies, download the packages,
    and update the environment
  - Additional dependencies forcing `conda` to install older packages that can
    create subtle issues in our environment (we want our code always to be
    forward compatible, but we can't afford our code to be back compatible)
  - People starting pinning down packages to get deterministic library behaviors
  - In the worst case, not being able to install the environment at all due to
    conflicting `conda` requirements

- On the one side, we want to minimize "conda bloat".
- On the other side, we want to be able to experiment with packages.

## Minimize conda bloat

- To minimize conda bloat, our process consists of adding a package to the conda
  recipe when a new package is actually needed by code and to run unit tests
  - Having code using the library and running unit tests for that code should
    happen together
  - The rule is "Important code should be tested, and if code is not important
    it should not be in the repo at all"
  - Thus a corollary is that all code in the repo should be tested

# Conda environment lifecycle

## Experimental conda environment

- On the other side we want to be free to experiment with a package that can
  save us tons of development time.

- The proposed approach is:
  - Install the package in whatever way you want on top of your standard conda
    environment (`conda`, `pip`, whatever)
  - Be aware that some packages are not easy to add to our production system
    (e.g. packages written by students trying to graduate, non-coding savvy PhDs
    and professors)
  - Create a new local experimental conda environment with:
    `create_conda.py --env_name develop.nlp`
  - If you want to reproduce your environment or share it (e.g., among the NLP
    team) you can branch `dev_scripts/install/requirements/develop.yaml` and
    modify it, then you can create an environment programmatically with:
    `create_conda.py --env_name develop.nlp --req_file dev_scripts/install/requirements/develop.nlp.yaml`

- We can make this process more automated by generalizing the scripts we already
  have.

## Releasing a new conda environment

- Once the new package is added to the official conda environment, we should:
  - Test the new conda environment locally, by creating a fresh environment and
    running all the tests
  - Compare the list of packages installed before / after the change:
    `git diff amp/dev_scripts/install/conda_envs/amp_develop.saggese.Darwin.gpmac.lan.txt`
    - E.g., Check whether installed pandas went from 0.25 to 0.14.1
  - Use the `dev` build to make sure Jenkins is happy with it, especially when
    we develop on a different OS than Linux
  - Send an email to the team asking them to recreate the environment

- Typically GP takes care of getting all this fun stuff to work, but you are
  welcome to try locally to minimize surprises.

# Conda maintenance (only for admins)

## Updating conda itself

- To update conda itself you can run:

```bash
> conda activate base

> conda --version
3.7.1

> conda update anaconda

> conda --version
3.8.0
```

## Cleaning conda packages

- One can clean up the entire cache of packages with:

```bash
> conda clean --yes --all
```

- This operation:
  - Affects the conda system for all the users
  - Is just about deleting cached artifacts so it should not have destructive
    effects
