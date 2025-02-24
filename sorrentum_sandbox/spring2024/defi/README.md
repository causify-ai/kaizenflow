# The `defi` container

## The `defi` container
- We have packaged all the tools you need to build and test dApps with Sorrentum
  in a Docker container

- You can get familiar with Docker using the lectures and tutorials from UMD
  DATA605
  - https://github.com/gpsaggese/umd_data605/tree/main/lectures
  - https://github.com/gpsaggese/umd_data605/tree/main/tutorials

- (For advanced users): The internals of the container are
  https://github.com/sorrentum/sorrentum/tree/master/defi/devops

## Using the `defi` container

- The container is controlled with the following scripts:
  - `docker_bash.sh`: start a new `defi` container
  - `docker_exec.sh`: start a new bash in the `defi` container
  - `docker_build.sh`: build the container (for admins)
  - `docker_kill.sh`: kill all the `defi` containers

## Build the `defi` container

- (For advanced users)
- This is typically performed by administrators and you can use the pre-built
  container
- To build the container storing all the DeFi toolchain:
  ```
  > cd $GIT_ROOT/defi/devops
  > docker_build.sh
  ```

## Run the `defi` container

- Typically, you want to have one `defi` container with multiple terminals
  attached to it to run servers (e.g., Ganache) and clients (e.g., Jupyter, bash)
- We suggest to use `tmux` to keep all the terminals in a single window
  and make it easy to control via keyboard
- Note that you have to run docker commands exactly from the `/defi` subdir
  ```
  > cd $GIT_ROOT/defi
  > devops/docker_bash.sh

  # Go to a new terminal.
  # Start a new bash on the same container.
  > devops/docker_exec.sh

  ...

  # Go to a new terminal.
  # Start a new bash on the same container.
  > devops/docker_exec.sh
  ```

## Install dependencies

- To complete the set-up you need to install node libraries to each project
- Open a new window and start a new bash in the running container
  ```
  > devops/docker_exec.sh
  docker> cd data/
  docker> devops/install_node_modules.sh
  ```

## Start Ganache

- Open a new window and start a new bash in the running container
  ```
  > devops/docker_exec.sh
  docker> /data/devops/run_ganache.sh
  ```

- The output of Ganache is in `/root/ganache.log`

## Start Jupyter

- Open a new window and start a new bash in the running container
  ```
  > devops/docker_exec.sh
  docker> /data/devops/run_jupyter.sh
  ```
- Go to the link where the Jupyter notebook is running
  - On your laptop: localhost:8888
  - On `dev1`: http://172.30.2.136:8889/tree
  - On `dev2`: http://172.30.2.128:8889/tree
    
## Solidity Linter

- Use the script `lint_solidity.sh` inside `dev_scripts` directory for formatting
  and linting the smart contracts
  
  ```
  > dev_scripts/lint_solidity.sh file.sol file2.sol ...
  ```
