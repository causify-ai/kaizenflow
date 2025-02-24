#!/bin/bash -xe

# """
# Test all the executables that need to bootstrap.
# """

(cd $HOME/src/...1/amp; dev_scripts/_setenv_amp.py)
(cd $HOME/src/...1/amp; dev_scripts/install/create_conda.py -h)

(cd $HOME/src/...1; dev_scripts/_setenv_amp.py)

(cd $HOME/src/...1/amp; source dev_scripts/setenv_amp.sh)
(cd $HOME/src/...1; source dev_scripts/setenv_....sh)
