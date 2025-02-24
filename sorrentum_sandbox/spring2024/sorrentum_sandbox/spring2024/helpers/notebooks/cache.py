# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown] pycharm={"name": "#%% md\n"}
# # Test Cache in Jupyter Notebook

# %%
# %load_ext autoreload
# %autoreload 2

import logging

import joblib

import helpers.hcache as hcache
import helpers.hdbg as hdbg
import helpers.hprint as hprint
import helpers.hs3 as hs3

hprint.config_notebook()

# hdbg.init_logger(verbosity=logging.DEBUG)
hdbg.init_logger(verbosity=logging.INFO)
# hdbg.test_logger()
_LOG = logging.getLogger(__name__)


# %% [markdown] pycharm={"name": "#%% md\n"}
# # Define computation function

# %%
def func(a, b):
    # hello
    # assert 0
    out = a * b
    print("Multiplication: %s * %s = %s" % (a, b, out))
    return out


inputs = (1, 2)
exp_output = 2

func(*inputs)

# %%
# !ls hello/joblib/__main__*/f/

# %%
# !pip install https://github.com/aabadie/joblib-s3.git

# %%
# #!git clone git://github.com/aabadie/joblib-s3.git
# !(cd joblib-s3 && pip install -r requirements.txt .)

# %%
# import joblibs3

# joblibs3.register_s3fs_store_backend()

# # dict(compress=False, bucket=None, anon=False,
#                                #key=None, secret=None, token=None, use_ssl=True)
# dict2 = {
#     "bucket": "alphamatic-data",
#     "key": dict_["aws_access_key_id"],
#     "secret": dict_["aws_secret_access_key"],
# }
# mem = joblib.Memory('joblib_cache', backend='s3', verbose=100, compress=True,
#                  backend_options=dict2)

# %%
# hjoblib.register_s3fs_store_backend()

s3fs = hs3.get_s3fs("am")

dict2 = {
    "bucket": "alphamatic-data",
    # "key": dict_["aws_access_key_id"],
    # "secret": dict_["aws_secret_access_key"],
    "s3fs": s3fs,
}

mem = joblib.Memory(
    "joblib_cache",
    backend="s3",
    verbose=100,
    compress=True,
    backend_options=dict2,
)

# %%
# hjoblib.register_s3fs_store_backend()

s3fs = hs3.get_s3fs("am")

dict2 = {
    "bucket": "alphamatic-data",
    # "key": dict_["aws_access_key_id"],
    # "secret": dict_["aws_secret_access_key"],
    "s3fs": s3fs,
}
path = "/tmp/cache.unit_test/root.98e1cf5b88c3.app.TestCachingOnS3.test_with_caching1"


s3fs.ls(path)

# mem = joblib.Memory(path, backend='s3', verbose=100, compress=True, backend_options=dict2)


# %%
print(dict_)

# %%
# dict_["bucket"] = "alphamatic-data/tmp"

print(dict_)


# %%
def dec(func=None, val=5):
    if func is not None:
        return


# %%

# %%
dict_ = hs3.get_aws_credentials("am")
print(dict_)
# s3fs = hs3.get_s3fs("am")
# s3fs.ls("s3://alphamatic-data/tmp")

# %%
s3fs.clear_instance_cache()


# %%
# import joblib

# cachedir = "./hello"
# memory = joblib.Memory(cachedir, verbose=0)


@mem.cache()
def f(x):
    # hello
    print("Running f(%s)" % x)
    return x


f(1)

# %%
hcache.cache(set_verbose_mode=True)


def hello():
    return "hello"


hello()

# %% [markdown] pycharm={"name": "#%% md\n"}
# ## Memory cache

# %%
# !ls /app/tmp.cache.disk/joblib/

# %%
# !ls /mnt/tmpfs/tmp.cache.mem/joblib/lib

# %% pycharm={"name": "#%%\n"}
memory_cached_func = hcache._Cached(
    func, use_mem_cache=True, use_disk_cache=False
)

print(memory_cached_func.get_function_cache_info())

# cache_type = None
# memory_cached_func.clear_function_cache(cache_type)

hdbg.dassert_eq(memory_cached_func(*inputs), exp_output)
hdbg.dassert_eq(memory_cached_func.get_last_cache_accessed(), "no_cache")

hdbg.dassert_eq(memory_cached_func(*inputs), exp_output)
hdbg.dassert_eq(memory_cached_func.get_last_cache_accessed(), "mem")

print("memory caching checks passed")


# %%
def computation_function(a, b):
    # hello
    # assert 0
    out = a * b
    print("Multiplication: %s * %s = %s" % (a, b, out))
    return out


inputs = (1, 2)
exp_output = 2

hdbg.dassert_eq(memory_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(memory_cached_computation.get_last_cache_accessed(), "mem")

# %% [markdown]
# ## Disk cache

# %% pycharm={"name": "#%%\n"}
disk_cached_computation = hcache._Cached(
    computation_function, use_mem_cache=False, use_disk_cache=True
)

disk_cached_computation.clear_function_cache("disk")

hdbg.dassert_eq(disk_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(disk_cached_computation.get_last_cache_accessed(), "no_cache")

hdbg.dassert_eq(disk_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(disk_cached_computation.get_last_cache_accessed(), "disk")

print("disk caching checks passed")

# %% [markdown]
# ## Full cache

# %% pycharm={"name": "#%%\n"}
fully_cached_computation = hcache._Cached(
    computation_function, use_mem_cache=True, use_disk_cache=True
)

fully_cached_computation.clear_function_cache()

hdbg.dassert_eq(fully_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(fully_cached_computation.get_last_cache_accessed(), "no_cache")

hdbg.dassert_eq(fully_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(fully_cached_computation.get_last_cache_accessed(), "mem")

hdbg.dassert_eq(fully_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(fully_cached_computation.get_last_cache_accessed(), "mem")

print("Clear mem cache")
fully_cached_computation.clear_function_cache("mem")

hdbg.dassert_eq(fully_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(fully_cached_computation.get_last_cache_accessed(), "disk")

hdbg.dassert_eq(fully_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(fully_cached_computation.get_last_cache_accessed(), "mem")

print("full caching checks passed")

# %%
hdbg.dassert_eq(fully_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(fully_cached_computation.get_last_cache_accessed(), "mem")

# %%
# This should fail all the times, because we clear the memory cache.
fully_cached_computation.clear_function_cache("mem")
hdbg.dassert_eq(fully_cached_computation(*inputs), exp_output)
hdbg.dassert_eq(fully_cached_computation.get_last_cache_accessed(), "mem")
