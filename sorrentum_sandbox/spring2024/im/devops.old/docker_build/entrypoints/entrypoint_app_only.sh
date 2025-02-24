#!/bin/bash
#
# Entrypoint for an app without PostgreSQL DB. This is useful to run `docker_bash`.
#

set -e

echo "STAGE: $STAGE"
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "POSTGRES_PORT: $POSTGRES_PORT"
echo "PostgreSQL will not be started"

umask 000

#source ~/.bash_profile

eval "$@"
