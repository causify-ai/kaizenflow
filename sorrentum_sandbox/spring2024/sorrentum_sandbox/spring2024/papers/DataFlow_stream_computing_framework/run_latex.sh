#!/bin/bash -xe
#GIT_ROOT="/Users/saggese/src/cmamp1"
export GIT_ROOT=$(pwd)
if [[ -z $GIT_ROOT ]]; then
    echo "Can't find GIT_ROOT=$GIT_ROOT"
    exit -1
fi;

FILE_NAME=DataFlow_stream_computing_framework
SUBDIR=docs/papers
dev_scripts/latex/run_latex.sh $SUBDIR/${FILE_NAME}.tex

#rm -f ${FILE_NAME}.pdf
/usr/bin/osascript << EOF
set theFile to POSIX file "${FILE_NAME}.pdf" as alias
tell application "Skim"
activate
set theDocs to get documents whose path is (get POSIX path of theFile)
if (count of theDocs) > 0 then revert theDocs
open theFile
end tell
EOF
