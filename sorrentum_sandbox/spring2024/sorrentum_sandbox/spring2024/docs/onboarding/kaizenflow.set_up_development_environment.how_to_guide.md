

<!-- toc -->

- [Set up KaizenFlow development environment](#set-up-kaizenflow-development-environment)
  * [Introduction](#introduction)
  * [Technologies used](#technologies-used)
  * [Clone the code](#clone-the-code)
  * [Building the thin environment](#building-the-thin-environment)
  * [Install and test Docker](#install-and-test-docker)
    + [Supported OS](#supported-os)
    + [Install Docker](#install-docker)
    + [Checking Docker installation](#checking-docker-installation)
    + [Docker installation troubleshooting](#docker-installation-troubleshooting)
  * [Tmux](#tmux)
  * [Some useful workflows](#some-useful-workflows)
  * [Coding Style](#coding-style)
  * [Linter](#linter)
    + [Run the linter and check the linter results](#run-the-linter-and-check-the-linter-results)
  * [Writing and Contributing Code](#writing-and-contributing-code)
  * [How to receive a crypto transfer](#how-to-receive-a-crypto-transfer)

<!-- tocstop -->

# Set up KaizenFlow development environment

## Introduction

This document outlines the development set up to be followed by KaizenFlow
contributors. By documenting the set up, we aim to streamline the information
flow and make the contribution process seamless by creating a collaborative and
efficient coding environment for all contributors.

Happy coding!

## Technologies used

- [UMD DATA605 Big Data Systems](https://github.com/gpsaggese/umd_data605)
  contains
  [lectures](https://github.com/gpsaggese/umd_data605/tree/main/lectures) and
  [tutorials](https://github.com/gpsaggese/umd_data605/tree/main/tutorials)
  about most of the technologies we use in KaizenFlow, e.g., Dask, Docker, Docker
  Compose, Git, github, Jupyter, MongoDB, Pandas, Postgres, Apache Spark
- You can go through the lectures and tutorials on a per-need basis, depending
  on what it's useful for you to develop
- As an additional resource to become proficient in using Linux and shell, you
  can refer to
  [The Missing Semester of Your CS Education](https://missing.csail.mit.edu/)

## Clone the code

- To clone the repo, use the cloning command described in the GitHub official
  documentation

- Example of cloning command:

  ```bash
  > git clone git@github.com:kaizen-ai/kaizenflow.git ~/src/kaizenflow1
  ```
  - The previous command might not work sometimes and an alternative command
    using HTTP instead of SSH

  ```bash
  > git clone https://github.com/kaizen-ai/kaizenflow.git ~/src/kaizenflow1
  ```

- All the source code should go under `~/src` (e.g., `/Users/<YOUR_USER>/src` on
  a Mac)
- The path to the local repo folder should look like this
  `~/src/{REPO_NAME}{IDX}` where
  - `REPO_NAME` is a name of the repository
  - IDX is an integer

## Building the thin environment

- Create the "thin environment" which contains the minimum set of dependencies
  needed for running the KaizenFlow Dev Docker container

- Build the thin environment; this is done once per client

  ```bash
  > cd $GIT_ROOT
  > source dev_scripts/client_setup/build.sh
  ```

- Activate the thin environment; make sure it is always activated
  ```
  > source dev_scripts/setenv_amp.sh
  ```

- If you see output like below, your environment is successfully built!
  ```
  ...
  alias sp='echo '\''source ~/.profile'\''; source ~/.profile'
  alias vi='/usr/bin/vi'
  alias vim='/usr/bin/vi'
  alias vimdiff='/usr/bin/vi -d'
  alias vip='vim -c "source ~/.vimrc_priv"'
  alias w='which'
  ==> SUCCESS <==
  ```
- If you encounter any issues, please post them by creating a new issue on
  GitHub and assign it to the `gsaggese`
  - You should report as much information as possible: what was the command,
    what is your platform, output of the command

## Install and test Docker

### Supported OS

- KaizenFlow supports Mac (both x86 and Apple Silicon) and Linux Ubuntu
- We do not support Windows and WSL: we have tried several times to port the
  tool chain to it, but there are always subtle incompatible behaviors that
  drive everyone crazy
  - If you are using Windows, we suggest to use dual boot with Linux or use a
    virtual machine with Linux
  - Install VMWare software
  - Reference video for installing
    [ubuntu](https://www.youtube.com/watch?v=NhlhJFKmzpk&ab_channel=ProgrammingKnowledge)
    on VMWare software
  - Make sure you set up your git and github
  - Install
    [docker](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)
    on your Ubuntu VM

### Install Docker

- Get familiar with Docker if you are not, e.g.,
  https://docs.docker.com/get-started/overview/

- We work in a Docker container that has all the required dependencies installed
  - You can use PyCharm / VS code on your laptop to edit code, but you want to
    run code inside the dev container since this makes sure everyone is running
    with the same system, and it makes it easy to share code and reproduce
    problems

- Install Docker Desktop on your PC
  - Links:
    - [Mac](https://docs.docker.com/desktop/install/mac-install/)
    - [Linux](https://docs.docker.com/desktop/install/linux-install/)
    - [Windows](https://docs.docker.com/desktop/install/windows-install/)

- Follow https://docs.docker.com/engine/install/

- For Mac you can also install `docker-cli` without the GUI using

  ```bash
  > brew install docker
  > brew link docker
  > brew install colima
  ```

- After installing make sure Docker works on your laptop (of course the version
  will be newer)

  ```bash
  > docker version
  Client:
   Cloud integration: v1.0.24
   Version:           20.10.17
   API version:       1.41
   Go version:        go1.17.11
   Git commit:        100c701
   Built:             Mon Jun  6 23:04:45 2022
   OS/Arch:           darwin/amd64
   Context:           default
   Experimental:      true

  Server: Docker Desktop 4.10.1 (82475)
   Engine:
    Version:          20.10.17
    API version:      1.41 (minimum version 1.12)
    Go version:       go1.17.11
    Git commit:       a89b842
    Built:            Mon Jun  6 23:01:23 2022
    OS/Arch:          linux/amd64
    Experimental:     false
   containerd:
    Version:          1.6.6
    GitCommit:        10c12954828e7c7c9b6e0ea9b0c02b01407d3ae1
   runc:
    Version:          1.1.2
    GitCommit:        v1.1.2-0-ga916309
   docker-init:
    Version:          0.19.0
    GitCommit:        de40ad0
  ```

### Checking Docker installation

- Check the installation by running:
  ```bash
  > docker pull hello-world
  Using default tag: latest
  latest: Pulling from library/hello-world
  Digest: sha256:fc6cf906cbfa013e80938cdf0bb199fbdbb86d6e3e013783e5a766f50f5dbce0
  Status: Image is up to date for hello-world:latest
  docker.io/library/hello-world:latest
  ```

### Docker installation troubleshooting

- Common problems with Docker
  - Mac DNS problem, try step 5 from the
    [article](https://medium.com/freethreads/mac-os-docker-error-response-from-daemon-net-http-request-canceled-while-waiting-for-connection-7d1069eb4ca9)
    and repeat the cmd below:
    ```bash
    > docker pull hello-world
    Error response from daemon: net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)
    ```
  - Linux sudo problem, see
    [here](https://stackoverflow.com/questions/48568172/docker-sock-permission-denied)
    for the solution
    ```bash
    > docker pull hello-world
    Got permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock: Get   http://%2Fvar%2Frun%2Fdocker.sock/v1.40/containers/json: dial unix /var/run/docker.sock: connect: permission denied
    ```

## Tmux

- To create the standard tmux view on a cloned environment run

  ```bash
  > go_amp.sh kaizenflow 1
  ```

- You need to create the tmux environment once per Git client and then you can
  re-connect with:

  ```bash
  # Check the available environments.
  > tmux ls
  cmamp1: 4 windows (created Fri Dec  3 18:27:09 2021) (attached)

  # Attach an environment.
  > tmux attach -t cmamp1
  ```

- You can re-run `go_amp.sh` when your tmux gets corrupted and you want to
  restart. Of course this doesn't impact the underlying Git repo

## Some useful workflows

- Check the installation by running:

  ```bash
  > docker pull hello-world
  Using default tag: latest
  ```

- Pull the latest KaizenFlow image; this is done once

  ```bash
  > i docker_pull
  or
  # TODO(Sameep): Update to kaizenflow once docker is updated.
  > docker pull sorrentum/cmamp:latest
  ```

- Pull the latest `dev_tools` image containing the linter; this is done once

  ```bash
  > i docker_pull_dev_tools
  or
  # TODO(Sameep): Update to kaizenflow once docker is updated.
  > docker pull sorrentum/dev_tools:prod
  ```

- Get the latest version of `master`

  ```bash
  # To update your feature branch with the latest changes from master run
  # the cmd below from a feature branch, i.e. not from master.
  > i git_merge_master
  # If you are on `master` just pull the remote changes.
  > i git_pull
  ```

- Start a Docker container

  ```bash
  > i docker_bash
  ```

- You can ignore all the warnings that do not prevent you from running the
  tests, e.g.,

  ```bash
  WARNING: The AM_AWS_ACCESS_KEY_ID variable is not set. Defaulting to a blank string.
  WARNING: The AM_AWS_DEFAULT_REGION variable is not set. Defaulting to a blank string.
  WARNING: The AM_AWS_SECRET_ACCESS_KEY variable is not set. Defaulting to a blank string.
  WARNING: The AM_FORCE_TEST_FAIL variable is not set. Defaulting to a blank string.
  WARNING: The CK_AWS_ACCESS_KEY_ID variable is not set. Defaulting to a blank string.
  WARNING: The CK_AWS_DEFAULT_REGION variable is not set. Defaulting to a blank string.
  WARNING: The CK_AWS_SECRET_ACCESS_KEY variable is not set. Defaulting to a blank string.
  WARNING: The CK_TELEGRAM_TOKEN variable is not set. Defaulting to a blank string.
  -----------------------------------------------------------------------------
  This code is not in sync with the container:
  code_version='1.4.1' != container_version='1.4.0'
  -----------------------------------------------------------------------------
  You need to:
  - merge origin/master into your branch with `invoke git_merge_master`
  - pull the latest container with `invoke docker_pull`
  ```

- Start a Jupyter server

  ```bash
  > i docker_jupyter
  ```

- To open a Jupyter notebook in a local web-browser:
  - In the output from the cmd above find an assigned port, e.g.,
    `[I 14:52:26.824 NotebookApp] http://0044e866de8d:10091/` -> port is `10091`
  - Add the port to the link like so: `http://localhost:10091/` or
    `http://127.0.0.1:10091`
  - Copy-paste the link into a web-browser and update the page

## Coding Style

- Adopt the coding style outlined
  [here](/docs/coding/all.coding_style.how_to_guide.md)

## Linter

- The linter is in charge of reformatting the code according to our conventions
  and reporting potential problems

### Run the linter and check the linter results

- Run the linter against the changed files in the PR branch

  ```bash
  > invoke lint --files "file1 file2..."
  ```

- More information about Linter -
  [Link](/docs/infra/linter_gh_workflow.explanation.md)
- Internalize the guidelines to maintain code consistency

## Writing and Contributing Code

- If needed, always start with creating an issue first, providing a summary of
  what you want to implement and assign it to yourself and your team
- Create a branch of your assigned issues/bugs
  - E.g., for a GitHub issue with the name: "Expose the linter container to
    KaizenFlow contributors #63", The GitHub issue and the branch name should be
    called `SorrTask63_Expose_the_linter_container_to_Kaizenflow_contributors`
- Implement the code based on the requirements in the assigned issue
- Run the linter on your code before pushing
- Do `git commit` and `git push` together so the latest changes are readily
  visible
- Make sure your branch is up-to-date with the master branch
- Create a Pull Request (PR) from your branch
- Add your assigned reviewers for your PR so that they are informed of your PR
- After being reviewed, the PR will be merged to the master branch by your
  reviewers
