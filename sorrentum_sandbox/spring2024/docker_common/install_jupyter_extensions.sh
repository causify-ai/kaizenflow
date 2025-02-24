#!/usr/bin/env bash
#
# Install Jupyter packages.
#

set -ex

echo "# Install Jupyter extensions"

# Create jupyter data dir.
DIR_NAME=$(jupyter --data-dir)
echo "Jupyter data dir: $DIR_NAME"
if [[ ! -d $DIR_NAME ]]; then
  mkdir -p $DIR_NAME
fi;

# Install extensions.
sudo jupyter contrib nbextension install

# Enable extensions.
extensions="
autosavetime/main
code_prettify/code_prettify
collapsible_headings/main
comment-uncomment/main
contrib_nbextensions_help_item/main
execute_time/ExecuteTime
highlighter/highlighter
jupyter-js-widgets/extension
notify/notify
runtools/main
toc2/main
spellchecker/main"

for v in $extensions; do
  jupyter nbextension enable $v
done;

# Disable configuration for nbextensions without explicit compatibility.
echo "{\"nbext_hide_incompat\": false}" > /$HOME/.jupyter/nbconfig/common.json

DIR=$(jupyter --data-dir)/nbextensions
if [[ ! -e $DIR ]]; then
    mkdir $DIR
fi

# Fix vim plugin extension (from dev_scripts/notebooks/fix_vim_plugin.sh).
# Install vim bindings.
cd $DIR
if [[ -e vim_binding ]]; then
    rm -rf vim_binding
fi
git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding

#jupyter nbextension enable vim_binding/vim_binding

jupyter notebook --generate-config -y
