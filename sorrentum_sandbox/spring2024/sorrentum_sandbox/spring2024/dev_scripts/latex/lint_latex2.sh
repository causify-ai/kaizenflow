#!/usr/bin/env bash
#
# Dockerized linter for Latex using `latexindent.pl`.
# This is the old flow.
#

set -eux
if [[ -z $1 ]]; then
    echo "Need to specify latex file to compile"
    exit -1
fi;
FILE_NAME=$1

# 1) Build container.
IMAGE=ghcr.io/cmhughes/latexindent.pl
# See devops/docker_build/install_publishing_tools.sh
cat >/tmp/tmp.dockerfile <<EOF
FROM alpine:latest
# Installing perl
RUN apk --no-cache add miniperl perl-utils

# Installing incompatible latexindent perl dependencies via apk
RUN apk --no-cache add \
    perl-log-dispatch \
    perl-namespace-autoclean \
    perl-specio \
    perl-unicode-linebreak

# Installing remaining latexindent perl dependencies via cpan
RUN apk --no-cache add curl wget make
RUN cd /usr/local/bin && \
    curl -L https://cpanmin.us/ -o cpanm && \
    chmod +x cpanm
RUN cpanm -n App::cpanminus
RUN cpanm -n File::HomeDir
RUN cpanm -n Params::ValidationCompiler
RUN cpanm -n YAML::Tiny
RUN cpanm -n 

RUN wget http://mirror.ctan.org/support/latexindent.zip && \
    unzip latexindent.zip && \
    cd latexindent && \
    chmod +x latexindent.pl && \
    mv latexindent.pl LatexIndent defaultSettings.yaml /usr/local/bin/
EOF
docker build -f /tmp/tmp.dockerfile -t $IMAGE .

# 2) Create script to run.
EXEC="./tmp.lint_latex.sh"
# Note that we need to escape some chars.
cat >$EXEC <<EOF
latexindent.pl -w -s $FILE_NAME
perl -pi -e 's/\t/  /g' $FILE_NAME
# Remove tightlist.
perl -ni -e 'print unless /\\\\tightlist/' $FILE_NAME
# Merge lines with \item
perl -i -pe 'if (/\\\\item\\s*$/) { chomp; \$_ .= <> }' $FILE_NAME
perl -pi -e 's/(\\\\item)\\s+/\$1 /' $FILE_NAME
#
perl -pi -e 's/\\\\\(/\\\$/g' $FILE_NAME
perl -pi -e 's/\\\\\)/\\\$/g' $FILE_NAME
#
latexindent.pl -w -s $FILE_NAME
perl -pi -e 's/\t/  /g' $FILE_NAME
EOF
chmod +x $EXEC

# 3) Run inside Docker.
CMD="sh -c '$EXEC'"
WORKDIR="$(realpath .)"
MOUNT="type=bind,source=${WORKDIR},target=${WORKDIR}"
USER="$(id -u $(logname)):$(id -g $(logname))"
#OPTS="--user "${USER}"
OPTS=""
docker run --rm -it $OPTS --workdir "${WORKDIR}" --mount "${MOUNT}" $IMAGE:latest $CMD "$@"

# To debug:
# > docker run --rm -it --user 2908:2908 --workdir /local/home/gsaggese/src/sasm-lime6/amp --mount type=bind,source=/local/home/gsaggese/src/sasm-lime6/amp,target=/local/home/gsaggese/src/sasm-lime6/amp ctags:latest
