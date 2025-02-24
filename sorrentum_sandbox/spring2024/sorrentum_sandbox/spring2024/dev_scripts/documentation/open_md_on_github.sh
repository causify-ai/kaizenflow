#!/bin/bash
#
# Open a filename (e.g,. a markdown) on GitHub.
# 

# Check if a file name is passed as an argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <filename>"
    exit 1
fi

# The filename is expected to be the first argument
filename="$1"

# Check if the file exists
if [ ! -f "$filename" ]; then
    echo "Error: File '$filename' not found."
    exit 1
fi

hash=$(git rev-parse HEAD)

url="https://github.com/cryptokaizen/cmamp/blob/$hash/$filename"

open $url
