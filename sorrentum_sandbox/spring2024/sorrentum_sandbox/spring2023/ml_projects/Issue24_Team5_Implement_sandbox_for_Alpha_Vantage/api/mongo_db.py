import os
from typing import List

from dotenv import load_dotenv
from models.ticker import Ticker
from models.time_series import TimeSeriesData
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()


class Mongo:
    MONGO_USER = os.environ.get("MONGO_USER")
    MONGO_PWD = os.environ.get("MONGO_PWD")

    mongo_str = f"mongodb+srv://{MONGO_USER}:{MONGO_PWD}@cluster0.jtf4vwu.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(mongo_str, server_api=ServerApi("1"))

    # If line below errors try this: https://stackoverflow.com/questions/59411362/ssl-certificate-verify-failed-certificate-verify-failed-unable-to-get-local-i
    db = client["DATA605"]
    collection = db["market"]

    @classmethod
    def download(cls) -> List[Ticker]:
        """Downloads the entire database stored in Mongo and returns it as a list of tickers"""
        data = cls.collection.find()
        if data:
            tickers = []
            for ticker_data in data:
                ticker_data["time_series_data"] = [
                    TimeSeriesData(**point)
                    for point in ticker_data["time_series_data"]
                ]
                tickers.append(Ticker(**ticker_data))
            return tickers

    @classmethod
    def get_ticker(cls, ticker: str) -> Ticker:
        """
        Returns individual data for a single specified ticker

        Parameters:
        ticker: str - Ticker for company lookup.
        """
        data = cls.collection.find_one({"_id": ticker.upper()})
        if data:
            data["time_series_data"] = [
                TimeSeriesData(**point) for point in data["time_series_data"]
            ]
            return Ticker(**data)

    @classmethod
    def save_data(cls, data: Ticker):
        """
        Saves a ticker class to mongoDB

        Parameters:
        data: Ticker - Class that needs to be saved.
        """
        if not data.time_series_data:
            return

        json = data.to_json()
        new_data = json["time_series_data"]

        # Checking for duplicate data
        current = cls.get_ticker(data.ticker)
        if current:
            new_data = [
                point.to_json()
                for point in data.time_series_data
                if point not in current.time_series_data
            ]
            if current.name != current.ticker:
                json["name"] = current.name

        json.pop("time_series_data", None)

        cls.collection.find_one_and_update(
            {"_id": data.ticker},
            {"$push": {"time_series_data": {"$each": new_data}}},
            upsert=True,
        )

        cls.collection.find_one_and_update(
            {"_id": data.ticker}, {"$set": json}, upsert=True
        )

    @classmethod
    def update_ticker_stats(cls, data: Ticker):
        """Update everything except the time series data"""
        
        json = data.to_json()
        json.pop('time_series_data', None)
        cls.collection.find_one_and_update(
            {"_id": data.ticker},
            {"$set": json},
            upsert=True
        )

    @classmethod
    def delete_ticker(cls, ticker: str):
        """Deletes all data related to a specific ticker"""
        cls.collection.delete_one({"_id": ticker})

    @classmethod
    def purge_database(cls):
        """Deletes everything in the database"""
        data = cls.download()
        for ticker in data:
            cls.delete_ticker(ticker.ticker)
