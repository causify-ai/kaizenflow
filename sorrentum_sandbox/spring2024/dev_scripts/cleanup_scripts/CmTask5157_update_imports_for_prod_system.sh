#!/bin/bash -xe

./dev_scripts/replace_text.py \
  --old "import dataflow_orange.system.Cx.Cx_prod_system_test_case as dtfosccpstc" \
  --new "import dataflow_amp.system.Cx.Cx_prod_system_test_case as dtfasccpstc" \
  --ext "py"

./dev_scripts/replace_text.py \
  --old "import dataflow_orange.system.Cx.Cx_prod_system as dtfosccprsy" \
  --new "import dataflow_amp.system.Cx.Cx_prod_system as dtfasccprsy" \
  --ext "py"

./dev_scripts/replace_text.py \
  --old "import dataflow_orange.system.Cx as dtfosyscx" \
  --new "import dataflow_amp.system.Cx as dtfamsysc" \
  --ext "py"

FILES=$(git diff --name-only HEAD)
./dev_scripts/replace_text.py \
  --old "dtfosccpstc" \
  --new "dtfasccpstc" \
  --ext "py" \
  --only_files "${FILES//$'\n'/ }"

./dev_scripts/replace_text.py \
  --old "dtfosccprsy" \
  --new "dtfasccprsy" \
  --ext "py" \
  --only_files "${FILES//$'\n'/ }"

./dev_scripts/replace_text.py \
  --old "dtfosyscx" \
  --new "dtfamsysc" \
  --ext "py" \
  --only_files "${FILES//$'\n'/ }"
