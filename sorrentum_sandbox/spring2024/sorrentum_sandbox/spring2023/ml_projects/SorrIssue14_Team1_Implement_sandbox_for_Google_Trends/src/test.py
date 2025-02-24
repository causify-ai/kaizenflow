import pandas as pd
import dask.dataframe as dd
from pmdarima.arima import auto_arima
from statsmodels.tsa.stattools import adfuller as ADF
import matplotlib.pyplot as plt


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


def predict_data(data, topic):
    # Convert the input data to a Dask dataframe with 10 partitions
    data = dd.from_pandas(data, npartitions=10)
    print("Step 1: Converting to Dask Dataframe, Done")

    # Preprocess the data
    processed_data = preprocess(data)
    print("Step 2: Preprocessing before prediction, Done")

    # Define the start and end dates for the prediction period
    start = processed_data.compute().index[-1] + pd.offsets.MonthBegin(1)
    end = processed_data.compute().index.values[-1] + pd.offsets.MonthBegin(12)
    date_range = pd.date_range(start=start, end=end, freq="MS")

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


if __name__ == '__main__':
    df = pd.read_csv("../files/ipad.csv")
    # fetching data from json as a dataframe
    resampled_df = predict_data(df, topic="ipads")

    historical_data = resampled_df[resampled_df["Record Type"] == 'data']
    predicted_data = resampled_df[resampled_df["Record Type"] == 'predictions']

    fig = plt.figure(figsize=(20, 5))

    plt.plot(historical_data.Time, historical_data.Frequency)
    plt.scatter(historical_data.Time, historical_data.Frequency, c="Orange", s=12)

    plt.plot(predicted_data.Time, predicted_data.Frequency, c="Red")
    plt.scatter(predicted_data.Time, predicted_data.Frequency, c="Green", s=12)

    plt.show()