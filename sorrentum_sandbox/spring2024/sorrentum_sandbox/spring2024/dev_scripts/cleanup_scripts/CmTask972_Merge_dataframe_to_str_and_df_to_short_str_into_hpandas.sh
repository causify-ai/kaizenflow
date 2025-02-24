#!/bin/bash -xe

# This script should be invoked on a different repo so that we don't annihilate
# this file.
SOURCE_REPO=CMTask972_merge_df_to_str_functions
TARGET_REPO=/Users/saggese/src/cmamp3
SCRIPT=$(pwd)/dev_scripts/cleanup_scripts/CmTask972_Merge_dataframe_to_str_and_df_to_short_str_into_hpandas.py

cd $TARGET_REPO

# Make sure that the source and target branch are at master.
#if [[ 0 == 1 ]]; then
#  git pull
#  i git_merge_master
#  git push --force
#fi

# Create the branch with the changes.
TARGET_BRANCH=CmTask972_Merge_dataframe_to_str_and_df_to_short_str_into_hpandas_2
#i git_branch_create -b $TARGET_BRANCH
git checkout -B $TARGET_BRANCH

# Clean up.
git reset --hard origin/$TARGET_BRANCH || True

# Apply manual changes.
git merge --no-commit origin/$SOURCE_REPO

# Replace function calls.
$SCRIPT

# Apply lint to affected files.
invoke lint -m --only-format
