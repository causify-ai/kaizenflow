

<!-- toc -->

- [DataFlow Data Format](#dataflow-data-format)

<!-- tocstop -->

## DataFlow Data Format

As explained in
[/docs/datapull/all.datapull_client_stack.explanation.md](/docs/datapull/all.datapull_client_stack.explanation.md),
raw data from `DataPull` is stored in a "long format", where the data is
conditioned on the asset (e.g., full_symbol), e.g.,
```
                             full_symbol        open    high    low     close ...
timestamp
2021-09-01 00:00:00+00:00   binance::ADA_USDT   2.768   2.770   2.762   2.762
2021-09-01 00:00:00+00:00   binance::AVAX_USDT  39.510  39.540  39.300 39.320
2021-09-01 00:00:00+00:00   binance::ADA_USDT   2.763   2.765   2.761   2.764
```

`DataFlow` represents data through multi-index dataframes, where:

- The index is a full timestamp
- The outermost column index is the "feature"
- The innermost column index is the asset, e.g.,
```
                                                            close           high
                           binance::ADA_USDT   binance::AVAX_USDT            ...
timestamp
2021-09-01 00:00:00+00:00              2.762                39.32
2021-09-01 00:00:00+00:00              2.764                39.19
```

The reason for this convention is that typically features are computed in a
uni-variate fashion (e.g., asset by asset), and DataFlow can vectorize
computation over the assets by expressing operations in terms of the features.
E.g., we can express a feature as
```
df["close", "open"].max() - df["high"]).shift(2)
```

A user can work with DataFlow at 4 levels of abstraction:

1.  Pandas long-format (non multi-index) dataframes and for-loops
    - We can do a group-by or filter by full_symbol
    - Apply the transformation on each resulting dataframe
    - Merge the data back into a single dataframe with the long-format

2.  Pandas multiindex dataframes
    - The data is in the DataFlow native format
    - We can apply the transformation in a vectorized way
    - This approach is best for performance and with compatibility with DataFlow
      point of view
    - An alternative approach is to express multi-index transformations in terms
      of approach 1 (i.e., single asset transformations and then concatenation).
      This approach is functionally equivalent to a multi-index transformation,
      but typically slow and memory inefficient

3.  DataFlow nodes
    - A DataFlow node implements a certain transformations on DataFrames
      according to the DataFlow convention and interfaces
    - Nodes operate on the multi-index representation by typically calling
      functions from level 2 above

4.  DAG
    - A series of transformations in terms of DataFlow nodes

An example is
[/dataflow/notebooks/gallery_synthetic_data_example.ipynb](/dataflow/notebooks/gallery_synthetic_data_example.ipynb)
