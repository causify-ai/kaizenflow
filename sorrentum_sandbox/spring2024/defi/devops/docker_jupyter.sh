#!/bin/bash -e
#
# Execute run_jupyter.sh in the container.
# 
# Usage:
# > docker_jupyter.sh -d /Users/saggese/src/git_gp1/code/book.2018.Martin.Bayesian_Analysis_with_Python.2e -v -u -p 8889
#

# Parse params.
export JUPYTER_HOST_PORT=8888
export JUPYTER_USE_VIM=0
export TARGET_DIR=""
export VERBOSE=0

OLD_CMD_OPTS=$@
while getopts p:d:uv flag
do
    case "${flag}" in
        p) JUPYTER_HOST_PORT=${OPTARG};;
        u) JUPYTER_USE_VIM=1;;
        d) TARGET_DIR=${OPTARG};;
        # /Users/saggese/src/git_gp1/code/
        v) VERBOSE=1;;
    esac
done

if [[ $VERBOSE == 1 ]]; then
    set -x
fi;

#
GIT_ROOT=$(git rev-parse --show-toplevel)
source $GIT_ROOT/docker_common/utils.sh

# Find the name of the container.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
DOCKER_NAME="$SCRIPT_DIR/docker_name.sh"
if [[ ! -e $SCRIPT_DIR ]]; then
    echo "Can't find $DOCKER_NAME"
    exit -1
fi;
source $DOCKER_NAME

# Run the script.
DOCKER_RUN_OPTS="-p $JUPYTER_HOST_PORT:$JUPYTER_HOST_PORT"
if [[ $TARGET_DIR != "" ]]; then
    DOCKER_RUN_OPTS="$DOCKER_RUN_OPTS -v $TARGET_DIR:/data"
fi;
CMD="/curr_dir/run_jupyter.sh $OLD_CMD_OPTS"

# From docker_cmd.sh passing DOCKER_OPTS.
docker image ls $FULL_IMAGE_NAME
docker manifest inspect $FULL_IMAGE_NAME | grep arch

CONTAINER_NAME=$IMAGE_NAME
docker run \
    --rm -ti \
    --name $CONTAINER_NAME \
    $DOCKER_RUN_OPTS \
    -v $(pwd):/curr_dir \
    $FULL_IMAGE_NAME \
    $CMD
