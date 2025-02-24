#!/bin/bash -e

# """
# Run a notebook end-to-end and save the results into an html file, measuring
# the elapsed time.
# """

source dev_scripts/helpers.sh

if [[ -z $1 ]]; then
    echo "Error: need to specify a ipynb file"
    exit -1
fi;

cmd="jupyter nbconvert $1 \
    --execute \
    --to html $1.html \
    --ExecutePreprocessor.kernel_name=python \
    --ExecutePreprocessor.timeout=-1
"

time execute $cmd
echo "SUCCESS"
