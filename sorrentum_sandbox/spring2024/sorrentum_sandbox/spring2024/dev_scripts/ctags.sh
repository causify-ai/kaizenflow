#!/usr/bin/env bash
#
# Dockerized ctags
#
# 
# sudo apt install universal-ctags
# rm tags
# ctags --languages=Python --exclude=.git --exclude=.mypy_cache -R .

set -eux

cat >/tmp/tmp.dockerfile <<EOF
FROM ubuntu:20.04

RUN apt-get update && \
    apt-get -y upgrade

# Install package (but it's from 2018).
#RUN apt install -y universal-ctags

# Build from source.
RUN export DEBIAN_FRONTEND=noninteractive; \
    apt-get install -y build-essential && \
    apt-get install -y automake && \
    apt-get install -y pkg-config && \
    apt-get install -y git

RUN export GIT_SSL_NO_VERIFY=1 && \
    git clone http://github.com/universal-ctags/ctags.git

RUN cd ctags && \
    ./autogen.sh && \
    ./configure --prefix=/usr/local && \
    make && \
    make install
RUN ctags --version
EOF

docker build -f /tmp/tmp.dockerfile -t ctags .

# Only allocate tty if one is detected. See - https://stackoverflow.com/questions/911168
#if [[ -t 0 ]]; then IT+=(-i); fi
#if [[ -t 1 ]]; then IT+=(-t); fi

USER="$(id -u $(logname)):$(id -g $(logname))"
WORKDIR="$(realpath .)"
MOUNT="type=bind,source=${WORKDIR},target=${WORKDIR}"

TAGS_FILE="tags"

cat >./run_tags.sh <<EOF
rm $TAGS_FILE
ctags --version || true
ctags --languages=python --exclude=.git --exclude=.mypy_cache -R .
echo "Created tags in '$TAGS_FILE'"
EOF
chmod +x ./run_tags.sh

CMD="bash -c './run_tags.sh'"

#OPTS="--user "${USER}"
OPTS=""
docker run --rm -it $OPTS --workdir "${WORKDIR}" --mount "${MOUNT}" ctags:latest $CMD "$@"

# To debug:
# > docker run --rm -it --user 2908:2908 --workdir /local/home/gsaggese/src/sasm-lime6/amp --mount type=bind,source=/local/home/gsaggese/src/sasm-lime6/amp,target=/local/home/gsaggese/src/sasm-lime6/amp ctags:latest
