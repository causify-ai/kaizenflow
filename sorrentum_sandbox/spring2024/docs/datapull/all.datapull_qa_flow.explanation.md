

<!-- toc -->

- [Data QA workflows](#data-qa-workflows)
  * [Quality-assurance metrics](#quality-assurance-metrics)
    + [Bulk data single-dataset QA metrics](#bulk-data-single-dataset-qa-metrics)
    + [Periodic QA metrics](#periodic-qa-metrics)
    + [Cross-datasets QA metrics](#cross-datasets-qa-metrics)
  * [Historical vs real-time QA flow](#historical-vs-real-time-qa-flow)
  * [Data QA workflow naming scheme](#data-qa-workflow-naming-scheme)

<!-- tocstop -->

# Data QA workflows

## Quality-assurance metrics

Each data set has QA metrics associated with it to ensure the data has the
minimum expected data quality.

- E.g., for 1-minute OHLCV data, some possible QA metrics are:
  - Missing bars for a given timestamp
  - Missing/nan OHLCV values within an individual bar
  - Data points with OHLC data and volume = 0
  - Data points where OHLCV data is not in the correct relationship
    - E.g., H and L are not higher or lower than O and C
  - Outliers data points
    - E.g., a data is more than N standard deviations from the running mean

The code for the QA flow is independent of bulk (i.e., historical) and periodic
(i.e., real-time) data.

### Bulk data single-dataset QA metrics

It is possible to run the QA flow to compute the quality of the historical data.
This is done typically as a one-off operation right after the historical data is
downloaded in bulk. This touches only one dataset, namely the one that was just
downloaded.

### Periodic QA metrics

Every N minutes of downloading real-time data, the QA flow is run to generate
statistics about the quality of the data. In case of low data quality data the
system sends a notification.

### Cross-datasets QA metrics

There are QA workflows that compare different data sets that are related to each
other, e.g.:

- Consider the case of downloading the same data (e.g., 1-minute OHLCV for spot
  `BTC_USDT` from Binance exchange) from different providers (e.g., Binance
  directly and a third-party provider).

- Consider the case where there is a REST API that allows to get data for a
  period of data and a websocket that streams the data

- Consider the case where one gets an historical dump of the data from a third
  party provider vs the data from the exchange real-time stream

- Consider the case of NASDAQ streaming data vs TAQ data disseminated once the
  market is close

## Historical vs real-time QA flow

Every period $T_{dl,hist}$, a QA flow is run where the real-time data is
compared to the historical data to ensure that the historical view of the data
matches the real-time one.

This is necessary but not sufficient to guarantee that the bulk historical data
can be reliably used as a proxy for the real-time data as-of, in fact this is
simply a self-consistency check. We do not have any guarantee that the data
source collected correctly historical data.

## Data QA workflow naming scheme

A QA workflow has a name that represents its characteristics in the format:
```
{qa_type}.{dataset_signature}
```

i.e.,

```markdown
production_qa.{download_mode}.{downloading_entity}.{action_tag}.{data_format}.{data_type}.{asset_type}.{universe}.{vendor}.{exchange}.{version\[-snapshot\]}.{asset}.{extension}
```

where:

- `qa_type`: the type of the QA flow, e.g.,
  - `production_qa`: perform a QA flow on historical and real-time data. The
    interface should be an IM client, which makes it possible to run QA on both
    historical and real-time data
  - `research_analysis`: perform a free-form analysis of the data. This can then
    be the basis for a `qa` analysis
  - `compare_historical_real_time`: compare historical and real-time data coming
    from the same source of data
  - `compare_historical_cross_comparison`: compare historical data from two
    different data sources The same rules apply as in downloader and derived
    dataset for the naming scheme.
```
research_cross_comparison.periodic.airflow.downloaded_1sec_1min.all.bid_ask.futures.all.ccxt_cryptochassis.all.v1_0_0
```

Since cross-comparison involves two (or more dataset) we use a short notation
merging the attributes that differ.

E.g., a comparison between the datasets

- `periodic.1minute.postgres.ohlcv.futures.1minute.ccxt.binance`
- `periodic.1day.postgres.ohlcv.futures.1minute.ccxt.binance`

is called:

```markdown
compare_qa.periodic.1minute-1day.postgres.ohlcv.futures.1minute.ccxt.binance
```

since the only difference is in the frequency of the data sampling.

It is possible to use a long format
`{dataset_signature1}-vs-{dataset_signature2}`.

E.g.,

```markdown
| Name                  | Dataset Signature                | Description                                                          | Frequency                 | Dashboard | Data Location | Active? |
| --------------------- | -------------------------------- | -------------------------------------------------------------------- | ------------------------- | --------- | ------------- | ------- |
| hist_dl1              | Historical download              | - All of the past day data<br>- Once a day at 0:00:00 UTC            | -                         | s3://...  | Yes           |
| rt_dl1                | Real-time download               | - Every minute                                                       | -                         | s3://...  | Yes           |
| rt_dl1.qa1            | Real-time QA check               | Check QA metrics for dl1                                             | Every 5 minutes           | -         | s3://...      | Yes     |
| hist_dl1.rt_dl1.check | Check of historical vs real-time | Check consistency between historical and real-time CCXT binance data | Once a day at 0:15:00 UTC | -         | -             | -       |
| rt_dl2                | Real-time download               | - vendor=CryptoChassis<br>- exchange=Binance<br>- data type=bid/ask  | Every minute              | -         | s3://...      | Yes     |
| rt_dl2.qa2            | Real-time QA check               | Check QA metrics for dl3                                             | Every 5 minutes           | -         | s3://...      | Yes     |
| rt_dl1_dl2.check      | Cross-data QA check              | Compare data from rt_dl1 and rt_dl2                                  | Every 5 minutes           | -         | -             | -       |
```
