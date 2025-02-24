"""
Transformation data for Reddit.

Import as:

import sorrentum_sandbox.examples.reddit.transform as ssesretr
"""
import logging
import re
from typing import List, Optional, Tuple

import pandas as pd

_LOG = logging.getLogger(__name__)


def get_the_top_most_comment_body(post: dict) -> str:
    """
    Get the top most comment body from a praw post.

    :param post: post for searching
    :return: body of the top most comment
    """
    try:
        body = str(post["comments"][0]["body"])
    except (IndexError, TypeError, KeyError):
        _LOG.warning("Error fetching top comment for the post: %s", post["title"])
        body = ""
    return body


def get_words_from_text(text: str) -> List[str]:
    """
    Process text and get words from it.

    :param text: text to process
    :return: list of words
    """
    regex = re.compile("[^a-zA-Z0-9]")
    text = regex.sub(" ", text)
    text = text.lower()
    words = set(text.split(" "))
    return list(filter(None, words))


def get_symbols_from_text(
    content: str, symbols: Optional[Tuple[str, ...]] = None
) -> List[str]:
    """
    Search in text and return found symbols.

    :param content: text for analyzing
    :param symbols: predefined list of symbols
    :return: found symbols
    """
    # This is an example of a cryptocurrency "universe", i.e. the set
    # of cryptocurrency one considers when constructing
    # their ETL pipeline`. For simplicity, a small set is used as an example.`
    if symbols is None:
        symbols = ("BTC", "ETH", "USDT", "USDC", "BNB")
    output = []
    lowercase_content = content.lower()
    for symbol in symbols:
        if symbol.lower() in lowercase_content:
            output += [symbol]
    return output


def extract_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Extract features from list of posts.

    :param data: list of reddit posts
    :return: List of feature with the _id field
    """
    output = []
    for _, post in data.iterrows():
        top_most_comment_body = get_the_top_most_comment_body(dict(post))
        symbols_from_content = get_symbols_from_text(post["selftext"])
        symbols_from_title = get_symbols_from_text(post["title"])
        symbols_from_top_comment = get_symbols_from_text(top_most_comment_body)
        cross_symbols = list(
            set(symbols_from_content).intersection(
                set(symbols_from_title), set(symbols_from_top_comment)
            )
        )
        features = {
            "reddit_post_id": post["id"],
            "symbols": symbols_from_content,
            "top_most_comment_body": top_most_comment_body,
            "top_most_comment_tokens": get_words_from_text(top_most_comment_body),
            # cross_symbols is symbols existing in:
            # - post content
            # - title
            # - top comment body
            "cross_symbols": cross_symbols,
        }
        output += [features]
    return pd.DataFrame(output)
