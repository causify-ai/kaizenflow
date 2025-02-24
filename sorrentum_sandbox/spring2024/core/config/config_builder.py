"""
Import as:

import core.config.config_builder as ccocobui
"""

import copy
import importlib
import logging
import os
import re
from typing import Dict, Optional, cast

import core.config.config_ as cconconf
import core.config.config_list as ccocolis
import core.config.config_utils as ccocouti
import helpers.hdbg as hdbg
import helpers.hdocker as hdocker
import helpers.hpickle as hpickle

_LOG = logging.getLogger(__name__)


# TODO(gp): This looks like it should go in `config_list_builder.py`.
def get_config_list_from_builder(config_builder: str) -> ccocolis.ConfigList:
    """
    Execute Python code `config_builder()` to build configs.

    The problem that we need to solve is how to pass builders across different
    executable (e.g., the simulator runs multiple tiles in parallel through
    multiple executables `dataflow/backtest/run_config_list.py`) so we can't
    use anything else than a string that is converted into a function as late
    as possible.

    :param config_builder: full Python command to create the configs.
        E.g., `nlp.build_config_list.build_PTask1088_config_list()`
    """
    _LOG.info("Executing function '%s'", config_builder)
    # `config_builder` looks like:
    #   `nlp.build_config_list.build_PTask1088_config_list()`
    # or
    #   `dataflow.pipelines.E8.E8d_configs.build_rc1_config_list("eg_v2_0-all.5T.2015_2022")`
    m = re.match(r"^(\S+)\.(\S+)\((.*)\)$", config_builder)
    hdbg.dassert(m, "config_builder='%s'", config_builder)
    # TODO(gp): Fix this.
    m = cast(re.Match, m)
    import_, function, args = m.groups()
    _LOG.debug("import=%s", import_)
    _LOG.debug("function=%s", function)
    _LOG.debug("args=%s", args)
    # Import the needed module.
    imp = importlib.import_module(import_)
    # Force the linter not to remove this import which is needed in the following
    # eval.
    _ = imp
    python_code = "imp.%s(%s)" % (function, args)
    _LOG.debug("executing '%s'", python_code)
    config_list = eval(python_code)
    _LOG.debug("type(config_list)=%s", str(type(config_list)))
    hdbg.dassert_isinstance(config_list, ccocolis.ConfigList)
    config_list.validate_config_list()
    return config_list


# #############################################################################


def get_notebook_config(
    config_file_path: Optional[str] = None,
) -> Optional[cconconf.Config]:
    """
    Get the config from the environment variables or from a file.

    :param config_file_path: path to a config file
    :return: the config or `None` if env vars are not set and `config_file_path`
        is None.
    """
    config = get_config_from_env()
    if config is not None:
        _LOG.info("Using config from env vars")
    elif config_file_path is not None:
        _LOG.info(
            "Config env vars not set. Using config from the pickle file: %s",
            config_file_path,
        )
        config_file_path = hdocker.replace_shared_root_path(config_file_path)
        config = hpickle.from_pickle(config_file_path)
        # To run locally we need to replace path to the shared folder, e.g.,
        # `/data/shared` -> `/shared_data`.
        config = ccocouti.replace_shared_dir_paths(config)
    else:
        config = None
        _LOG.warning("No config found, returning None")
    return config


# #############################################################################


def patch_config_list(
    config_list: ccocolis.ConfigList, experiment_list_params: Dict[str, str]
) -> ccocolis.ConfigList:
    """
    Patch the configs with information needed to run.

    This function is used by `run_notebook.py` and `run_config_list.py`
    to pass information through the `Config` to the process running the
    experiment.
    """
    hdbg.dassert_isinstance(config_list, ccocolis.ConfigList)
    # Transform all the configs inside the config_list.
    configs_out = []
    for idx, config in enumerate(config_list.configs):
        config = config.copy()
        # Add `idx` for book-keeping.
        config[("backtest_config", "id")] = idx
        # Inject all the experiment_list_params in the config.
        for key in sorted(experiment_list_params.keys()):
            config[("backtest_config", key)] = experiment_list_params[key]
        # Inject the dst dir of the entire experiment list.
        hdbg.dassert_in("dst_dir", experiment_list_params)
        dst_dir = experiment_list_params["dst_dir"]
        # Add experiment result dir.
        dst_subdir = f"result_{idx}"
        experiment_result_dir = os.path.join(dst_dir, dst_subdir)
        config[
            ("backtest_config", "experiment_result_dir")
        ] = experiment_result_dir
        #
        configs_out.append(config)
    # Create a copy of the ConfigList and update the internal `configs`.
    config_list_out = copy.deepcopy(config_list)
    config_list_out.configs = configs_out
    hdbg.dassert_isinstance(config_list_out, ccocolis.ConfigList)
    return config_list_out


def get_config_from_experiment_list_params(
    idx: int, experiment_list_params: Dict[str, str]
) -> ccocolis.ConfigList:
    """
    Get the `idx`-th config (stored as a `ConfigList`) built from the
    experiment list params, which includes `config_builder`

    E.g., `dataflow.pipelines.E8d.E8d_configs.build_rc1_config_list("eg_v2_0-all.5T.2015_2022")`

    This is used by `run_config_stub.py` using the params from command line.

    :param experiment_list_params: parameters from `run_config_stub.py`, e.g.,
        `config_builder`, `experiment_builder`, `dst_dir`.
    """
    config_builder = experiment_list_params["config_builder"]
    # Build all the configs.
    config_list = get_config_list_from_builder(config_builder)
    # Patch the configs with experiment metadata.
    config_list = patch_config_list(config_list, experiment_list_params)
    # Create a config_list with a single config corresponding to the selected one.
    config_list_out = config_list.copy()
    config = config_list.configs[idx]
    config_list_out.configs = [config]
    return config_list_out


# #############################################################################


# TODO(Grisha): allow reading config from a file using the
# `__NOTEBOOK_CONFIG_PATH__` environment variable.
# TODO(gp): rename to get_experiment_config_from_env since it's a particular
# case of passing certain params.
def get_config_from_env() -> Optional[cconconf.Config]:
    """
    Build a config passed through environment vars, if possible, or return
    `None`.
    """
    config_vars = [
        "__CONFIG_BUILDER__",
        "__CONFIG_IDX__",
        "__CONFIG_DST_DIR__",
        "__NOTEBOOK_CONFIG_PATH__",
    ]
    # Check the existence of any config var in env.
    if not any(var in os.environ for var in config_vars):
        _LOG.debug("No CONFIG* env vars for building config: returning")
        config = None
        return config
    _LOG.warning("Found config vars in environment")
    hdbg.dassert(
        all(var in os.environ for var in config_vars),
        "Some config vars '%s' were defined, but not all"
        % (", ".join(config_vars)),
    )
    _LOG.info(
        "__NOTEBOOK_CONFIG_PATH__: %s", os.environ["__NOTEBOOK_CONFIG_PATH__"]
    )
    params = {}
    #
    config_idx = int(os.environ["__CONFIG_IDX__"])
    _LOG.info("config_idx=%s", config_idx)
    #
    config_builder = os.environ["__CONFIG_BUILDER__"]
    _LOG.info("config_builder=%s", config_builder)
    params["config_builder"] = config_builder
    #
    # TODO(gp): -> config_dst_dir?
    dst_dir = os.environ["__CONFIG_DST_DIR__"]
    _LOG.info("dst_dir=%s", dst_dir)
    params["dst_dir"] = dst_dir
    #
    config_list = get_config_from_experiment_list_params(config_idx, params)
    config = config_list.get_only_config()
    return config
