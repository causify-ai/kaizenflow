#
# Configure the local (thin) client built with `dev_scripts/client_setup/build.sh`.
#

# TODO(gp): -> dev_scripts -> dev_scripts_amp

PWD=$(pwd)
AMP=$PWD

# Give permissions to read / write to user and group.
umask 002

# #############################################################################
# Virtual env
# #############################################################################

# This needs to be in sync with dev_scripts/client_setup/build.sh
VENV_DIR="$HOME/src/venv/amp.client_venv"
if [[ ! -d $VENV_DIR ]]; then
    echo "Can't find VENV_DIR='$VENV_DIR': checking the container one"
    # The venv in the container is in a different spot. Check that.
    VENV_DIR="/venv/amp.client_venv"
    if [[ ! -d $VENV_DIR ]]; then
        echo "ERROR: Can't find VENV_DIR='$VENV_DIR'. Create it with client_setup/build.sh"
        return -1
    fi;
fi;

ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
echo "# Activate virtual env '$ACTIVATE_SCRIPT'"
if [[ ! -f $ACTIVATE_SCRIPT ]]; then
    echo "ERROR: Can't find '$ACTIVATE_SCRIPT'"
    return -1
fi;
source $ACTIVATE_SCRIPT

echo "which python="$(which python 2>&1)
echo "python -v="$(python --version)

# #############################################################################
# PATH
# #############################################################################

echo "# Set path"

export PATH=.:$PATH

export PATH=$AMP:$PATH

# Add to the PATH all the first level directory under `dev_scripts`.
export PATH="$(find "$(pwd)/dev_scripts" -maxdepth 1 -type d -not -path "$(pwd)" | tr '\n' ':' | sed 's/:$//'):$PATH"

# Remove duplicates.
export PATH=$(echo $PATH | perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, scalar <>))')

# Print.
echo "PATH="
echo $PATH | perl -e 'print join("\n", grep { not $seen{$_}++ } split(/:/, scalar <>))'

# #############################################################################
# PYTHONPATH
# #############################################################################

echo "# Set PYTHONPATH"
export PYTHONPATH=$PWD:$PYTHONPATH

# Remove duplicates.
export PYTHONPATH=$(echo $PYTHONPATH | perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, scalar <>))')

# Print on different lines.
echo "PYTHONPATH="
echo $PYTHONPATH | perl -e 'print join("\n", grep { not $seen{$_}++ } split(/:/, scalar <>))'

# #############################################################################
# Configure environment
# #############################################################################

source $AMP/dev_scripts/setenv_amp.configure_env.sh

echo "==> SUCCESS <=="
