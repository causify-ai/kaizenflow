#!/bin/bash -xe

EXTENSIONS="md"
OLD_MARKER="<!--ts-->"
OLD_MARKER_STOP="<!--te-->"
NEW_MARKER="<!-- toc -->"
NEW_MARKER_STOP="<!-- tocstop -->"


replace_text.py \
    --only_dirs "docs" \
    --ext "$EXTENSIONS" \
    --old "$OLD_MARKER" \
    --new "$NEW_MARKER" \
    --mode "replace_with_perl" 

replace_text.py \
    --only_dirs "docs" \
    --ext "$EXTENSIONS" \
    --old "$OLD_MARKER_STOP" \
    --new "$NEW_MARKER_STOP" \
    --mode "replace_with_perl" 