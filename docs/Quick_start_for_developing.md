# Getting a first issue to work on (aka warm-up issue)

- The goal is to get comfortable with the development system

- Mark certain bugs as “good-as-first-bug”
- Write unit tests
- Copy-paste-modify
- Simple refactoring

# How to contribute code (short version)

- The proper way to contribute to the Sorrentum project is as follows:
  - Create a branch of your assigned issues/bugs
    - E.g., for a GitHub issue with the name "Expose the linter container to
      Sorrentum contributors #63", the branch name should be
      `SorrTask63_Expose_the_linter_container_to_Sorrentum_contributors`
    - This step is automated through the invoke flow
  - Push the code to your branch
  - Make sure you are following our coding practices (see above)
  - Make sure your branch is up-to-date with the master branch
  - Create a Pull Request (PR) from your branch
  - Add your assigned reviewers for your PR so that they are informed of your PR
  - After being reviewed, it will be merged to the master branch by your
    reviewers

# Sorrentum Docker container

- We work in a Docker container that has all the required dependencies installed

  - You can use PyCharm / VS code on your laptop to edit code, but you want to
    run code inside the container since this makes sure everyone is running with
    the same system and it makes it easy to share code and reproduce problems

  0. Build the thin environment

  ```
  > source dev_scripts/client_setup/build.sh
  ```

  1. Activate the thin environment

  ```
  > source dev_scripts/setenv_amp.sh
  ```

  2. Pull the latest cmamp image

  ```
  > i docker_pull
  or
  > docker pull sorrentum/cmamp:latest
  ```

  3. Merge the latest version of master into your branch

  ```
  > i git_merge_master
  ```

  To start a Docker container:

  ```
  > i docker_bash
  ```

  To start a Jupyter server:

  ```
  > i docker_jupyter
  ```

