"""
Import as:

import sorrentum_sandbox.examples.ml_projects.Issue24_Team5_Implement_sandbox_for_Alpha_Vantage.models.ticker as ssempitisfavmt
"""

from typing import List

import dask.dataframe as dd
import pandas as pd
from api.alpha_vantage import AlphaVantage
from dask.distributed import Client

from models.time_series import DataType, TimeInterval, TimeSeriesData

_ = Client("scheduler:8786")


class Ticker:
    def __init__(
        self,
        ticker: str,
        get_name: bool = False,
        time_series_data: List[TimeSeriesData] = None,
        **kwargs,
    ) -> None:
        self.ticker = ticker
        self.name = kwargs.pop('name', ticker)
        if get_name and (self.ticker == self.name):
            self.name = AlphaVantage.get_name_for(ticker)

        self.last_updated = None
        self.last_open = None
        self.last_close = None

        self.time_series_data = time_series_data
        if self.time_series_data:
            last = self.time_series_data[0]

            self.last_updated = last.date
            self.last_open = last.open
            self.last_close = last.close

        kwargs.pop('_id', None)
        if kwargs:
            for k, v in kwargs.items():
                self.__setattr__(k, v)

        

    def __repr__(self) -> str:
        return f"""
        Name: {self.name} | {self.ticker}
        Last Updated: {self.last_updated}
        Last Open: {self.last_open}
        Last Close: {self.last_close}
        Datapoints: {len(self.time_series_data) if self.time_series_data else "No Data"}
        """

    def get_data(
            self,
            data_type: DataType,
            time_interval: TimeInterval = TimeInterval.HOUR
        ):
        """
        Requests and loads the specified data type using Alpha Vantage.

        Parameters:
        data_type: DataType - Data type requested (eg. DataType.DAILY)
        """
        fn = AlphaVantage.get_method(data_type.value)
        self.time_series_data = fn(self.ticker, interval=time_interval.value)
        self.update()

    def update(self):
        """Updates object attributes based on latest information if available."""
        if self.time_series_data:
            last = self.time_series_data[0]

            self.last_updated = last.date
            self.last_open = last.open
            self.last_close = last.close

    def to_json(self) -> dict:
        """Converts object to JSON as long as it has time_series_data"""
        if self.time_series_data:
            json = {}
            for k, v in self.__dict__.items():
                if isinstance(v, list):
                    json[k] = [point.to_json() for point in v]
                else:
                    json[k] = v

            return json
    
    def to_CSV(self):
        """Stores data in CSV format locally"""
        json = self.to_json()
        if json:
            df = pd.DataFrame(json['time_series_data'])
            df.to_csv(f'./{self.ticker.lower()}.csv')

    def compute_rolling_averages(self):
        """Calculates the Rolling Averages for 20, 50 and 200"""

        try:
            df = dd.from_pandas(pd.DataFrame(self.time_series_data), npartitions=1)
            df = df.query("type=='intraday'").sort_values(by='date')
            df2 = df.drop(columns=['type', 'date'])

            for window in [20, 50, 200]:
                avgs = df2.rolling(window=window).mean()
                avg = avgs.tail(1).close.values[0]
                if avg:
                    self.__setattr__(f"rolling_avg_{window}", avg)
        except Exception as e:
            print(e)
            pass

    def compute_rsi(self):
        """Calculates the Relative Strength Index (RSI)"""

        try:
            df = dd.from_pandas(pd.DataFrame(self.time_series_data), npartitions=1)
            df = df.query("type=='intraday'").sort_values(by='date')
            df2 = df.drop(columns=['type', 'date']).diff()

            gain = df2.mask(df2 < 0, 0)
            loss = -df2.mask(df2 > 0, 0)

            avg_gain = gain.rolling(14).mean().tail(1).close.values[0]
            avg_loss = loss.rolling(14).mean().tail(1).close.values[0]
            
            rsi = 100 - (100 / (1 + (avg_gain / avg_loss)))
            if rsi:
                self.__setattr__('rsi', rsi)
        except Exception as e:
            print(e)
            pass
    
    def calculate_stats(self):
        """Calls all of the computations to make a ticker whole"""

        self.compute_rolling_averages()
        self.compute_rsi()
