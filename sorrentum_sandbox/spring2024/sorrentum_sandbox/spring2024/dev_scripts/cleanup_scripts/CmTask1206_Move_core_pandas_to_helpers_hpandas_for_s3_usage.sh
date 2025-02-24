#!/bin/bash -xe

if [[ 0 == 1 ]]; then
    # This script should be invoked on a different repo so that we don't annihilate
    # this file.
    SOURCE_REPO=CMTask1206_run_script
    TARGET_REPO=/Users/saggese/src/cmamp2
    cd $TARGET_REPO

    # Make sure that the source and target branch are at master.
    #if [[ 0 == 1 ]]; then
    #  git pull
    #  i git_merge_master
    #  git push --force
    #fi

    # Create the branch with the changes.
    TARGET_BRANCH=CMTask1206_transform_compatible_with_s3_move_pandas_helpers_2
    #i git_branch_create -b $TARGET_BRANCH
    git checkout -B $TARGET_BRANCH

    # Clean up.
    git reset --hard origin/$TARGET_BRANCH

    # Apply manual changes.
    git merge --no-commit origin/$SOURCE_REPO
fi;

# Move `read_csv` from `core.pandas_helpers` to `helpers.hpandas`.
# Rename to `read_csv_to_df`.
./dev_scripts/replace_text.py \
  --old "cpanh.read_csv" \
  --new "hpandas.read_csv_to_df" \
  --ext "py"

# Move `read_parquet` from `core.pandas_helpers` to `helpers.hpandas`.
# Rename to `read_parquet_to_df`.
./dev_scripts/replace_text.py \
  --old "cpanh.read_parquet" \
  --new "hpandas.read_parquet_to_df" \
  --ext "py"

# Add imports to affected files.
FILES=$(git diff --name-only HEAD)
./dev_scripts/replace_text.py \
  --old "import core.pandas_helpers as cpanh" \
  --new "import helpers.hpandas as hpandas; import core.pandas_helpers as cpanh" \
  --ext "py" \
  --only_files "${FILES//$'\n'/ }" # Replace new lines with space.

# Remove unused imports from affected files.
invoke lint -m --only-format
