#!/bin/bash

# """
# Apply process_jupytext.py to all the ipynb files.
# """

#ACTION="$*"
#ACTION="pair"
#ACTION="test"
ACTION="sync"
find . -name "*.ipynb" | grep -v ipynb_checkpoints | xargs -t -L 1 process_jupytext.py --action $ACTION --file 
