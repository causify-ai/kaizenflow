#!/bin/bash -xe

# """
# Compute a UML plot of the class hierarchy of code in a dir using pylint.
# """

DIR=$1
if [[ -z $DIR ]]; then
    echo "You need to specify a dir"
    exit -1
fi;
pyreverse $DIR --ignore=test
dot -Tpng classes.dot >classes.png
# This works only on macOS.
if [[ $(uname) == "Darwin" ]]; then
    open classes.png
fi;
