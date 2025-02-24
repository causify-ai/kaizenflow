#!/bin/bash -e

# """
# Commit in all the repos.
# It assumes that everything has been pulled.
# """

# TODO(gp): Make sure all repos are pointing to the same branch, e.g.,
# `master`.

AMP_DIR="amp"
source $AMP_DIR/dev_scripts/helpers.sh

msg="$@"
echo "msg='$msg'"
if [[ -z $msg ]]; then
  echo "Need a commit message"
  exit -1
fi;

cd amp
execute "git commit -am '$msg'"
execute "git push"
cd ..

execute "git add amp"
execute "git commit -am '$msg'"
execute "git push"
