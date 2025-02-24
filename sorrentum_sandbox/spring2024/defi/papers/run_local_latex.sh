#!/bin/bash -xe
#GIT_ROOT="/Users/saggese/src/cmamp1"
if [[ -z $GIT_ROOT ]]; then
    echo "Can't find GIT_ROOT=$GIT_ROOT"
    exit -1
fi;

FILE_NAME=tulip
(cd $GIT_ROOT/defi/papers; pdflatex ${FILE_NAME}.tex && pdflatex ${FILE_NAME}.tex)

#rm -f ${FILE_NAME}.pdf
/usr/bin/osascript << EOF
set theFile to POSIX file "./${FILE_NAME}.pdf" as alias
tell application "Skim"
activate
set theDocs to get documents whose path is (get POSIX path of theFile)
if (count of theDocs) > 0 then revert theDocs
open theFile
end tell
EOF
