#!/bin/bash -e

# """
# Compute statistics about the unit tests.
# """

# TODO(gp): Merge it inside run_tests.py

# Get the path to amp dir.
EXEC_NAME="${BASH_SOURCE[0]}"
EXEC_PATH=$(dirname "$EXEC_NAME")
AMP_DIR=$(cd $EXEC_PATH/../..; pwd -P)
echo "AMP_DIR=$AMP_DIR"
if [[ $(basename $AMP_DIR) != "amp" ]]; then
    echo "AMP_DIR=$AMP_DIR doesn't point to amp"
    exit -1
fi;

source $AMP_DIR/dev_scripts/helpers.sh

DST_DIR="/tmp"

# ##################################################################################

echo
CMD="pytest --collect-only >$DST_DIR/tmp.pytest.txt"
execute $CMD

# TODO(gp): Remove spaces.
RES=$(grep "UnitTestCase" $DST_DIR/tmp.pytest.txt | wc -l)
echo
echo "# Number of test classes: $RES"

RES=$(grep "TestCaseFunction" $DST_DIR/tmp.pytest.txt | wc -l)
echo "# Number of test functions: $RES"

# ##################################################################################

echo
CMD="pytest --collect-only -m skip >tmp.pytest_skip.txt"
execute $CMD

RES=$(grep "TestCaseFunction" $DST_DIR/tmp.pytest_skip.txt | wc -l)
echo
echo "# Number of skipped test functions: $RES"

# ##################################################################################

echo
CMD="pytest --collect-only -m fast >tmp.pytest_slow.txt"
execute $CMD

RES=$(grep "TestCaseFunction" $DST_DIR/tmp.pytest_slow.txt | wc -l)
echo
echo "# Number of test slow functions: $RES"

# Clean up.
#rm -f tmp.pytest.txt tmp.pytest_skip.txt tmp.pytest_slow.txt
