#!/usr/bin/env bash
#
# Dockerized linter for Latex using prettier.
# This is the new flow.
#

set -eux
if [[ -z $1 ]]; then
    echo "Need to specify latex file to compile"
    exit -1
fi;
FILE_NAME=$1

# 1) Build container.
IMAGE=lint_latex
# See devops/docker_build/install_publishing_tools.sh
cat >/tmp/tmp.dockerfile <<EOF
FROM ubuntu:latest

RUN apt-get update && \
    apt-get -y upgrade

RUN apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js.
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get update && apt-get install -y nodejs
RUN node -v
RUN npm -v

# Install Prettier.
RUN npm install -g prettier && \
    npm install -g prettier-plugin-latex
EOF
docker build -f /tmp/tmp.dockerfile -t $IMAGE .

# 2) Create script to run.
EXEC="./tmp.lint_latex.sh"
# Note that we need to escape some chars.
cat >$EXEC <<EOF
npx prettier \
    --plugin=/usr/lib/node_modules/prettier-plugin-latex/dist/prettier-plugin-latex.js \
    --prose-wrap always \
    --tab-width 2 \
    --use-tabs false \
    --print-width 80 \
    --write \
    $@
EOF
chmod +x $EXEC

# 3) Run inside Docker.
CMD="sh -c '$EXEC'"
WORKDIR="$(realpath .)"
MOUNT="type=bind,source=${WORKDIR},target=${WORKDIR}"
USER="$(id -u $(logname)):$(id -g $(logname))"
#OPTS="--user "${USER}"
OPTS=""
docker run --rm -it $OPTS --workdir "${WORKDIR}" --mount "${MOUNT}" $IMAGE:latest $CMD "$@"

# To debug:
#docker run --rm -it $OPTS --workdir "${WORKDIR}" --mount "${MOUNT}" $IMAGE:latest bash
# > docker run --rm -it \
#   --user 2908 --workdir /local/home/gsaggese/src/sasm-lime6/amp --mount type=bind,source=/local/home/gsaggese/src/sasm-lime6/amp,target=/local/home/gsaggese/src/sasm-lime6/amp ctags:latest
