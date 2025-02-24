#!/bin/bash -xe

OPTS="--wallet.deterministic"

#cmd="(ganache -h 0.0.0.0 $OPTS 2>&1 >~/ganache.log) &"
cmd="(ganache -h 0.0.0.0 $OPTS 2>&1 | tee ~/ganache.log)"

eval $cmd

#(ganache -h 0.0.0.0 2>&1 >~/ganache.log) &
