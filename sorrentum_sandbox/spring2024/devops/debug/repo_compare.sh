#!/bin/bash
#
# Compare GH workflows / devops / config dirs of different repos.
#

# Select the dirs to compare.
GIT_CLIENT="amp1"
echo "GIT_CLIENT=$GIT_CLIENT"

if [[ 0 == 1 ]]; then
    # amp vs lm.
    DIR1=$HOME/src/$GIT_CLIENT/amp
    DIR2=$HOME/src/$GIT_CLIENT
elif [[ 0 == 1 ]]; then
    # amp vs dev_tools.
    DIR1=$HOME/src/$GIT_CLIENT/amp
    DIR2=$HOME/src/dev_tools1
else
    # amp vs optimizer.
    DIR1=$HOME/src/$GIT_CLIENT
    DIR2=$HOME/src/$GIT_CLIENT/optimizer
fi;

echo "DIR1=$DIR1"
echo "DIR2=$DIR2"

if [[ ! -d $DIR1 ]]; then
    echo "ERROR: '$DIR1' doesn't exist"
fi;
if [[ ! -d $DIR2 ]]; then
    echo "ERROR: '$DIR2' doesn't exist"
fi;

# Compare some configuration files.
if [[ 0 == 1 ]]; then
    for file in .dockerignore .gitignore conftest.py invoke.yaml mypy.ini pytest.ini tasks.py
    do
        vimdiff {$DIR1,$DIR2}/$file
    done;
fi;

# Compare devops.
if [[ 1 == 1 ]]; then
    DIR="devops"
    echo "Comparing $DIR"
    diff_to_vimdiff.py --dir1 $DIR1/$DIR --dir2 $DIR2/$DIR
    # --only_different_files
fi;

# Compare .github/workflows
if [[ 0 == 1 ]]; then
    DIR=".github/workflows"
    echo "Comparing $DIR"
    diff_to_vimdiff.py --dir1 $DIR1/$DIR --dir2 $DIR2/$DIR
fi;

# TODO(gp): If a file is a link, do not compare.
