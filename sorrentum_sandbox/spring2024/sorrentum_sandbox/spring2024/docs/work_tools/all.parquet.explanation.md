

<!-- toc -->

- [Pyarrow Parquet management](#pyarrow-parquet-management)
  * [Introduction](#introduction)
  * [Implementation details](#implementation-details)
    + [Writing Parquet](#writing-parquet)
    + [Reading Parquet](#reading-parquet)
  * [Change log](#change-log)
    + [2024-02-26: cmamp-1.14.0](#2024-02-26-cmamp-1140)
      - [Rationale](#rationale)
    + [2024-03-11: CmampTask7331 Remove `ns vs us` hacks related to Pyarrow 14.0.2](#2024-03-11-cmamptask7331-remove-ns-vs-us-hacks-related-to-pyarrow-1402)
      - [Time unit conversion when writing to Parquet](#time-unit-conversion-when-writing-to-parquet)
      - [Time unit conversion when reading from Parquet](#time-unit-conversion-when-reading-from-parquet)

<!-- tocstop -->

# Pyarrow Parquet management

## Introduction

- What is Parquet?
  - Parquet is a columnar storage file format that provides efficient data
    compression and encoding schemes with enhanced performance to handle complex
    data in bulk. It is designed to support complex data structures and is ideal
    for big data processing.

- Core features of Parquet:
  - Efficient storage and compression: Parquet uses efficient encoding and
    compression techniques to store data in a columnar format, reducing the
    storage space and improving the read performance
  - Support for various compression algorithms: Parquet supports various
    compression algorithms such as Snappy, Gzip, and LZO
  - Support for complex data types: Parquet supports complex data types such as
    nested fields, arrays, and maps, making it suitable for handling complex
    data structures
  - Efficient encoding and decoding schemes: Parquet provides efficient encoding
    and decoding schemes for complex data types, improving the read and write
    performance

- Pyarrow
  - Pyarrow is a cross-language development platform for in-memory data that
    provides efficient data interchange between Python and other languages. It
    is designed to support complex data structures and is ideal for big data
    processing.
  - Pyarrow provides efficient data interchange between Python and other
    languages, enabling seamless data exchange between different systems
  - It supports various data types and complex data structures, making it
    suitable for handling complex data processing tasks

## Implementation details

The `helpers.hparquet` module provides a set of helper functions to manage
Parquet files using the pyarrow library.

### Writing Parquet

- `to_parquet()`
  - Writes a Pandas DataFrame to a Parquet file

- `to_partitioned_parquet()`
  - Writes a Pandas DataFrame to a partitioned Parquet files

### Reading Parquet

- `from_parquet()`
  - Reads a Parquet file or partitional Parquet files into a Pandas DataFrame

## Change log

### 2024-02-26: cmamp-1.14.0

- Upgraded pyarrow to 14.0.2 -> 15.0.0
- Update outomes in the tests due to the new version of pyarrow changed the size
  of the some Parquet files
- Delete `partition_filename` from `to_partitioned_parquet()` function
  - Delete `partition_filename_cb` in the `pq.write_to_dataset()` call
- Delete `partition_filename` arguments from the all calls of
  `to_partitioned_parquet()` function
- In the `list_and_merge_pq_files()`
  - In the `pq.ParquetDataset()` change `use_legacy_dataset=True` to
    `partitioning=None`
- Introduce `purify_parquet_file_names()` in the `helpers/hunit_test.py`

#### Rationale

- The upgrade to pyarrow 15.0.0 is necessary to keep the library up-to-date and
  benefit from the latest features and improvements
- Due the `partition_filename_cb` is deprecated in the new version of pyarrow,
  it is necessary to remove it from the `to_partitioned_parquet()` function
  - After discussion with the team, we decided to remove the
    `partition_filename` from the `to_partitioned_parquet()` function
  - The consequence of this change is that the Parquet files will be saved with
    the default names like `<guid>-<number>.parquet` for example
    `f3b3e3e33e3e3e3e3e3e3e3e3e3e3e3e-0.parquet`
- In the pyarrow 1.15.0 the `use_legacy_dataset` is deprecated and the
  `partitioning` should be used instead
  - When we use the `partitioning=None` in `pq.ParquetDataset()` then we will
    not use the partitioning and will not add the partitioned columns to the
    dataset
  - Some tests expect the Parquet files with the name `data.parquet`. The
    `purify_parquet_file_names()` changes the names of the Parquet files to
    `data.parquet` in the goldens

### 2024-03-11: CmampTask7331 Remove `ns vs us` hacks related to Pyarrow 14.0.2

- Remove time unit casting to `us` in the `to_parquet()`
- Keep time unit casting to `ns` in the `from_parquet()`

#### Time unit conversion when writing to Parquet

- **Context**: Before the upgrade to pyarrow 15.0.0, casting the time unit to
  `us` was necessary to avoid the `pyarrow.lib.ArrowInvalid` exception.
- **Problem**: In pyarrow 15.0.0, this exception is no longer raised, and the
  time unit is preserved correctly.
- **Insight**: Casting the time unit to `us` in the `to_parquet()` function is
  no longer necessary and can be removed. At the same time, casting to `us` in
  the `to_parquet()` function does not make sense since the time unit will be
  converted back to `ns` in the `from_parquet()` function.
- **Solution**: Remove the casting of the time unit to `us` in the
  `to_parquet()` function.

#### Time unit conversion when reading from Parquet

- **Context**: The pyarrow version prior to 15.0.0 did not correctly preserve
  the time unit information when reading data back from Parquet files. That's
  why casting the time unit to `ns` was necessary in the `from_parquet()`
  function.
- **Problem**: Since the upgrade to pyarrow 15.0.0, casting the time unit to
  `ns` is no longer necessary, as the new version of pyarrow correctly preserves
  the time unit. See the Pyarrow issue for details:
  https://github.com/apache/arrow/issues/33321 When reading Parquet files with a
  time unit that is not in ['us', 'ns'], the `pyarrow.lib.ArrowInvalid`
  exception could be raised. This could occur when Pyarrow attempts to cast the
  time unit to a lower resolution. This behavior is tested in the
  `test_parquet_files_with_mixed_time_units_2` test. In this case, the
  alphabetical order of the files is important. The data from the first file
  will be cast to the time unit of the rest of the files.
- **Insight**: The general approach is to preserve the time unit information
  after reading data back from Parquet files. Currently, resolving this issue is
  challenging because Parquet data is mixed with data from CSV files, which
  convert the time unit to `ns` by default. Refer to CmampTask7331 for details.
  https://github.com/cryptokaizen/cmamp/issues/7331
- **Solution**: Retain the casting of the time unit to `ns` in the
  `from_parquet()` function.
