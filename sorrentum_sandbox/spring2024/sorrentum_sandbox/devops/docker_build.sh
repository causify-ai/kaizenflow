#!/bin/bash -e

# Set parameters by default.
export DOCKER_BUILDKIT=1
#export DOCKER_BUILDKIT=0
#export DOCKER_BUILD_MULTI_ARCH=1
export DOCKER_BUILD_MULTI_ARCH=0

# Function to display help message
show_help() {
cat << EOF
Usage: ${0##*/} [OPTIONS]

This script accepts optional binary options to control its behavior.

Options:
  --use_multi_arch_build  Enable multi-architecture build.
  --no_buildkit           Disable the use of BuildKit.
  -h, --help              Display this help and exit.

EOF
}

# Parse command line options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --use_multi_arch_build) DOCKER_BUILD_MULTI_ARCH=1 ;;
        --no_buildkit) DOCKER_BUILDKIT=0 ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown option: $1" >&2; show_help; exit 1 ;;
    esac
    shift
done

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

build_container_image
