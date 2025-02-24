#!/bin/bash -xe

# Diff everything.
if [[ 1 == 1 ]]; then
    dev_scripts/diff_to_vimdiff.py --dir1 $AMP_DIR --dir2 $CMAMP_DIR
    exit 0
fi;

#SUBDIR=helpers
#SUBDIR=im
#SUBDIR=im_v2
#SUBDIR=oms
#SUBDIR=market_data
SUBDIR=dataflow
#SUBDIR=optimizer
#SUBDIR=research/cc
#SUBDIR=research_amp
# Diff dir.
if [[ 0 == 1 ]]; then
    dev_scripts/diff_to_vimdiff.py --dir1 $AMP_DIR/$SUBDIR --dir2 $CMAMP_DIR/$SUBDIR
    exit 0
fi;

#RSYNC_OPTS="--delete -au"
RSYNC_OPTS="--delete -a"

if [[ 1 == 1 ]]; then
    if [[ 0 == 1 ]]; then
        # Sync dir cmamp -> amp.
        rsync $RSYNC_OPTS $CMAMP_DIR/$SUBDIR/ $AMP_DIR/$SUBDIR
    else
        # Sync dir amp -> cmamp.
        rsync $RSYNC_OPTS $AMP_DIR/$SUBDIR/ $CMAMP_DIR/$SUBDIR
    fi;
fi;


if [[ 1 == 1 ]]; then
    diff -r --brief $AMP_DIR/$SUBDIR $CMAMP_DIR/$SUBDIR
fi;
