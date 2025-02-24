# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Description

# %% [markdown]
# - A gallery notebook to `ml_collections.ConfigDict`.
#
# - In general, there are two classes called `ConfigDict` and `FrozenConfigDict` which are "dict-like" data structures with dot access to nested elements
#
# - Main ways of expressing configurations of experiments and models.

# %% [markdown]
# # Imports

# %%
# Install `ml_collections` to env temporary.
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install ml_collections)"

# %%
import ml_collections as ml

# %% [markdown]
# # `ConfigDict()`
#
# ## Initialization
#
# - It has dot-based access as well as dict-style key access
#
# - It is type safe (once a value is set one cannot change its type)
#
# - Observation: The keys are stored or added in alphabetical order
#
# - Cannot have `.` in a key name.
#
# - Args:
#     - `initial_dictionary`: May be one of the following:
#
#         - `dict` - In this case, all values of `initial_dictionary` that are
#         dictionaries are also be converted to `ConfigDict`. However,
#         dictionaries within values of non-dict type are untouched
#
#         - `ConfigDict` - In this case, all attributes are uncopied, and only the
#         top-level object (self) is re-addressed. This is the same behavior
#         as Python dict, list, and tuple
#
#         - `FrozenConfigDict` - In this case, `initial_dictionary` is converted to
#         a `ConfigDict` version of the initial dictionary for the
#         `FrozenConfigDict` (reversing any mutability changes `FrozenConfigDict`
#         made)
#
#     - `type_safe`: If set to True, once an attribute value is assigned, its type
#           cannot be overridden without `.ignore_type()` context manager
#           (default: True)
#     - `convert_dict`: If set to True, all dict used as value in the ConfigDict
#           will automatically be converted to ConfigDict (default: True)

# %%
config = {
    "meta": {"id_col": "asset_id", "use_historical": True},
    "system_log_dir": "/shared_data/CMTask5198_log_dir_1",
    "ohlcv_market_data": {
        "vendor": "CCXT",
        "mode": "trade",
        "universe": {
            "universe_version": "v7.1",
            "test_asset_id": 1467591036,
        },
    },
}
# `ConfigDict` class:
#  https://github.com/google/ml_collections/blob/master/ml_collections/config_dict/config_dict.py#L575
config = ml.ConfigDict(config)
config

# %%
# Create a config using `create` function.
config_create = ml.config_dict.create(
    level_0=ml.config_dict.create(level_1=ml.config_dict.create(level=2)),
    other_param="some_value",
)
print(config_create, "\n")
print(type(config_create))

# %%
# If `is_type_safe=True` which is a default value,
# it's impossible to re-write the value using different
# type. TypeError is raised. See an example below.
# config["vendor"] = 123
# `int` types can be assigned to `float`.
config.is_type_safe

# %%
# Check if the config is converting dicts to `ConfigDict` automatically.
config.convert_dict

# %% [markdown]
# ## Get / Set values

# %%
# Get a config value using 2 ways: dict key or dot-method.
# E.g.: dot-method - `config.ohlcv_market_data.universe`.
print(f"""using keys: {config["meta"]["id_col"]}""")

# %%
# Get value from existing key.
config.get("ohlcv_market_data")

# %%
# Get default value if key is not present.
default_value = "Not Present"
config.get("hello", default=default_value)

# %%
config.get_type("system_log_dir")

# %%
# Get a type of the field associated with a key.
config.get_type("ohlcv_market_data")

# %%
# Add new key.
config["bar_duration"] = "5T"
config

# %%
# Keys are stored alphabatically.
config["cat"] = "foo"
config

# %% [markdown]
# ## Update
#
# - Update values based on matching keys in another dict-like object
# - Cannot update from multiple dictionaries and from different types
# -  Args:
#       - *other: A (single) dict-like container, e.g. a dict or ConfigDict.
#       - **kwargs: Additional keyword arguments to update the ConfigDict.

# %%
update_dict = {"bar_duration": "7T", "cat": "bar"}
config.update(update_dict, test="new_value")
config

# %%
# In-place update the values taken from a flattened dict.
# We can also add a new key to the config.
flattend_dict = {
    "ohlcv_market_data.universe.universe_version": "v7.2",
    "new_key": "new_value",
}
config.update_from_flattened_dict(flattend_dict)
config

# %% [markdown]
# ## `lock()` and `unlock()`

# %%
# Lock the config in order not to add new keys.
config.lock()

# %%
# Check if config is locked.
config.is_locked

# %%
# `KeyError` is raised trying to add new key while config is locked.
config["test2"] = "test_value"

# %%
# Exisitng keys can be modified even if the config is locked.
config["bar_duration"] = "6T"
config

# %%
# Config can be unlocked.
config.unlock()
config["test"] = "test_value"
config

# %%
# Check if config is unlocked.
config.is_locked

# %%
# Recursively rename the keys.
new_cfg = ml.config_dict.recursive_rename(config, "vendor", "vendor2")
new_cfg

# %% [markdown]
# # General Functionality.

# %%
# Get a a JSON representation of the object, fails if there is a cycle.
config.to_json()

# %%
# Get a a best effort JSON representation of the object.
# Tries to serialize objects not inherently supported by JSON encoder. This
# may result in the configdict being partially serialized, skipping the
# unserializable bits. Ensures that no errors are thrown. Fails if there is a
# cycle.
config.to_json_best_effort()

# %%
# Convert a ConfigDict to a regular dict.
config.to_dict()

# %% [markdown]
# # FieldReferences and placeholders
#
# - A `FieldReference` is useful for having multiple fields (keys) use the same value. It can also be used for lazy computation
#
# - You can use `placeholder()` as a shortcut to create a `FieldReference` (field) with a `None` default value. This is useful if a program uses optional configuration fields

# %% [markdown]
# ## Initialization

# %%
# Create a simple `FieldReference`.
field_reference = ml.FieldReference(0)
field_reference

# %%
# Create a `placeholder` which returns a `FieldReference`
# with a type and default value to null.
placeholder = ml.config_dict.placeholder(int)
placeholder

# %% [markdown]
# ## Get / Set FieldReference

# %%
# Get and Set the placeholder value.
placeholder.set(1)
placeholder.get()

# %%
# Get a FieldReference.
c = ml.FieldReference(ml.FieldReference(10))
c.get()

# %%
# Computation with FieldReference.
ref = ml.FieldReference(1.0)
other = ml.FieldReference(3)
ref_plus_other = ref + other
ref_plus_other.get()

# %%
# Set a FieldReference.
# Cannot set a value of other types.
ref.set(2)
other.set(4)
ref_plus_other.get()

# %%
# Get one-way reference.
# Changing `a` will change `b`.
# For 2-way ref, use `get_ref()`.
# More example on this below.
cfg = {"a": 1, "b": 2}
cfg = ml.ConfigDict(cfg)
cfg.b = cfg.get_oneway_ref("a")
cfg.a = 5
print(cfg)

# %%
# Changing `b` will not change `a`.
cfg.b = 6
print(cfg)

# %% [markdown]
# ## Using Placeholders

# %%
field_reference2 = ml.FieldReference(1)
cfg_dict = {
    "reference_value": field_reference2,
    # We can also use `required_placeholder` to make the
    # required to true.
    "optional": ml.config_dict.placeholder(str, required=True),
    "nested": {"reference_value": field_reference2},
}
cfg = ml.ConfigDict(cfg_dict)
# Cannot access optional without setting a value as `required=True`.
# Default is `required=False`.
# Below example will raise an error.
# cfg.optional
cfg.optional = "hi"
cfg

# %%
print(cfg)

# %%
# Raises Type error as this field is an str.
# cfg.optional = 12
cfg.optional = "hello"
# Changes the value of both reference_value and nested.reference_value fields
cfg.reference_value = 3
print(cfg)

# %% [markdown]
# ## Update

# %%
# Update to/from FieldReference fields.
# Cannot update a FieldReference from another FieldReference.
# Since both of them pointing to the same reference, so value
# update will happen at both places.
ref = ml.FieldReference(1)
first_dict = {"a": ref, "b": ref}
cfg = ml.ConfigDict(first_dict)
from_dict = {"a": 2, "b": 3}
# Only `b` is valid.
cfg.update(from_dict)
print(cfg)

# %%
ref = ml.FieldReference(1)
ref2 = ml.FieldReference(12)
first_dict = {"a": ref, "b": ref2}
cfg = ml.ConfigDict(first_dict)
from_dict = {"a": 2, "b": 3}
cfg.update(from_dict)
cfg

# %% [markdown]
# ## Lazy Computations

# %%
# Lazy computation on `FieldReference`.
ref = ml.FieldReference(1)
non_lazy = ref.get() + 1
# Operations with FieldReference will return another FieldReference
# that points to the original's value.
lazy = ref + 1
ref.set(4)
print(f"Non Lazy - {non_lazy}")
print(f"Lazy - {lazy.get()}")

# %%
# Lazy Computaiton on `ConfigDict`.
# `get_ref()` returns a FieldReference initialized on key's value.
config = {"a": 1, "b": 0}
config = ml.ConfigDict(config)
# Newly defined value of `a` will be used as it will perform lazy
# computation when used with `get_ref()`.
config.b = config.get_ref("a") + 10
config.a = 2
config.c = config.get_ref("b") + 10
print(config)

# %% [markdown]
# ## Cycles in `ReferenceFields`
#
# - Cannot have cycles in reference fields.

# %%
config = ml.ConfigDict()
config.a = 1
config.b = config.get_ref("a") + 10
# This will raise `MutabilityError`.
config.a = config.get_ref("b") + 2

# %% [markdown]
# ## Resolve References

# %%
# Create a config with references.
field = ml.FieldReference("a string")
int_field = ml.FieldReference(5)
cfg = {
    "dict": {
        "float": 2.3,
        "field_ref1": field,
        "field_ref2": field,
        "field_ref_int1": int_field,
        "field_ref_int2": int_field + 5,
        "placeholder": ml.config_dict.placeholder(str),
        "cfg": ml.ConfigDict({"integer": 1, "int_field": int_field}),
    }
}
cfg = ml.ConfigDict(cfg)
cfg

# %%
# Returns a ConfigDict copy with FieldReferences replaced by values.
cfg_resolved = cfg.copy_and_resolve_references()
cfg_resolved

# %% [markdown]
# # `FrozenConfigDict()`
#
# - Immutable and hashable type of ConfigDict
#
# - `FrozenConfigDict` is fully immutable. It contains no lists or sets (at
#   initialization, lists and sets are converted to tuples and frozensets).
#
# - The only potential sources of mutability are attributes with custom types, which
#   are not touched.
#
# - It is recommended to convert a `ConfigDict` to `FrozenConfigDict` after
#   construction if possible
#
# - `FrozenConfig` can be converted to different form such as `json`, `dict`. See example under `ConfigDict` section.
# - Args:
#     - initial_dictionary: May be one of the following:
#         - `dict`: In this case all values of initial_dictionary that are
#         dictionaries are also converted to FrozenConfigDict. If there are
#         dictionaries contained in lists or tuples, an error is raised.
#
#         - `ConfigDict`: In this case all ConfigDict attributes are also
#         converted to FrozenConfigDict.
#
#         - `FrozenConfigDict`: In this case all attributes are uncopied, and
#         only the top-level object (self) is re-addressed.
#     - `type_safe`: See ConfigDict documentation. Note that this only matters
#           if the FrozenConfigDict is converted to ConfigDict at some point.


# %%
config = {
    "meta": {"id_col": "asset_id", "use_historical": True},
    "system_log_dir": "/shared_data/CMTask5198_log_dir_1",
    "ohlcv_market_data": {
        "vendor": "CCXT",
        "mode": "trade",
        "universe": {
            "universe_version": "v7.1",
            "test_asset_id": 1467591036,
        },
    },
}
# `ConfigDict` class:
#  https://github.com/google/ml_collections/blob/master/ml_collections/config_dict/config_dict.py#L575
config = ml.ConfigDict(config)
print(config, "\n")
print(type(config))

# %%
# Converting `ConfigDict` to `FrozenConfigDict` as recommended.
frozen_config = ml.FrozenConfigDict(config)
print(frozen_config, "\n")
print(type(frozen_config))

# %%
# TAttempt on updating a `FrozenConfig` value(s) should raise an
# AttributeError exception.
# Should raise an exception. See an example below.
# frozen_config['bar_duration'] = '6T'
# frozen_config['new'] = 'new'

# %%
# If we need to update a `FrozenConfigDict` at some point, we can:
#   - convert it to a `ConfigDict`
#   - update existing value(s)
#   - convert it back to the `FrozenConfigDict`
normal_config = frozen_config.as_configdict()
print(f"Type of normal config = {type(normal_config)}")
normal_config["bar_duration"] = "6T"
frozen_config2 = ml.FrozenConfigDict(normal_config)
print(frozen_config2)

# %%
# Set a new key to the `FrozenConfig` dict.
frozen_config._frozen_setattr("hello", "val")
frozen_config
