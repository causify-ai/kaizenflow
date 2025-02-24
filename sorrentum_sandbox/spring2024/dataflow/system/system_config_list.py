"""
Import as:

import dataflow.system.system_config_list as dtfssycoli
"""

import copy
from typing import Optional

import core.config as cconfig
import dataflow.system.system as dtfsyssyst
import helpers.hdbg as hdbg
import helpers.hprint as hprint

# TODO(gp): @all add unit tests for this.
# TODO(gp): Improve str if needed.
class SystemConfigList(cconfig.ConfigList):
    """
    Store a list of configs corresponding to a given System.
    """

    def __init__(self) -> None:
        super().__init__()
        self._system: Optional[dtfsyssyst.System] = None

    def __str__(self) -> str:
        """
        Print a list of configs into a readable string.
        """
        txt = []
        txt.append("# %s" % hprint.to_object_str(self))
        txt.append(hprint.indent(str(self._system)))
        txt.append(hprint.indent(super().__str__()))
        txt = "\n".join(txt)
        return txt

    @property
    def system(self) -> dtfsyssyst.System:
        hdbg.dassert_is_not(self._system, None)
        return self._system

    @system.setter
    def system(self, system: dtfsyssyst.System) -> None:
        hdbg.dassert_isinstance(system, dtfsyssyst.System)
        self._system = system

    def copy(self) -> "SystemConfigList":
        return copy.deepcopy(self)

    @classmethod
    def from_system(cls, system: dtfsyssyst.System) -> "SystemConfigList":
        """
        Build a SystemConfigList from a System.
        """
        hdbg.dassert_isinstance(system, dtfsyssyst.System)
        #
        system_config_list = cls()
        system_config_list.system = system
        system_config_list.configs = [system.config]
        return system_config_list


# #############################################################################
# Utils
# #############################################################################


def build_tile_config_list(
    system: dtfsyssyst.System,
) -> SystemConfigList:
    """
    Define and fill `SystemConfigList` with universe and periods.
    """
    hdbg.dassert_isinstance(system, dtfsyssyst.System)
    system_config_list = SystemConfigList.from_system(system)
    #
    system_config_list = (
        cconfig.build_config_list_with_tiled_universe_and_periods(
            system_config_list
        )
    )
    hdbg.dassert_isinstance(system_config_list, SystemConfigList)
    return system_config_list
