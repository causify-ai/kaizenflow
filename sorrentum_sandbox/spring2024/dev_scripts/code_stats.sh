#!/bin/bash
echo "# Numer of files in repo"
find . -name "*.py" | wc -l

echo "# LOC in repo"
find . -name "*.py" | xargs cat | wc -l
