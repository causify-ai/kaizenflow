#!/bin/bash -e
#
# """
# Show one level of dirs under im_v2:
# > tree.sh -d 1 -p im_v2
#
# Show all files under im_v2:
# > tree.sh -p im_v2
# """

#set -x

# Initialize default values
# Flag for clean_up, 0 means no clean_up, 1 means perform clean_up.
clean_up=0  
# Default depth value.
depth=0     
# Path.
path=""

# Function to show usage.
show_usage() {
    echo "Usage: $0 [-c] [-d depth] -p path"
    echo "  -c        Optional clean up flag"
    echo "  -d depth  Optional depth parameter"
    echo "  -p path   Mandatory path"
}

# Parse command-line options.
while getopts 'cd:p:' flag; do
    case "${flag}" in
        c) clean_up=1 ;;
        d) depth="${OPTARG}" ;;
        p) path="${OPTARG}" ;;
        *) show_usage
           exit 1 ;;
    esac
done

# Script logic.
#echo "Clean up: $clean_up"
#echo "Depth: $depth"

if [[ $clean_up -ne 0 ]]; then
    git clean -fd
    find . -name "__pycache__" -o -name "tmp.build" -o -name ".ipynb_checkpoints" | xargs rm -rf
fi;

opts="--dirsfirst -n -F --charset unicode"
if [[ $depth -ne 0 ]]; then
    opts="$opts -L $depth"
fi;

if [[ -z $path ]]; then
    echo "Need to specify dir"
    exit -1
fi;

tree $opts $path
