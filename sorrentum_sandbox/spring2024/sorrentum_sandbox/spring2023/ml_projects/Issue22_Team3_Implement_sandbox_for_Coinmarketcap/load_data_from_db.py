import pandas as pd
import pymongo
import sorrentum_sandbox.examples.ml_projects.Issue22_Team3_Implement_sandbox_for_Coinmarketcap as coinmarketcap

coinmarketcap_db = coinmarketcap.db

def connect_db() -> coinmarketcap_db.MongoClient:
    """
    Connect to MongoDB.
    """
    mongo_loader = coinmarketcap_db.MongoClient(
        mongo_client=pymongo.MongoClient(
            host="host.docker.internal",
            port=27017,
            username="mongo",
            password="mongo",
        ),
        db_name="CoinMarketCap",
    )
    return mongo_loader


def get_quote_data(collection_name: str) -> pd.DataFrame:
    """
    Get quote data from MongoDB.
    """
    mongo_loader = connect_db()
    quote_data = mongo_loader.load(collection_name)
    return quote_data
