# Required Packages for the thin environment and GH Actions

<!-- toc -->

- [Thin environment](#thin-environment)
  * [Packages](#packages)
  * [Candidate Packages to remove](#candidate-packages-to-remove)
- [GH Actions](#gh-actions)
  * [Packages](#packages-1)
  * [Candidate Packages to remove](#candidate-packages-to-remove-1)

<!-- tocstop -->

## Thin environment

File location:

- [requirements.txt](https://github.com/cryptokaizen/cmamp/blob/master/dev_scripts/client_setup/requirements.txt)

### Packages

- `boto3`
  - Interacts with the AWS services:
  - [`boto3` import in the `haws`](https://github.com/cryptokaizen/cmamp/blob/master/helpers/haws.py#L10)
  - [`haws` usage in the `lib_tasks_docker_release.py`](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_docker_release.py#L862)

- `invoke`
  - Need for running the invoke targets:
  - [\_run_tests](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_pytest.py#L299)

- `poetry`
  - Manage dependencies in the dev image:
  - [docker_build_local_image](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_docker_release.py#L119)

- `pytest`
  - To run `Docker image QA tests`:
  - [\_run_qa_tests](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_docker_release.py#L119)

- `tqdm`
  - Widely used for showing the progress of the process for example:
  - [\_fix_invalid_owner](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_perms.py#L243)

- `s3fs`
  - Needed for some invoke targets, for example:
  - [docker_update_prod_task_definition](https://github.com/cryptokaizen/cmamp/blob/CmampTask6520_gDoc_for_required_packages_in_github_workflow_and_thin_env/helpers/lib_tasks_docker_release.py#L866)

### Candidate Packages to remove

- `docker` and `docker-compose`

  Should to be moved to os installation
  https://github.com/cryptokaizen/cmamp/issues/6498

## GH Actions

File location:

- [gh_requirements.txt](https://github.com/cryptokaizen/cmamp/blob/master/.github/gh_requirements.txt)

### Packages

- `invoke`
  - Need for running the invoke targets:
  - [\_run_tests](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_pytest.py#L299)

- `poetry`
  - Manages dependencies in the dev image:
  - [docker_build_local_image](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_docker_release.py#L119)

- `pytest`
  - To run `Docker image QA tests`:
  - [\_run_qa_tests](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_docker_release.py#L119)

- `tqdm`
  - Widely used for showing the progress of the process for example:
  - [\_fix_invalid_owner](https://github.com/cryptokaizen/cmamp/blob/master/helpers/lib_tasks_perms.py#L243)

- `s3fs`
  - Needed for some invoke targets, for example:
  - [docker_update_prod_task_definition](https://github.com/cryptokaizen/cmamp/blob/CmampTask6520_gDoc_for_required_packages_in_github_workflow_and_thin_env/helpers/lib_tasks_docker_release.py#L866)

### Candidate Packages to remove

- `docker` and `docker-compose` should to be moved to os installation
  https://github.com/cryptokaizen/cmamp/issues/6498
