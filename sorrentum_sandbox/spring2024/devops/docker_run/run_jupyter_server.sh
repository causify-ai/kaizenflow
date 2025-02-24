#!/usr/bin/env bash

set -e

FILE_NAME="devops/docker_run/run_jupyter_server.sh"
echo "##> $FILE_NAME"

cmd="jupyter notebook --ip=* --port=${PORT} --allow-root --NotebookApp.token=''"
echo "> cmd=$cmd"
eval $cmd
