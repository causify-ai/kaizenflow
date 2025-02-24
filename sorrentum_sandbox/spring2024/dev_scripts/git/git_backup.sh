#!/bin/bash -e

# """
# Create a tarball of all the files added / modified according to git_files.sh
# """

source helpers.sh

FILES=$(git_files.sh | xargs)
echo "FILES=$FILES"
DATETIME=$(date "+%Y%m%d-%H%M%S")
REPO_NAME=$(basename `git rev-parse --show-toplevel`)
BACKUP_FILE=~/src/backups/backup.$REPO_NAME.$DATETIME.tgz
echo "BACKUP_FILE=$BACKUP_FILE"
tar czf $BACKUP_FILE $FILES
echo "Done"

echo
echo "# Backup file is:"
path $BACKUP_FILE

echo
echo "# Testing tarball ..."
ls -l $BACKUP_FILE
tar tzf $BACKUP_FILE
