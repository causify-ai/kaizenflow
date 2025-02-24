# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description

# %% [markdown]
# This notebook contains tools for debugging an individual `CcxtBroker` execution.
#
# The notebook is responsible for aspects of the execution experiment run that are related to the correctness of the execution, as opposed to the analysis of the result:
# - Consistency of logging
# - Correctness in the submission of orders
# - Consistency between trades and submitted orders
# - Order time profiling

# %% run_control={"marked": false}
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import logging

import core.config as cconfig
import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hprint as hprint
import im_v2.common.universe as ivcu
import oms.broker.ccxt.ccxt_aggregation_functions as obccagfu
import oms.broker.ccxt.ccxt_execution_quality as obccexqu
import oms.broker.ccxt.ccxt_logger as obcccclo

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %%
# When running manually, specify the path to the config to load config from file,
# for e.g., `.../reconciliation_notebook/fast/result_0/config.pkl`.
config_file_name = None
config = cconfig.get_notebook_config(config_file_name)
if config is None:
    system_log_dir = "/shared_data/toma/CmTask7440_1"

    config_dict = {"system_log_dir": system_log_dir}
    config = cconfig.Config.from_dict(config_dict)
print(config)

# %% run_control={"marked": false}
log_dir = config["system_log_dir"]
ccxt_log_reader = obcccclo.CcxtLogger(log_dir)
#
data = ccxt_log_reader.load_all_data(
    convert_to_dataframe=True, abort_on_missing_data=False
)
ccxt_order_response_df = data["ccxt_order_responses"]
ccxt_trades_df = data["ccxt_trades"]
oms_child_order_df = data["oms_child_orders"]
oms_parent_order_df = data["oms_parent_orders"]
ccxt_fills = data["ccxt_fills"]

# %%
# Print the Broker config.
if "broker_config" in data:
    print(hprint.to_pretty_str(data["broker_config"]))
    universe_version = data["broker_config"]["universe_version"]
else:
    _LOG.warning("broker_config file not present in %s", log_dir)
    universe_version = None

# %%
# Print the used Config, if any.
experiment_config = obcccclo.load_config_for_execution_analysis(log_dir)
print(experiment_config)

# %%
ccxt_order_response_df.head(3)

# %% [markdown]
# ## Child order responses

# %%
ccxt_order_response_df.info()

# %% [markdown]
# ## Child orders

# %%
oms_child_order_df.info()

# %%
oms_child_order_df.head(3)

# %% [markdown]
# ### Extract the OMS parent order ID

# %%
oms_child_order_df["parent_order_id"] = oms_child_order_df["extra_params"].apply(
    lambda x: x["oms_parent_order_id"]
)
oms_child_order_df.head(3)

# %%
# Check how many child orders are generated per parent_order_id.
oms_child_order_df["parent_order_id"].value_counts().value_counts()

# %% [markdown]
# ### Check the error messages in non-submitted orders.

# %%
# Select the OMS child orders with no CCXT ID and check their error messages.
not_submitted_oms_child_order_df = oms_child_order_df.loc[
    oms_child_order_df["ccxt_id"] == -1
]
print(
    f"Number of not submitted OMS child orders={not_submitted_oms_child_order_df.shape[0]} \
    out of total orders={oms_child_order_df.shape[0]}"
)

# %%
# Extract all error messages from unsubmitted orders.
not_submitted_oms_child_order_df["error_msg"] = not_submitted_oms_child_order_df[
    "extra_params"
].apply(lambda x: x["error_msg"])


# %%
# Display error messages grouped by symbol.
# Get the universe to map asset_id's.
universe = ivcu.get_vendor_universe(
    "CCXT", "trade", version=universe_version, as_full_symbol=True
)
asset_id_to_symbol_mapping = ivcu.build_numerical_to_string_id_mapping(universe)
not_submitted_oms_child_order_df[
    "full_symbol"
] = not_submitted_oms_child_order_df["asset_id"].map(asset_id_to_symbol_mapping)
# Get value counts of error messages.
error_msg = not_submitted_oms_child_order_df.groupby("full_symbol")[
    "error_msg"
].value_counts()
error_msg

# %% [markdown]
# ### Check the buy and sell orders with max notional

# %% run_control={"marked": true}
oms_child_order_notionals = (
    oms_child_order_df["diff_num_shares"] * oms_child_order_df["limit_price"]
)
max_sell_notional = oms_child_order_notionals[oms_child_order_notionals < 0].min()
max_buy_notional = oms_child_order_notionals[oms_child_order_notionals > 0].max()
_LOG.info(
    "Max sell notional: %s\nMax buy notional: %s",
    max_sell_notional,
    max_buy_notional,
)

# %% [markdown]
# ## Parent orders

# %%
oms_parent_order_df.head(3)

# %%
# Extract `ccxt_id` of child orders into a separate column.
oms_parent_order_df["child_order_ccxt_ids"] = oms_parent_order_df[
    "extra_params"
].apply(lambda x: x["ccxt_id"])
oms_parent_order_df.head(3)

# %%
# Check how many child orders per parent order were successfully submitted.
# A value between maximum expected and 0 can mean that some child orders
# could not get through, while otherwise being well-formed.
# A value of 0 means that the parent order had an issue, e.g.
# having a notional that made all child orders below a minimum.
oms_parent_order_df["submitted_child_order_num"] = oms_parent_order_df[
    "child_order_ccxt_ids"
].str.len()
oms_parent_order_df["submitted_child_order_num"].value_counts()

# %% [markdown]
# ## Trades

# %%
ccxt_trades_df.info()

# %% [markdown]
# ### Verify that all trades correspond to logged child orders

# %%
# Verify that all trades have an associated order response.
# If the trade does not have an associated order, it means
# that a trade was executed that was not accounted for during the experiment.
all(ccxt_trades_df["order"].isin(ccxt_order_response_df["order"]))

# %%
# Verify that all trades have an associated 'ccxt_id' in OMS child orders.
# This verifies that there is a consistency between a CCXT order, OMS order and
# a CCXT trade. If a trade has no associated OMS child order `ccxt_id`, it means
# that an unexpected trade was executed, for example, by a different actor on the same account.
all(ccxt_trades_df["order"].isin(oms_child_order_df["ccxt_id"]))

# %% [markdown]
# ### Check orders that do not correspond to any trades

# %% run_control={"marked": true}
# Existence of such orders is not necessarily a bug.
# It means that a given OMS child order was not filled.
child_orders_with_no_trades = ~oms_child_order_df["ccxt_id"].isin(
    ccxt_trades_df["order"]
)
child_orders_with_no_trades.sum()

# %% [markdown]
# ### Check the correctness of trade amount

# %% run_control={"marked": false}
# If the traded amount is larger than the order, it means that an extra trade
# is executed and the order is filled for a larger amount.
# This can mean an accounting error on the exchange side.
trade_amount_by_order = ccxt_trades_df.groupby("order").agg({"amount": "sum"})
accepted_child_order_df = oms_child_order_df.loc[
    oms_child_order_df["ccxt_id"] != -1
]
trade_amount_by_order["child_order_amount"] = accepted_child_order_df.set_index(
    "ccxt_id"
)["diff_num_shares"].abs()

# %%
mask = (
    trade_amount_by_order["amount"] > trade_amount_by_order["child_order_amount"]
)
trade_amount_by_order.loc[mask]

# %%
# Check the difference between the filled amount and the agg child order quantities.
trade_amount_by_order["diff"] = (
    trade_amount_by_order["child_order_amount"] - trade_amount_by_order["amount"]
)
trade_amount_by_order = trade_amount_by_order.rename(
    {"amount": "aggregated_trades_quantity"}, axis=1
)
trade_amount_by_order = trade_amount_by_order[
    ["child_order_amount", "aggregated_trades_quantity", "diff"]
]
trade_amount_by_order[trade_amount_by_order["diff"] > 0]

# %% [markdown]
# ### Verify that CCXT IDs are equal in both child orders and responses

# %%

# %%
# Verify that we are not logging any CCXT orders that are not a part
# of the experiment, i.e. have no OMS order associated with it.
# We expect all retrieved responses to be a subset of CCXT IDs
# connected to the OMS child orders.
submitted_oms_orders_ccxt_ids = set(
    oms_child_order_df.loc[oms_child_order_df["ccxt_id"] != -1][
        "ccxt_id"
    ].unique()
)
ccxt_response_ids = set(ccxt_order_response_df["order"].unique())
ccxt_response_ids.issubset(submitted_oms_orders_ccxt_ids)

# %% [markdown]
# # Group trades by order

# %%
# Aggregate fills by order.
ccxt_trades_by_order = obccagfu.aggregate_fills_by_order(ccxt_trades_df)
ccxt_trades_by_order.head(3)

# %% [markdown]
# # Time profiling for child orders

# %%
oms_child_order_df_unpacked = ccxt_log_reader.load_oms_child_order(
    unpack_extra_params=True, convert_to_dataframe=True
)

# %%
# Get the timestamps of events for each child order
events = obccexqu.get_oms_child_order_timestamps(oms_child_order_df_unpacked)
events = events.sort_values(events.first_valid_index(), axis=1)

# %%
events.head(3)

# %%
# Get the difference between event timestamps.
time_delays = obccexqu.get_time_delay_between_events(events)

# %%
time_delays.boxplot(rot=45, ylabel="Time delay")

# %% [markdown]
# ## Plot zero and non-zero waves separately

# %% [markdown]
# ### Plot zero wave

# %%
# Since wave 0 begins execution later due to portfolio computation,
# we plot the time delays for it separately.
wave_zero = oms_child_order_df_unpacked[
    oms_child_order_df_unpacked["wave_id"] == 0
]
# Get the timestamps of events for each child order
wave_zero_events = obccexqu.get_oms_child_order_timestamps(wave_zero)
# Skip plotting wave 0 if it was not executed during the run.
plot_wave_zero = len(wave_zero_events) > 0
if plot_wave_zero:
    wave_zero_events = wave_zero_events.sort_values(
        wave_zero_events.first_valid_index(), axis=1
    )
else:
    _LOG.warning("Wave 0 was not executed during the run. Skipping plotting.")

# %%
wave_zero_events.head(3)

# %%
if plot_wave_zero:
    # Get the difference between event timestamps.
    time_delays = obccexqu.get_time_delay_between_events(wave_zero_events)

# %%
if plot_wave_zero:
    time_delays.boxplot(rot=45, ylabel="Time delay").set_title(
        "Time delay between events for wave 0"
    )

# %% [markdown]
# ### Plot the rest of the waves

# %% run_control={"marked": false}
# Plot non-zero wave time to get the "average" time of the
# order submission, without computing portfolio and forecasts.
non_wave_zero_events = oms_child_order_df_unpacked[
    oms_child_order_df_unpacked["wave_id"] > 0
]
# Get the timestamps of events for each child order
non_wave_zero_events = obccexqu.get_oms_child_order_timestamps(
    non_wave_zero_events
)
non_wave_zero_events = non_wave_zero_events.sort_values(
    non_wave_zero_events.first_valid_index(), axis=1
)

# %%
non_wave_zero_events.head(3)

# %%
# Get the difference between event timestamps.
time_delays = obccexqu.get_time_delay_between_events(non_wave_zero_events)

# %%
time_delays.boxplot(rot=45, ylabel="Time delay").set_title(
    "Time delay between events for waves >0"
)

# %%
