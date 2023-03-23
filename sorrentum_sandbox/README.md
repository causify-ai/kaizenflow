-   [Sorrentum Sandbox](#sorrentum-sandbox){#toc-sorrentum-sandbox}
-   [Running the Sorrentum Jupyter
    container](#running-the-sorrentum-jupyter-container){#toc-running-the-sorrentum-jupyter-container}
    -   [Running Jupyter](#running-jupyter){#toc-running-jupyter}
    -   [Running bash](#running-bash){#toc-running-bash}
-   [Sorrentum system
    container](#sorrentum-system-container){#toc-sorrentum-system-container}
    -   [High-level
        description](#high-level-description){#toc-high-level-description}
    -   [Scripts](#scripts){#toc-scripts}
    -   [Sorrentum app
        container](#sorrentum-app-container){#toc-sorrentum-app-container}
    -   [Bring up Sorrentum data
        node](#bring-up-sorrentum-data-node){#toc-bring-up-sorrentum-data-node}
    -   [Check the Airflow
        status](#check-the-airflow-status){#toc-check-the-airflow-status}
    -   [Pausing Airflow
        service](#pausing-airflow-service){#toc-pausing-airflow-service}
    -   [Restarting the
        services](#restarting-the-services){#toc-restarting-the-services}
    -   [Tutorial Airflow](#tutorial-airflow){#toc-tutorial-airflow}
-   [Sorrentum system
    examples](#sorrentum-system-examples){#toc-sorrentum-system-examples}
    -   [Binance](#binance){#toc-binance}
        -   [Run system in standalone
            mode](#run-system-in-standalone-mode){#toc-run-system-in-standalone-mode}
        -   [Run inside
            Airflow](#run-inside-airflow){#toc-run-inside-airflow}
    -   [Reddit](#reddit){#toc-reddit}
    -   [Running outside
        Airflow](#running-outside-airflow){#toc-running-outside-airflow}
        -   [Download data](#download-data-1){#toc-download-data-1}
        -   [Load, QA and
            Transform](#load-qa-and-transform){#toc-load-qa-and-transform}
    -   [Running inside
        Airflow](#running-inside-airflow){#toc-running-inside-airflow}

# Sorrentum Sandbox

- This dir `sorrentum_sandbox` contains examples for Sorrentum data nodes
  - The code can be run on a local machine with `Docker`, without the need of
    any cloud production infrastructure
  - It allows to experiment with and prototype Sorrentum nodes

- The current structure of the `sorrentum_sandbox` directory is as follows:
  ```
  > cd $GIT_ROOT/sorrentum_sandbox && $GIT_ROOT/dev_scripts/tree.sh

  ./
  |-- common/
  |   |-- __init__.py
  |   |-- client.py
  |   |-- download.py
  |   |-- save.py
  |   `-- validate.py
  |-- devops/
  |   |-- airflow_data/
  |   |   |-- dags/
  |   |   |   |-- __init__.py
  |   |   |   |-- airflow_tutorial.py
  |   |   |   |-- download_periodic_1min_postgres_ohlcv_binance.py
  |   |   |   |-- download_periodic_5min_mongo_posts_reddit.py
  |   |   |   |-- validate_and_extract_features_periodic_5min_mongo_posts_reddit.py
  |   |   |   `-- validate_and_resample_periodic_1min_postgres_ohlcv_binance.py
  |   |   `-- __init__.py
  |   |-- Dockerfile
  |   |-- __init__.py
  |   |-- docker-compose.yml
  |   |-- docker_bash.sh*
  |   |-- docker_build.sh*
  |   |-- docker_clean.sh*
  |   |-- docker_clean_all.sh*
  |   |-- docker_cmd.sh*
  |   |-- docker_exec.sh*
  |   |-- docker_pull.sh*
  |   |-- docker_push.sh*
  |   |-- init_airflow_setup.sh*
  |   |-- reset_airflow_setup.sh*
  |   `-- setenv.sh
  |-- docker_common/
  |   |-- bashrc
  |   |-- create_links.sh*
  |   |-- etc_sudoers
  |   |-- install_jupyter_extensions.sh*
  |   |-- update.sh*
  |   |-- utils.sh
  |   `-- version.sh*
  |-- examples/
  |   |-- altdata_notebooks/
  |   |   |-- Blockchain.com.ipynb
  |   |   |-- Blockchain.com.py
  |   |   |-- Chainlink.ipynb
  |   |   |-- Chainlink.py
  |   |   |-- CoinGecko.ipynb
  |   |   |-- CoinGecko.py
  |   |   |-- CoinMarketCap.ipynb
  |   |   |-- CoinMarketCap.py
  |   |   |-- Glassnode.ipynb
  |   |   |-- Glassnode.py
  |   |   |-- Kibot.ipynb
  |   |   |-- Kibot.py
  |   |   |-- YahooFinance.ipynb
  |   |   |-- YahooFinance.py
  |   |   |-- __init__.py
  |   |   |-- bitquery_uniswap.ipynb
  |   |   |-- bitquery_uniswap.py
  |   |   |-- github.com.ipynb
  |   |   |-- github.com.py
  |   |   |-- google_trends.ipynb
  |   |   |-- google_trends.py
  |   |   |-- kaiko.com.ipynb
  |   |   |-- kaiko.com.py
  |   |   |-- twitter.com.ipynb
  |   |   `-- twitter.com.py
  |   |-- ml_projects/
  |   |   |-- SorrIssue14_Team1_Implement_sandbox_for_Google_Trends/
  |   |   |-- SorrIssue1_Predict_large_asset_movements_with_NLP/
  |   |   |-- SorrIssue2_Cross_exchange_arbitrage_CEX_CEX/
  |   |   |-- SorrIssue3_Implement_Avellaneda_model/
  |   |   |-- SorrIssue4_Predict_bid_ask_movements_with_order_book_data/
  |   |   `-- SorrIssue8_Predict_Intraday_Trading_Volume/
  |   |       `-- intraday_volume_task1.ipynb
  |   |-- systems/
  |   |   |-- binance/
  |   |   |   |-- test/
  |   |   |   |   `-- test_download_to_csv.py
  |   |   |   |-- __init__.py
  |   |   |   |-- db.py
  |   |   |   |-- download.py
  |   |   |   |-- download_to_csv.py*
  |   |   |   |-- download_to_db.py*
  |   |   |   |-- load_and_validate.py*
  |   |   |   |-- load_validate_transform.py*
  |   |   |   `-- validate.py
  |   |   |-- reddit/
  |   |   |   |-- __init__.py
  |   |   |   |-- db.py
  |   |   |   |-- download.py
  |   |   |   |-- download_to_db.py*
  |   |   |   |-- load_validate_transform.py*
  |   |   |   |-- transform.py
  |   |   |   `-- validate.py
  |   |   `-- __init__.py
  |   |-- Dockerfile
  |   |-- README.md
  |   |-- bashrc
  |   |-- docker_bash.sh*
  |   |-- docker_build.sh*
  |   |-- docker_build.version.log
  |   |-- docker_clean.sh*
  |   |-- docker_exec.sh*
  |   |-- docker_jupyter.sh*
  |   |-- docker_push.sh*
  |   |-- etc_sudoers
  |   |-- install_jupyter_extensions.sh*
  |   |-- run_jupyter.sh*
  |   |-- set_env.sh
  |   |-- tutorial_jupyter.ipynb
  |   `-- version.sh*
  |-- projects/
  |   |-- SorrIssue1_Predict_large_asset_movements_with_NLP/
  |   |   `-- task_1_compute_returns.ipynb
  |   `-- SorrIssue2_Cross_exchange_arbitrage_CEX_CEX/
  |       |-- Making Single Dataframe.ipynb
  |       |-- Merging_Dfs.ipynb
  |       `-- Single_Dataframe.ipynb
  |-- README.md
  `-- __init__.py

  21 directories, 98 files
  ```

- Focusing on the directory structure:
  ```
  > tree . -d --charset unicode
  .
  |-- common
  |-- devops
  |   `-- airflow_data
  |       `-- dags
  |-- docker_common
  |-- examples
  |   |-- altdata_notebooks
  |   |-- ml_projects
  |   |   |-- SorrIssue14_Team1_Implement_sandbox_for_Google_Trends
  |   |   |-- SorrIssue1_Predict_large_asset_movements_with_NLP
  |   |   |-- SorrIssue2_Cross_exchange_arbitrage_CEX_CEX
  |   |   |-- SorrIssue3_Implement_Avellaneda_model
  |   |   |-- SorrIssue4_Predict_bid_ask_movements_with_order_book_data
  |   |   `-- SorrIssue8_Predict_Intraday_Trading_Volume
  |   `-- systems
  |       |-- binance
  |       |   `-- test
  |       `-- reddit

  21 directories
  ```

- `common/`: contains abstract system interfaces for the different blocks of the 
   ETL pipeline
  - Read the code top to bottom to get familiar with the interfaces
    ```
    > vi $GIT_ROOT/sorrentum_sandbox/common/*.py
    ```

- `docker_common/`: common code for Docker tasks

- `devops/`: contains the Dockerized Sorrentum data node
  - it contains the Airflow task scheduler and its DAGs
  - it can run any Sorrentum data nodes, like the ones in `examples/systems`

- `examples/`:
  - `altdata_notebooks`: contains notebooks showing the API of multiple
    datasources
  - `ml_projects`: contains machine learning projects
  - `systems`: contains several examples of end-to-end Sorrentum data nodes
    - E.g., downloading price data from Binance and posts/comments from Reddit
    - Each system implements the interfaces in `common`

# Running the Sorrentum Jupyter container

- We use Python and Jupyter for all the research projects

- IPython Notebook / Jupyter is an enhanced command shell for Python, that offers
  enhanced introspection, rich media, tab completion, and history
- IPython Notebook started as a web browser-based interface to IPython and
  proved especially popular with data scientists
- A few years ago, the Notebook functionality was forked off as a separate project,
  called [Jupyter](http://jupyter.org/). Jupyter provides support for many other
  languages in addition to Python

## Running Jupyter

- We have built a `sorrentum_jupyter` container that allows to run Jupyter with
  all the needed dependencies

- To start Jupyter do:
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/examples
  > docker_jupyter.sh
  ++ git rev-parse --show-toplevel
  + GIT_ROOT=/Users/saggese/src/sorrentum1
  + REPO_NAME=sorrentum
  + IMAGE_NAME=jupyter
  + FULL_IMAGE_NAME=sorrentum/jupyter
  + docker image ls sorrentum/jupyter
  REPOSITORY   TAG       IMAGE ID   CREATED   SIZE
  + CONTAINER_NAME=jupyter
  + docker run --rm -ti --name jupyter -p 8888:8888 -v /Users/saggese/src/sorrentum1/sorrentum_sandbox:/data sorrentum/jupyter /data/devops/jupyter_docker/run_jupyter.sh
  Unable to find image 'sorrentum/jupyter:latest' locally
  latest: Pulling from sorrentum/jupyter
  677076032cca: Already exists
  4c9de205ab0e: Pull complete
  ...
  7d1edc5584d3: Pull complete
  ac0e0cb28d27: Pull complete
  Digest: sha256:3be2a9bcbae4919d532d891d76ddb57cd8a13d0a8dd518cbdd5e7ed6ab3fa30a
  Status: Downloaded newer image for sorrentum/jupyter:latest
  + jupyter-notebook --port=8888 --no-browser --ip=0.0.0.0 --allow-root --NotebookApp.token= --NotebookApp.password=
  [I 16:29:44.061 NotebookApp] Writing notebook server cookie secret to /root/.local/share/jupyter/runtime/notebook_cookie_secret
  [I 16:29:44.061 NotebookApp] Authentication of /metrics is OFF, since other authentication is disabled.
  [W 16:29:44.273 NotebookApp] All authentication is disabled.  Anyone who can connect to this server will be able to run code.
  [I 16:29:44.276 NotebookApp] [jupyter_nbextensions_configurator] enabled 0.6.1
  [I 16:29:44.284 NotebookApp] Serving notebooks from local directory: /
  [I 16:29:44.284 NotebookApp] Jupyter Notebook 6.5.2 is running at:
  [I 16:29:44.284 NotebookApp] http://917f7e30d7c6:8888/
  [I 16:29:44.284 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
  ```

- This will start a Jupyter server in the container listening on port 8888
    - As discussed above, the Docker start command maps the 8888 port on the
      container to the 8888 port on the host
    - You can access it from the host, by pointing your browser to
      `localhost:8888` or `http://127.0.0.1:8888`

- Navigate to `/data` to see the directories mounted on Docker

- Now you can execute notebooks

## Running bash

- You can run bash in the Sorrentum Jupyter container with:
  ```
  > docker_bash.sh
  ```

<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->
<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->
<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->

# Sorrentum system container

## High-level description

- The Docker container contains several services:
  - Airflow
  - Postgres
  - MongoDB

- Inspect the Dockerfile and the compose file to understand what's happening
  behind the scenes
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > vi docker-compose.yml Dockerfile .env
  ```

- The system needs three Docker images:
  - `postgres`: prebuilt image for PostgreSQL, downloaded directly from
    DockerHub
  - `mongo`: prebuilt image for Mongo, downloaded directly from DockerHub
  - `sorrentum/sorrentum`: the image can be either built locally or downloaded
    from DockerHub
    - It is used to run Airflow and the Sorrentum application
    - The container containing the application is `airflow_cont`

  <!--
  // Generated with:
  // cd ~/src/sorrentum1/sorrentum_sandbox/devops
  // docker run --rm -it --name dcv -v $(pwd):/input pmsipilot/docker-compose-viz render -m image docker-compose.yml --no-volumes --force
  -->
  ![image](https://user-images.githubusercontent.com/33238329/223691802-0f0ec9ce-9854-48a7-9a30-1a8d452f77ce.png)
  
## Scripts

- Remember that commands prepended with:
  - `>` are run outside the Sorrentum app container in a terminal of your local
    computer
  - `docker>` are run inside the Sorrentum app container after running
    `docker_bash.sh` or `docker_exec.sh`

- To configure the environment run:
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > source $GIT_ROOT/sorrentum_sandbox/devops/setenv.sh
  ```

- There are several scripts that allow to connect to Airflow container:
  - `docker_prune.sh`: remove all the Sorrentum images
  - `docker_prune_all.sh`: remove all the images needed for the Sorrentum node
  - `docker_pull.sh`: pull image of the Sorrentum app container
  - `docker_bash.sh`: start a Sorrentum app container
  - `docker_exec.sh`: start another shell in an already running Sorrentum app
    container
  - `docker_cmd.sh`: execute one command inside the Sorrentum app container
  - `docker_build.sh`: build the image of the Sorrentum app container
  - `docker_push.sh`: push to DockerHub the image of the Sorrentum app container

- E.g., you can check the Airflow version with:
  ```
  > docker_bash.sh
  docker> airflow version
  2.2.2
  ```

## Sorrentum app container

- The Sorrentum app container image is already pre-built and should be
  automatically downloaded from DockerHub `sorrentum/sorrentum`
 
- You can also build manually the Sorrentum container using Docker
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > docker_build.sh
  ```
- Building the container takes a few minutes
- There can be warnings but as long as the build process terminates with:
  ```
  Successfully built a7ca17283abb
  Successfully tagged sorrentum/sorrentum:latest

  + exit 0
  + docker image ls sorrentum/sorrentum
  REPOSITORY            TAG       IMAGE ID       CREATED         SIZE
  sorrentum/sorrentum   latest    a7ca17283abb   2 seconds ago   2.2GB
  ```
  it's fine

- Note that Docker-compose automates also the building phases of the entire
  system
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > docker-compose build
  ```
  
## Bring up Sorrentum data node

- The best approach is to see the Airflow logs at the same time as running other
  commands:
  - Run Airflow server in one terminal window
  - Run other tools in other windows (e.g., using tmux) using `docker_exec.sh`,

- After the containers are ready, you can bring up the service with:
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > docker-compose up
  ```

- Starting the system can take some time

- Note that there can be some errors / warnings, but things are good as long 
  as you see Airflow starting like below:
  ```
  airflow_scheduler_cont  |   ____________       _____________
  airflow_scheduler_cont  |  ____    |__( )_________  __/__  /________      __
  airflow_scheduler_cont  | ____  /| |_  /__  ___/_  /_ __  /_  __ \_ | /| / /
  airflow_scheduler_cont  | ___  ___ |  / _  /   _  __/ _  / / /_/ /_ |/ |/ /
  airflow_scheduler_cont  |  _/_/  |_/_/  /_/    /_/    /_/  \____/____/|__/
  airflow_scheduler_cont  | [2022-11-10 17:09:29,521] {scheduler_job.py:596} INFO - Starting the scheduler
  airflow_scheduler_cont  | [2022-11-10 17:09:29,522] {scheduler_job.py:601} INFO - Processing each file at most -1 times
  airflow_scheduler_cont  | [2022-11-10 17:09:29,531] {manager.py:163} INFO - Launched DagFileProcessorManager with pid: 20
  airflow_scheduler_cont  | [2022-11-10 17:09:29,533] {scheduler_job.py:1114} INFO - Resetting orphaned tasks for active dag runs
  airflow_scheduler_cont  | [2022-11-10 17:09:29 +0000] [19] [INFO] Starting gunicorn 20.1.0
  airflow_scheduler_cont  | [2022-11-10 17:09:29,539] {settings.py:52} INFO - Configured default timezone Timezone('UTC')
  airflow_scheduler_cont  | [2022-11-10 17:09:29 +0000] [19] [INFO] Listening at: http://0.0.0.0:8793 (19)
  airflow_scheduler_cont  | [2022-11-10 17:09:29 +0000] [19] [INFO] Using worker: sync
  airflow_scheduler_cont  | [2022-11-10 17:09:29 +0000] [21] [INFO] Booting worker with pid: 21
  airflow_scheduler_cont  | [2022-11-10 17:09:29 +0000] [22] [INFO] Booting worker with pid: 22
  ```

- The Airflow service provided in the container uses `LocalExecutor` which is 
  suitable for test / dev environments
  - For more robust deployments it is possible to add more components to the
    docker-compose (e.g., `Celery` and `Redis`)

## Check the Airflow status

- Check that the Airflow service is up by going with your browser to
  `localhost:8091`
  - You should see the Airflow login
  - You can't log in since you don't have username / password yet

- You can see the services running as Docker containers:
  ```
  > docker images | perl -n -e 'print if /sorrentum|postgres|mongo/;'
  sorrentum/sorrentum:latest    latest    223859f6c70e   5 hours ago     2.19GB
  mongo                         latest    0850fead9327   4 weeks ago     700MB
  postgres                      14.0      317a302c7480   14 months ago   374MB

  > docker container ls
  CONTAINER ID   IMAGE                      COMMAND                  CREATED   STATUS                  PORTS                     NAMES
  454e70e42b9f   sorrentum/sorrentum:latest "/usr/bin/dumb-init …"   12 seconds ago   Up Less than a second   8080/tcp                  airflow_scheduler_cont
  5ac4c7f6d883   sorrentum/sorrentum:latest "/usr/bin/dumb-init …"   12 seconds ago   Up 10 seconds           0.0.0.0:8091->8080/tcp    airflow_cont
  37e86b58c247   postgres:14.0              "docker-entrypoint.s…"   13 seconds ago   Up 11 seconds           0.0.0.0:5532->5432/tcp    postgres_cont
  c33f70195dd3   mongo                      "docker-entrypoint.s…"   13 seconds ago   Up 12 seconds           0.0.0.0:27017->27017/tcp  mongo_cont

  > docker volume ls
  DRIVER    VOLUME NAME
  local     5bd623d00c7c07d2364d876883669f3032182da89ad858aac57a0219528f4272
  local     sorrentum_data_node_airflow-database-data
  local     sorrentum_data_node_airflow-log-volume
  ```

- When starting the Airflow container for the first time you need to initialize
  Airflow
- Take a look at the script that configures Airflow
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > vi ./init_airflow_setup.sh
  ```
- In a different terminal window outside the Docker container, run:
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > ./init_airflow_setup.sh
  ...
  [2023-01-22 01:07:31,578] {manager.py:214} INFO - Added user airflow
  User "airflow" created with role "Admin"
  ```

- Now if you go to the browser to `localhost:8091` on your local machine you can
  log in with the default login credentials `airflow`:`airflow`
- Upon successful login you should see the Airflow UI
  ![image](https://user-images.githubusercontent.com/49269742/215845132-6ca56974-495d-4ca2-9656-32000033f341.png)
- To enable a DAG and start executing it based on provided interval, flip the
  switch next to the DAG name
  - E.g., you can enable the DAG `download_periodic_1min_postgres_ohlcv_binance` which
    downloads OHLCV data from Binance and saves it into Postgres

## Pausing Airflow service

- You can bring down the Sorrentum service (persisting the state) with:
  ```
  > docker compose down
  Container mongo_cont                 Removed
  Container airflow_cont               Removed
  Container airflow_scheduler_cont     Removed
  Container postgres_cont              Removed
  Network sorrentum_data_node_default  Removed
  ```
- You can see in the Airflow window that the service has stopped

- You can verify the state of Docker containers directly with:
  ```
  > docker container ls
  > docker volume ls
  ```
- Note that the containers are only paused

- Restarting the service keeps the volume which contains the state of Postgres:
  ```
  docker compose restart

  > docker container ls
  > docker volume ls
  ```
- The containers are restarted

## Restarting the services

- To remove all the containers and volumes, which corresponds to resetting 
  completely the system
  ```
  > docker-compose down -v --rmi all
  Removing airflow_scheduler_cont ... done
  Removing airflow_cont           ... done
  Removing postgres_cont          ... done
  Removing network airflow_default
  Removing volume airflow_ck-airflow-database-data
  Removing volume airflow_ck-airflow-log-volume
  Removing image postgres:14.0
  Removing image resdev-airflow:latest

  > docker container ls
  > docker volume ls
  ```
- Since you are starting from scratch here you need to re-run
  `./init_airflow_setup.sh`

- To rebuild after trying out some changes in dockerfile/compose file
  ```
  > docker-compose up --build --force-recreate
  ```

# Tutorial Airflow

- From [official tutorial](https://airflow.apache.org/docs/apache-airflow/2.2.2/tutorial.html)

- The code of the tutorial is at
  ```
  > vi $GIT_ROOT/sorrentum_sandbox/devops/airflow_data/dags/airflow_tutorial.py
  ```

- Start the Sorrentum container with Airflow inside
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > docker-compose up
  ```

- In Airflow web-server navigate to http://localhost:8091/tree?dag_id=tutorial

## Interacting with Airflow

- Lots of the Airflow commands can be executed through the CLI or the web
  interface

- Make sure that the pipeline is parsed successfully
  ```
  > docker_exec.sh
  docker> python /opt/airflow/dags/airflow_tutorial.py
  ```

- Print the list of active DAGs
  ```
  docker> airflow dags list
  dag_id                                                        | filepath                                                         | owner   | paused
  ==============================================================+==================================================================+=========+=======
  download_periodic_5min_mongo_posts_reddit                     | download_periodic_5min_mongo_posts_reddit.py                     | airflow | True
  download_periodic_1min_postgres_ohlcv_binance                 | download_periodic_1min_postgres_ohlcv_binance.py                 | airflow | True
  tutorial                                                      | airflow_tutorial.py                                              | airflow | False
  validate_and_extract_features_periodic_5min_mongo_posts_reddit | validate_and_extract_features_periodic_5min_mongo_posts_reddit.py | airflow | True
  validate_and_resample_periodic_1min_postgres_ohlcv_binance    | validate_and_resample_periodic_1min_postgres_ohlcv_binance.py    | airflow | True

- Print the list of tasks in the "tutorial" DAG
  ```
  docker> airflow tasks list tutorial
  print_date
  sleep
  templated
  ```

- Print the hierarchy of tasks in the "tutorial" DAG.
  ```
  docker> airflow tasks list tutorial --tree
  <Task(BashOperator): print_date>
    <Task(BashOperator): sleep>
    <Task(BashOperator): templated>
  ```

- Testing `print_date` task by executing with a logical / execution date in the past:
  ```
  docker> airflow tasks test tutorial print_date 2015-06-01
  [2023-01-23 10:15:34,862] {dagbag.py:500} INFO - Filling up the DagBag from /opt/airflow/dags
  [2023-01-23 10:15:34,949] {taskinstance.py:1035} INFO - Dependencies all met for <TaskInstance: tutorial.print_date None [None]>
  [2023-01-23 10:15:34,961] {taskinstance.py:1241} INFO -
  --------------------------------------------------------------------------------
  [2023-01-23 10:15:34,961] {taskinstance.py:1242} INFO - Starting attempt 1 of 2
  [2023-01-23 10:15:34,962] {taskinstance.py:1243} INFO -
  --------------------------------------------------------------------------------
  [2023-01-23 10:15:34,965] {taskinstance.py:1262} INFO - Executing <Task(BashOperator): print_date> on 2015-06-01T00:00:00+00:00
  ...
  [2023-01-23 10:15:35,061] {subprocess.py:74} INFO - Running command: ['bash', '-c', 'date']
  [2023-01-23 10:15:35,071] {subprocess.py:85} INFO - Output:
  [2023-01-23 10:15:35,076] {subprocess.py:89} INFO - Mon Jan 23 10:15:35 UTC 2023
  [2023-01-23 10:15:35,076] {subprocess.py:93} INFO - Command exited with return code 0
  [2023-01-23 10:15:35,092] {taskinstance.py:1280} INFO - Marking task as SUCCESS. dag_id=tutorial, task_id=print_date, execution_date=20150601T000000, start_date=20230123T101534, end_date=20230123T101535
  ```

- Testing `sleep` task
  ```
  docker> airflow tasks test tutorial sleep 2015-06-01
  [2023-01-23 10:16:01,653] {dagbag.py:500} INFO - Filling up the DagBag from /opt/airflow/dags
  [2023-01-23 10:16:01,731] {taskinstance.py:1035} INFO - Dependencies all met for <TaskInstance: tutorial.sleep None [None]>
  [2023-01-23 10:16:01,739] {taskinstance.py:1241} INFO -
  --------------------------------------------------------------------------------
  [2023-01-23 10:16:01,739] {taskinstance.py:1242} INFO - Starting attempt 1 of 4
  [2023-01-23 10:16:01,739] {taskinstance.py:1243} INFO -
  --------------------------------------------------------------------------------
  [2023-01-23 10:16:01,741] {taskinstance.py:1262} INFO - Executing <Task(BashOperator): sleep> on 2015-06-01T00:00:00+00:00
  ...
  [2023-01-23 10:16:01,817] {subprocess.py:74} INFO - Running command: ['bash', '-c', 'sleep 5']
  [2023-01-23 10:16:01,825] {subprocess.py:85} INFO - Output:
  [2023-01-23 10:16:06,833] {subprocess.py:93} INFO - Command exited with return code 0
  [2023-01-23 10:16:06,860] {taskinstance.py:1280} INFO - Marking task as SUCCESS. dag_id=tutorial, task_id=sleep, execution_date=20150601T000000, start_date=20230123T101601, end_date=20230123T101606
  ```

- Let's run a backfill for a week:
  ```
  docker> airflow dags backfill tutorial \
    --start-date 2015-06-01 \
    --end-date 2015-06-07

  [2023-01-23 10:22:52,258] {base_executor.py:82} INFO - Adding to queue: ['airflow', 'tasks', 'run', 'tutorial', 'print_date', 'backfill__2015-06-01T00:00:00+00:00', '--ignore-depends-on-past', '--local', '--pool', 'default_pool', '--subdir', 'DAGS_FOLDER/airflow_tutorial.py', '--cfg-path', '/tmp/tmpw702ubqo']
  [2023-01-23 10:22:52,302] {base_executor.py:82} INFO - Adding to queue: ['airflow', 'tasks', 'run', 'tutorial', 'print_date', 'backfill__2015-06-02T00:00:00+00:00', '--local', '--pool', 'default_pool', '--subdir', 'DAGS_FOLDER/airflow_tutorial.py', '--cfg-path', '/tmp/tmpff926sgr']
  [2023-01-23 10:22:52,358] {base_executor.py:82} INFO - Adding to queue: ['airflow', 'tasks', 'run', 'tutorial', 'print_date', 'backfill__2015-06-03T00:00:00+00:00', '--local', '--pool', 'default_pool', '--subdir', 'DAGS_FOLDER/airflow_tutorial.py', '--cfg-path', '/tmp/tmp9otpet70']
  [2023-01-23 10:22:52,408] {base_executor.py:82} INFO - Adding to queue: ['airflow', 'tasks', 'run', 'tutorial', 'print_date', 'backfill__2015-06-04T00:00:00+00:00', '--local', '--pool', 'default_pool', '--subdir', 'DAGS_FOLDER/airflow_tutorial.py', '--cfg-path', '/tmp/tmptq82tgu9']
  ```

- Backfilling will respect dependencies, emit logs, update DB to record status

- On the web-server you can see that all the DAG executions completed
  successfully
  ![image](https://user-images.githubusercontent.com/89211724/214028156-8bc0acac-7559-46aa-9ce5-2825957aa190.png)

<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->
<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->
<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->

# Sorrentum system examples

- The following examples under `sorrentum_sandbox/examples/systems` demonstrate
  small standalone Sorrentum data nodes
- Each example implements concrete classes from the interfaces specified in
  `sorrentum_sandbox/common`, upon which command line scripts are built
- Initially, we want to run the systems directly
  - The actual execution of scripts can be orchestrated by Apache Airflow
- The code relies on the Sorretum Airflow container described in the session
  below

## Binance

- In this example we utilize Binance REST API, available free of charge
- We build a small ETL pipeline used to download and transform OHLCV market data
  for selected cryptocurrencies

  ```
  > (cd $GIT_ROOT/sorrentum_sandbox/examples/systems/binance && $GIT_ROOT/dev_scripts/tree.sh)
  ./
  |-- test/
  |   `-- test_download_to_csv.py
  |-- __init__.py
  |-- db.py
  |-- download.py
  |-- download_to_csv.py*
  |-- download_to_db.py*
  |-- load_and_validate.py*
  |-- load_validate_transform.py*
  `-- validate.py
  ```

### Run system in standalone mode

- The example code can be found in `sorrentum_sandbox/examples/systems/binance`

- There are various files:
  - `db.py`: contains the interface to load / save Binance raw data to Postgres
    - i.e., "Load stage" of an ETL pipeline
  - `download.py`: implement the logic to download the data from Binance
    - i.e., "Extract stage"
  - `download_to_csv.py`: implement Extract stage to CSV
  - `download_to_db.py`: implement Extract stage to PostgreSQL
  - `load_and_validate.py`: implement a pipeline loading data into a
    CSV file and then validating data
  - `load_validate_transform.py`: implement a pipeline loading data
    into DB, validating data, processing data, and saving data back to DB
  - `validate.py`: implement simple QA pipeline

#### Download data

- To get to know what type of data we are working with in this example you can run:
  ```
  > docker_bash.sh
  docker> cd /cmamp/sorrentum_sandbox/examples/systems/binance
  docker> ./download_to_csv.py --start_timestamp '2022-10-20 10:00:00+00:00' --end_timestamp '2022-10-21 15:30:00+00:00' --target_dir 'binance_data'
  INFO: > cmd='/cmamp/sorrentum_sandbox/examples/binance/download_to_csv.py --start_timestamp 2022-10-20 10:00:00+00:00 --end_timestamp 2022-10-21 15:30:00+00:00 --target_dir binance_data' report_memory_usage=False report_cpu_usage=False
  INFO: Saving log to file '/cmamp/sorrentum_sandbox/examples/binance/download_to_csv.py.log'
  06:45:25 - INFO  download.py download:120                               Downloaded data:
             currency_pair           open           high            low          close      volume      timestamp           end_download_timestamp
  0      ETH_USDT  1295.95000000  1297.34000000  1295.95000000  1297.28000000  1.94388000  1666260060000 2023-01-23 11:45:22.729119+00:00
  1      ETH_USDT  1297.28000000  1297.28000000  1297.28000000  1297.28000000  0.00000000  1666260120000 2023-01-23 11:45:22.729188+00:00
  2      ETH_USDT  1297.28000000  1297.28000000  1297.28000000  1297.28000000  0.00000000  1666260180000 2023-01-23 11:45:22.729201+00:00
  3      ETH_USDT  1297.28000000  1297.28000000  1297.28000000  1297.28000000  0.00000000  1666260240000 2023-01-23 11:45:22.729246+00:00
  4      ETH_USDT  1297.28000000  1297.28000000  1297.28000000  1297.28000000  0.00000000  1666260300000 2023-01-23 11:45:22.729261+00:00
  ```

- The script downloads around 1 day worth of OHLCV bars (aka candlestick) into a
  CSV file
  ```
  docker> ls binance_data/
  bulk.manual.download_1min.csv.ohlcv.spot.v7.binance.binance.v1_0_0.csv

  docker> more binance_data/bulk.manual.download_1min.csv.ohlcv.spot.v7.binance.binance.v1_0_0.csv
  currency_pair,open,high,low,close,volume,timestamp,end_download_timestamp
  ETH_USDT,1295.95000000,1297.34000000,1295.95000000,1297.28000000,1.94388000,1666260060000,2023-01-23 11:45:22.729119+00:00
  ETH_USDT,1297.28000000,1297.28000000,1297.28000000,1297.28000000,0.00000000,1666260120000,2023-01-23 11:45:22.729188+00:00
  ETH_USDT,1297.28000000,1297.28000000,1297.28000000,1297.28000000,0.00000000,1666260180000,2023-01-23 11:45:22.729201+00:00
  ```

- An example of an OHLCV data snapshot:

  |currency_pair|open          |high          |low           |close         |volume    |timestamp    |end_download_timestamp          |
  |-------------|--------------|--------------|--------------|--------------|----------|-------------|--------------------------------|
  |ETH_USDT     |1295.95000000 |1297.34000000 |1295.95000000 |1297.28000000 |1.94388000|1666260060000|2023-01-13 13:01:53.101034+00:00|
  |BTC_USDT     |19185.10000000|19197.71000000|19183.13000000|19186.63000000|1.62299500|1666260060000|2023-01-13 13:01:54.508880+00:00|

  - Each row represents the state of an asset for a given minute
  - In the above example we have data points for two currency pairs `ETH_USDT`
    and `BTC_USDT` for a given minute denoted by UNIX timestamp 1666260060000
    (`2022-10-20 10:01:00+00:00`), which in Sorrentum protocol notation represents
    time interval `[2022-10-20 10:00:00+00:00, 2022-10-20 10:00:59.99+00:00)`
  - Within this timeframe `ETH_USDT` started trading at `1295.95`, reached the
    highest (lowest) price of `1297.34`(`1295.95`) and ended at `1297.28`.  

#### Run QA
 
- To familiarize yourself with the concepts of data quality assurance /
  validation you can proceed with the example script
  `load_and_validate.py` which runs a trivial data QA operations (i.e.
  checking the dataset is not empty)
  ```
  docker> ./load_and_validate.py \
          --start_timestamp '2022-10-20 12:00:00+00:00' \
          --end_timestamp '2022-10-21 12:00:00+00:00' \
          --source_dir 'binance_data' \
          --dataset_signature 'bulk.manual.download_1min.csv.ohlcv.spot.v7.binance.binance.v1_0_0'
  INFO: Saving log to file '/cmamp/sorrentum_sandbox/examples/systems/binance/load_and_validate.py.log'
  06:05:21 - INFO  validate.py run_all_checks:87                          Running all QA checks:
  06:05:21 - INFO  validate.py run_all_checks:90                          EmptyDatasetCheck: PASSED
  06:05:21 - INFO  validate.py run_all_checks:90                          GapsInTimestampCheck: PASSED
  ```

#### Run unit tests

#### Run ETL pipeline

### Run inside Airflow

- Bring up the services via docker-compose as described above
- Visit `localhost:8091/home`
- Sign in using the default credentials `airflow`:`airflow`
- There are two Airflow DAGs preloaded for this example stored in the dir
  `$GIT_ROOT/sorrentum_sandbox/devops/airflow_data/dags`
  ```
  > vi $GIT_ROOT/sorrentum_sandbox/devops/airflow_data/dags/*binance*.py
  ```

   - `download_periodic_1min_postgres_ohlcv_binance`:
     - scheduled to run every minute
     - download the last minute worth of OHLCV data using
       `examples/binance/download_to_db.py`
   - `validate_and_resample_periodic_1min_postgres_ohlcv_binance`
     - scheduled to run every 5 minutes
     - load data from a postgres table, resample it, and save back the data
       using `examples/binance/load_validate_transform.py`
- A few minutes after enabling the DAGs in Airflow, you can check the PostgreSQL
  database to preview the results of the data pipeline
  - The default password is `postgres`
  ```
  > docker_exec.sh
  docker> psql -U postgres -p 5532 -d airflow -h host.docker.internal -c 'SELECT * FROM binance_ohlcv_spot_downloaded_1min LIMIT 5'

  docker> psql -U postgres -p 5532 -d airflow -h host.docker.internal -c 'SELECT * FROM binance_ohlcv_spot_resampled_5min LIMIT 5'
  ```

<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->
<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->
<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->

## Reddit

- In this example we use Reddit REST API, available free of charge, to build a
  small ETL pipeline to download and transform Reddit posts and comments for
  selected subreddits
- A prerequisite to use this code is to obtain [Reddit
  API](https://www.reddit.com/wiki/api/) keys (client ID and secret)

  ```
  > examples/reddit
  |-- __init__.py
  |-- db.py
  |-- download.py
  |-- download_to_db.py*
  |-- load_validate_transform.py*
  |-- transform.py
  `-- validate.py

  1 directory, 12 files
  ```

## Running outside Airflow

- The example code can be found in `sorrentum_sandbox/examples/reddit`
- There are various files:
  - `db.py`: contains the interface to load / save Reddit posts data to MongoDB
    (Load/Extract stage)
  - `download.py`: implement the logic to download raw data from Reddit (Extract
    stage)
  - `download_to_db.py`: implement extract stage to MongoDB
  - `load_validate_transform.py`: implement a pipeline loading data into DB,
    validating data, processing raw data (computing features), and saving
    transformed data back to DB
  - `validate.py`: implement simple QA pipeline
  - `transform.py`: implement simple feature computation utilities from raw data 

### Download data

- Make sure to specify Reddit API credentials in
  `$GIT_ROOT/sorrentum_sandbox/devops/.env` in the section labeled as `Reddit`
  before running the scripts
  ```
  # Reddit.
  REDDIT_CLIENT_ID=some_client_id
  REDDIT_SECRET=some_secret
  ```
- To explore the data structure run (assumes having mongo container up and running):
  ```bash
  > cd /cmamp/sorrentum_sandbox/examples/reddit/
  docker> ./download_to_db.py \
      --start_timestamp '2022-10-20 10:00:00+00:00' \
      --end_timestamp '2022-10-21 15:30:00+00:00'
  ```
- Since the script is setup to download new posts, it's optimal to specify as
  recent timestamps as possible
- Connect to a MongoDB and query some documents from the `posts` collection
  ```bash
  docker> python
  >>> import sorrentum_sandbox.examples.reddit.db as ssexredb
  >>> import pymongo; import pandas as pd
  >>> mongodb_client = pymongo.MongoClient(
  ...     host=ssexredb.MONGO_HOST, port=27017, username="mongo", password="mongo"
  ... )
  >>> reddit_mongo_client = ssexredb.MongoClient(mongodb_client, "reddit")
  >>> data = reddit_mongo_client.load(
  ...     dataset_signature="posts",
  ... )
  >>> data
  >>> <<output truncated for readability, example below>>
  ```
- An example database entry (truncated for readability) is below:
  ```json
    {
      "_id": {"$oid": "63bd466b85a76c62bb578e49"},
      ...
      "created": {"$date": "2023-01-10T11:01:29.000Z"},
      "created_utc": "1673348489.0",
      "discussion_type": "null",
      "distinguished": "null",
      "domain": "\"crypto.news\"",
      "downs": "0",
      "edited": "false",
      "permalink": "\"/r/CryptoCurrency/comments/108741k/us_prosecutors_urge_victims_of_ftx_collapse_to/\"",
      "send_replies": "false",
      "title": "\"US prosecutors urge victims of FTX collapse to speak out.\"",
      "ups": "1",
      "upvote_ratio": "1.0",
      "url": "\"https://crypto.news/us-prosecutors-urge-victims-of-ftx-collapse-to-speak-out/\"",
      "url_overridden_by_dest": "\"https://crypto.news/us-prosecutors-urge-victims-of-ftx-collapse-to-speak-out/\"",
      "user_reports": "[]",
      ...
    }
  ```

### Load, QA and Transform

- The Second step is extracting features. Run as: 
  ```
  > cd /cmamp/sorrentum_sandbox/examples/reddit/
  docker> ./load_validate_transform.py \
      --start_timestamp '2022-10-20 10:00:00+00:00' \
      --end_timestamp '2022-10-21 15:30:00+00:00'
  ```
- In MongoDB it can be found in the `processed_posts` collection
- To query the DB use the same code as above, in the **download data** section, specifying `processed_posts` in the `dataset_signature` argument

- Example:
  ```json
  {
    "_id": {"$oid": "63bd461de978f68eae1c4e11"},
    "cross_symbols": ["USDT"],
    "reddit_post_id": "\"108455o\"",
    "symbols": ["ETH", "USDT"],
    "top_most_comment_body": "\"Pro & con info are in the collapsed comments below for the following topics: [Crypto.com(CRO)](/r/CryptoCurrency/comments/108455o/cryptocom_is_delisting_usdt_what_do_they_know/j3q51fa/), [Tether](/r/CryptoCurrency/comments/108455o/cryptocom_is_delisting_usdt_what_do_they_know/j3q52ab/).\"",
    "top_most_comment_tokens": ["con", "pro", "cro", "collapsed", "are", "tether", "j3q51fa", "r", "usdt", "is", "comments", "topics", "for", "in", "com", "cryptocom", "delisting", "they", "know", "crypto", "what", "do", "j3q52ab", "cryptocurrency", "info", "108455o", "below", "following", "the"]
  }
  ```

## Running inside Airflow

- Bring up the services via docker-compose as described above
- Make sure to specify Reddit API credentials in
  `$GIT_ROOT/sorrentum_sandbox/devops/.env` in the section labeled as `Reddit`
  before running the setup
  ```
  # Reddit.
  REDDIT_CLIENT_ID=some_client_id
  REDDIT_SECRET=some_secret
  ```
- Visit `localhost:8091/home`
- Sign in using the default credentials airflow:airflow
- There are two Airflow DAGs preloaded for this example stored in the dir
  `$GIT_ROOT/sorrentum_sandbox/devops/airflow_data/dags`
  - `download_periodic_5min_mongo_posts_reddit`:
    - scheduled to run every 5 minutes
    - download new posts submitted in the last 5 minutes from chosen subreddits
      (in this example `r/Cryptocurrency` and `r/CryptoMarkets`) using
      `examples/reddit/download_to_db.py`
  - `validate_and_extract_features_periodic_5min_mongo_posts_reddit`
    - scheduled to run every 5 minutes
    - load data from a MongoDB collection, compute feature, and save back to the
      database using `examples/reddit/load_validate_transform.py`
