#!/bin/bash
#
# Compare GH workflows / devops / config dirs of different repos.
#

# Select the dirs to compare.
DIR1=$(pwd)
DIR2=$(pwd)/amp

echo "DIR1=$DIR1"
echo "DIR2=$DIR2"

if [[ ! -d $DIR1 ]]; then
    echo "ERROR: '$DIR1' doesn't exist"
fi;
if [[ ! -d $DIR2 ]]; then
    echo "ERROR: '$DIR2' doesn't exist"
fi;

# Compare the scripts to create the dev env.
if [[ 1 == 1 ]]; then
    SUFFIX1="devto"
    #SUFFIX1="lem"
    #SUFFIX1="lime"
    SUFFIX2="amp"
    vimdiff $DIR1/dev_scripts_$SUFFIX1/go_$SUFFIX1.sh $DIR2/dev_scripts/go_$SUFFIX2.sh 
    vimdiff $DIR1/dev_scripts_$SUFFIX1/tmux_$SUFFIX1.sh $DIR2/dev_scripts/tmux_$SUFFIX2.sh 
    vimdiff $DIR1/dev_scripts_$SUFFIX1/setenv.sh $DIR2/dev_scripts/setenv_$SUFFIX2.sh 
fi;

# Compare some configuration files.
if [[ 0 == 1 ]]; then
    for file in .dockerignore .gitignore conftest.py invoke.yaml mypy.ini pytest.ini tasks.py repo_config.py
    do
        vimdiff {$DIR1,$DIR2}/$file
    done;
fi;

# Compare devops.
if [[ 0 == 1 ]]; then
    DIR="devops"
    echo "Comparing $DIR"
    diff_to_vimdiff.py --dir1 $DIR1/$DIR --dir2 $DIR2/$DIR
    # --only_different_files
fi;

# Compare .github/workflows
# TODO(gp): Maybe use .github
if [[ 0 == 1 ]]; then
    DIR=".github/workflows"
    echo "Comparing $DIR"
    diff_to_vimdiff.py --dir1 $DIR1/$DIR --dir2 $DIR2/$DIR
fi;

# TODO(gp): If a file is a link, do not compare.
