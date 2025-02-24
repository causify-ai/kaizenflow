#!/bin/bash -xe

replace_text.py \
    --old "pytest.raises" \
    --new "self.assertRaises" \
    --ext "py,ipynb"

replace_text.py \
    --old "fail.value" \
    --new "fail.exception" \
    --ext "py,ipynb"
