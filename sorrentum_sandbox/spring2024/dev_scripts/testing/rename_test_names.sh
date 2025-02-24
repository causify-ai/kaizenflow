#!/bin/bash -e

# """
# Rename based on a regular expression.
#
# Usage example:
# > ./dev_scripts/testing/rename_test_names.sh TestReadDataFromDisk TestDiskDataSource core/dataflow/test/TestReadDataFromDisk*
# This will replace "TestReadDataFromDisk" with "TestDiskDataSource" in all
# files starting with "core/dataflow/test/TestReadDataFromDisk"
# """

for path in "${@:3}"
do
  new_path="${path//$1/$2}"
  mv "$path" "$new_path"
  echo "$path -> $new_path"
done
