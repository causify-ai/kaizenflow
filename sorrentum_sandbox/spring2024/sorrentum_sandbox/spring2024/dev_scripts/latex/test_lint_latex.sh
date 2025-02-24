FILE_NAME=$1
git checkout $FILE_NAME
dev_scripts/latex/lint_latex.sh $FILE_NAME
gd $FILE_NAME
