#!/bin/bash -xe

script_name="dev_scripts/cleanup_scripts/CMTask2573_Move_get_config_from_nested_dict_to_Config.sh"

replace_text.py \
  --old "cconfig.get_config_from_nested_dict" \
  --new "cconfig.Config.from_dict" \
  --exclude_files $script_name \

replace_text.py \
  --old "cfgb.get_config_from_nested_dict" \
  --new "cconfig.Config.from_dict" \
  --exclude_files $script_name \

replace_text.py \
  --old "ccocouti.get_config_from_nested_dict" \
  --new "cconfig.Config.from_dict" \
  --exclude_files $script_name \

# Remove unused imports from affected files.
invoke lint -m --only-format
