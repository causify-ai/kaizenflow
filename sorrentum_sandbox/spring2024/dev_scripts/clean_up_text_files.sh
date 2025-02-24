#!/bin/bash -e

# From https://stackoverflow.com/questions/43491498/python-script-should-end-with-new-line-or-not-pylint-contradicting-itself
#
# While Python interpreters typically do not require line end character(s) on
# the last line, other programs processing Python source files may do, and it
# is simply good practice to have it. This is confirmed in Python docs: Line
# Structure which states that a physical line is ended by the respective line
# end character(s) of the platform.

# https://stackoverflow.com/questions/36043061/automatically-add-newline-on-save-in-pycharm

# Bad
#
# > tail -3 helpers/hplayback.py | xxd
# 00000000: 2320 2020 2020 7265 7475 726e 2072 6573  #     return res
# 00000010: 0a23 2060 6060 0a0a                      .# ```..
#
# where 0a = \n
#
# > pylint helpers/hplayback.py
# helpers/hplayback.py:487:0: C0305: Trailing newlines (trailing-newlines)

# Bad
# > perl -pi -e 'chomp if eof' helpers/hplayback.py
#
# > tail -3 helpers/hplayback.py | xxd
# 00000010: 290a 2320 2020 2020 7265 7475 726e 2072  ).#     return r
# 00000020: 6573 0a23 2060 6060                      es.# ```
#
# > pylint helpers/hplayback.py
# helpers/hplayback.py:486:0: C0304: Final newline missing (missing-final-newline)

# Good
#
# > tail -3 helpers/hplayback.py | xxd
# 00000010: 290a 2320 2020 2020 7265 7475 726e 2072  ).#     return r
# 00000020: 6573 0a23 2060 6060 0a                   es.# ```.

# Bad
#
# > cat sorrentum_sandbox/examples/reddit/__init__.py | xxd
# 00000000: 0a
#
# > pylint sorrentum_sandbox/examples/reddit/__init__.py
# > sorrentum_sandbox/examples/reddit/__init__.py:1:0: C0305: Trailing newlines (trailing-newlines)

# Previous versions of the script did
# - Remove trailing spaces:
#   ```bash
#   > find . -name "*.py" -o -name "*.txt" -o -name "*.json" | xargs perl -pi -e 's/\s+$/\n/'
#   ```
# - Add end-of-file marker:
#   ```bash
#   > find . -name "*.py" | xargs sed -i '' -e '$a\'
#   ```
# - Remove end-of-file:
#   ```bash
#   > find . -name -name "*.txt" | xargs perl -pi -e 'chomp if eof'
#   ```

#echo "Remove trailing spaces in each line ..."
#find . -name "*.py" -o -name "*.txt" -o -name "*.json" | xargs perl -pi -e 's/\s+$/\n/'

SCRIPT_NAME="/tmp/remove_empty_lines.py"
cat <<EOF > $SCRIPT_NAME
#! /usr/bin/env python

import sys

for filename in sys.argv[1:]:
    print(filename)
    # Read the entire file.
    with open(filename, 'r') as file:
        lines = file.readlines()

    # Modify the last line.
    if lines:
        lines = [line.rstrip("\n") for line in lines]
        lines = "\n".join(lines)
        lines = lines.rstrip("\n") + "\n"
    else:
        lines = ""

    # Write the modified content back to the file
    with open(filename, 'w') as file:
        file.write(lines)
EOF
chmod +x $SCRIPT_NAME

#mode="Test"
#mode="Test_on_file"
mode="Run_on_everything"

if [[ $mode == "Test" ]]; then
    # To test the process.
    FILE="sorrentum_sandbox/examples/reddit/validate.py"
    echo $FILE
    SHOW="tail -c -20"
    #
    echo; echo "# Test 1: Current file"
    git checkout $FILE
    echo "Before"; $SHOW $FILE | xxd
    $SCRIPT_NAME $FILE
    echo "After"; $SHOW $FILE | xxd
    #
    echo; echo "# Test 2: Multiple new lines"
    git checkout $FILE
    perl -pi -e '$\ = eof ? "\n\n\n" : ""' $FILE
    echo "Before"; $SHOW $FILE | xxd
    $SCRIPT_NAME $FILE
    echo "After"; $SHOW $FILE | xxd
    #
    echo; echo "# Test 3: No new line"
    git checkout $FILE
    perl -pi -e '$\ = eof ? "x" : ""' $FILE
    echo "Before"; $SHOW $FILE | xxd
    $SCRIPT_NAME $FILE
    echo "After"; $SHOW $FILE | xxd
    #
    echo; echo "# Test 4: Exactly one new line"
    git checkout $FILE
    perl -pi -e '$\ = eof ? "x\n" : ""' $FILE
    echo "Before"; $SHOW $FILE | xxd
    $SCRIPT_NAME $FILE
    echo "After"; $SHOW $FILE | xxd
    #
    echo; echo "# Test 5: Empty file"
    FILE="/tmp/__init__.py"
    rm $FILE || true
    touch $FILE
    echo "Before"; $SHOW $FILE | xxd
    $SCRIPT_NAME $FILE
    echo "After"; $SHOW $FILE | xxd
fi;

if [[ $mode == "Test_on_file" ]]; then
    # Run on a single file.
    #FILE="dataflow/core/nodes/test/outcomes/TestArmaDataSource.test1/output/test.txt"
    #FILE="/Users/saggese/src/cmamp1/dataflow/core/nodes/test/outcomes/TestArmaDataSource.test1/output/test.txt"
    FILE="/Users/saggese/src/sorrentum1/dataflow/core/nodes/test/outcomes/TestArmaDataSource.test1/output/test.txt"
    $SCRIPT_NAME $FILE
fi;

if [[ $mode == "Run_on_everything" ]]; then
    # Run on everything.
    echo "Make sure that last line terminates with exactly new line (0x0a)"
    find . -name "*.py" -o -name "*.json" -o -name "*.sh" | xargs -n 10 $SCRIPT_NAME
    find . -name "*.txt" | grep -v "/output/" | xargs -n 10 $SCRIPT_NAME
    #
    find . -name "*.txt" | xargs -n 10 $SCRIPT_NAME
    git checkout master -- helpers/test/outcomes/Test_get_dir_signature1.test2/output/test.txt
fi;
