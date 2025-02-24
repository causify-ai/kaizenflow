#!/bin/bash
#
# Entrypoint for an app that runs together with PostgreSQL.
#

set -e

postgres_ready() {
  pg_isready -d $POSTGRES_DB -p $POSTGRES_PORT -h $POSTGRES_HOST
}

echo "STAGE: $STAGE"
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "POSTGRES_PORT: $POSTGRES_PORT"

until postgres_ready; do
  >&2 echo 'Waiting for PostgreSQL to become available...'
  sleep 1
done
>&2 echo 'PostgreSQL is available'

umask 000

#source ~/.bash_profile

export PYTHONPATH=/app:$PYTHONPATH
echo "PYTHONPATH=$PYTHONPATH"

# Initialize the DB.
./im/devops/docker_scripts/init_im_db.py --db $POSTGRES_DB

eval "$@"
