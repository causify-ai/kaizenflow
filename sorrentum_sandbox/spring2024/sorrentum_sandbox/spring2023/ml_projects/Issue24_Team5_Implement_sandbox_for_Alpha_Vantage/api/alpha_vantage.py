"""
Import as:

import sorrentum_sandbox.examples.ml_projects.Issue24_Team5_Implement_sandbox_for_Alpha_Vantage.api.alpha_vantage as ssempitisfavaav
"""

import os
from typing import List

import requests
from dotenv import load_dotenv
from models.time_series import DataType, TimeInterval, TimeSeriesData

load_dotenv()


class AlphaVantage:
    API_KEY = os.environ.get("ALPHA_VANTAGE")

    @classmethod
    def get_method(cls, data_type: DataType):
        """
        Gets the method for retrieving specified data type.

        Parameters:
        data_type: DataType - Type of data requested

        Returns:
        classmethod - method used to retrieve specified data type
        """
        if data_type == DataType.INTRADAY:
            return cls.get_intraday_for
        elif data_type == DataType.DAILY:
            return cls.get_daily_for
        elif data_type == DataType.WEEKLY:
            return cls.get_weekly_for
        elif data_type == DataType.MONTHLY:
            return cls.get_monthly_for
        else:
            return None

    @classmethod
    def get_name_for(cls, ticker: str) -> str:
        """
        Gets the name for specified ticker. Uses 1 API Request.

        Parameters:
        ticker: str - Ticker Symbol

        Returns:
        str - Name of Company

        Raises: LookupError if the exact ticker symbol is not found
        """

        url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={ticker}&apikey={cls.API_KEY}"
        request = requests.get(url)
        data = request.json()

        if data.get("Note"):
            return print("Out of API calls, try again later.")

        if data["bestMatches"]:
            if data["bestMatches"][0]["1. symbol"] == ticker:
                return data["bestMatches"][0]["2. name"]

        return f"{ticker}?"

    @classmethod
    def get_intraday_for(
        cls, ticker: str, interval: TimeInterval = TimeInterval.FIVE
    ) -> List[TimeSeriesData]:
        """
        Gets current day's (or latest trading day if holiday/weekend) trading
        information for specified ticker. Uses 1 API Request.

        Parameters:
        ticker: str - Ticker Symbol
        interval: TimeInterval - Time interval wanted (default is 5 minute intervals)

        Returns:
        List[TimeSeriesData]
        """

        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval={interval}&outputsize=full&apikey={cls.API_KEY}"
        request = requests.get(url)
        data = request.json()

        if data.get("Note"):
            return print("Out of API calls, try again later.")

        data = TimeSeriesData.load_json(data_type=DataType.INTRADAY, data=data)
        return data

    @classmethod
    def get_daily_for(cls, ticker: str, **kwargs) -> List[TimeSeriesData]:
        """
        Gets years worth of trading days for specified ticker. Uses 1 API
        Request.

        Parameters:
        ticker: str - Ticker Symbol

        Returns:
        List[TimeSeriesData]
        """

        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&outputsize=full&apikey={cls.API_KEY}"
        request = requests.get(url)
        data = request.json()

        if data.get("Note"):
            return print("Out of API calls, try again later.")

        data = TimeSeriesData.load_json(data_type=DataType.DAILY, data=data)
        return data

    @classmethod
    def get_weekly_for(cls, ticker: str, **kwargs) -> List[TimeSeriesData]:
        """
        Gets years worth of trading weeks for specified ticker. Uses 1 API
        Request.

        Parameters:
        ticker: str - Ticker Symbol

        Returns:
        List[TimeSeriesData]
        """

        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={ticker}&outputsize=full&apikey={cls.API_KEY}"
        request = requests.get(url)
        data = request.json()

        if data.get("Note"):
            return print("Out of API calls, try again later.")

        data = TimeSeriesData.load_json(data_type=DataType.WEEKLY, data=data)
        return data

    @classmethod
    def get_monthly_for(cls, ticker: str, **kwargs) -> List[TimeSeriesData]:
        """
        Gets years worth of trading months for specified ticker. Uses 1 API
        Request.

        Parameters:
        ticker: str - Ticker Symbol

        Returns:
        List[TimeSeriesData]
        """

        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol={ticker}&outputsize=full&apikey={cls.API_KEY}"
        request = requests.get(url)
        data = request.json()

        if data.get("Note"):
            return print("Out of API calls, try again later.")

        data = TimeSeriesData.load_json(data_type=DataType.MONTHLY, data=data)
        return data

    @classmethod
    def get_sentiment_for(cls, ticker: str):
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={cls.API_KEY}"
        request = requests.get(url)
        return request.json()
