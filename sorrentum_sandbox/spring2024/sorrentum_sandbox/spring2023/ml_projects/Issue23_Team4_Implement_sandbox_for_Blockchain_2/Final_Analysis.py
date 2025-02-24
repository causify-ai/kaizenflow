from Data_Access import get_data
import psycopg2
import pandas as pd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
# import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta,timezone
import dask.dataframe as dd
# from Dask import create_full_dask_df

import hvplot.pandas  # noqa
# import sorrentum_sandbox.common.download as ssandown
import hvplot



import dask.dataframe as dd
import pandas as pd
datasets = [
"Real_Time_Difficulty",
"Historical_Difficulty",
"Real_Time_Market_Cap",
"Historical_Market_Cap",
"Real_Time_Trade_Volume",
"Historical_Trade_Volume",
"Historical_Market_Price",
"Real_Time_Market_Price",
]


def create_full_dask_df(datasets):
# store all the dataframes into dask dataframes
    dask_dfs = []
    for dataset in datasets:
        pandas_df = get_data(dataset)
        dask_df = dd.from_pandas(pandas_df, npartitions=1)
        dask_df = dask_df.reset_index().set_index('index')
        dask_dfs.append(dask_df)

    full_dask_df = dd.concat(dask_dfs, axis=0)
    return full_dask_df

full_dask_df=create_full_dask_df(datasets)

# Access the Dask DataFrames using the partition indices
histDiff = full_dask_df.partitions[0]
realDiff = full_dask_df.partitions[1]
histCap = full_dask_df.partitions[2]
realCap = full_dask_df.partitions[3]
histVolume = full_dask_df.partitions[4]
realVolume = full_dask_df.partitions[5]
histPrice = full_dask_df.partitions[6]
realPrice = full_dask_df.partitions[7]




#Converts Unix timestamp to 'YYYY-MM-DD' DateTime format
histDiff['timestamp'] = dd.to_datetime(histDiff.timestamp, unit='s')

realDiff['timestamp'] = dd.to_datetime(realDiff.timestamp, unit='s')

#Display length of DASK Dataframe

#Converts Unix timestamp to 'YYYY-MM-DD' DateTime format
histCap['timestamp'] = dd.to_datetime(histCap.timestamp, unit='s')


realCap['timestamp'] = dd.to_datetime(realCap.timestamp, unit='s')



#Converts Unix timestamp to 'YYYY-MM-DD' DateTime format
histPrice['timestamp'] = dd.to_datetime(histPrice.timestamp, unit='s')

realPrice['timestamp'] = dd.to_datetime(realPrice.timestamp, unit='s')

#Converts Unix timestamp to 'YYYY-MM-DD' DateTime format
histVolume['timestamp'] = dd.to_datetime(histVolume.timestamp, unit='s')

realVolume['timestamp'] = dd.to_datetime(realVolume.timestamp, unit='s')



histDiffPano = histDiff.copy()
#Compute the mean value of each day's transactions and assign it to a DASK Dataframe
histDiffPano = histDiffPano.set_index('timestamp').resample('D').mean().compute()
#Plot a line graph of the values in the DASK Dataframe
fig = go.Figure()
fig.add_trace(go.Scatter(x=histDiffPano.index, y=histDiffPano['values'],name='Full history BTC Difficulty'))
fig.update_layout(showlegend=True,title="BTC Historical Difficulty",xaxis_title="Time",yaxis_title="Difficulty",font=dict(family="Courier New, monospace"))
fig.show()

histCapPano = histCap.copy()
#Compute the mean value of each day's transactions and assign it to a DASK Dataframe
histCapPano = histCapPano.set_index('timestamp').resample('D').mean().compute()
#Plot a line graph of the values in the DASK Dataframe
fig = go.Figure()
fig.add_trace(go.Scatter(x=histCapPano.index, y=histCapPano['values'],name='Full history BTC Markey Cap'))
fig.update_layout(showlegend=True,title="BTC Historical Market Cap",xaxis_title="Time",yaxis_title="USD",font=dict(family="Courier New, monospace"))
fig.show()

histPricePano = histPrice.copy()
#Compute the mean value of each day's transactions and assign it to a DASK Dataframe
histPricePano = histPricePano.set_index('timestamp').resample('D').mean().compute()
#Plot a line graph of the values in the DASK Dataframe
fig = go.Figure()
fig.add_trace(go.Scatter(x=histPricePano.index, y=histPricePano['values'],name='Full history BTC Market Price'))
fig.update_layout(showlegend=True,title="BTC Historical Market Price",xaxis_title="Time",yaxis_title="USD",font=dict(family="Courier New, monospace"))
fig.show()

histVolumePano = histVolume.copy()
#Compute the mean value of each day's transactions and assign it to a DASK Dataframe
histVolumePano = histVolumePano.set_index('timestamp').resample('D').mean().compute()
#Plot a line graph of the values in the DASK Dataframe
fig = go.Figure()
fig.add_trace(go.Scatter(x=histVolumePano.index, y=histVolumePano['values'],name='Full history BTC Trade Volume'))
fig.update_layout(showlegend=True,title="BTC Historical Trade Volume",xaxis_title="Time",yaxis_title="USD",font=dict(family="Courier New, monospace"))
fig.show()


realDiffPano = realDiff.copy()
#Compute the mean value of each day's transactions and assign it to a DASK Dataframe
realDiffPano = realDiffPano.set_index('timestamp').resample('D').mean().compute()
#Plot a line graph of the values in the DASK Dataframe
fig = go.Figure()
fig.add_trace(go.Scatter(x=realDiffPano.index, y=realDiffPano['values'],name='Full Real-Time BTC Difficulty'))
fig.update_layout(showlegend=True,title="BTC Real-Time Difficulty",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

realCapPano = realCap.copy()
#Compute the mean value of each day's transactions and assign it to a DASK Dataframe
realCapPano = realCapPano.set_index('timestamp').resample('D').mean().compute()
#Plot a line graph of the values in the DASK Dataframe
fig = go.Figure()
fig.add_trace(go.Scatter(x=realCapPano.index, y=realCapPano['values'],name='Full Real-Time BTC Market Cap'))
fig.update_layout(showlegend=True,title="BTC Real-Time Market Cap",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

realPricePano = realPrice.copy()
#Compute the mean value of each day's transactions and assign it to a DASK Dataframe
realPricePano = realPricePano.set_index('timestamp').resample('D').mean().compute()
#Plot a line graph of the values in the DASK Dataframe
fig = go.Figure()
fig.add_trace(go.Scatter(x=realPricePano.index, y=realPricePano['values'],name='Full Real-Time BTC Market Price'))
fig.update_layout(showlegend=True,title="BTC Real-Time Market Price",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

realVolumePano = realVolume.copy()
#Compute the mean value of each day's transactions and assign it to a DASK Dataframe
realVolumePano = realVolumePano.set_index('timestamp').resample('D').mean().compute()
#Plot a line graph of the values in the DASK Dataframe
fig = go.Figure()
fig.add_trace(go.Scatter(x=realVolumePano.index, y=realVolumePano['values'],name='Full Real-Time BTC Trade Volume'))
fig.update_layout(showlegend=True,title="BTC Real-Time Trade Volume",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()


# Preparing data to be passed to the Historical BTC Network Difficulty model
histDiffOutliers = histDiffPano.copy()
histDiffOutliers.fillna(method ='bfill', inplace = True)

# Training the Historical model
histDiff_isolation_detector = IsolationForest(n_estimators=150,random_state=0,contamination='auto')
histDiff_isolation_detector.fit(histDiffOutliers['values'].values.reshape(-1, 1))


# Preparing data to be passed to the Historical BTC Market Cap model
histCapOutliers = histCapPano.copy()
histCapOutliers.fillna(method ='bfill', inplace = True)

# Training the Historical model
histCap_isolation_detector = IsolationForest(n_estimators=150,random_state=0,contamination='auto')
histCap_isolation_detector.fit(histCapOutliers['values'].values.reshape(-1, 1))


# Preparing data to be passed to the Historical BTC Market Price model
histPriceOutliers = histPricePano.copy()
histPriceOutliers.fillna(method ='bfill', inplace = True)

# Training the Historical model
histPrice_isolation_detector = IsolationForest(n_estimators=150,random_state=0,contamination='auto')
histPrice_isolation_detector.fit(histPriceOutliers['values'].values.reshape(-1, 1))


# Preparing data to be passed to the Historical BTC Trade Volume model
histVolumeOutliers = histVolumePano.copy()
histVolumeOutliers.fillna(method ='bfill', inplace = True)

# Training the Historical model
histVolume_isolation_detector = IsolationForest(n_estimators=150,random_state=0,contamination='auto')
histVolume_isolation_detector.fit(histVolumeOutliers['values'].values.reshape(-1, 1))


# Preparing data to be passed to the Real-Time BTC Network Difficulty model
realDiffOutliers = realDiffPano.copy()
realDiffOutliers.fillna(method ='bfill', inplace = True)

# Training the Real-Time model
realDiff_isolation_detector = IsolationForest(n_estimators=150,random_state=0,contamination='auto')
realDiff_isolation_detector.fit(realDiffOutliers['values'].values.reshape(-1, 1))


# Preparing data to be passed to the Real-Time BTC Market Cap model
realCapOutliers = realCapPano.copy()
realCapOutliers.fillna(method ='bfill', inplace = True)

# Training the Real-Time model
realCap_isolation_detector = IsolationForest(n_estimators=150,random_state=0,contamination='auto')
realCap_isolation_detector.fit(realCapOutliers['values'].values.reshape(-1, 1))


# Preparing data to be passed to the Real-Time BTC Market Price model
realPriceOutliers = realPricePano.copy()
realPriceOutliers.fillna(method ='bfill', inplace = True)

# Training the Real-Time model
realPrice_isolation_detector = IsolationForest(n_estimators=150,random_state=0,contamination='auto')
realPrice_isolation_detector.fit(realPriceOutliers['values'].values.reshape(-1, 1))


# Preparing data to be passed to the Real-Time BTC Trade Volume model
realVolumeOutliers = realVolumePano.copy()
realVolumeOutliers.fillna(method ='bfill', inplace = True)

# Training the Real-Time model
realVolume_isolation_detector = IsolationForest(n_estimators=150,random_state=0,contamination='auto')
realVolume_isolation_detector.fit(realVolumeOutliers['values'].values.reshape(-1, 1))

#Arrange the data of Historical BTC Network Difficulty and predicts the anomalies
histDiff_data_ready = np.linspace(histDiffOutliers['values'].min(), histDiffOutliers['values'].max(), len(histDiffOutliers)).reshape(-1,1)
histDiffOutlier = histDiff_isolation_detector.predict(histDiff_data_ready)

#Arrange the data of Historical BTC Market Cap and predicts the anomalies
histCap_data_ready = np.linspace(histCapOutliers['values'].min(), histCapOutliers['values'].max(), len(histCapOutliers)).reshape(-1,1)
histCapOutlier = histCap_isolation_detector.predict(histCap_data_ready)

#Arrange the data of Historical BTC Market Price and predicts the anomalies
histPrice_data_ready = np.linspace(histPriceOutliers['values'].min(), histPriceOutliers['values'].max(), len(histPriceOutliers)).reshape(-1,1)
histPriceOutlier = histPrice_isolation_detector.predict(histPrice_data_ready)

#Arrange the data of Historical BTC Trade Volume and predicts the anomalies
histVolume_data_ready = np.linspace(histVolumeOutliers['values'].min(), histVolumeOutliers['values'].max(), len(histVolumeOutliers)).reshape(-1,1)
histVolumeOutlier = histVolume_isolation_detector.predict(histVolume_data_ready)

#Arrange the data of Real-Time BTC Network Difficulty and predicts the anomalies
realDiff_data_ready = np.linspace(realDiffOutliers['values'].min(), realDiffOutliers['values'].max(), len(realDiffOutliers)).reshape(-1,1)
realDiffOutlier = realDiff_isolation_detector.predict(realDiff_data_ready)

#Arrange the data of Real-Time BTC Market Cap and predicts the anomalies
realCap_data_ready = np.linspace(realCapOutliers['values'].min(), realCapOutliers['values'].max(), len(realCapOutliers)).reshape(-1,1)
realCapOutlier = realCap_isolation_detector.predict(realCap_data_ready)

#Arrange the data of Real-Time BTC Market Price and predicts the anomalies
realPrice_data_ready = np.linspace(realPriceOutliers['values'].min(), realPriceOutliers['values'].max(), len(realPriceOutliers)).reshape(-1,1)
realPriceOutlier = realPrice_isolation_detector.predict(realPrice_data_ready)

#Arrange the data of Real-Time BTC Trade Volume Difficulty and predicts the anomalies
realVolume_data_ready = np.linspace(realVolumeOutliers['values'].min(), realVolumeOutliers['values'].max(), len(realVolumeOutliers)).reshape(-1,1)
realVolumeOutlier = realVolume_isolation_detector.predict(realVolume_data_ready)

#Display the heads of Historical DASK Dataframes
    #In 'Outlier' column, -1 means not outlier, 1 means is outlier

histDiffOutliers['outlier'] = histDiffOutlier


histCapOutliers['outlier'] = histCapOutlier



histPriceOutliers['outlier'] = histPriceOutlier



histVolumeOutliers['outlier'] = histVolumeOutlier




#Display the heads of Real-Time DASK Dataframes
    #In 'Outlier' column, -1 means not outlier, 1 means is outlier
realDiffOutliers['outlier'] = realDiffOutlier


realCapOutliers['outlier'] = realCapOutlier


realPriceOutliers['outlier'] = realPriceOutlier

realVolumeOutliers['outlier'] = realVolumeOutlier


a = histDiffOutliers.loc[histDiffOutliers['outlier'] == 1] #anomaly
#Plot line graph of the anomolies over the line graph of Historical BTC Network Difficulty
fig = go.Figure()
fig.add_trace(go.Scatter(x=histDiffOutliers['values'].index, y=histDiffOutliers['values'].values,mode='lines',name='BTC Difficulty'))
fig.add_trace(go.Scatter(x=a.index, y=a['values'].values,mode='markers',name='Anomaly',marker_symbol='x',marker_size=2))
fig.update_layout(showlegend=True,title="BTC Historical Difficulty Anomalies - IsolationForest",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

a = histCapOutliers.loc[histCapOutliers['outlier'] == 1] #anomaly
#Plot line graph of the anomolies over the line graph of Historical BTC Market Cap
fig = go.Figure()
fig.add_trace(go.Scatter(x=histCapOutliers['values'].index, y=histCapOutliers['values'].values,mode='lines',name='BTC Market Cap'))
fig.add_trace(go.Scatter(x=a.index, y=a['values'].values,mode='markers',name='Anomaly',marker_symbol='x',marker_size=2))
fig.update_layout(showlegend=True,title="BTC Historical Market Cap Anomalies - IsolationForest",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

a = histPriceOutliers.loc[histPriceOutliers['outlier'] == 1] #anomaly
#Plot line graph of the anomolies over the line graph of Historical BTC Market Price
fig = go.Figure()
fig.add_trace(go.Scatter(x=histPriceOutliers['values'].index, y=histPriceOutliers['values'].values,mode='lines',name='BTC Market Price'))
fig.add_trace(go.Scatter(x=a.index, y=a['values'].values,mode='markers',name='Anomaly',marker_symbol='x',marker_size=2))
fig.update_layout(showlegend=True,title="BTC Historical Market Price Anomalies - IsolationForest",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

a = histVolumeOutliers.loc[histVolumeOutliers['outlier'] == 1] #anomaly
#Plot line graph of the anomolies over the line graph of Historical BTC Trade Volume
fig = go.Figure()
fig.add_trace(go.Scatter(x=histVolumeOutliers['values'].index, y=histVolumeOutliers['values'].values,mode='lines',name='BTC Trade Volume'))
fig.add_trace(go.Scatter(x=a.index, y=a['values'].values,mode='markers',name='Anomaly',marker_symbol='x',marker_size=2))
fig.update_layout(showlegend=True,title="BTC Historical Trade Volume Anomalies - IsolationForest",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()


a = realDiffOutliers.loc[realDiffOutliers['outlier'] == 1] #anomaly
#Plot line graph of the anomolies over the line graph of Historical BTC Network Difficulty
fig = go.Figure()
fig.add_trace(go.Scatter(x=realDiffOutliers['values'].index, y=realDiffOutliers['values'].values,mode='lines',name='BTC Difficulty'))
fig.add_trace(go.Scatter(x=a.index, y=a['values'].values,mode='markers',name='Anomaly',marker_symbol='x',marker_size=2))
fig.update_layout(showlegend=True,title="BTC Real-Time Difficulty Anomalies - IsolationForest",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

a = realCapOutliers.loc[realCapOutliers['outlier'] == 1] #anomaly
#Plot line graph of the anomolies over the line graph of Historical BTC Market Cap
fig = go.Figure()
fig.add_trace(go.Scatter(x=realCapOutliers['values'].index, y=realCapOutliers['values'].values,mode='lines',name='BTC Market Cap'))
fig.add_trace(go.Scatter(x=a.index, y=a['values'].values,mode='markers',name='Anomaly',marker_symbol='x',marker_size=2))
fig.update_layout(showlegend=True,title="BTC Real-Time Market Cap Anomalies - IsolationForest",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

a = realPriceOutliers.loc[realPriceOutliers['outlier'] == 1] #anomaly
#Plot line graph of the anomolies over the line graph of Historical BTC Market Price
fig = go.Figure()
fig.add_trace(go.Scatter(x=realPriceOutliers['values'].index, y=realPriceOutliers['values'].values,mode='lines',name='BTC Market Price'))
fig.add_trace(go.Scatter(x=a.index, y=a['values'].values,mode='markers',name='Anomaly',marker_symbol='x',marker_size=2))
fig.update_layout(showlegend=True,title="BTC Real-Time Market Price Anomalies - IsolationForest",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()

a = realVolumeOutliers.loc[realVolumeOutliers['outlier'] == 1] #anomaly
#Plot line graph of the anomolies over the line graph of Historical BTC Trade Volume
fig = go.Figure()
fig.add_trace(go.Scatter(x=realVolumeOutliers['values'].index, y=realVolumeOutliers['values'].values,mode='lines',name='BTC Trade Volume'))
fig.add_trace(go.Scatter(x=a.index, y=a['values'].values,mode='markers',name='Anomaly',marker_symbol='x',marker_size=2))
fig.update_layout(showlegend=True,title="BTC Real-Time Trade Volume Anomalies - IsolationForest",xaxis_title="Time",yaxis_title="Prices",font=dict(family="Courier New, monospace"))
fig.show()


#Compute the mean value of each yeas's transactions and assign it to a DASK Dataframe
print('Historical BTC Network Difficulty')
histDiffDatacheck = histDiff.groupby([histDiff['timestamp'].dt.year])['values'].mean()
print(histDiffDatacheck.head())
print('------------------------------------')

#Compute the mean value of each yeas's transactions and assign it to a DASK Dataframe
print('Historical BTC Market Cap')
histCapDatacheck = histCap.groupby([histCap['timestamp'].dt.year])['values'].mean()
print(histCapDatacheck.head())
print('------------------------------------')

#Compute the mean value of each yeas's transactions and assign it to a DASK Dataframe
print('Historical BTC Market Price')
histPriceDatacheck = histPrice.groupby([histPrice['timestamp'].dt.year])['values'].mean()
print(histPriceDatacheck.head())
print('------------------------------------')

#Compute the mean value of each yeas's transactions and assign it to a DASK Dataframe
print('Historical BTC Trade Volume')
histVolumeDatacheck = histVolume.groupby([histVolume['timestamp'].dt.year])['values'].mean()
print(histVolumeDatacheck.head())
print('------------------------------------')


#Compute the mean value of each yeas's transactions and assign it to a DASK Dataframe
print('Real-Time BTC Network Difficulty')
realDiffDatacheck = realDiff.groupby([realDiff['timestamp'].dt.year])['values'].mean()
print(realDiffDatacheck.head())
print('------------------------------------')

#Compute the mean value of each yeas's transactions and assign it to a DASK Dataframe
print('Real-Time BTC Market Cap')
realCapDatacheck = realCap.groupby([realCap['timestamp'].dt.year])['values'].mean()
print(realCapDatacheck.head())
print('------------------------------------')

#Compute the mean value of each yeas's transactions and assign it to a DASK Dataframe
print('Real-Time BTC Market Price')
realPriceDatacheck = realPrice.groupby([realPrice['timestamp'].dt.year])['values'].mean()
print(realPriceDatacheck.head())
print('------------------------------------')

#Compute the mean value of each yeas's transactions and assign it to a DASK Dataframe
print('Real-Time BTC Trade Volume')
realVolumeDatacheck = realVolume.groupby([realVolume['timestamp'].dt.year])['values'].mean()
print(realVolumeDatacheck.head())
print('------------------------------------')


#Plot bar graph of the mean for each year in the Historical BTC Network Difficulty DASK Dataframe
histDiffDatacheck.hvplot.bar(x='timestamp', y='values', rot=45)


#Plot bar graph of the mean for each year in the Historical BTC Market Cap DASK Dataframe
histCapDatacheck.hvplot.bar(x='timestamp', y='values', rot=45)

#Plot bar graph of the mean for each year in the Historical BTC Market Price DASK Dataframe
histPriceDatacheck.hvplot.bar(x='timestamp', y='values', rot=45)

#Plot bar graph of the mean for each year in the Historical BTC Trade Volume DASK Dataframe
histVolumeDatacheck.hvplot.bar(x='timestamp', y='values', rot=45)

#Plot bar graph of the mean for each year in the Real-time BTC Network Difficulty DASK Dataframe
realDiffDatacheck.hvplot.bar(x='timestamp', y='values', rot=45)
#Plot bar graph of the mean for each year in the Real-time BTC Market Cap DASK Dataframe
realCapDatacheck.hvplot.bar(x='timestamp', y='values', rot=45)

#Plot bar graph of the mean for each year in the Real-time BTC Market Price DASK Dataframe
realPriceDatacheck.hvplot.bar(x='timestamp', y='values', rot=45)

#Plot bar graph of the mean for each year in the Real-time BTC Trade Volume DASK Dataframe
realVolumeDatacheck.hvplot.bar(x='timestamp', y='values', rot=45)


