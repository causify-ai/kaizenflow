#!/bin/bash
#
# Build the helpers package.
#

set -ex

# Go inside the container
# > i docker_bash
# pip install wheel
#python setup.py bdist_wheel
# ls -l dist/*.whl
# root@497249d87bfc:/app/amp# ls -l dist/*.whl
# -rw-r--r-- 1 root root 82894 May  3 16:35 dist/helpers-1.2-py3-none-any.whl

# From outside the container
python setup.py sdist

# > ls -l dist/helpers-1.2.tar.gz
# -rw-r--r--  1 saggese  staff  73344 May  3 12:41 dist/helpers-1.2.tar.gz

FILE=$(ls -1 dist/*.tar.gz)
echo "FILE=$FILE"
ls -l $FILE

#cp $FILE /Users/saggese/src/dev_tools/helpers.tar.gz

path $FILE
