#!/bin/bash -xe
for FILE in etc_sudoers install_jupyter_extensions.sh bashrc
do
    echo "FILE=$FILE"
    if [[ -f $FILE ]]; then
        rm -f $FILE
    fi;
    ln -s ../../docker_common/$FILE .
done;
