#!/bin/bash -xe

if [[ 0 == 1 ]]; then
    # This script should be invoked on a different repo so that we don't annihilate
    # this file.
    SOURCE_REPO=CMTask974_run_script
    TARGET_REPO=/Users/saggese/src/cmamp2
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
    git reset --hard origin/$TARGET_BRANCH

    # Apply manual changes.
    git merge --no-commit origin/$SOURCE_REPO
fi;

# Move dataframe_to_str from hprint to hpandas.
./dev_scripts/replace_text.py \
  --old "hprint.dataframe_to_str" \
  --new "hpandas.dataframe_to_str" \
  --ext "py"

# Move df_to_short_str from hprint to hpandas.
./dev_scripts/replace_text.py \
  --old "hprint.df_to_short_str" \
  --new "hpandas.df_to_short_str" \
  --ext "py"

# Add imports to affected files.
FILES=$(git diff --name-only HEAD)
./dev_scripts/replace_text.py \
  --old "import helpers.hprint as hprint" \
  --new "import helpers.hpandas as hpandas; import helpers.hprint as hprint" \
  --ext "py" \
  --only_files "${FILES//$'\n'/ }" # Replace new lines with space.

# Remove unused imports from affected files.
invoke lint -m --only-format
