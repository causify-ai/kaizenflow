from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import List


class DataType(str, Enum):
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TimeInterval(str, Enum):
    ONE = "1min"
    FIVE = "5min"
    FIFTHTEEN = "15min"
    THIRTY = "30min"
    HOUR = "60min"


@dataclass
class TimeSeriesData:
    type: DataType
    date: date
    open: float
    close: float
    high: float
    low: float
    volume: int

    def to_json(self):
        dic = {
            "date": self.date,
            "open": self.open,
            "close": self.close,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
        }
        dic["type"] = self.type if isinstance(self.type, str) else self.type.value
        return dic

    @classmethod
    def load_json(cls, data_type: DataType, data: dict) -> list:
        """
        Transforms Alpha Vantage JSON request response into list of TimeSeriesData objects

        Parameters:
        data_type: DataType - Type of data passed in, used to categorize in case multiple data types are requested.
        data: dict - JSON response from Alpha Vantage

        Returns:
        List[TimeSeriesData]
        """

        time_series: List[cls] = []
        for key in data.keys():
            if "Time Series" in key:
                datapoint = data[key]
                for date in datapoint.keys():
                    info = {k[3:]: v for (k, v) in datapoint[date].items()}

                    try:
                        dt = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        dt = datetime.strptime(date, "%Y-%m-%d")

                    temp = cls(
                        type=data_type,
                        date=dt,  # 2023-02-24 18:40:00
                        open=float(info["open"]),
                        close=float(info["close"]),
                        high=float(info["high"]),
                        low=float(info["low"]),
                        volume=int(info["volume"]),
                    )
                    time_series.append(temp)
        return time_series
