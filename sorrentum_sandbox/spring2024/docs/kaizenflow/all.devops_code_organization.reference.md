

<!-- toc -->

- [Code organization](#code-organization)

<!-- tocstop -->

- See changelog in `version.txt`

# Code organization

- The organization of a `devops` dir is like in the following
  - `compose`
    - Docker compose files
  - `docker_build`
    - Everything related to building a Docker image
  - `docker_run`
    - Everything related to running a Docker image
  - `env`
    - Docker env files

- An example is below
  ```
  > tree devops

  devops
  ├── README.md
  ├── compose
  │   ├── docker-compose.yml
  │   └── docker-compose_as_submodule.yml
  ├── debug
  │   └── repo_compare.sh
  ├── docker_build
  │   ├── create_users.sh
  │   ├── dev.Dockerfile
  │   ├── etc_sudoers
  │   ├── fstab
  │   ├── install_dind.sh
  │   ├── install_jupyter_extensions.sh
  │   ├── install_os_packages.sh
  │   ├── install_python_packages.sh
  │   ├── old
  │   │   └── conda.yml
  │   ├── poetry.lock
  │   ├── poetry.toml
  │   └── pyproject.toml
  ├── docker_run
  │   ├── aws_credentials.sh
  │   ├── bashrc
  │   ├── entrypoint.sh
  │   ├── run_jupyter_server.sh
  │   ├── setenv.sh
  │   └── test_setup.sh
  └── env
      └── default.env
  ```

- The layout for versions 1.x.x was
  ```
  > tree devops.OLD
  devops.OLD/
  ├── compose
  │   ├── docker-compose.yml
  │   └── docker-compose_as_submodule.yml
  ├── debug
  │   └── repo_compare.sh
  ├── docker_build
  │   ├── README.md
  │   ├── dev.Dockerfile
  │   ├── entrypoint
  │   │   ├── aws_credentials.sh
  │   │   └── patch_environment_variables.sh
  │   ├── entrypoint.sh
  │   ├── fstab
  │   ├── install_jupyter_extensions.sh
  │   ├── install_packages.sh
  │   ├── install_requirements.sh
  │   ├── old
  │   │   └── conda.yml
  │   ├── poetry.lock
  │   ├── poetry.toml
  │   ├── pyproject.toml
  │   └── test
  │       ├── test_mount_fsx.sh
  │       ├── test_mount_s3.sh
  │       └── test_volumes.sh
  ├── docker_scripts
  │   └── run_jupyter_server.sh
  └── env
      └── default.env
  ```
