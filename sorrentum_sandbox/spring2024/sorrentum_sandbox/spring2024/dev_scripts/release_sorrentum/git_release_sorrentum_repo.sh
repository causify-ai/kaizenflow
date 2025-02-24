#!/bin/bash -xe

# This scripts releases the `cryptokaizen/cmamp` repo to `sorrentum/sorrentum`.
# Details at https://docs.google.com/document/d/1ZISW8KudmO6oCY5kMJGgynDPFmAvJlBHTnSk-2hHXR8/edit#

# Conceptually
# 1) Check out the source Git repo `cryptokaizen/cmamp` locally
# 2) Remove all the branches besides master
# 3) Remove all the ipynb metadata and password leaks
# 4) Push the updated Git repo to sorrentum/sorrentum

SRC_REPO="cryptokaizen/cmamp.git"

DST_REPO="sorrentum/sorrentum_test"
SRC_DIR="$HOME/src/sorrentum_src"
DST_DIR="$HOME/src/sorrentum_dst"

# find sorrentum_sandbox -name "*.ipynb" | xargs nb-clean clean
# find research_amp/altdata -name "*.ipynb" | xargs nb-clean clean

# From where we are running this script.
RUN_REPO_PATH=$(pwd)
PATH=$RUN_REPO_PATH/dev_scripts/release_sorrentum:$PATH
PATH=$RUN_REPO_PATH/dev_scripts/release_sorrentum/filter_repo:$PATH
export PYTHONPATH=$RUN_REPO_PATH/dev_scripts/release_sorrentum/filter_repo:$PYTHONPATH
echo "PATH=$PATH"

if [[ 0 == 1 ]]; then
    GITHUB_KEY="/Users/saggese/.ssh/id_rsa.cryptokaizen.github"
    export GIT_SSH_COMMAND='ssh -i $GITHUB_KEY'
    gh auth login --with-token <$GITHUB_KEY
fi;

# Create a fresh copy of the source repo.
if [[ 0 == 1 ]]; then
    rm -rf $SRC_DIR
    git clone --mirror git@github.com:$SRC_REPO $SRC_DIR/.git
    du -d 1 -h $SRC_DIR/.git
    # Turn the bare repo into a normal one.
    cd $SRC_DIR
    git config --bool core.bare false
    git checkout master
    du -d 1 -h $SRC_DIR
    # Turn off the connection to the remote.
    git remote rm origin
    git remote -v
fi;

# Remove all branches.
if [[ 0 == 1 ]]; then
    git branch -a | tee >/dev/null
    git branch | grep -v "master" | xargs git branch -D
    git branch -a | tee >/dev/null
    du -d 1 -h $SRC_DIR
    # Force a clean up.
    # From https://stackoverflow.com/questions/1904860/how-to-remove-unreferenced-blobs-from-my-git-repository
    git -c gc.reflogExpire=0 \
        -c gc.reflogExpireUnreachable=0 \
        -c gc.rerereresolved=0 \
        -c gc.rerereunresolved=0 \
        -c gc.pruneExpire=now \
        gc
    #git gc
    du -d 1 -h $SRC_DIR
fi;

if [[ 0 == 1 ]]; then
    cd $SRC_DIR
    source ~/src/venv/amp.client_venv/bin/activate

    if [[ 0 == 1 ]]; then
        git filter-repo --analyze --force
    fi;

    # Clean up ipynb files in all history using filter-repo.
    if [[ 0 == 1 ]]; then
        if [[ 0 == 1 ]]; then
            pip install nb-clean git-filter-repo
        fi;
        which lint_history.py
        #git filter-branch --tree-filter 'git ls-files -z "*.ipynb" | xargs -0 -n 1 nb-clean clean'
        # wget https://raw.githubusercontent.com/newren/git-filter-repo/main/git-filter-repo
        #lint_history.py --relevant 'return filename.endswith(b".ipynb")' nb-clean clean
        lint_history.py --relevant 'return filename.endswith(b".ipynb")' $RUN_REPO_PATH/dev_scripts/release_sorrentum/nb-clean.sh
    fi;

    # Clean up ipynb files in master using filter-repo.

    # Old way using filter-branch and nbconvert.
    #if [[ 0 == 1 ]]; then
    #    git filter-branch --tree-filter 'jupyter nbconvert --to=notebook --inplace --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True'
    #fi;

    #if [[ 0 == 1 ]]; then
    #    find . -name "*.ipynb" | xargs -n 1 -t jupyter nbconvert --to=notebook --inplace --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True 
    #    # git commit 
    #fi;

    # Install gitleaks
    # https://github.com/gitleaks/gitleaks/releases/download/v8.16.3/gitleaks_8.16.3_linux_x64.tar.gz

    # Check and remove leaks.
    if [[ 0 == 1 ]]; then
        gitleaks detect --report-path gitleaks.before.json -v || true

        #\jack "Fingerprint" gitleaks.before.txt | \grep -v ipynb | tee cfile

        # > grep "RuleID" leaks.json  | sort | uniq
        # "RuleID": "aws-access-token",
        #  "RuleID": "easypost-api-token",
        #  "RuleID": "generic-api-key",
        #  "RuleID": "telegram-bot-api-token",

        # Check the output.
        # \jack "Fingerprint" log.txt | \grep -v ipynb | perl -p -e 's/^.*Fingerprint: \S{40}:(.*):.*:(.*)/vim $1 +$2/' | tee cfile
        # source cfile

        # jq '.[] | select (.RuleID == "telegram-bot-api-token") | .Secret' leaks.json

        # Get all the secrets in a file.
        jq '.[] | .Secret' gitleaks.before.json | sort | sed 's/"//g' | uniq >passwords.txt
        cat "665840871993" >>passwords.txt
    fi;

    # Clean history and the current commits from passwords.
    #    if [[ 0 == 1 ]]; then
    #        # git filter-repo --replace-text passwords.txt
    #        bfg --replace-text passwords.txt --no-blob-protection
    #        git commit -am "Remove passwords"
    #        git reflog expire --expire=now --all && git gc --prune=now --aggressive
    #    fi;
    if [[ 1 == 1 ]]; then
        git filter-repo --replace-text passwords.txt
    fi;

    # Check for leaks after the clean up.
    if [[ 0 == 1 ]]; then
        gitleaks detect --report-path gitleaks.after.json -v
    fi;
fi;

# TODO(gp): Sometimes I need to just run the command from a fresh terminal.
# error validating token: Get "https://api.github.com/": net/http: invalid header field value for "Authorization"
if [[ 0 == 1 ]]; then
    GITHUB_KEY="/Users/saggese/.ssh/id_rsa.alphamatic.github"
    export GIT_SSH_COMMAND="ssh -i $GITHUB_KEY"
    gh auth login --with-token <$GITHUB_KEY
fi;

# Create the GitHub remote target repo.
if [[ 1 == 1 ]]; then
    gh repo delete --confirm $DST_REPO
    #gh repo create --private $DST_REPO
    gh repo create --public $DST_REPO
    gh repo view $DST_REPO
fi;

# Push to the remote target repo.
if [[ 1 == 1 ]]; then
    cd $SRC_DIR
    git remote add origin git@github.com:${DST_REPO}.git
    git push --mirror git@github.com:${DST_REPO}.git
fi;

# Create the local target repo.
if [[ 0 == 1 ]]; then
    rm -rf $DST_DIR
    mkdir $DST_DIR
    cd $DST_DIR
    echo "# sorrentum_test" >> README.md
    git init
    git add README.md
    git commit -m "first commit"
    git branch -M main
    git remote add origin git@github.com:${DST_REPO}.git
    git push -u origin main
    #
    # open https://github.com/sorrentum/sorrentum_test
fi;
