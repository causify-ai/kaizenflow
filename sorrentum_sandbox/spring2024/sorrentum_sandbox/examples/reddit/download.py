"""
Extract part of the ETL and QA pipeline.

Import as:

import sorrentum_sandbox.examples.reddit.download as ssexredo
"""
import dataclasses
import datetime
import json
import logging
import os
from typing import List, Optional, Tuple

import pandas as pd
import praw

import sorrentum_sandbox.common.download as ssacodow

_LOG = logging.getLogger(__name__)
REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_SECRET = os.environ["REDDIT_SECRET"]


@dataclasses.dataclass
class PostFeatures:
    subreddit: str
    created: datetime.datetime
    symbols: List[str]
    post_length: int
    title: str
    content: str
    number_of_upvotes: int
    number_of_comments: int
    top_comment: str

    def dict(self) -> dict:
        return {k: str(v) for k, v in dataclasses.asdict(self).items()}


class PostsDownloader(ssacodow.DataDownloader):
    """
    Download Reddit data using praw lib.
    """

    def __init__(self) -> None:
        self.reddit_client = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_SECRET,
            user_agent=REDDIT_SECRET,
        )
        # Since we want to store a raw data in its initial state, we need to fetch
        # data in JSON format. In other case (non-JSON) we should to build
        # deserializer for every type of reddit objects.
        # From the `praw` docs:
        # "...json_dict, which contains the original API response, should be
        # stored on every object in the json_dict attribute. Default is False as
        # memory usage will double if enabled."
        self.reddit_client.config.store_json_result = True

    def download(
        self,
        *,
        start_timestamp: Optional[pd.Timestamp] = pd.Timestamp.min,
        end_timestamp: Optional[pd.Timestamp] = pd.Timestamp.max,
        numbers_post_to_fetch: int = 5,
        subreddits: Optional[Tuple[str, ...]] = None
    ) -> ssacodow.RawData:
        """
        Download posts in the hot category in the predefined subreddits.

        :param start_timestamp: start datetime for searching
        :param end_timestamp: end datetime for searching
        :param numbers_post_to_fetch: maximum number posts to fetch
        :param subreddits: tuple of subreddits to fetch
        :return: downloaded data in raw format
        """
        if subreddits is None:
            subreddits = ("Cryptocurrency", "CryptoMarkets")
        output = []
        for subreddit in subreddits:
            _LOG.info("Subreddit (%s) is downloading...", subreddit)
            # Note: This iterator is slow: ~30s for the two
            #  subreddits and 10 posts for every subreddit.
            new_posts = self.reddit_client.subreddit(subreddit).new(
                limit=numbers_post_to_fetch
            )
            for post in new_posts:
                post_timestamp = pd.Timestamp(
                    post.created_utc, unit="s", tzinfo=datetime.timezone.utc
                )
                if not start_timestamp <= post_timestamp <= end_timestamp:
                    continue
                _LOG.info("Post: (%s) is downloading...", post.title)
                post_as_dict = self._transform_to_dict(post)
                post_as_dict["created"] = post_timestamp
                output += [post_as_dict]
        _LOG.info("Reddit download finished.")
        return ssacodow.RawData(output)

    @staticmethod
    def _transform_to_dict(source: praw.models.Submission) -> dict:
        """
        Transform object to dict.

        :param source: object to transform
        :return: transformed dictionary
        """
        output_comments = []
        # Get comments before main transform since it is not possible to do it
        # after an iterator is fetched.
        if hasattr(source, "comments"):
            for comment in source.comments:
                output_comments += [PostsDownloader._transform_to_dict(comment)]
        output = vars(source)
        for key in output:
            # If object can't be deserialized then assign a question mark.
            try:
                output[key] = json.dumps(output[key])
            except (TypeError, OverflowError):
                output[key] = "?"
        if len(output_comments) > 0:
            output["comments"] = output_comments
        return output
