PWD=$(pwd)
AMP=$PWD

# #############################################################################
# Virtual env
# #############################################################################

# This needs to be in sync with dev_scripts/client_setup/build.sh
VENV_DIR="$HOME/src/venv/amp.cvxpy_venv"

echo "# Activate virtual env"
source $VENV_DIR/bin/activate

echo "which python="$(which python 2>&1)
echo "python -v="$(python --version)

echo "cvxpy -v="$(python -c "import cvxpy as cp; print(cp.__version__)")
