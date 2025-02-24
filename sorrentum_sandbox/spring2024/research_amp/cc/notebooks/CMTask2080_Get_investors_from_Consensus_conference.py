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
import pandas as pd

# %% [markdown]
# # Load the data

# %%
data = pd.read_csv(
    "/shared_data/consensus_conference.csv", index_col="Unnamed: 0"
)
data

# %% [markdown]
# # Tier 1 filter

# %% [markdown]
# ## Either Partner or VC

# %% run_control={"marked": false}
# `Partner` in job.
mask1 = data["job"].str.contains("Partner", case=False, na=False)
print("Selecting partner=", mask1.sum())
# `Venture,Capital,VC` in company.
mask2 = data["company"].str.contains("venture|capital|VC", case=False, na=False)
print("Company count=", mask2.sum())
# Exclude LLP (lawyer firms).
mask3 = data["company"].str.contains("LLP", na=False)
print("Company count=", mask3.sum())

# Collect all Tier-1 contacts.
tier1_ease = data[(mask1 | mask2) & ~mask3]
tier1_ease = tier1_ease.drop_duplicates()
tier1_ease

# %% [markdown]
# ## Partner and VC is obligatory

# %%
# `Partner` in job.
mask1 = data["job"].str.contains("Partner", case=False, na=False)
print("Selecting partner=", mask1.sum())
# `Venture,Capital,VC` in company.
mask2 = data["company"].str.contains("venture|capital|VC", case=False, na=False)
print("Company count=", mask2.sum())

# Collect all Tier-1 contacts.
tier1 = data[(mask1 & mask2)]
tier1 = tier1.drop_duplicates()
tier1

# %% [markdown]
# ## Investment-related jobs

# %%
# `Investor` in job.
mask1 = data["job"].str.contains("investor", case=False, na=False)
print("Selecting Investor=", mask1.sum())
# Exclude IR positions.
mask2 = data["job"].str.contains("Relations", case=False, na=False)
# More investor-related jobs.
mask3 = data["job"].str.contains("investment", case=False, na=False)
print("Selecting Investment=", mask3.sum())

new_names = data[(mask1 | mask3) & ~mask2]
# Exclude previously found Tier-1 names.
new_names = new_names[~new_names["name"].isin(list(tier1["name"]))]
# Drop those with missing `company` field.
new_names = new_names[new_names["company"].notna()]
# Drop duplicates.
new_names = new_names.drop_duplicates(keep="last")
new_names

# %% [markdown]
# ## Save results

# %%
new_names.to_csv("tier1.csv")


# %% [markdown]
# ## Phantombuster format converter

# %%
def conver_to_phantombuster(df):
    ph_contacts = df["name"].map(str) + " " + df["company"].map(str)
    return ph_contacts


# %%
conver_to_phantombuster(new_names)
