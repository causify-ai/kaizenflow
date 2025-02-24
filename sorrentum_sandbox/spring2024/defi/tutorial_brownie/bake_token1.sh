#!/bin/bash -xe

SRC_DIR="/data/tutorial_brownie"
DST_DIR="/data/tutorial_brownie/bake_token1"

if [[ -d $DST_DIR ]]; then
    rm -rf $DST_DIR
fi;

brownie bake token $DST_DIR

cp -r $SRC_DIR/proj_files/brownie-config.yaml $DST_DIR
cp $SRC_DIR/proj_files/goerli.json ~/.brownie/accounts/goerli.json

cd $DST_DIR
brownie compile

brownie test
