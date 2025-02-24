# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

import ib_insync

print(ib_insync.__all__)

import im.ib.data.extract.gateway.utils as imidegaut

# %%
ib = imidegaut.ib_connect(client_id=33, is_notebook=True)

# %%
# Look for ES.

# symbol = "ES"
symbol = "NG"
# symbol = "CL"
contract = ib_insync.Future(symbol, includeExpired=True)
df = imidegaut.get_contract_details(ib, contract, simplify_df=False)

display(df)

# cds = ib.reqContractDetails(contract)

# contracts = [cd.contract for cd in cds]

# ib_insync.util.df(contracts)

# %%
df

# %%
# df.reset_index(drop=True)

# %%
import copy

# %%
def create_contracts(ib, contract, symbols):
    contracts = []
    for symbol in symbols:
        contract_tmp = copy.copy(contract)
        contract_tmp.symbol = symbol
        # ib.qualifyContracts(contract_tmp)
        contracts.append(contract_tmp)
    return contracts


contract = ib_insync.Future(symbol, includeExpired=True)
symbols = "ES CL NG".split()
create_contracts(ib, contract, symbols)

# %%
contract2.symbol = "E"

# %%
import im.ib.data.extract.gateway.metadata as imidegame

file_name = "./metadata.csv"
ibmeta = imidegame.IbMetadata()

ibmeta.update(ib, [contract], file_name, reset=True)

# %%
ibmeta.load(file_name)

# %%
