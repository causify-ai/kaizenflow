

<!-- toc -->

- [Debug information](#debug-information)
  * [Node output data](#node-output-data)
  * [Node output statistics](#node-output-statistics)
  * [Profiling statistics](#profiling-statistics)

<!-- tocstop -->

# Debug information

There are switches in the `DAG` class that control how much debugging
information it saves.

- `save_node_io` decides whether a `DAG` instance writes output `DataFrame` to
  disk for each `Node`, refer to the corresponding [section](#node-output-data)
  for details; The permissible values are:
  - `""`: save nothing
  - `df_as_csv`: save output as CSV
  - `df_as_pq`: save output as Parquet
  - `df_as_csv_and_pq`: save output as both CSV and Parquet
- `save_node_stats` decides whether a `DAG` instance writes statistics (e.g.,
  size, columns, types, index) about output `DataFrame` to disk for each `Node`
  or not
  - Refer to the corresponding [section](#node-output-statistics) for details
- `profile_execution` decides whether a `DAG` instance writes information about
  `Node` memory consumption and its execution time or not
  - Refer to the corresponding [section](#profiling-statistics) for details

Worth noting that writing files to disk is expensive in terms of time so the
corresponding switches should be turned on only when debugging a system run.

When running a System all the data is stored at `.../dag/node_io`.

## Node output data

The `DAG` class saves an output `DataFrame` for each `bar_timestamp` and each
`Node` at `.../dag/node_io/node_io.data`. E.g.:

```bash
> ls system_log_dir/dag/node_io/node_io.data/

predict.0.read_data.df_out.20240123_080000.20240123_080011.parquet
predict.0.read_data.df_out.20240123_080000.20240123_080011.csv
predict.0.read_data.df_out.20240123_081200.20240123_081211.parquet
predict.0.read_data.df_out.20240123_081200.20240123_081211.csv
predict.1.generate_feature_panels.df_out.20240123_080000.20240123_080014.parquet
predict.1.generate_feature_panels.df_out.20240123_080000.20240123_080014.csv
predict.1.generate_feature_panels.df_out.20240123_081200.20240123_081211.parquet
predict.1.generate_feature_panels.df_out.20240123_081200.20240123_081211.csv
...
```

A file name follows the following pattern:
`{method}.{topological_id}.{nid}.df_out.{bar_timestamp}.{wall_clock_time}.{extension}`,
e.g., `predict.0.read_data.df_out.20240123_080000.20240123_080011.parquet`

- `method` is `fit` or `predict`
- `topological_id` is the `Node` id, e.g., `0` for the first `Node`
- `nid` is `Node` name, e.g., `read_data`, `resample`
- `bar_timestamp` is the timestamp of a bar for which a DAG was computed
- `wall_clock_time` machine time when a `Node` is computed
- `extension` file extensions, e.g., `csv` or `pq`

An output `DataFrame` is stored in the `DataFlow` format, i.e. indexed by
timestamps and asset_ids, e.g.:
```
|                           |       open |            |            |      close |            |            |     volume |            |            |
|---------------------------|-----------:|-----------:|-----------:|-----------:|-----------:|-----------:|-----------:|-----------:|-----------:|
|                           | 1030828978 | 1464553467 | 8968126878 | 1030828978 | 1464553467 | 8968126878 | 1030828978 | 1464553467 | 8968126878 |
| 2023-11-03 09:10:00-04:00 |   0.435053 |   0.316767 |   0.575763 |   0.435053 |   0.316767 |   0.002544 |   0.435053 |   0.316767 |   0.575763 |
| 2023-11-03 09:15:00-04:00 |   0.707034 |   0.144804 |   0.123079 |   0.707034 |   0.144804 |   0.123079 |  0.707034  |   0.144804 |  0.144804  |
```

## Node output statistics

The `DAG` class saves a `TXT` file with statistics for each `bar_timestamp` and
each `Node` at `.../dag/node_io/node_io.data`. E.g.:

```bash
> ls system_log_dir/dag/node_io/node_io.data/ | grep "txt"

predict.0.read_data.df_out.20240123_080000.20240123_080011.txt
predict.0.read_data.df_out.20240123_081200.20240123_081211.txt
predict.1.generate_feature_panels.df_out.20240123_080000.20240123_080014.txt
predict.1.generate_feature_panels.df_out.20240123_081200.20240123_081211.txt
...
```

File content:

- Index
- Columns
- Data types
- Memory by column
- Number of nans
- Munber of zeroes
- Dataframe

E.g.:

```bash
> cat system_log_dir/dag/node_io/node_io.data/predict.0.read_data.df_out.20240123_080000.20240123_080011.txt
index=[2024-01-23 07:48:00-05:00, 2024-01-23 08:00:00-05:00]
columns=('open', 1030828978),('open', 1464553467),('open', 8968126878),('close', 1030828978),('close', 1464553467),('close', 8968126878),('volume', 1030828978),('volume', 1464553467),('volume', 8968126878)...
shape=(13, 240)
* type=
| col_name | dtype                 | num_unique                       | num_nans          | first_elem     | type(first_elem)              |
|----------|-----------------------|----------------------------------|-------------------|----------------|-------------------------------|
| 0        | index                 | datetime64[ns, America/New_York] | 13 / 13 = 100.00% | 0 / 13 = 0.00% | 2024-01-23T12:48:00.000000000 |
| 1        | ('open', 1030828978)  | float64                          | 12 / 13 = 92.31%  | 0 / 13 = 0.00% | 0.2483                        |
| 2        | ('open', 1464553467)  | float64                          | 13 / 13 = 100.00% | 0 / 13 = 0.00% | 2212.24                       |
| 3        | ('open', 8968126878)  | float64                          | 13 / 13 = 100.00% | 0 / 13 = 0.00% | 38854.5                       |
| 4        | ('close', 1030828978) | float64                          | 12 / 13 = 92.31%  | 0 / 13 = 0.00% | 0.2483                        |
| 5        | ('close', 1464553467) | float64                          | 13 / 13 = 100.00% | 0 / 13 = 0.00% | 2212.24                       |
| 6        | ('close', 8968126878) | float64                          | 13 / 13 = 100.00% | 0 / 13 = 0.00% | 38854.5                       |
| 7        | ('volume', 1030828978)| float64                          | 12 / 13 = 92.31%  | 0 / 13 = 0.00% | 0.2483                        |
| 8        | ('volume', 1464553467)| float64                          | 13 / 13 = 100.00% | 0 / 13 = 0.00% | 2212.24                       |
| 9        | ('volume', 8968126878)| float64                          | 13 / 13 = 100.00% | 0 / 13 = 0.00% | 38854.5                       |
....
* memory =
|                     |         |         |
|---------------------|---------|---------|
|                     | shallow | deep    |
| Index               | 660.0 b | 660.0 b |
| (open, 1030828978)  | 104.0 b | 104.0 b |
| (open, 1464553467)  | 104.0 b | 104.0 b |
| (open, 8968126878)  | 104.0 b | 104.0 b |
| (close, 1030828978) | 104.0 b | 104.0 b |
| (close, 1464553467) | 104.0 b | 104.0 b |
| (close, 8968126878) | 104.0 b | 104.0 b |
| (volume, 1030828978)| 104.0 b | 104.0 b |
| (volume, 1464553467)| 104.0 b | 104.0 b |
| (volume, 8968126878)| 104.0 b | 104.0 b |
|...                  |         |         |
|total                | 25.0 KB | 45.3 KB |
num_nans=0 / 3120 = 0.00%
num_zeros=0 / 3120 = 0.00%
num_nan_rows=13 / 3120 = 0.42%
num_nan_cols=240 / 3120 = 7.69%
...
```

## Profiling statistics

The `DAG` class saves `TXT` files with memory and time statistics for each
`bar_timestamp` and before and after each `Node` is computed. The files are
saved at `.../dag/node_io/node_io.prof`.

The file written after `Node` execution contains the timestamp when the
execution ended, the memory status, the run-time of the node and the memory
difference.

E.g.:

```bash
> cat system_log_dir/dag/node_io/node_io.prof/predict.9.process_forecasts.after_execution.20240201_052000.txt
    timestamp=20240201_102040
    memory=rss=1.163GB vms=1.621GB mem_pct=15%
    node_execution done (0.026 s)
    run_node done (1.774 s)
    run_node done: start=(1.163GB 1.621GB 15%) end=(1.163GB 1.621GB 15%) diff=(-0.000GB 0.000GB -0%)
```
