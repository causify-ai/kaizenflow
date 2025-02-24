# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: Python [conda env:.conda-develop] *
#     language: python
#     name: conda-env-.conda-develop-py
# ---

# %% [markdown]
# # Description

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline

import json

import jsonpickle
import jsonpickle.ext.pandas as jsonpickle_pandas

jsonpickle_pandas.register_handlers()

import logging

import pandas as pd

import helpers.hdbg as hdbg
import helpers.henv as henv
import helpers.hplayback as hplayba
import helpers.hprint as hprint

# %%
hdbg.init_logger(verbosity=logging.INFO)

_LOG = logging.getLogger(__name__)

_LOG.info("%s", henv.get_system_signature()[0])

hprint.config_notebook()

# %%
import pandas as pd

data = {
    "Product": ["Desktop Computer", "Tablet", "iPhone", "Laptop"],
    "Price": [700, 250, 800, 1200],
}

df = pd.DataFrame(data, columns=["Product", "Price"])
df.index.name = "hello"
print(df)

# %%
# df.to_json(orient="")
df.to_dict(orient="series")

# %%
hplayba.to_python_code(df)

# %%
pd.DataFrame.from_dict(
    {
        "Product": ["Desktop Computer", "Tablet", "iPhone", "Laptop"],
        "Price": [700, 250, 800, 1200],
    }
)

# %%
use_playback = True


def F(a, b):
    if use_playback:
        playback = hplayba.Playback("assert_equal", "F", a, b)
        playback.start()
    c = a + b
    if use_playback:
        output = playback.end(c)
        res = output
    else:
        res = c
    return res


a = df
b = df
print(F(a, b))

# %%
hplayba.to_python_code(["3", 3])

# %%
hplayba.round_trip_convert(df, logging.INFO)

# %%
hplayba.round_trip_convert("hello", logging.INFO)


# %%
def F(a, b):
    return a + b


# %%
# Initialize values for unit test.
dummy_0 = r"3"
dummy_0 = jsonpickle.decode(dummy_0)
dummy_1 = r"2"
dummy_1 = jsonpickle.decode(dummy_1)
# Call function.
act = F(dummy_0, dummy_1)
# Create expected value of function output.
exp = r"5"
exp = jsonpickle.decode(exp)
# Check.
assert act == exp


# %%
class Playback:

    # def __init__(self, file_name, mode, *args, **kwargs):
    # self.args = args
    # self.kwargs = kwargs
    def __init__(self, file_name, mode, func_name, a, b):
        self.a = a
        self.b = b

    def start(self):
        self.a_json = jsonpickle.encode(self.a)
        self.b_json = jsonpickle.encode(self.b)

    def end(self, ret):
        self.ret_json = jsonpickle.encode(ret)
        output = []
        output.append("# Initialize values for unit test.")
        output.append("a = %s" % jsonpickle.decode(self.a_json))
        output.append("b = %s" % jsonpickle.decode(self.b_json))
        output.append("# Apply values.")
        output.append("act = F(a, b)")
        output.append("exp = %s" % jsonpickle.decode(self.ret_json))
        # output.append("self.assertEqual(act, exp)")
        # output.append("assert act == exp")
        output = "\n".join(output)
        print("output=", output)


# def F(a: int, b: int):
#     c = {}
#     c["pavel"] = a + b
#     return c


def F(a: int, b: int):
    playback = Playback("", "", "F", a, b)
    playback.start()
    c = {}
    c["pavel"] = a + b
    playback.end(c)
    return c


res = F(3, 4)
print(res)


# %%
class Playback:

    # def __init__(self, file_name, mode, *args, **kwargs):
    # self.args = args
    # self.kwargs = kwargs
    def __init__(self, file_name, mode, func_name, a, b):
        self.a = a
        self.b = b

    def start(self):
        self.a_json = jsonpickle.encode(self.a)
        self.b_json = jsonpickle.encode(self.b)

    def end(self, ret):
        self.ret_json = jsonpickle.encode(ret)
        output = []
        output.append("# Initialize values for unit test.")
        # output.append("a = %s" % jsonpickle.decode(self.a_json))
        # output.append("b = %s" % jsonpickle.decode(self.b_json))
        output.append("a = r'%s'" % self.a_json)
        output.append("a = jsonpickle.decode(a)")
        output.append("b = r'%s'" % self.b_json)
        output.append("b = jsonpickle.decode(b)")
        output.append("# Apply values.")
        # output.append("act = F(a, b)[1]")
        output.append("act = F(a, b)")
        output.append("exp = r'%s'" % self.ret_json)
        output.append("exp = jsonpickle.decode(exp)")
        # output.append("self.assertEqual(act, exp)")
        output.append("assert act.equals(exp)")
        # output.append("assert act == exp")
        output = "\n".join(output)
        return output


# def F(a: int, b: int):
#     c = {}
#     c["pavel"] = a + b
#     return c

use_playback = True


def F(a: pd.DataFrame, b: pd.DataFrame):
    if use_playback:
        playback = Playback("", "", "F", a, b)
        playback.start()
    # c = {}
    # c["pavel"] = a + b
    c = a + b
    if use_playback:
        output = playback.end(c)
        res = output, c
    else:
        res = c
    return res


a = pd.DataFrame({"Price": [700, 250, 800, 1200]})
b = pd.DataFrame({"Price": [1, 1, 1, 1]})

res = F(a, b)
output = res[0]
print(output)
exec(output)

# %%
# Initialize values for unit test.
a = r'{"py/object": "pandas.core.frame.DataFrame", "values": "Price\n700\n250\n800\n1200\n", "txt": true, "meta": {"dtypes": {"Price": "int64"}, "index": "{\"py/object\": \"pandas.core.indexes.range.RangeIndex\", \"values\": \"[0, 1, 2, 3]\", \"txt\": true, \"meta\": {\"dtype\": \"int64\", \"name\": null}}"}}'
a = jsonpickle.decode(a)

# %%
a = pd.DataFrame({"Price": [700, 250, 800, 1200]})

# round_trip(a)
frozen = jsonpickle.encode(a)
print(frozen)
print("frozen2 = '%s'" % frozen)
# print("frozen = '%s'" % frozen)
assert 0
#
print("frozen=")
print(json_pretty_print(frozen))
#
obj2 = jsonpickle.decode(frozen)

# %%
frozen2 = r'{"py/object": "pandas.core.frame.DataFrame", "values": "Price\n700\n250\n800\n1200\n", "txt": true, "meta": {"dtypes": {"Price": "int64"}, "index": "{\"py/object\": \"pandas.core.indexes.range.RangeIndex\", \"values\": \"[0, 1, 2, 3]\", \"txt\": true, \"meta\": {\"dtype\": \"int64\", \"name\": null}}"}}'
print(frozen2)
# print("\n")
# print(frozen)
if False and isinstance(frozen2, str):
    # print(frozen2[61])
    # assert 0
    frozen2 = json.loads(frozen2)
    print(frozen2)
frozen2 = jsonpickle.decode(frozen2)

# %%
a = """{"py/object": "pandas.core.frame.DataFrame", "values": "Price\n700\n250\n800\n1200\n", "txt": true, "meta": {"dtypes": {"Price": "int64"}, "index": "{\"py/object\": \"pandas.core.indexes.range.RangeIndex\", \"values\": \"[0, 1, 2, 3]\", \"txt\": true, \"meta\": {\"dtype\": \"int64\", \"name\": null}}"}}"""
a = jsonpickle.decode(a)

# %%
# Initialize values for unit test.
a = '{"py/object": "pandas.core.frame.DataFrame", "values": "Price\n700\n250\n800\n1200\n", "txt": true, "meta": {"dtypes": {"Price": "int64"}, "index": "{"py/object": "pandas.core.indexes.range.RangeIndex", "values": "[0, 1, 2, 3]", "txt": true, "meta": {"dtype": "int64", "name": null}}"}}'
a = jsonpickle.decode(a)
b = '{"py/object": "pandas.core.frame.DataFrame", "values": "Price\n1\n1\n1\n1\n", "txt": true, "meta": {"dtypes": {"Price": "int64"}, "index": "{"py/object": "pandas.core.indexes.range.RangeIndex", "values": "[0, 1, 2, 3]", "txt": true, "meta": {"dtype": "int64", "name": null}}"}}'
b = jsonpickle.decode(b)
# Apply values.
act = F(a, b)
exp = '{"py/object": "pandas.core.frame.DataFrame", "values": "Price\n701\n251\n801\n1201\n", "txt": true, "meta": {"dtypes": {"Price": "int64"}, "index": "{"py/object": "pandas.core.indexes.range.RangeIndex", "values": "[0, 1, 2, 3]", "txt": true, "meta": {"dtype": "int64", "name": null}}"}}'
exp = jsonpickle.decode(exp)
assert act == exp

# %%
# Initialize values for unit test.
a = 3
b = 4
# Apply values.
act = F(a, b)
exp = {"pavel": 7}
assert act == exp

# %%
df2 = round_trip(df)


# %%
class Thing:
    def __init__(self, name):
        self.name = name


obj = Thing("Awesome")

round_trip(obj)


# %%
def test(a: int, b: int):
    print(round_trip(a))


test("strunz", 6)
test(4, 6)
test(["hello"], 6)

# %%
df.index.dtype  #

# %%
df.dtypes

# %%
# import io
# import io.StringIO
# from io import StringIO

# output = StringIO.StringIO()

orient = "columns"
# orient = "split"
# orient = "records"
# orient = "table"
df_as_str = df.to_json(orient=orient)

# split
# records
# index
# values
# table
# columns (the default format)

python_code = []
target_var = "df_as_str"
python_code.append("%s = %s" % (target_var, df_as_str))
python_code.append("%s.index.name = '%s'" % (target_var, df.index.name))
python_code = "\n".join(python_code)
print(python_code)

exec(python_code)

# %%
airr = eval(df_as_str)
df2 = pd.DataFrame.from_dict(arr, orient="columns")
df2.index.name

# %%
