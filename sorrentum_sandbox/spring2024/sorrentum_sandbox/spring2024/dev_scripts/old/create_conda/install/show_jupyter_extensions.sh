#!/bin/bash -e

DIR_NAME=$(jupyter --data-dir)/nbextensions
echo "DIR_NAME=$DIR_NAME"

jupyter nbextension list

echo "==========================================="
echo "Summary"
echo "==========================================="
jupyter nbextension list 2>/dev/null | grep enabled | awk '{print $1}' | sort | uniq
