#!/bin/bash -e
#
# Run Jupyter notebook in a container:
# 
# -p: set the port in the container (although it needs to be forwarded to the
#     container)
# -v: enable vim shortcuts
# -d: map a target dir. This is needed by the enclosing script and ignored here
#
# > run_jupyter -p 8888 -v -d /Users/saggese/src/git_gp1/code/

# Parse params.
export JUPYTER_HOST_PORT=8888
export JUPYTER_USE_VIM=0
export TARGET_DIR=""
export VERBOSE=0

while getopts p:d:uv flag
do
    case "${flag}" in
        p) JUPYTER_HOST_PORT=${OPTARG};;
        u) JUPYTER_USE_VIM=1;;
        d) TARGET_DIR=${OPTARG};;
        v) VERBOSE=1;;
    esac
done

if [[ $VERBOSE == 1 ]]; then
    set -x
fi;

if [[ $JUPYTER_USE_VIM != 0 ]]; then
    jupyter nbextension enable vim_binding/vim_binding
fi;

# Run Jupyter.
jupyter-notebook \
    --port=$JUPYTER_HOST_PORT \
    --no-browser \
    --ip=* \
    --NotebookApp.token='' --NotebookApp.password='' \
    --allow-root
