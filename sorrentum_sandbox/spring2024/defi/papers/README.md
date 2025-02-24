https://hub.docker.com/r/blang/latex

$GIT_ROOT/dev_scripts/latex/latexdockercmd.sh pdflatex daocross_daoswap.tex

$GIT_ROOT/dev_scripts/latex/latexdockercmd.sh latexmk -cd -f -interaction=batchmode -pdf daocross_daoswap.tex

On mac:
sshfs -o IdentityFile=~/.ssh/ck/saggese-cryptomatic.pem saggese@172.30.2.136:/data/saggese/src/cmamp1/defi/papers /tmp/dev1

dev_scripts/latex/skim.sh

* Using TexShop

sudo tlmgr install amsrefs

* Install the formatter

From https://github.com/cmhughes/latexindent.pl

brew install perl
brew install cpanm
cpanm YAML::Tiny
cpanm File::HomeDir
brew install latexindent

* Indent

latexindent -w tulip.tex
