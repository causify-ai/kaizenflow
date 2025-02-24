#!/usr/bin/env python3
##Import requried packages
import pandas as pd
import psycopg2 as psycop

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


# Pulling Data from Issues Table-
issues_check_query = "SELECT * FROM github_issues"
issues_df = get_db_connection(issues_check_query)
issues_df.rename(
    columns={
        0: "id",
        1: "number",
        2: "title",
        3: "created_at",
        4: "updated_at",
        5: "closed_at",
        6: "author_association",
        7: "comments",
        8: "body",
        9: "user_login",
        10: "user_id",
        11: "Crypto_Name",
        12: "Extension",
    },
    inplace=True,
)
print("Pulling The Issues df:", issues_df.head(2))


# Pulling Data from Commits Table-
commits_check_query = "SELECT * FROM github_commits"
commits_df = get_db_connection(commits_check_query)
commits_df.rename(
    columns={
        0: "total",
        1: "week",
        2: "days",
        3: "Crypto_Name",
        4: "Extension",
        5: "Sun",
        6: "Mon",
        7: "Tue",
        8: "Wed",
        9: "Thur",
        10: "Fri",
        11: "Sat",
    },
    inplace=True,
)
print("Pulling the Commits df:", commits_df.head(2))


# Pulling Data from Main Table-
main_check_query = "SELECT * FROM github_main"
main_df = get_db_connection(main_check_query)
main_df.rename(
    columns={
        0: "id",
        1: "created_at",
        2: "updated_at",
        3: "pushed_at",
        4: "size",
        5: "stargazers_count",
        6: "watchers_count",
        7: "forks_count",
        8: "open_issues_count",
        9: "watchers",
        10: "network_count",
        11: "subscribers_count",
        12: "owner_id",
        13: "organization_id",
        14: "Crypto",
        15: "inserted_at",
    },
    inplace=True,
)
print("Pulling the Main df:", main_df.head(2))


# Inserting to separte csv..
print("Inserting to CSV Files")

issues_df.to_csv("github_issues.csv", encoding="utf-8", index=False)
commits_df.to_csv("github_commits.csv", encoding="utf-8", index=False)
main_df.to_csv("github_main.csv", encoding="utf-8", index=False)
print("Insertion Done!")
