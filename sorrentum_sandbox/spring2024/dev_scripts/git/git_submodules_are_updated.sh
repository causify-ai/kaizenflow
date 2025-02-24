#!/bin/bash -e

# """
# Print the relevant Git hash pointers to amp.
# """

# amp pointer in p1.
echo "# amp pointer in p1"
cmd='git ls-tree master | \grep amp | perl -pe "s/\t/ /" | cut -d " " -f3'
eval $cmd

# amp head.
echo "# amp head"
cd amp
cmd="git rev-parse HEAD"
amp_head=$($cmd)
echo $amp_head
cd ..

# amp remote head.
echo "# amp remote head"
cmd='git ls-remote git@github.com:alphamatic/amp HEAD 2>/dev/null | perl -pe "s/\t/ /" | cut -d " " -f 1'
eval $cmd
