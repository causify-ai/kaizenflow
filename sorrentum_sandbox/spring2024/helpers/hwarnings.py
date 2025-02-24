"""
When this module is imported certain annoying warnings are disabled.

Import as:

import helpers.hwarnings as hwarnin
"""

if False:
    _WARNING = "\033[33mWARNING\033[0m"
    print(f"{_WARNING}: Disabling annoying warnings")

# Avoid dependency from other `helpers` modules, such as `helpers.hprint`, to
# prevent import cycles.

import warnings

# From https://docs.python.org/3/library/warnings.html

# TODO(gp): For some reason "once" doesn't work, so we ignore all of the warnings.
action = "ignore"

try:
    import statsmodels

    _HAS_STATSMODELS = True
except ImportError:
    _HAS_STATSMODELS = False


if _HAS_STATSMODELS:
    # /venv/lib/python3.8/site-packages/statsmodels/tsa/stattools.py:1910:
    # InterpolationWarning: The test statistic is outside of the range of p-values
    # available in the look-up table. The actual p-value is greater than the
    # p-value returned.
    from statsmodels.tools.sm_exceptions import InterpolationWarning

    # warnings.simplefilter("ignore", category=InterpolationWarning)

    # /venv/lib/python3.8/site-packages/statsmodels/tsa/stattools.py:1906:
    # InterpolationWarning: The test statistic is outside of the range of p-values
    # available in the look-up table. The actual p-value is smaller than the
    # p-value returned.
    warnings.filterwarnings(
        action,
        category=InterpolationWarning,
        module=".*statsmodels.*",
        lineno=1906,
        append=False,
    )

    warnings.filterwarnings(
        action,
        category=InterpolationWarning,
        module=".*statsmodels.*",
        lineno=1910,
        append=False,
    )


# /venv/lib/python3.8/site-packages/ipykernel/ipkernel.py:283:
# DeprecationWarning: `should_run_async` will not call `transform_cell`
# automatically in the future. Please pass the result to `transformed_cell`
# argument and any exception that happen during thetransform in
# `preprocessing_exc_tuple` in IPython 7.17 and above.
#  and should_run_async(code)
warnings.filterwarnings(
    action,
    category=DeprecationWarning,
    module=".*ipykernel.*",
    lineno=283,
    append=False,
)


# TODO(gp): Add this TqdmExperimentalWarning

try:
    import pandas as pd

    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False


if _HAS_PANDAS:
    pd.set_option("mode.chained_assignment", None)
    # TODO(gp): We should fix the issues and re-enable.
    # See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
    #   row["net_cost"] -= cost
    # /app/amp/oms/order_processing/order_processor.py:376: SettingWithCopyWarning:
    # A value is trying to be set on a copy of a slice from a DataFrame

    # /venv/lib/python3.8/site-packages/pandas/io/sql.py:761: UserWarning: pandas
    # only support SQLAlchemy connectable(engine/connection) ordatabase string URI or
    # sqlite3 DBAPI2 connectionother DBAPI2 objects are not tested, please consider
    # using SQLAlchemy
    #
    # This seems a false alarm:
    # https://github.com/pandas-dev/pandas/issues/45660#issuecomment-1077355514
    warnings.filterwarnings(
        action,
        category=UserWarning,
        module=".*pandas.*",
        lineno=761,
        append=False,
    )

    # run_leq_node:  38%|███▊      | 3/8 [00:05<00:09,  1.98s/it]/app/amp/helpers/hdbg.py:309: PerformanceWarning: indexing past lexsort depth may impact performance.
    #  cond = value in valid_values
    warnings.filterwarnings(
        action,
        category=pd.errors.PerformanceWarning,
        module=".*hdbg.py.*",
        lineno=309,
        append=False,
    )

    # run_leq_node:   0%|          | 0/8 [00:00<?, ?it/s]/app/amp/helpers/hpandas.py:1069: FutureWarning: The frame.append method is deprecated and will be removed from pandas in a future version. Use pandas.concat instead.
    # mem_use_df = mem_use_df.append(mem_use_df_total.T)
    warnings.filterwarnings(
        action,
        category=FutureWarning,
        module=".*hpandas.*",
        lineno=1069,
        append=False,
    )

    # /app/amp/oms/portfolio.py:818: FutureWarning: pandas.Int64Index is deprecated and will be removed from pandas in a future version. Use pandas.Index with the appropriate dtype instead.
    # hdbg.dassert_isinstance(idx, pd.Int64Index)
    warnings.filterwarnings(
        action,
        category=FutureWarning,
        module=".*portfolio.py.*",
        lineno=818,
        append=False,
    )

    # run_leq_node:  38%|███▊      | 3/8 [00:07<00:12,  2.46s/it]/app/amp/helpers/hdbg.py:309: PerformanceWarning: indexing past lexsort depth may impact performance.
    # cond = value in valid_values
    warnings.filterwarnings(
        action,
        category=pd.errors.PerformanceWarning,
        module=".*hdbg.py.*",
        lineno=309,
        append=False,
    )

    # /venv/lib/python3.8/site-packages/sklearn/preprocessing/_data.py:2590: UserWarning: n_quantiles (1001) is greater than the total number of samples (19). n_quantiles is set to n_samples.
    warnings.filterwarnings(
        action,
        category=UserWarning,
        module=".*_data.py.*",
        lineno=2590,
        append=False,
    )
