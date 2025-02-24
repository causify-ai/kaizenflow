#!/usr/bin/env bash

set -e

FILE_NAME="optimizer/devops/docker_run/entrypoint.sh"
echo "##> $FILE_NAME"

echo "UID="$(id -u)
echo "GID="$(id -g)

echo "# Activate environment"
source /${ENV_NAME}/bin/activate

source devops/docker_run/setenv.sh

# Allow working with files outside a container.
#umask 000

# Enable dind unless the user specifies otherwise (needed for prod image).
if [ -z "$AM_ENABLE_DIND" ]; then
    AM_ENABLE_DIND=0
    echo "AM_ENABLE_DIND=$AM_ENABLE_DIND"
fi;

if [[ $AM_ENABLE_DIND == 1 ]]; then
    echo "Setting up Docker-in-docker"
    if [[ ! -d /etc/docker ]]; then
        sudo mkdir /etc/docker
    fi;
    # This is needed to run the database in dind mode (see CmTask309).
    # TODO(gp): For some reason appending to file directly `>>` doesn't work.
    sudo echo '{ "storage-driver": "vfs" }' | sudo tee -a /etc/docker/daemon.json

    # Start Docker Engine.
    sudo /etc/init.d/docker start
    sudo /etc/init.d/docker status
fi;

# Mount other file systems.
# mount -a || true
# sudo change perms to /mnt/tmpfs

# Check set-up.
./devops/docker_run/test_setup.sh

# AWS.
echo "# Check AWS authentication setup"
if [[ $AM_AWS_ACCESS_KEY_ID == "" ]]; then
    unset AM_AWS_ACCESS_KEY_ID
else
    echo "AM_AWS_ACCESS_KEY_ID='$AM_AWS_ACCESS_KEY_ID'"
fi;

if [[ $AM_AWS_SECRET_ACCESS_KEY == "" ]]; then
    unset AM_AWS_SECRET_ACCESS_KEY
else
    echo "AM_AWS_SECRET_ACCESS_KEY='***'"
fi;

if [[ $AM_AWS_DEFAULT_REGION == "" ]]; then
    unset AM_AWS_DEFAULT_REGION
else
    echo "AM_AWS_DEFAULT_REGION='$AM_AWS_DEFAULT_REGION'"
fi;
aws configure --profile am list || true

echo "OPT_CONTAINER_VERSION='$OPT_CONTAINER_VERSION'"

# Test the installed packages.
if [[ $AM_ENABLE_DIND == 1 ]]; then
    echo "docker -v: "$(docker -v)
    echo "docker-compose -v: "$(docker-compose -v)
fi;
VAL=$(which python)
echo "which python: $VAL"
VAL=$(python -V)
echo "python -V: $VAL"
VAL=$(python -c "import pandas; print(pandas.__version__)")
echo "pandas: $VAL"
VAL=$(python -c "import cvxopt; print(cvxopt.__version__)")
echo "cvxopt: $VAL"
VAL=$(python -c "import cvxpy; print(cvxpy.__version__)")
echo "cvxpy: $VAL"
VAL=$(python -c "import helpers; print(helpers)")
echo "helpers: $VAL"

echo "PATH=$PATH"
echo "PYTHONPATH=$PYTHONPATH"
echo "entrypoint.sh: '$@'"

# TODO(gp): eval seems to be more general, but it creates a new executable.
eval "$@"
