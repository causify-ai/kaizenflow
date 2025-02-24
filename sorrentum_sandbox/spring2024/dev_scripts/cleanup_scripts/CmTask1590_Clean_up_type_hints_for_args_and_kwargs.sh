#!/bin/bash -xe

# CmTask1590 - Replace type hints for `*args` and `**kwargs` with `Any`.
replace_text.py \
  --action "replace" \
  --old "(\*(\*kw)?args: )(Dict\[str, Any\]|Tuple\[Any\]|List\[Any\]|int)" \
  --new "\1Any"
