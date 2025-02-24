#!/bin/bash -e

# """
# Backup and then update labels of several GitHub repos.
# """

EXEC="/Users/saggese/src/github/github-label-maker/github-label-maker.py"

SRC_DIR="./dev_scripts/github/labels"
SRC_NAME="$SRC_DIR/gh_tech_labels.json"
#SRC_NAME="$SRC_DIR/gh_org_labels.json"
DST_DIR="$SRC_DIR/backup"


function label() {
    FULL_OPTS="$OPTS -o $OWNER -r $REPO"
    CMD="python $EXEC $FULL_OPTS -t $GH_TOKEN"
    echo "> $CMD"
    eval $CMD
    echo "Done"
}


function backup_and_update() {
    # Backup.
    if [[ 1 == 1 ]]; then
        FILE_NAME="$DST_DIR/labels.$OWNER.$REPO.json"
        OPTS="-d $FILE_NAME"
        label
    fi;

    # Update.
    if [[ 0 == 1 ]]; then
        OPTS="-m $SRC_NAME"
        label
    fi;
}


# .../...
OWNER="..."
REPO="..."
if [[ 1 == 1 ]]; then
    backup_and_update
fi;

# alphamatic/amp
OWNER="alphamatic"
REPO="amp"
if [[ 1 == 1 ]]; then
    backup_and_update
fi;
