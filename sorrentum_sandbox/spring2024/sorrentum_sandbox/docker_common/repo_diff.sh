#!/bin/bash -xe

ROOT_SRC_DIR=$HOME/src/sorrentum1

if [[ 0 == 1 ]]; then
    DST_SUBDIR="umd_icorps"
    #DST_SUBDIR="umd_defi"

    # Diff `//sorrentum/sorrentum_sandbox/docker_common` vs `DST_SUBDIR/docker_common`.
    SRC_DIR=$ROOT_SRC_DIR/sorrentum_sandbox/docker_common; DST_DIR=$HOME/src/$DST_SUBDIR/docker_common; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR

    # Diff `//sorrentum/sorrentum/devops` dir vs `DST_SUBDIR/
    SRC_DIR=$ROOT_SRC_DIR/sorrentum_sandbox/devops; DST_DIR=$HOME/src/$DST_SUBDIR/project/icorps; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR

    # Diff `//sorrentum/defi/devops` dir vs `DST_SUBDIR/
    SRC_DIR=$ROOT_SRC_DIR/defi/devops; DST_DIR=$HOME/src/$DST_SUBDIR/project/icorps; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR
fi;

if [[ 1 == 1 ]]; then
    DST_SUBDIR="umd_data605_1"

    # Diff `//sorrentum/sorrentum_sandbox/docker_common` vs `DST_SUBDIR/docker_common`.
    SRC_DIR=$ROOT_SRC_DIR/sorrentum_sandbox/docker_common; DST_DIR=$HOME/src/$DST_SUBDIR/docker_common; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR

    # Diff `//sorrentum/sorrentum/devops` dir vs `DST_SUBDIR/
    SRC_DIR=$ROOT_SRC_DIR/sorrentum_sandbox/devops; DST_DIR=$HOME/src/$DST_SUBDIR/project/icorps; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR

    # Diff `//sorrentum/defi/devops` dir vs `DST_SUBDIR/
    SRC_DIR=$ROOT_SRC_DIR/defi/devops; DST_DIR=$HOME/src/$DST_SUBDIR/project/icorps; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR
fi;
