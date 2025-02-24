#!/usr/bin/env python
import os

import praw

reddit = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_SECRET"],
    user_agent=os.environ["REDDIT_SECRET"]
)
print(reddit)
print(reddit.user.me())
# Example: Getting the 10 hottest posts from the Python subreddit
for submission in reddit.subreddit('python').hot(limit=10):
    print(submission.title)
