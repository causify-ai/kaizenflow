#!/usr/bin/env python
"""
Load and validate historical data from a PostgreSQL table,
perform ML predictions and load back the result into PostgreSQL.

> load_validate_transform.py \
    --topic 'washing machine' \
    --source_table 'google_trends_data' \
    --target_table 'google_trends_predictions'
"""
import argparse

import dask.dataframe as dd
from pmdarima.arima import auto_arima
from statsmodels.tsa.stattools import adfuller as ADF
import matplotlib.pyplot as plt

import pandas as pd

import common.validate as sinsaval
import src.db as sisebidb
import src.validate as sisebiva


# #############################################################################
# Data processing.
# #############################################################################


def preprocess(data):
    # Change the date(str) to datetime using Dask's to_datetime function
    data['Date'] = dd.to_datetime(data['Time'], format='%b %Y')

    # Change the index into datetime using set_index method
    data = data.set_index('Date')
    frequencies = data[['Frequency']]

    return frequencies


def draw_ADF(df):
    # Calculate the first and second differences of the 'Frequency' column and add them to the dataframe
    df['diff_1'] = df['Frequency'].diff(1)
    df['diff_2'] = df['diff_1'].diff(1)

    # Replace missing values in the differences with 0
    df['diff_1'] = df['diff_1'].fillna(0)
    df['diff_2'] = df['diff_2'].fillna(0)

    # Calculate the Augmented Dickey-Fuller (ADF) test statistics for the 'Frequency' column and its differences
    adf = ADF(df['Frequency'].to_dask_array(lengths=True))
    diff1_adf = ADF(df['diff_1'].to_dask_array(lengths=True))
    diff2_adf = ADF(df['diff_2'].to_dask_array(lengths=True))

    # Print the ADF test statistics for the 'Frequency' column and its differences
    print('timeseries adf:', adf)
    print('timeseries diff_1 adf:', diff1_adf)
    print('timeseries diff_2 adf:', diff2_adf)

    # Plot the dataframe as subplots
    df.compute().plot(subplots=True, figsize=(15, 12))

    # Remove the 'diff_1' and 'diff_2' columns from the dataframe
    df = df.drop(labels=['diff_2'], axis=1)
    df = df.drop(labels=['diff_1'], axis=1)

    # Return the dataframe without the 'diff_1' and 'diff_2' columns
    return df


def apply_ARIMA(data, start, end, date_range):
    # Set the training data to the input 'data'
    train = data

    # Fit an ARIMA model to the training data using the auto_arima function
    arima_model = auto_arima(train, start_p=0, d=1, start_q=0,
                             max_p=5, max_d=5, max_q=5, start_P=0,
                             D=1, start_Q=0, max_P=5, max_D=5,
                             max_Q=5, m=12, seasonal=True,
                             error_action='warn', trace=True,
                             supress_warnings=True, stepwise=True,
                             random_state=20, n_fits=50)

    # Generate predictions for the specified time range using the fitted ARIMA model
    predictions = pd.DataFrame(arima_model.predict(start=start, end=end, n_periods=12), index=date_range)
    predictions.columns = ["Frequencies"]

    # Return the predicted frequencies as a dataframe
    return predictions


def predict_data(data: pd.DataFrame, topic: str) -> pd.DataFrame:
    # Convert the input data to a Dask dataframe with 10 partitions
    data = dd.from_pandas(data, npartitions=10)
    print("\nStep 1: Converting to Dask Dataframe, Done")

    # Preprocess the data
    processed_data = preprocess(data)
    print("Step 2: Preprocessing before prediction, Done")

    # Define the start and end dates for the prediction period
    start = processed_data.compute().index[-1] + pd.offsets.MonthBegin(1)
    end = pd.Timestamp(processed_data.compute().index.values[-1]) + pd.offsets.MonthBegin(12)
    date_range = pd.date_range(start=start, end=end, freq="MS")

    # if one wants to see the diffs.
    # apply_ARIMA(data, start, end, date_range)

    # Generate predictions for the specified time range using the apply_ARIMA function
    predictions = apply_ARIMA(processed_data.compute(), start, end, date_range)
    print("Step 4: Predicting best fit using AIRMA models, Done")

    # Reformat the predicted frequencies as a dataframe
    predictions = pd.DataFrame({
        "Topic": [topic] * 12,
        "Time": predictions.index.tolist(),
        "Record Type": ["predictions"] * 12,
        "Frequency": predictions["Frequencies"].tolist()
    })
    print("Step 5: Reformatting predictions according to DB requirements, Done")

    # Reformat the input data according to DB requirements
    data = data.drop('Time', axis=1)
    data = pd.DataFrame(data.compute())
    data["Record Type"] = ["data"] * len(data)
    data = data.rename(columns={'Date': 'Time'})
    data = data.reindex(columns=['Topic', 'Time', 'Record Type', 'Frequency'])
    print("Step 6: Reformatting historical data according to DB requirements, Done")

    # Concatenate the historical data with the predictions
    resampled_df = pd.concat([data, predictions])
    resampled_df = resampled_df.reset_index(drop=True)
    print("Step 7: Concatinating historical data with predictions, Done")

    # Convert the resulting dataframe back to a Dask dataframe with 10 partitions and convert the 'Frequency' column to integers
    resampled_df = dd.from_pandas(resampled_df, npartitions=10)
    resampled_df['Frequency'] = resampled_df['Frequency'].astype(int)
    print("Step 8: converting frequencies to 'int', Done")

    # Compute and return the resulting dataframe
    return resampled_df.compute()


def plot_figure(resampled_df: pd.DataFrame) -> None:
    # fetching historical and predicted data from resampled data
    historical_data = resampled_df[resampled_df["Record Type"] == 'data']
    predicted_data = resampled_df[resampled_df["Record Type"] == 'predictions']

    # setting the figure size
    fig = plt.figure(figsize=(20, 5))

    # plot historical data
    plt.plot(historical_data.Time, historical_data.Frequency)
    plt.scatter(historical_data.Time, historical_data.Frequency, c="Orange", s=12)

    # plot predicted data
    plt.plot(predicted_data.Time, predicted_data.Frequency, c="Red")
    plt.scatter(predicted_data.Time, predicted_data.Frequency, c="Green", s=12)

    plt.show()

# #############################################################################
# Script.
# #############################################################################


def _add_load_args(
        parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """
    Add the command line options for exchange download.
    """
    parser.add_argument(
        "--topic",
        required=True,
        action="store",
        type=str,
        help="topic to predict",
    )
    parser.add_argument(
        "--source_table",
        action="store",
        required=True,
        type=str,
        help="DB table to load data from",
    )
    parser.add_argument(
        "--target_table",
        action="store",
        required=True,
        type=str,
        help="DB table to save transformed data into",
    )
    return parser


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = _add_load_args(parser)
    # parser = hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    target_table = args.target_table
    topic = args.topic.replace("_", " ").lower()

    # 1) Load data.
    db_conn = sisebidb.get_db_connection()
    db_client = sisebidb.PostgresClient(db_conn)

    data = db_client.load(
        dataset_signature=args.source_table,
        topic=topic
    )
    data.rename(columns={'topic': 'Topic', 'date_stamp': 'Time', 'frequency': 'Frequency'}, inplace=True)
    print("Data fetched from 'google_trends_data' table:")
    print(data, "\n")

    # 2) QA
    denormalized_dataset_check = sisebiva.DenormalizedDatasetCheck()
    dataset_validator = sinsaval.SingleDatasetValidator(
        [denormalized_dataset_check]
    )
    dataset_validator.run_all_checks([data])

    # 3) Transform data.
    resampled_data = predict_data(data, topic)

    # 4) Save back to DB.
    db_saver = sisebidb.PostgresDataFrameSaver(db_conn)
    db_saver.save(resampled_data, target_table, topic)

    # 5) plotting
    # plot_figure(resampled_data)


if __name__ == "__main__":
    _main(_parse())
