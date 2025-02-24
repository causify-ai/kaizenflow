#!/bin/bash -e
#
# """
# Open all the interesting Python files under a dir with vim.
#
# Print only:
# > vi_all_py.sh -t -p im_v2
#
# Max depth:
# > vi_all_py.sh -t -d 2 -p im_v2
#
# Open with vim:
# > vi_all_py.sh -p im_v2
# """

#set -x

# Initialize default values.
print_only=0
include_notebooks=0
include_tests=0
# Default depth value.
depth=0
# Path.
path=""

# Function to show usage.
show_usage() {
    echo "Usage: $0 [-t] [-d depth] -p path"
    echo "  -t        Dry run"
    echo "  -d depth  Optional depth parameter"
    echo "  -n        Include notebooks"
    echo "  -r        Include tests"
    echo "  -p path   Mandatory path"
}

# Parse command-line options.
while getopts 'tnrd:p:' flag; do
    case "${flag}" in
        t) print_only=1 ;;
        n) include_notebooks=1 ;;
        r) include_tests=1 ;;
        d) depth="${OPTARG}" ;;
        p) path="${OPTARG}" ;;
        *) show_usage
           exit 1 ;;
    esac
done

if [[ -z $path ]]; then
    echo "Need to specify dir"
    exit -1
fi;
OPTS=""
if [[ $depth -ne 0 ]]; then
    OPTS="-maxdepth $depth"
fi;
CMD="find $path $OPTS -name \"*.py\""
CMD="$CMD | grep -v __init__"
if [[ $include_notebooks -ne 1 ]]; then
    CMD="$CMD | grep -v /notebooks/"
fi;
if [[ $include_tests -ne 1 ]]; then
    CMD="$CMD | grep -v /test/"
fi;
echo "CMD='$CMD'"
FILES=$(eval $CMD)
if [[ $print_only -ne 0 ]]; then
    echo "$FILES" | sed 's/ /\n/g'
    exit -1
fi;
vim $FILES
