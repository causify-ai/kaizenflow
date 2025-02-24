#!/bin/bash -e

# set -x

DIR_PREFIX=$1
if [[ -z $DIR_PREFIX ]]; then
  echo "ERROR: You need to specify the prefix of the dir, e.g. 'amp' or 'cmamp'"
  exit -1
fi;

IDX=$2
if [[ -z $IDX ]]; then
    echo "ERROR: You need to specify a client, like 1, 2, 3..."
    exit -1
fi;

#DIR_NAME="$HOME/src_vc/$DIR_PREFIX$IDX"
DIR_NAME="$HOME/src/$DIR_PREFIX$IDX"
if [[ ! -d $DIR_NAME ]]; then
    echo "Can't find dir $DIR_NAME"
    exit -1
fi;
FILE="dev_scripts/tmux_amp.sh $DIR_PREFIX $IDX"
echo "> $DIR_NAME/$FILE"

cd $DIR_NAME
exec $FILE
