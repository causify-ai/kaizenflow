#!/usr/bin/env python

import pymongo
import pandas as pd
import sorrentum_sandbox.examples.reddit.db as ssexredb

mongodb_client = pymongo.MongoClient(
    host=ssexredb.MONGO_HOST, port=27017, username="mongo", password="mongo"
)
reddit_mongo_client = ssexredb.MongoClient(mongodb_client, "reddit")
data = reddit_mongo_client.load(
    dataset_signature="posts",
)
print(data)
