#!/bin/bash -xe

im_client_test_case_dirs="amp/dev_scripts/cleanup_scripts dev_scripts/cleanup_scripts im_v2/common/data/client amp/im_v2/common/data/client"
mdata_test_case_dirs="dev_scripts/cleanup_scripts amp/dev_scripts/cleanup_scripts"

replace_text.py \
  --old "import im_v2.common.data.client.test.im_client_test_case as icdctictc" \
  --new "import im_v2.common.data.client as icdc" \
  --exclude_dirs "$im_client_test_case_dirs"

replace_text.py \
  --old "icdctictc." \
  --new "icdc." \
  --exclude_dirs "$im_client_test_case_dirs"

replace_text.py \
  --old "import market_data.test.market_data_test_case as mdtmdtca" \
  --new "import market_data as mdata" \
  --exclude_dirs "$mdata_test_case_dirs"

replace_text.py \
  --old "mdtmdtca." \
  --new "mdata." \
  --exclude_dirs "$mdata_test_case_dirs"

# Remove unused imports from affected files.
invoke lint -m --only-format
