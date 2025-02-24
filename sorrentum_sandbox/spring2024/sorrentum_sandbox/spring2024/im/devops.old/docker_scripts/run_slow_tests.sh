#!/usr/bin/env bash

set -e

OPTS="-vv -rpa --log-cli-level=INFO"

# TODO(gp): Fix this pytest markers.
SKIPPED_TESTS="slow and \
    not superslow and \
    not broken_deps and \
    not need_data_dir and \
    not not_docker"

TEST_DIR="im"

# Run tests.
cmd="pytest ${OPTS} -m '${SKIPPED_TESTS}' ${TEST_DIR}"
echo "> cmd=$cmd"
eval $cmd
