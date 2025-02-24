## Derived data workflows

**Derived data workflows**. Data workflows can transform datasets into other
datasets

- E.g., resample 1 second data into 1 minute data

The data is then written back to the same data source as the originating data
(e.g., DB for period / real-time data, Parquet / csv / S3 for historical data).

TODO(gp): Add a plot (we are the source of the provider)

**Derived data naming scheme**. We use the same naming scheme as in downloaded
data set {dataset_signature}

but we encode the information about the content of the newly generated data in
the `action_tag` attribute of the data, e.g., `resample_1min` to distinguish it
from `downloaded_1sec`.

We use this approach so that the scheme of the derived data is the same as a
downloaded data set.

**Derived data research flow.** The goal is to decide how to transform the raw
data into derived data and come up with QA metrics to assess the quality of the
transformation

- It can be cross-vendor or not

- E.g., sample 1sec data to 1min and compare to a reference. The sampling is
  done on the fly since the researcher is trying to understand how to resample
  (e.g., removing outliers) to get a match

**Derived data production flow.** The research flow is frozen and put in
production

- E.g., run the resample script to sample and write back to DB and historical
  data. This flow can be run in historical mode (to populate the backend with
  the production data) and in real-time mode (to compute the streaming data)

**Derived data QA flow**. the goal is to monitor that the production flow is
still performing properly with respect to the QA metrics

- E.g., the 1-sec to 1-min resampling is not performed on-the-fly, but it uses
  the data already computed by the script in the production flow.

- This flow is mainly run in real-time, but we might want to look at QA
  performance also historically

This same distinction can also be applied to feature computation and to the
machine learning flow.

Provider -> data -> Us -> derived flow -> Us -> features -> Us -> ML -> Exchange
