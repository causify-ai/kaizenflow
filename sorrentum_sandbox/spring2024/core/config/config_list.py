"""
Import as:

import core.config.config_list as ccocolis
"""

import copy
from typing import Iterator, List, Optional

import core.config.config_ as cconconf
import core.config.config_utils as ccocouti
import helpers.hdbg as hdbg
import helpers.hprint as hprint


class ConfigList:
    """
    Contain a list of configs.

    Other classes can derive from this class adding more objects (e.g.,
    a `System`).
    """

    def __init__(self, configs: Optional[List[cconconf.Config]] = None) -> None:
        if configs is None:
            configs = []
        ccocouti.validate_configs(configs)
        self._configs: List[cconconf.Config] = configs

    def __len__(self) -> int:
        return len(self._configs)

    def __getitem__(self, key: int) -> cconconf.Config:
        hdbg.dassert_isinstance(key, int)
        hdbg.dassert_lte(0, key)
        hdbg.dassert_lt(key, len(self._configs))
        return self._configs[key]

    def __iter__(self) -> Iterator[cconconf.Config]:
        return iter(self._configs)

    # TODO(gp): Improve str if needed.
    def __str__(self) -> str:
        """
        Print a list of configs into a readable string.
        """
        txt = []
        txt.append("# %s" % hprint.to_object_str(self))
        txt.append(hprint.indent(ccocouti.configs_to_str(self.configs)))
        txt = "\n".join(txt)
        return txt

    @property
    def configs(self) -> List[cconconf.Config]:
        return self._configs

    @configs.setter
    def configs(self, configs: List[cconconf.Config]) -> None:
        ccocouti.validate_configs(configs)
        self._configs = configs

    def get_only_config(self) -> cconconf.Config:
        """
        Return the only config.

        This is an helper used when we pass around a ConfigList storing
        a single config, since we want to carry additional information
        (e.g., `System` in `SystemConfigList`) together with the config.
        """
        hdbg.dassert_eq(len(self._configs), 1)
        config = self._configs[0]
        hdbg.dassert_isinstance(config, cconconf.Config)
        return config

    # TODO(gp): For some reason it doesn't work as classmethod.
    def copy(self) -> "ConfigList":
        return copy.deepcopy(self)

    def validate_config_list(self) -> None:
        """
        Assert if the list of configs contains duplicates.
        """
        ccocouti.validate_configs(self.configs)
