#!/bin/bash -xe
DIR=$(jupyter --data-dir)/nbextensions
if [[ ! -e $DIR ]]; then
    mkdir $DIR
fi
cd $DIR
if [[ -e vim_binding ]]; then
    rm -rf vim_binding
fi
git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding
jupyter nbextension enable vim_binding/vim_binding
