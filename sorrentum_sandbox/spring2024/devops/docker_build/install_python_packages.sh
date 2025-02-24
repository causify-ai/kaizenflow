#!/usr/bin/env bash
#
# Install Python packages.
#

set -ex

FILE_NAME="devops/docker_build/install_python_packages.sh"
echo "#############################################################################"
echo "##> $FILE_NAME"
echo "#############################################################################"

echo "# Installing ${ENV_NAME}"

if [[ 0 == 1 ]]; then
    # Conda flow.
    echo "# Building environment with conda"
    update_env () {
        echo "Installing ${ENV_FILE} in ${ENV_NAME}"
        ENV_FILE=${1}
        conda env update -n ${ENV_NAME} --file ${ENV_FILE}
    }

    AMP_CONDA_FILE="devops/docker_build/conda.yml"
    update_env ${AMP_CONDA_FILE}

    conda clean --all --yes
else
    # Poetry flow.
    echo "# Building environment with poetry"

    # Print config.
    poetry config --list --local

    # TODO(gp): We prefer to compute the dependencies outside the container so
    # we can source control the lock file.
    # Compute dependencies.
    #poetry lock

    if [[ 0 == 1 ]]; then
        # Install with poetry.
        echo "# Install with poetry"
        poetry install

        # poetry prepends a `.` to the env.
        ln -sf .${ENV_NAME} ${ENV_NAME}
    else
        # Install with poetry inside a venv.
        echo "# Install with venv + poetry"

        python3 -m ${ENV_NAME} /${ENV_NAME}
        source /${ENV_NAME}/bin/activate

        pip3 install wheel

        poetry install

        # Export deps from poetry and install with pip.
        #poetry export -f requirements.txt --output requirements.txt
        #pip3 install --upgrade pip
        #pip3 install --no-deps -r requirements.txt
    fi;

    poetry env list

    # Clean up.
    # TODO(gp): Enable this.
    #poetry cache clear --all -q pypi
fi;

# Some tools refer to `python` and `pip`.
# TODO(gp): Move to install_packages.sh
if [[ ! -e /usr/bin/python ]]; then
    ln -s /usr/bin/python3 /usr/bin/python
fi;
if [[ ! -e /usr/bin/pip ]]; then
    ln -s /usr/bin/pip3 /usr/bin/pip
fi;

# Install cvxopt outside poetry since it doesn't work with poetry
# `https://github.com/cvxopt/cvxopt/issues/78#issuecomment-263962654`.
apt-get install -y libblas-dev liblapack-dev cmake
apt-get install -y wget
wget http://faculty.cse.tamu.edu/davis/SuiteSparse/SuiteSparse-4.5.3.tar.gz
tar -xf SuiteSparse-4.5.3.tar.gz 
export CVXOPT_SUITESPARSE_SRC_DIR=$(pwd)/SuiteSparse
pip install cvxopt

# We install cvxpy here after poetry since it doesn't work with poetry
# ```
# ERROR: cvxpy-1.2.2-cp38-cp38-manylinux_2_24_x86_64.whl is not a supported wheel on this platform.
# ```
pip3 install cvxpy

# Update the bashrc.
echo "" >>~/.bashrc
echo "set -o vi" >>~/.bashrc

# Clean up.
if [[ $CLEAN_UP_INSTALLATION ]]; then
    echo "Cleaning up installation..."
    DIRS="/usr/lib/gcc /app/tmp.pypoetry /tmp/*"
    du -hs $DIRS | sort -h
    rm -rf $DIRS
fi;
