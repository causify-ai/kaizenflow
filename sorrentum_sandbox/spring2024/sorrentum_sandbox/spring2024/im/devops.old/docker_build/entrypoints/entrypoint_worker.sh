#!/bin/bash

# TODO(gp): Move to im/airflow/devops/docker_build
# TODO(gp): -> entrypoint_airflow_worker.sh

set -e

echo "STAGE: $STAGE"
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "POSTGRES_PORT: $POSTGRES_PORT"

env
cd /app
pwd

# Workaround to make work AWS CLI work.
# The rest of this workaround is in
# im/devops/docker_build/im_db_loader_worker.dev.Dockerfile
if sudo test -d "/root/.aws" ; then
  echo "Copy AWS credentials."
  sudo cp -r /root/.aws /home/airflow/
  sudo chown -R airflow:airflow /home/airflow/.aws
else
  echo "Skip copy AWS credentials."
fi

postgres_ready() {
  pg_isready -d $POSTGRES_DB -p $POSTGRES_PORT -h $POSTGRES_HOST
}

until postgres_ready; do
  >&2 echo 'Waiting for PostgreSQL to become available...'
  sleep 1
done
>&2 echo 'PostgreSQL is available'

umask 000

# TODO(gp): Why is this needed at all?
# source ~/.bash_profile

export PYTHONPATH=/app:$PYTHONPATH
echo "PYTHONPATH=$PYTHONPATH"

# Initialize the DB.
# TODO(gp): Use the same initialization scheme as in EDGAR.
./im/devops/docker_scripts/init_im_db.py --db $POSTGRES_DB

eval "$@"
