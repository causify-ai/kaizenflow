import logging

import core.config as cconfig
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


def run_experiment(config_list: cconfig.ConfigList) -> None:
    """
    Run an experiment that fails/succeeds depending on the param `fail` stored
    inside the config.
    """
    hdbg.dassert_isinstance(config_list, cconfig.ConfigList)
    config = config_list.get_only_config()
    _LOG.info("config=\n%s", config)
    hdbg.dassert_isinstance(config, cconfig.Config)
    if config is None:
        raise ValueError("No config provided")
    if config["fail"]:
        raise ValueError("Failure")
    _LOG.info("Success")
