#!/bin/bash -xe

SRC_DIR="/data/tutorial_brownie"
DST_DIR="/data/tutorial_brownie/hello_world_contract"

if [[ -d $DST_DIR ]]; then
    rm -rf $DST_DIR
fi;
mkdir $DST_DIR
cd $DST_DIR

brownie init

# Copy files.
cp -r $SRC_DIR/proj_files/hello_world_contract.sol $DST_DIR/contracts
cp -r $SRC_DIR/proj_files/brownie-config.yaml $DST_DIR

brownie compile

brownie test
