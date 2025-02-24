#!/bin/bash -xe
ROOT_SRC_DIR=/Users/saggese/src/cmamp2
ROOT_DST_DIR=/Users/saggese/src/sorrentum

# Clean up.
find sorrentum_sandbox -name "*.ipynb" | xargs nb-clean clean
find research_amp/altdata -name "*.ipynb" | xargs nb-clean clean

for DIR in sorrentum_sandbox research_amp/altdata
do
    echo "DIR=$DIR"
    SRC_DIR=$ROOT_SRC_DIR/$DIR/
    DST_DIR=$ROOT_DST_DIR/$DIR/
    echo "SRC_DIR=$SRC_DIR -> DST_DIR=$DST_DIR"
    if [[ 1 == 1 ]]; then
        #(cd $SRC_DIR; invoke git_clean)
        rm -rf $DST_DIR
        rsync -arhv $SRC_DIR $DST_DIR
        (cd $ROOT_DST_DIR; git add $DIR)
    fi;
done;
