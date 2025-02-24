#!/bin/bash -xe
#FILE="
time scp -i ~/.ssh/ck/saggese-cryptomatic.pem -C daocross_daoswap.tex saggese@172.30.2.136:/data/saggese/src/cmamp1/defi/papers/daocross_daoswap.tex

REMOTE_GIT_ROOT="/data/saggese/src/cmamp1"
remote_cmd="cd $REMOTE_GIT_ROOT/defi/papers; $REMOTE_GIT_ROOT/dev_scripts/latex/latexdockercmd.sh pdflatex daocross_daoswap.tex && $REMOTE_GIT_ROOT/dev_scripts/latex/latexdockercmd.sh latexmk -cd -f -interaction=batchmode -pdf daocross_daoswap.tex"
ssh -i ~/.ssh/ck/saggese-cryptomatic.pem saggese@172.30.2.136 $remote_cmd

#rm -f daocross_daoswap.pdf
time scp -i ~/.ssh/ck/saggese-cryptomatic.pem -C saggese@172.30.2.136:$REMOTE_GIT_ROOT/defi/papers/daocross_daoswap.pdf .
/usr/bin/osascript << EOF
set theFile to POSIX file "./daocross_daoswap.pdf" as alias
tell application "Skim"
activate
set theDocs to get documents whose path is (get POSIX path of theFile)
if (count of theDocs) > 0 then revert theDocs
open theFile
end tell
EOF
