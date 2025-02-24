#!/bin/bash -xe
docker run -it --rm \
  --volume "$PWD:/home/bfg/workspace" \
  bfg \
  --delete-files id_rsa
