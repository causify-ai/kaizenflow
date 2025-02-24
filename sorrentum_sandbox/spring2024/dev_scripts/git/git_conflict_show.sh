#!/bin/bash -e

# """
# Generate the files involved in a merge conflict.
# """

for FILE in $*; do
  echo "# Processing $FILE"
  BASE="$FILE.1_base"
  git show :1:$FILE >$BASE
  #
  OUR="$FILE.2_our"
  git show :2:$FILE >$OUR
  #
  THEIR="$FILE.3_their"
  git show :3:$FILE >$THEIR
  #
  #ls $FILE.*
  echo "> vimdiff $THEIR $OUR"
  echo "> vimdiff $BASE $OUR"
  echo "> vimdiff $BASE $THEIR"
done;
