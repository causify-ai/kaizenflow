#!/bin/bash -xe
#GIT_ROOT="/Users/saggese/src/cmamp1"
if [[ -z $GIT_ROOT ]]; then
    echo "Can't find GIT_ROOT=$GIT_ROOT"
    exit -1
fi;

# Relative to papers, without '.tex'.
FILE_NAME=fin_econ_ai/fin_econ_ai
(cd $GIT_ROOT/papers; pdflatex ${FILE_NAME}.tex && pdflatex ${FILE_NAME}.tex)

PDF_FILE_NAME=$(basename $FILE_NAME)
open -a Skim papers/${PDF_FILE_NAME}.pdf

#rm -f ${FILE_NAME}.pdf
#/usr/bin/osascript << EOF
#set theFile to POSIX file "$GIT_ROOT/papers/${FILE_NAME}.pdf" as alias
#tell application "Skim"
#activate
#set theDocs to get documents whose path is (get POSIX path of theFile)
#if (count of theDocs) > 0 then revert theDocs
#open theFile
#end tell
#EOF
