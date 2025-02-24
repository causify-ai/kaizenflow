#!/bin/bash -e

conda info -e

DIR_NAME=$(jupyter --data-dir)
echo "Jupyter data dir: $DIR_NAME"
if [[ ! -d $DIR_NAME ]]; then
  mkdir -p $DIR_NAME
fi;
ls $DIR_NAME

if [[ 0 == 1 ]]; then
  # jupyter nbextension install https://rawgithub.com/lambdalisue/jupyter-vim-binding/master/vim_binding.js --nbextensions=$(jupyter --data-dir)/nbextensions/vim_binding
  # Sometimes the vim extension gives problems. This procedure typically solves
  # the problem.
  # Note on installation:
  #     https://github.com/lambdalisue/jupyter-vim-binding/wiki/Installation
  VIM_DIR=$DIR_NAME/nbextensions/vim_binding
  if [[ -d $VIM_DIR ]]; then
      rm -rf $VIM_DIR
  fi;
  mkdir -p $VIM_DIR
  cd $VIM_DIR
  # vim bindings.
  git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding
  # Activate the extension.
  jupyter nbextension enable vim_binding/vim_binding
  exit -1
fi;

extensions="
vim_binding/vim_binding
autosavetime/main
code_prettify/code_prettify
collapsible_headings/main
comment-uncomment/main
contrib_nbextensions_help_item/main
execute_time/ExecuteTime
highlighter/highlighter
jupyter-js-widgets/extension
limit_output/main
notify/notify
runtools/main
toc2/main"
#nb_anacondacloud/main
#nb_conda/main
#jnbextensions_configurator/config_menu/main
#nbextensions_configurator/tree_tab/main
#nbpresent/js/nbpresent.min


# jupyter contrib nbextension install --user

for v in $extensions; do
  #  cmd="jupyter nbextension install --user $v"
  #  echo "> $cmd"
  #  if [[ 1 == 1 ]]; then
  #    eval $cmd
  #  fi;
  cmd="jupyter nbextension enable $v"
  echo "> $cmd"
  if [[ 1 == 1 ]]; then
    eval $cmd
  fi;
done;
