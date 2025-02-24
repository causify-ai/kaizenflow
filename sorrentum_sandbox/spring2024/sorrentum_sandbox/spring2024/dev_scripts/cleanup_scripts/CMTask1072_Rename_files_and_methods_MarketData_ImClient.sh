#!/bin/bash -xe

#if [[ 0 == 1 ]]; then
    # This script should be invoked on a different repo so that we don't annihilate
    # this file.
    #SOURCE_REPO=CMTask974_run_script
    #TARGET_REPO=/Users/saggese/src/cmamp2
    #cd $TARGET_REPO

    # Make sure that the source and target branch are at master.
    #if [[ 0 == 1 ]]; then
    #  git pull
    #  i git_merge_master
    #  git push --force
    #fi

    # Create the branch with the changes.
    #TARGET_BRANCH=CmTask1074_numeric_to_numerical_1
    #i git_branch_create -b $TARGET_BRANCH
    #git checkout -B $TARGET_BRANCH

    # Clean up.
    #git reset --hard origin/$TARGET_BRANCH

    # Apply manual changes.
    #git merge --no-commit origin/$SOURCE_REPO
#fi;

# CmTask1072 - Rename class "AbstractMarketData" to "MarketData".
./dev_scripts/replace_text.py \
  --old "AbstractMarketData" \
  --new "MarketData" \

# CmTask1072 - Rename method "construct_full_symbol()" to "build_full_symbol()".
./dev_scripts/replace_text.py \
  --old "construct_full_symbol" \
  --new "build_full_symbol" \

# CmTask1072 - Rename method "dassert_is_valid()" to "dassert_output_data_is_valid()".
./dev_scripts/replace_text.py \
  --old 'dassert_is_valid\(' \
  --new 'dassert_output_data_is_valid\(' \
  --dirs "im_v2" \
  
# CmTask1072 - Rename method "get_numerical_ids_from_full_symbols()" to "get_asset_ids_from_full_symbols()".
./dev_scripts/replace_text.py \
  --old "get_numerical_ids_from_full_symbols" \
  --new "get_asset_ids_from_full_symbols" \

# CmTask1072 - Rename class "MarketDataImClient" to "ImClientMarketData".
./dev_scripts/replace_text.py \
  --old "MarketDataImClient" \
  --new "ImClientMarketData" \

# CmTask1072 - Rename "numeric" to "numerical".
./dev_scripts/replace_text.py \
   --old 'numeric_' \
   --new 'numerical_' \
   --dirs "im_v2" \
   
./dev_scripts/replace_text.py \
   --old 'numeric_' \
   --new 'numerical_' \
   --dirs "market_data" \

# CmTask1072 - Rename method "build_num_to_string_id_mapping()" to "build_numerical_to_string_id_mapping()".
./dev_scripts/replace_text.py \
   --old 'build_num_to_string_id_mapping' \
   --new 'build_numerical_to_string_id_mapping' \
   --dirs "im_v2" \
   
# CmTask1072 - Rename method "get_full_symbols_from_numerical_ids()" to "get_full_symbols_from_asset_ids()".
./dev_scripts/replace_text.py \
   --old 'get_full_symbols_from_numerical_ids' \
   --new 'get_full_symbols_from_asset_ids' \

# CmTask1072 - Rename class "TestBuildNumericToStringIdMapping" to
# "TestBuildNumericalToStringIdMapping".
./dev_scripts/replace_text.py \
  --old "TestBuildNumericToStringIdMapping" \
  --new "TestBuildNumericalToStringIdMapping" \

# CmTask1072 - Rename class "TestStringToNumId" to "TestStringToNumericalId".
./dev_scripts/replace_text.py \
  --old "TestStringToNumId" \
  --new "TestStringToNumericalId" \

# Remove unused imports from affected files.
invoke lint -m --only-format
