#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##Import requried packages
import pandas as pd
import logging
import requests
import json
from pandas import json_normalize
import warnings
import psycopg2 as psycop

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", None)

import sorrentum_sandbox.common.download as ssandown

_LOG = logging.getLogger(__name__)


def downloader(pair, target_table, **kwargs):

    ##Links for requests
    if pair == "BTC":
        link = "https://api.github.com/repos/bitcoin/bitcoin"
    elif pair == "SOL":
        link = "https://api.github.com/repos/solana-labs/solana"
    elif pair == "ETH":
        link = "https://api.github.com/repos/ethereum"
    elif pair == "DOGE":
        link = "https://api.github.com/repos/dogecoin/dogecoin"
    elif pair == "MATIC":
        link = "https://api.github.com/repos/maticnetwork/bor"
    elif pair == "STORJ":
        link = "https://api.github.com/repos/storj/storj"
    elif pair == "AVAX":
        link = "https://api.github.com/repos/ava-labs"
    elif pair == "SAND":
        link = "https://api.github.com/repos/thesandboxgame"
    elif pair == "DYDX":
        link = "https://api.github.com/repos/dydxprotocol"
    elif pair == "BNB":
        link = "https://api.github.com/repos/bnb-chain"

    crypto = [link]

    # Extension for different stats
    yearly_commits = "/stats/commit_activity"
    weekly_commits_aggregated = "/stats/code_frequency"
    total_commits_users = "/stats/participation"
    hourly_commits = "/stats/punch_card"
    issues = "/issues"
    issue_comments = "/issues/comments"

    # Defining Data Frame for main data
    data = pd.DataFrame()

    ##-- For Yearly Commits
    yc_df = pd.DataFrame()

    ##-- For Issues Data
    issues_df = pd.DataFrame()

    # Creating a loop to get the required data---

    ## Use this to fetch for all cryptos
    # crypto = [BTC, SOL, ETH, DOGE, MATIC, STORJ, AVAX, SAND, DYDX, BNB]
    ## Use this for specific crypto
    # crypto = [pair]

    # extensions = [yearly_commits, weekly_commits_aggregated , total_commits_users, hourly_commits, issues , issue_comments]
    extensions = [issues, yearly_commits]

    for m in crypto:
        common = requests.get(m).json()
        d1 = json_normalize(common)
        crypto_name = m.split("/")[-1]
        d1["Crypto"] = crypto_name
        d1["inserted_at"] = pd.Timestamp.now()
        data = data.append(d1)

        for n in extensions:
            # Extension---
            pull = requests.get(m + n).json()
            d2 = json_normalize(pull)
            d2["Crypto_Name"] = crypto_name
            d2["Extension"] = n
            if n == yearly_commits:
                yc_df = yc_df.append(d2)
            elif n == weekly_commits_aggregated:
                wca_df = wca_df.append(d2)
            elif n == total_commits_users:
                tcu_df = tcu_df.append(d2)
            elif n == hourly_commits:
                d2 = pd.DataFrame(
                    pull, columns=["Day", "Hour", "Number of Commits"]
                )
                hc_df = hc_df.append(d2)
            elif n == issues:
                issues_df = issues_df.append(d2)
            elif n == issue_comments:
                issuecom_df = issuecom_df.append(d2)
            else:
                continue

        print("Extension DF for crypto", m, "done for:", n)
    print("DFs for crypto done for:", m)

    # Preprocessing--
    # 1.For Yearly Commit Data Frame---
    ###Convertin Days Column values in 'Yearly Commit' to separte columns
    if yc_df.empty:
        print("Dataframe is empty!")
    else:
        yc_df[["Sun", "Mon", "Tue", "Wed", "Thur", "Fri", "Sat"]] = pd.DataFrame(
            yc_df.days.tolist(), index=yc_df.index
        )

    # 2.For the main data frame -----
    ##Rearranging columns & Keeping only the features that are needed
    data = data[
        [
            "id",
            "created_at",
            "updated_at",
            "pushed_at",
            "size",
            "stargazers_count",
            "watchers_count",
            "forks_count",
            "open_issues_count",
            "watchers",
            "network_count",
            "subscribers_count",
            "owner.id",
            "organization.id",
            "Crypto",
            "inserted_at",
        ]
    ]
    # Renaming the columns
    data = data.rename(
        columns={"owner.id": "owner_id", "organization.id": "organization_id"},
        inplace=False,
    )

    # 3.For the Issues data frame -----
    issues_df = issues_df[
        [
            "id",
            "number",
            "title",
            "created_at",
            "updated_at",
            "closed_at",
            "author_association",
            "comments",
            "body",
            "user.login",
            "user.id",
            "Crypto_Name",
            "Extension",
        ]
    ]
    # Renaming the columns
    issues_df = issues_df.rename(
        columns={"user.login": "user_login", "user.id": "user_id"}, inplace=False
    )

    # Connection String for main DB
    def get_db_connection(query_var):
        connection = psycop.connect(
            host="host.docker.internal",
            dbname="airflow",
            port=5532,
            user="postgres",
            password="postgres",
        )
        drt_cursor = connection.cursor()
        drt_cursor.execute(query_var)
        data = drt_cursor.fetchall()
        connection.close()
        return pd.DataFrame(data)

    # checking for existing IDs in Issues Data table-
    issues_check_query = "SELECT * FROM github_issues"
    issues_check = get_db_connection(issues_check_query)
    print("Existing Issues df:", issues_check.head(2))
    allowed = issues_check.iloc[:, 0].unique()
    # Removing existing IDs from fetched dataframe
    issues_df.loc[issues_df.id.isin(allowed), "duplicate_id"] = 1
    issues_df["duplicate_id"] = issues_df.duplicate_id.fillna(value=0)
    issues_df = issues_df[issues_df["duplicate_id"] == 0]
    # Dropping not requried columns---
    issues_df = issues_df.drop(["duplicate_id"], axis=1)

    # Datatable to be inserted
    if target_table == "github_main":
        table = data
        _LOG.info(f"\nInserting GitHub Main data: \n\t {data.head()}")
    elif target_table == "github_commits":
        table = yc_df
        _LOG.info(f"\nInserting GitHub Yearly Commits data: \n\t {yc_df.head()}")
    elif target_table == "github_issues":
        table = issues_df
        _LOG.info(f"\nNew Unique GitHub Issues found: {len(issues_df)}")
        _LOG.info(f"\nInserting GitHub Issues data: \n\t {issues_df.head()}")
    else:
        table = data