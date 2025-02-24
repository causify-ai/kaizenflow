

<!-- toc -->

- [Tutorial Airflow](#tutorial-airflow)
  * [Interacting with Airflow](#interacting-with-airflow)

<!-- tocstop -->

# Tutorial Airflow

- From
  [official tutorial](https://airflow.apache.org/docs/apache-airflow/2.2.2/tutorial.html)

- The code of the tutorial is at
  ```bash
  > vi $GIT_ROOT/sorrentum_sandbox/devops/airflow_data/dags/airflow_tutorial.py
  ```

- Start the Sorrentum container with Airflow inside
  ```bash
  > cd $GIT_ROOT/sorrentum_sandbox/devops
  > docker-compose up
  ```

- In Airflow web-server navigate to http://localhost:8091/tree?dag_id=tutorial

## Interacting with Airflow

- Lots of the Airflow commands can be executed through the CLI or the web
  interface

- Make sure that the pipeline is parsed successfully
  ```bash
  > docker_exec.sh
  docker> python /opt/airflow/dags/airflow_tutorial.py
  ```

- Print the list of active DAGs
  ```bash
  docker> airflow dags list
  dag_id                                                        | filepath                                                         | owner   | paused
  ==============================================================+==================================================================+=========+=======
  download_periodic_5min_mongo_posts_reddit                     | download_periodic_5min_mongo_posts_reddit.py                     | airflow | True
  download_periodic_1min_postgres_ohlcv_binance                 | download_periodic_1min_postgres_ohlcv_binance.py                 | airflow | True
  tutorial                                                      | airflow_tutorial.py                                              | airflow | False
  validate_and_extract_features_periodic_5min_mongo_posts_reddit | validate_and_extract_features_periodic_5min_mongo_posts_reddit.py | airflow | True
  validate_and_resample_periodic_1min_postgres_ohlcv_binance    | validate_and_resample_periodic_1min_postgres_ohlcv_binance.py    | airflow | True
  ```

- Print the list of tasks in the "tutorial" DAG
  ```
  docker> airflow tasks list tutorial
  print_date
  sleep
  templated
  ```

- Print the hierarchy of tasks in the "tutorial" DAG.
  ```bash
  docker> airflow tasks list tutorial --tree
  <Task(BashOperator): print_date>
    <Task(BashOperator): sleep>
    <Task(BashOperator): templated>
  ```

- Testing `print_date` task by executing with a logical / execution date in the
  past:
  ```bash
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
  ```bash
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
  ```bash
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
