#!/bin/bash -xe

script_name="amp/dev_scripts/cleanup_scripts/CMTask2692_Refactor_system_test_case.sh"
outputs="helpers/test/outcomes/"
system_test_case="amp/dataflow/system/system_test_case.py"

replace_text.py \
  --old "system_tester." \
  --new "dtfsys." \
  --exclude_files $script_name \
  --exclude_files $outputs \
  --exclude_files $system_test_case \

replace_text.py \
  --old "import dataflow.system.test.system_test_case as dtfsytsytc" \
  --new "import dataflow.system as dtfsys" \
  --exclude_files $script_name \
  --exclude_files $outputs \
  --exclude_files $system_test_case \

replace_text.py \
  --old "dtfsytsytc." \
  --new "dtfsys." \
  --exclude_files $script_name \
  --exclude_files $outputs \
  --exclude_files $system_test_case \

# Remove unused imports from affected files.
invoke lint -m --only-format
