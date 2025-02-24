#!/bin/bash -e
#
# Delete all images.
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

# Print Sorrentum images.
echo "# Docker images to delete"
docker image ls | grep $FULL_IMAGE_NAME

# Remove images.
echo "# Removing image"
docker image ls | grep $FULL_IMAGE_NAME | awk '{print $1}' | xargs -n 1 -t docker image rm -f

# Print all images.
echo "# Docker images"
docker image ls
