#!/bin/bash -e

# """
# Roll fwd the submodules.
# """

# TODO(gp): Convert to Python.
# TODO(gp): Enforce that we run this only from a top Git submodule.
# TODO(gp): Allow to work with different branches.

clean=0
if [[ $1 == "clean" ]]; then
    echo "Running 'git clean -fd' as requested"
    clean=1
    exit -1
fi;

AMP_DIR="amp"
BRANCH="master"
echo "BRANCH=$BRANCH"

source $AMP_DIR/dev_scripts/helpers.sh

echo "# amp pointer in p1 is at:"
cmd="git ls-tree master | grep amp"
execute $cmd

cmd="git submodule update --remote"
execute $cmd

# TODO(gp): Factor out this code in a loop.

# Pull p1
echo "+ Pull p1"
git checkout $BRANCH
git pull --autostash
if [[ $clean == 1 ]]; then
    git clean -fd
fi;

# Pull amp
echo "+ Pull amp"
cd amp

cmd="dev_scripts/git/git_hash_head.sh"
execute $cmd

git checkout $BRANCH
git pull --autostash
if [[ $clean == 1 ]]; then
    git clean -fd
fi;

cmd="dev_scripts/git/git_hash_head.sh"
execute $cmd

cd ..
git add amp

echo "# amp pointer in p1 is at:"
cmd="git ls-tree master | grep amp"
execute $cmd

msg='git commit -am "Move forward git submodules" && git push'
SCRIPT_NAME="./tmp_push.sh"
echo $msg > $SCRIPT_NAME
chmod +x $SCRIPT_NAME
echo "Run:"
echo "> $msg"
echo "or"
echo "> $SCRIPT_NAME"
