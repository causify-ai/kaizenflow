# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Imports

# %%
import re

import gspread as gs
import pandas as pd

# %%
# # !sudo /bin/bash -c "(source /venv/bin/activate; pip install gspread)"

# %% [markdown]
# # Configs

# %%
json_key = "steady-computer-354216-eb3e67b30a7b.json"
gc = gs.service_account(filename=json_key)

# %% [markdown]
# # Load the data

# %% [markdown]
# ## MIG

# %%
# Configuration for MIG.
mig_link = "https://docs.google.com/spreadsheets/d/1gxOVAtjk_oEz7WsNVfdST67SupISZ2U-ePUzuep5IEo/edit#gid=0"
mig_env = gc.open_by_url(mig_link)

# %% run_control={"marked": false}
# Read MIG from gsheet.
mig_ws = mig_env.worksheet("Firms")
mig = pd.DataFrame(mig_ws.get_all_records())
# Unify the absense of e-mails.
mig["Submit by email"] = mig["Submit by email"].replace({"": "not available"})
mig.head(3)

# %% [markdown]
# ## Mail_merge

# %%
# Configuration for `Mail_merge`.
mm_link = "https://docs.google.com/spreadsheets/d/11AXt9Yzwmk1is_wprFDuE3vbS67gpwOO8gRfB4teC34/edit#gid=348677750"
mm_env = gc.open_by_url(mm_link)
worksheet_list = mm_env.worksheets()
worksheet_list

# %%
mail_merge = []
for i in range(len(worksheet_list)):
    df_tmp = pd.DataFrame(mm_env.get_worksheet(i).get_all_records()).iloc[:, :4]
    df_tmp.columns = ["Email", "Name", "Company", "Consensus"]
    mail_merge.append(df_tmp)
mail_merge = pd.concat(mail_merge)
mail_merge.tail(3)

# %% [markdown]
# # Select the contacts that haven't been reached yet

# %% [markdown]
# ## Drop the contacts that are already in the pipeline

# %%
# Convert MIG to the e-mail reach format.
mig_emails = mig[mig["Submit by email"] != "not available"][
    ["Submit by email", "Name"]
]
mig_emails.shape

# %%
# Extract e-mails that were previously used in campaign.
mail_merge_emails = list(mail_merge["Email"])
# Filter by those names for new unique e-mails.
new_iteration = mig_emails[~mig_emails["Submit by email"].isin(mail_merge_emails)]
display(new_iteration)


# %% [markdown]
# ## Sanity check

# %%
def check_email_format(email):
    # Regular expression for validating an Email.
    regex_email = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    # Sanity check.
    if not (re.fullmatch(regex_email, email)):
        email = None
    return email


# %%
new_iteration_cleaned = new_iteration.copy()
# Replace "bad" emails with NaN.
new_iteration_cleaned["Submit by email"] = new_iteration_cleaned[
    "Submit by email"
].apply(lambda x: check_email_format(x))
# Save "bad" emails in a separate DataFrame for manual check.
bad_emails_list = list(
    new_iteration_cleaned[new_iteration_cleaned["Submit by email"].isna()]["Name"]
)
bad_emails = new_iteration[new_iteration["Name"].isin(bad_emails_list)]
bad_emails

# %%
# Get rid of NaNs in "clean" contacts.
new_iteration_cleaned = new_iteration_cleaned[
    new_iteration_cleaned["Submit by email"].notna()
]
new_iteration_cleaned

# %% [markdown]
# ## Save the file

# %%
# new_iteration_cleaned.to_csv("new_iteration.csv")
