

<!-- toc -->

- [Sorrentum Sandbox](#sorrentum-sandbox)
- [Sorrentum system container](#sorrentum-system-container)
  * [High-level description](#high-level-description)
  * [Scripts](#scripts)
  * [Sorrentum app container](#sorrentum-app-container)
    + [Clean up](#clean-up)
    + [Pull image from Dockerhub](#pull-image-from-dockerhub)
    + [Build image locally](#build-image-locally)
  * [Bring up Sorrentum data node](#bring-up-sorrentum-data-node)
  * [Check the Airflow status](#check-the-airflow-status)
  * [Pausing Airflow service](#pausing-airflow-service)
  * [Restarting the services](#restarting-the-services)
- [Sorrentum system examples](#sorrentum-system-examples)
  * [Binance](#binance)
    + [Run system in standalone mode](#run-system-in-standalone-mode)
      - [Download data](#download-data)
      - [Run QA](#run-qa)
      - [Run unit tests](#run-unit-tests)
      - [Run ETL pipeline](#run-etl-pipeline)
    + [Run inside Airflow](#run-inside-airflow)
  * [Reddit](#reddit)
  * [Running outside Airflow](#running-outside-airflow)
    + [Download data](#download-data-1)
    + [Load, QA and Transform](#load-qa-and-transform)
  * [Running inside Airflow](#running-inside-airflow)

<!-- tocstop -->

# Sorrentum Sandbox

- This dir `sorrentum_sandbox` contains examples for Sorrentum data nodes
  - It allows to experiment with and prototype Sorrentum nodes, which are
    comprised of multiple services (e.g., Airflow, MongoDB, Postgres)
  - All the code can be run on a local machine with `Docker`, without the need
    of any cloud production infrastructure

- The current structure of the `sorrentum_sandbox` directory is as follows:

  ```markdown
  > $GIT_ROOT/dev_scripts/tree.sh -p sorrentum_sandbox
  ...
  ```

- Focusing on the directory structure:
  ```
  > $GIT_ROOT/dev_scripts/tree.sh -p $GIT_ROOT/sorrentum_sandbox -d 1 -c
  /Users/saggese/src/sorrentum2/sorrentum_sandbox/
  |-- common/
  |-- devops/
  |-- docker_common/
  |-- examples/
  |-- research/
  |-- spring2023/
  |-- spring2024/
  |-- __init__.py
  |-- tutorial.sorrentum_airflow.md
  |-- tutorial.sorrentum_dev_container.md
  `-- tutorial.sorrentum_jupyter_container.md
  ```

- `common/`: contains abstract system interfaces for the different blocks of the
  Sorrentum ETL pipeline
  - Read the code top to bottom to get familiar with the interfaces
    ```
    > vi $GIT_ROOT/sorrentum_sandbox/common/*.py
    ```
- `devops/`: contains the Dockerized Sorrentum data node
  - It contains the Airflow task scheduler and its DAGs
  - It can run any Sorrentum data nodes, like the ones in
    `$GIT_ROOT/sorrentum_sandobox/examples`
- `docker_common/`: common code for Docker tasks
- `examples/`: - contains several examples of end-to-end Sorrentum data nodes
    - E.g., downloading price data from Binance and posts/comments from Reddit
    - Each system implements the interfaces in `common`
- `research/`: Sorrentum research projects
- `spring2023/`: class projects for Spring 2023 (team projects about building
  Sorrentum systems)
- `spring2024/`: class projects for Spring 2024 DATA605 class (individual projects
  about building examples of big data technologies)

<!-- ############################################################################### -->
<!-- ############################################################################### -->
<!-- ############################################################################### -->

# Sorrentum system container

## High-level description

- This system contains several services:
  - Airflow
  - Postgres
  - MongoDB

- It is modeled after
  https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html

- Inspect the Dockerfile and the compose file to understand what's happening
  behind the scenes
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > vi docker-compose.yml Dockerfile
  ```

- The system needs several Docker images and several containers
  - `postgres`: pre-built image for PostgreSQL, downloaded directly from
    DockerHub
  - `mongo`: pre-built image for Mongo, downloaded directly from DockerHub
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

  ```bash
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > source $GIT_ROOT/sorrentum_sandbox/devops/setenv.sh
  ```

- There are several scripts that allow to use the Airflow container:
  - `docker_ls.sh`: show the Sorrentum containers
  - `docker_prune.sh`: remove the Sorrentum app image
  - `docker_prune_all.sh`: remove all the images needed for the Sorrentum node
    (e.g., mongo, postgres, ...)
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
  2.8.2
  ```

## Sorrentum app container

### Clean up

- You might have some images from previous runs, e.g.,

  ```bash
  > docker images | grep sorrentum
  sorrentum/sorrentum             latest            d298b34ae6db   43 minutes ago   4.03GB
  sorrentum/jupyter               latest            360b1d8a2f7e   3 days ago       1.38GB
  sorrentum/cmamp                 dev               e61ee1b8c77a   2 weeks ago      3.31GB
  sorrentum/sorrentum             Spring2023        0a0b62706879   10 months ago    2.42GB

  > docker images | grep mongo
  mongo                           latest            35e5c11c442d   8 days ago       721MB

  > docker images | grep postgres
  postgres                        14.0              01b2dbb34042   2 years ago      354MB

  > docker images | grep airflow
  ```

- There is also a convenient script

  ```bash
  > docker_ls.sh
  # Sorrentum
  sorrentum/sorrentum           latest            d298b34ae6db   12 hours ago    4.03GB
  sorrentum/jupyter             latest            360b1d8a2f7e   3 days ago      1.38GB
  sorrentum/cmamp               dev               e61ee1b8c77a   2 weeks ago     3.31GB
  sorrentum/sorrentum           Spring2023        0a0b62706879   10 months ago   2.42GB
  # Mongo
  mongo                         latest            35e5c11c442d   9 days ago      721MB
  # Postgres
  postgres                      14.0              01b2dbb34042   2 years ago     354MB
  # Airflow
  ```

- You can clean up your Docker system from the images
  ```
  > docker_prune_all.sh
  ```

### Pull image from Dockerhub

- The Sorrentum app container image is already pre-built and can be downloaded
  from DockerHub `sorrentum/sorrentum`
  ```
  > docker_pull.sh
  ```

- You can see the public available images on https://hub.docker.com/u/sorrentum
  or from command line
  ```
  > curl -s "https://hub.docker.com/v2/repositories/sorrentum/?page_size=100" | jq '.results|.[]|.name'
  ```

### Build image locally

- You can also build manually the Sorrentum container using Docker
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > docker_build.sh
  ```
- Building the container takes a few minutes
- There can be warnings but it's fine as long as the build process terminates
  with something along the lines of:
  ```
  Successfully built a7ca17283abb
  Successfully tagged sorrentum/sorrentum:latest

  + exit 0
  + docker image ls sorrentum/sorrentum
  REPOSITORY            TAG       IMAGE ID       CREATED         SIZE
  sorrentum/sorrentum   latest    a7ca17283abb   2 seconds ago   2.2GB
  ```

- Note that `docker-compose` automates the building phases of the entire system,
  by building, pulling images according to the compose file
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > docker-compose build
  ```

## Bring up Sorrentum data node

- The best approach is to see the Airflow logs in one window at the same time as
  running other commands in a different windows:
  - Run Airflow server in one terminal window using `docker compose up`
  - Run other tools in other windows using `docker_exec.sh`
  - You can use `tmux` to allow multiple windows in the same shell

- After the containers are ready, you can bring up the service with:
  ```
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > docker-compose up
  ```

- Starting the system can take some time

- Note that there can be some errors / warnings, but things are good as long as
  you see Airflow starting like below:
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
  `localhost:8080`
  - You should see the Airflow login with user `airflow` and password `airflow`

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

- Upon successful login you should see the Airflow UI
  ![image](https://user-images.githubusercontent.com/49269742/215845132-6ca56974-495d-4ca2-9656-32000033f341.png)
- To enable a DAG and start executing it based on provided interval, flip the
  switch next to the DAG name
  - E.g., you can enable the DAG `download_periodic_1min_postgres_ohlcv_binance`
    which downloads OHLCV data from Binance and saves it into Postgres

## Pausing Airflow service

- You can bring down the Sorrentum service (persisting the state) with:
  ```bash
  > docker compose down
  [+] Running 9/9
   ✔ Container devops-airflow-worker-1     Stopped
   ✔ Container mongo_cont                  Stopped
   ✔ Container devops-airflow-triggerer-1  Stopped
   ✔ Container devops-airflow-scheduler-1  Stopped
   ✔ Container devops-airflow-webserver-1  Stopped
   ✔ Container postgres_cont               Stopped
   ✔ Container devops-airflow-init-1       Stopped
   ✔ Container devops-postgres-1           Stopped
   ✔ Container devops-redis-1              Stopped
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
  ```bash
  > docker-compose down -v --rmi all
  [+] Running 12/12
   ✔ Container devops-airflow-webserver-1  Removed
   ✔ Container devops-airflow-triggerer-1  Removed
   ✔ Container devops-airflow-worker-1     Removed
   ✔ Container devops-airflow-scheduler-1  Removed
   ✔ Container postgres_cont               Removed
   ✔ Container mongo_cont                  Removed
   ✔ Container devops-airflow-init-1       Removed
   ✔ Container devops-postgres-1           Removed
   ✔ Container devops-redis-1              Removed
   ✔ Volume devops_postgres-db-volume      Removed
   ✔ Volume devops_airflow-database-data   Removed
   ✔ Network devops_default                Removed

  > docker container ls
  > docker volume ls
  ```

- To rebuild after trying out some changes in dockerfile/compose file
  ```bash
  > docker-compose up --build --force-recreate
  ```

<!-- ############################################################################### -->
<!-- ############################################################################### -->
<!-- ############################################################################### -->

# Sorrentum examples

- The following examples under `sorrentum_sandbox/examples` demonstrate small
  standalone Sorrentum data nodes
- Each example implements concrete classes from the interfaces specified in
  `sorrentum_sandbox/common`, upon which command line scripts are built
- Initially, we want to run the systems directly
  - The actual execution of scripts will be orchestrated by Apache Airflow
- The code relies on the Sorrentum Airflow container described in the session
  below

## Binance

### Run system in standalone mode

- In this example we utilize Binance REST API, available free of charge
- We build a small ETL pipeline used to download and transform OHLCV market data
  for selected cryptocurrencies

- The example code can be found in `sorrentum_sandbox/examples/binance`
  ```bash
  > dev_scripts/tree.sh -p $GIT_ROOT/sorrentum_sandbox/examples/binance -c
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

- Let's look at the files one by one
  ```bash
  > vi $GIT_ROOT/sorrentum_sandbox/examples/binance/*.py
  ```

- There are various files:
  - `db.py`: contains the interface to load / save Binance raw data to Postgres
    - I.e., "Load stage" of an ETL pipeline
  - `download.py`: implement the logic to download the data from Binance
    - I.e., "Extract stage"
  - `download_to_csv.py`: implement Extract stage to CSV
  - `download_to_db.py`: implement Extract stage to PostgreSQL
  - `load_and_validate.py`: implement a pipeline loading data into a CSV file
    and then validating data
  - `load_validate_transform.py`: implement a pipeline loading data into DB,
    validating data, processing data, and saving data back to DB
  - `validate.py`: implement simple QA pipeline

#### Download data

- To get to know what type of data we are working with in this example you can
  run:
  ```bash
  > docker_bash.sh
  docker> cd /cmamp/sorrentum_sandbox/examples/binance
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
  ...
  ```

- An example of an OHLCV data snapshot:

  | currency_pair | open           | high           | low            | close          | volume     | timestamp     | end_download_timestamp           |
  | ------------- | -------------- | -------------- | -------------- | -------------- | ---------- | ------------- | -------------------------------- |
  | ETH_USDT      | 1295.95000000  | 1297.34000000  | 1295.95000000  | 1297.28000000  | 1.94388000 | 1666260060000 | 2023-01-13 13:01:53.101034+00:00 |
  | BTC_USDT      | 19185.10000000 | 19197.71000000 | 19183.13000000 | 19186.63000000 | 1.62299500 | 1666260060000 | 2023-01-13 13:01:54.508880+00:00 |
  - Each row represents the state of an asset for a given minute
  - In the above example we have data points for two currency pairs `ETH_USDT`
    and `BTC_USDT` for a given minute denoted by UNIX timestamp 1666260060000
    (`2022-10-20 10:01:00+00:00`), which in Sorrentum protocol notation
    represents time interval
    `[2022-10-20 10:00:00+00:00, 2022-10-20 10:00:59.99+00:00)`
  - Within this timeframe `ETH_USDT` started trading at `1295.95`, reached the
    highest (lowest) price of `1297.34`(`1295.95`) and ended at `1297.28`.

#### Run QA

- To familiarize yourself with the concepts of data quality assurance /
  validation you can proceed with the example script `load_and_validate.py`
  which runs a trivial data QA operations (i.e. checking the dataset is not
  empty)
  ```bash
  docker> ./load_and_validate.py \
          --start_timestamp '2022-10-20 12:00:00+00:00' \
          --end_timestamp '2022-10-21 12:00:00+00:00' \
          --source_dir 'binance_data' \
          --dataset_signature 'bulk.manual.download_1min.csv.ohlcv.spot.v7.binance.binance.v1_0_0'
  INFO: Saving log to file '/cmamp/sorrentum_sandbox/examples/binance/load_and_validate.py.log'
  06:05:21 - INFO  validate.py run_all_checks:87                          Running all QA checks:
  06:05:21 - INFO  validate.py run_all_checks:90                          EmptyDatasetCheck: PASSED
  06:05:21 - INFO  validate.py run_all_checks:90                          GapsInTimestampCheck: PASSED
  ```
- This can be considered as part of the T in ETL, even if it's just read-only
  operation

#### Run ETL pipeline

### Run inside Airflow

- Bring up the services via docker-compose as described above
  ```bash
  > docker compose up
  ```
- Visit `localhost:8080/home`
- Sign in using the default credentials `airflow`:`airflow`
- There are two Airflow DAGs preloaded for this example stored in the dir
  `$GIT_ROOT/sorrentum_sandbox/devops/dags`
  ```
  > vi $GIT_ROOT/sorrentum_sandbox/devops/dags/*binance*.py
  ```
  - `download_periodic_1min_postgres_ohlcv_binance`:
    - Scheduled to run every minute
    - Download the last minute worth of OHLCV data using
      `examples/binance/download_to_db.py`
  - `validate_and_resample_periodic_1min_postgres_ohlcv_binance`
    - Scheduled to run every 5 minutes
    - Load data from a postgres table, resample it, and save back the data using
      `examples/binance/load_validate_transform.py`

- A few minutes after enabling the DAGs in Airflow, you can check the PostgreSQL
  database to preview the results of the data pipeline
- The default password is `postgres`
  ```bash
  > docker_exec.sh
  docker> psql -U postgres -p 5532 -d airflow -h host.docker.internal -c 'SELECT * FROM binance_ohlcv_spot_downloaded_1min LIMIT 5'

  docker> psql -U postgres -p 5532 -d airflow -h host.docker.internal -c 'SELECT * FROM binance_ohlcv_spot_resampled_5min LIMIT 5'
  ```

<!--  ///////////////////////////////////////////////////////////////////////////////////////////// -->

## Reddit

- In this example we use Reddit REST API, available free of charge, to build a
  small ETL pipeline to download and transform Reddit posts and comments for
  selected subreddits
- A prerequisite to use this code is to obtain
  [Reddit API](https://www.reddit.com/wiki/api/) keys (client ID and secret)
  ```bash
  > dev_scripts/tree.sh -p $GIT_ROOT/sorrentum_sandbox/examples/reddit -c
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

### Creating a Reddit API key

https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example

name: My_app
script
description: empty
about url: empty
redirect uri: http://www.example.com/unused/redirect/uri

https://www.reddit.com/prefs/apps

```
My_app
personal use script
-TW...Nw
change icon
secret	oU...67Q
name	My_app
description
about url	
redirect uri	http://www.example.com/unused/redirect/uri
user Hopeful_Leek_4710
```

### Download data

- Make sure to specify Reddit API credentials in
  `$GIT_ROOT/sorrentum_sandbox/devops/.env` in the section labeled as `Reddit`
  before running the scripts
  ```verbatim
  # Reddit.
  REDDIT_CLIENT_ID=some_client_id
  REDDIT_SECRET=some_secret
  ```
- Then enter the container with `docker_exec.sh`
  - You need to run in the existing container and not a new one created by
    `docker_bash.sh`
- Test the connection to Reddit
  ```bash
  docker> cd /cmamp/sorrentum_sandbox/examples/reddit
  docker> ./sanity_check_reddit.py
  <praw.reddit.Reddit object at 0xffffb6e71f10>
  None
  Sunday Daily Thread: What's everyone working on this week?
  Monday Daily Thread: Project ideas!
  Geospatial Big Data Visualization with Python
  Fuzzy process matching
  I Built a Squaredle Bot
  I shared a Python Exploratory Data Analysis Project on YouTube
  Introducing thread: Extending the built-in threading module
  How often do you find yourself ditching wrapper libraries?
  Github Copilot Lies to me
  Stockdex: Python Package to Extract Financial Insights From Multiple Sources
  ```

- Test the connection to Mongo
  ```bash
  > ./sanity_check_mongo.py
  Empty DataFrame
  Columns: []
  Index: []
  ```
- It is initially empty

- To explore the data structure run (assumes having mongo container up and
  running):
  ```bash
  docker> cd /cmamp/sorrentum_sandbox/examples/reddit/
  docker> ./download_to_db.py --start_timestamp '2024-03-10 10:00:00+00:00' --end_timestamp '2024-03-11 15:30:00+00:00'
  INFO: Saving log to file '/cmamp/sorrentum_sandbox/examples/reddit/download_to_db.py.log'
  07:48:50 - INFO  download.py download:82            Subreddit (Cryptocurrency) is downloading...
  07:48:51 - INFO  download.py download:94            Post: (Swapped BNB smartchain to ETHEREUM ) is downloading...
  07:48:51 - INFO  download.py download:94            Post: (Loopring (LRC) Receives a Very Bullish Rating Monday: Is it Time to Get on Board?) is downloading...
  07:48:52 - INFO  download.py download:94            Post: (Cheapest and easiest way to convert 2.4 million FLOKI coin I forgot I had?) is downloading...
  07:48:52 - INFO  download.py download:94            Post: (How long does TRC20 transfers take?) is downloading...
  07:48:52 - INFO  download.py download:94            Post: (UK regulator to allow crypto exchange-traded notes for professional investors) is downloading...
  07:48:53 - INFO  download.py download:82            Subreddit (CryptoMarkets) is downloading...
  07:48:53 - INFO  download.py download:94            Post: (Bitcoin Price Enters Uncharted Territories with New ATH above $71K. What's Next? Listen to Dr. Emmett Brown: "ROADS?! WHERE WE'RE GOING WE DON'T NEED ROADS!!!") is downloading...
  07:48:53 - INFO  download.py download:94            Post: (What do you think about trading robots?) is downloading...
  07:48:53 - INFO  download.py download:94            Post: (Why This Student-Led Investment Fund Poured 7% of its Holdings into Bitcoin) is downloading...
  07:48:54 - INFO  download.py download:94            Post: (Bitcoin (BTC) Surges to $71,000, Sets New All-Time High) is downloading...
  07:48:54 - INFO  download.py download:94            Post: (KuCoin is illegally withholding delisted tokens) is downloading...
  07:48:54 - INFO  download.py download:98            Reddit download finished.
  07:48:54 - INFO  download_to_db.py _main:35                             Connecting to Mongo
  07:48:54 - INFO  download_to_db.py _main:45                             Saving 10 records into Mongo
  ```
- Since the script is setup to download new posts, it's optimal to specify as
  recent timestamps as possible
- Connect to a MongoDB and query some documents from the `posts` collection
  ```bash
  > ./test_mongo.py
                          _id comment_limit  comment_sort  ... post_hint                                            preview                                           comments
  0  65eeefa662d92a6d84baaab5          2048  "confidence"  ...       NaN                                                NaN                                                NaN
  1  65eeefa662d92a6d84baaab6          2048  "confidence"  ...    "link"  {"images": [{"source": {"url": "https://extern...  [{'_replies': '?', '_submission': '?', '_reddi...
  2  65eeefa662d92a6d84baaab7          2048  "confidence"  ...       NaN                                                NaN  [{'_replies': '?', '_submission': '?', '_reddi...
  3  65eeefa662d92a6d84baaab8          2048  "confidence"  ...       NaN                                                NaN  [{'_replies': '?', '_submission': '?', '_reddi...
  4  65eeefa662d92a6d84baaab9          2048  "confidence"  ...    "link"  {"images": [{"source": {"url": "https://extern...  [{'_replies': '?', '_submission': '?', '_reddi...
  5  65eeefa662d92a6d84baaaba          2048  "confidence"  ...   "image"  {"images": [{"source": {"url": "https://previe...  [{'_replies': '?', '_submission': '?', '_reddi...
  6  65eeefa662d92a6d84baaabb          2048  "confidence"  ...       NaN                                                NaN  [{'_replies': '?', '_submission': '?', '_reddi...
  7  65eeefa662d92a6d84baaabc          2048  "confidence"  ...    "link"  {"images": [{"source": {"url": "https://extern...                                                NaN
  8  65eeefa662d92a6d84baaabd          2048  "confidence"  ...    "self"  {"images": [{"source": {"url": "https://extern...                                                NaN
  9  65eeefa662d92a6d84baaabe          2048  "confidence"  ...       NaN                                                NaN  [{'_replies': '?', '_submission': '?', '_reddi...

  [10 rows x 120 columns]
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

- The second step is extracting features. Run as:
  ```bash
  docker> cd /cmamp/sorrentum_sandbox/examples/reddit/
  docker> ./load_validate_transform.py \
      --start_timestamp '2022-10-20 10:00:00+00:00' \
      --end_timestamp '2022-10-21 15:30:00+00:00'
  ```
- In MongoDB it can be found in the `processed_posts` collection
- To query the DB use the same code as above, in the **download data** section,
  specifying `processed_posts` in the `dataset_signature` argument

- Example:
  ```json
  {
    "_id": { "$oid": "63bd461de978f68eae1c4e11" },
    "cross_symbols": ["USDT"],
    "reddit_post_id": "\"108455o\"",
    "symbols": ["ETH", "USDT"],
    "top_most_comment_body": "\"Pro & con info are in the collapsed comments below for the following topics: [Crypto.com(CRO)](/r/CryptoCurrency/comments/108455o/cryptocom_is_delisting_usdt_what_do_they_know/j3q51fa/), [Tether](/r/CryptoCurrency/comments/108455o/cryptocom_is_delisting_usdt_what_do_they_know/j3q52ab/).\"",
    "top_most_comment_tokens": [
      "con",
      "pro",
      "cro",
      "collapsed",
      "are",
      "tether",
      "j3q51fa",
      "r",
      "usdt",
      "is",
      "comments",
      "topics",
      "for",
      "in",
      "com",
      "cryptocom",
      "delisting",
      "they",
      "know",
      "crypto",
      "what",
      "do",
      "j3q52ab",
      "cryptocurrency",
      "info",
      "108455o",
      "below",
      "following",
      "the"
    ]
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
  `$GIT_ROOT/sorrentum_sandbox/devops/dags`
  - `download_periodic_5min_mongo_posts_reddit`:
    - Scheduled to run every 5 minutes
    - Download new posts submitted in the last 5 minutes from chosen subreddits
      (in this example `r/Cryptocurrency` and `r/CryptoMarkets`) using
      `examples/reddit/download_to_db.py`
  - `validate_and_extract_features_periodic_5min_mongo_posts_reddit`
    - Scheduled to run every 5 minutes
    - Load data from a MongoDB collection, compute feature, and save back to the
      database using `examples/reddit/load_validate_transform.py`
