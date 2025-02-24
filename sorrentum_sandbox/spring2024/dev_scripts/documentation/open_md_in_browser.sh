#!/bin/bash
#
# Render a markdown using Pandoc and then open it in a browser.
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

# Process the file (you can replace the following line with your processing code)
echo "Processing file: $filename"

dst_filename="tmp.rendered_md.html"

pandoc $filename -o $dst_filename

echo "Saved to $dst_filename"
open $dst_filename
