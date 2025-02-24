"""
Import as:

import core.config.config_ as cconconf
"""

# This file is called `config_.py` and not `config.py` to avoid circular
# imports from the fact that also the package `core/config` can be imported as
# `import config`.

import collections
import copy
import inspect
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg
import helpers.hdict as hdict
import helpers.hintrospection as hintros
import helpers.hio as hio
import helpers.hpandas as hpandas
import helpers.hpickle as hpickle
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)

# Mute this module unless we want to debug it.
# NOTE: Keep this enabled when committing.
_LOG.setLevel(logging.INFO)

# Disable _LOG.debug.
# _LOG.debug = lambda *_: 0


# Set config version.
# See `docs/kaizenflow/ck.system_config.explanation.md` for detailed info.
CONFIG_VERSION = "v3"


# Placeholder value used in configs, when configs are built in multiple phases.
DUMMY = "__DUMMY__"


# # Design notes:
#
# - A Config is a recursive structure of Configs
#   - It handles compounded keys, update_mode, clobber_mode
#   - Each Config uses internally an _OrderedDict
# - A _OrderedDict enforces writing / reading policies
#   - It only allow one key lookup
#   - It can contain more Configs (but no dict)
# - We use these two different data structures to clearly separate when we want
#   to use compounded keys or scalar keys
# - We don't allow `dict` in Config as leaves
#   - We assume that a dict leaf represents a Config for an object
#   - `dict` are valid in composed data structures, e.g., list, tuples
# - We require the user to explicitly mark a value from the config as used,
#   when we don't want subsequent writes to change its value
#   - Thus, by default __getitem__() has mark_as_use=False and the user needs
#     to explicitly use `get_and_mark_as_used()` method

# # Issues with tracking accurately write-after-use:
#
# - Nested config add extra complexity mixing Dict and Config
#   - An alternative design could have been that `Config` derives from
#     `_OrderedConfig` using default value to create the keys on the fly without
#     compound key notation
#   - it would be simpler if a `Config` held a `_OrderedConfig` and that
#     contained only other `_OrderedConfig` (instead of `dict`)
# - What happens when the user does `**...to_dict()`, should it be considered
#   all read?
#   - Probably yes, and that's what the user likely intend
# - What happens if the user does `read["key1"]` and that is a Config, should
#   be considered all read?
#   - Probably yes, but that's not what the user intends to do when doing
#     `read["key1"]["key2"]` instead of `read["key1", "key2"]`?
# - What happens when printing a `Config`?
#   - That would be considered a read, but it's not what the user intends


# Keys in a Config are strings or ints.
ScalarKey = Union[str, int]

# Valid type of each component of a key.
# TODO(gp): Not sure if ScalarKeyValidTypes can be derived from ScalarKey.
ScalarKeyValidTypes = (str, int)

# A scalar or compound key can be used to access a Config.
CompoundKey = Union[str, int, Iterable[str], Iterable[int]]

# The key can be anything, besides a dict.
ValueTypeHint = Any


_NO_VALUE_SPECIFIED = "__NO_VALUE_SPECIFIED__"

# `update_mode` specifies how values are written when a key already exists
#   inside a Config
# The modes are:
#   - `None`: use the default behavior specified in the constructor
#   - `assert_on_overwrite`: don't allow any overwrite (in order to be safe)
#       - if a key already exists, then assert
#       - if a key doesn't exist, then assign the new value
#   - `overwrite`: assign the key, whether the key exists or not
#   - `assign_if_missing`: this mode is used to complete a config, preserving
#     what already exists
#       - if a key already exists, leave the old value and raise a warning
#       - if a key doesn't exist, then assign the new value
_VALID_UPDATE_MODES = (
    "assert_on_overwrite",
    "overwrite",
    "assign_if_missing",
)

# `clobber_mode` specifies whether values can be updated after they have been
#   used
# The modes are:
#   - `allow_write_after_use`: allow to write a key even after that key was
#     already used. A warning is issued in this case
#   - `assert_on_write_after_use`: assert if an outside user tries to write a
#     value that has already been used
_VALID_CLOBBER_MODES = (
    "allow_write_after_use",
    "assert_on_write_after_use",
)

# `report_mode` specifies how to report an error
# The modes are:
#   - `none` (default): only report the exception from `_get_item()`
#   - `verbose_log_error`: report the full key and config in the log
#   - `verbose_exception`: report the full key and config in the exception
#     (e.g., used in the unit tests)
_VALID_REPORT_MODES = ("verbose_log_error", "verbose_exception", "none")


# `unused_variables_mode` specifies how to treat unused variables when
# `check_unused_variables()` is called. This method should be called
# when all the objects using the Config have been built and thus we are
# guaranteed that everything is stable.
# The modes are:
#   - `warning_on_error` (default): report a warning for unused variables
#   - `assert_on_error`: raise an error for unused variables
_VALID_UNUSED_VARIABLES_MODES = ("warning_on_error", "assert_on_error")

# #############################################################################
# _ConfigWriterInfo
# #############################################################################


class OverwriteError(RuntimeError):
    """
    Trying to overwrite a value.
    """


class ClobberError(RuntimeError):
    """
    Trying to overwrite a value that has already been read.
    """


# TODO(gp): It seems that one can't derive from a typed data structure.
# _OrderedDictType = collections.OrderedDict[ScalarKey, Any]
# TODO(gp): Consider using a dict since after Python3.6 it is ordered.
_OrderedDictType = collections.OrderedDict


class _ConfigWriterInfo:
    """
    Store information on the function that writes a value into a Config.
    """

    def __init__(self):
        # Capture information about who is constructing this object.
        self._full_traceback = self._get_full_traceback()
        self._shorthand_caller = self._get_shorthand_caller()

    def __str__(self) -> str:
        return self._shorthand_caller

    def __repr__(self) -> str:
        return self._full_traceback

    @staticmethod
    def _get_full_traceback() -> str:
        """
        Return full traceback as str.

        Example of a traceback string:
        ```
        File "/usr/lib/python3.8/unittest/case.py", line 633, in _callTestMethod
            method()
        File "/app/core/config/test/test_config.py", line 2037, in test4
            actual_value = test_config.get_and_mark_as_used("key2")
        ...
        File "/app/core/config/config_.py", line 188, in _get_full_traceback
            return hintros.stacktrace_to_str()
        File "/app/helpers/hintrospection.py", line 254, in stacktrace_to_str
            txt = traceback.format_stack()
        ```
        """
        return hintros.stacktrace_to_str()

    @staticmethod
    def _get_shorthand_caller() -> str:
        """
        Return a shorthand for the latest outside caller of the function.

        The shorthand includes:
        - file name
        - line where the function is called
        - name of the caller

        Example of the output:

        'dataflow/system/system_builder_utils.py::49::get_config_template'
        """
        stack = inspect.stack()
        # Select the current filename.
        filename = stack[0].filename
        # Select the latest caller that is outside of the current module.
        # Due to abundance of internal recursive calls, we want to get the first
        # call outside of the current module. E.g. for the stacktrace:
        # ```
        # FrameInfo(frame=<frame at 0x7fdce4734230, file '/app/core/config/test/test_config.py', line 2037, code test4>, filename='/app/core/config/test/test_config.py', lineno=2037, function='test4', code_context=['        actual_value = test_config.get_and_mark_as_used("key2")\n'], index=0)
        # FrameInfo(frame=<frame at 0x4cafb50, file '/app/core/config/config_.py', line 1198, code _get_item>, filename='/app/core/config/config_.py', lineno=1198, function='_get_item', code_context=['        ret = self._config.__getitem__(key, mark_key_as_used=mark_key_as_used)  # type: ignore\n'], index=0)
        # FrameInfo(frame=<frame at 0x7fdce471edd0, file '/app/core/config/config_.py', line 475, code _mark_as_used>, filename='/app/core/config/config_.py', lineno=475, function='_mark_as_used', code_context=['            writer = _ConfigWriterInfo()\n'], index=0)
        # FrameInfo(frame=<frame at 0x4d0cd70, file '/app/core/config/config_.py', line 178, code __init__>, filename='/app/core/config/config_.py', lineno=178, function='__init__', code_context=['        self._shorthand_caller = self._get_shorthand_caller()\n'], index=0)
        # FrameInfo(frame=<frame at 0x7fdce471e230, file '/app/core/config/config_.py', line 210, code _get_shorthand_caller>, filename='/app/core/config/config_.py', lineno=207, function='_get_shorthand_caller', code_context=['        stack = inspect.stack()\n'], index=0)
        # ```
        # We select the first one with a different file, i.e.:
        # `FrameInfo(frame=<frame at 0x7fdce4734230, file '/app/core/config/test/test_config.py', line 2037, code test4>, filename='/app/core/config/test/test_config.py', lineno=2037, function='test4', code_context=['        actual_value = test_config.get_and_mark_as_used("key2")\n'], index=0)`
        #
        caller = next(call for call in stack if call.filename != filename)
        latest_outside_caller = (
            f"{caller.filename}::{caller.lineno}::{caller.function}"
        )
        return latest_outside_caller


# #############################################################################
# _OrderedConfig
# #############################################################################


class _OrderedConfig(_OrderedDictType):
    """
    A dict data structure that allows to read and write with strict policies.

    An `_OrderedConfig` is a recursive structure with:
    - any Python scalar
    - a `Config` (which wraps another `_OrderedConfig`)
    - Python dicts are not allowed since we want to use `Config`
    - any other Python data structure (e.g., list, tuple)
    """

    # /////////////////////////////////////////////////////////////////////////////
    # Set.
    # /////////////////////////////////////////////////////////////////////////////

    def __setitem__(
        self,
        key: ScalarKey,
        val: ValueTypeHint,
        *,
        update_mode: Optional[str] = "overwrite",
        clobber_mode: Optional[str] = "allow_write_after_use",
    ) -> None:
        """
        Each val is encoded as a tuple (marked_as_used, writer, value) where:

        - marked_as_used: stores whether the value has been already used and thus
          needs to be protected from successive writes, depending on
          clobber_mode
        - writer: stores the stacktrace of the function that used the value.
          Uses `_ConfigWriterInfo` if `marked_as_used` == True, otherwise `None`
        - value: stores the actual value

        For `update_mode` and `clobber_mode` see module docstring.

        Since this class is supposed to be found at leaves level, by default
        the modes are set up as less restrictive, but are inherited from
        `Config` in most actual uses.
        """
        _LOG.debug(hprint.to_str("key val update_mode clobber_mode"))
        hdbg.dassert_isinstance(key, ScalarKeyValidTypes)
        # TODO(gp): Difference between amp and cmamp.
        if isinstance(val, dict):
            raise ValueError(
                f"For key='{key}' val='{val}' should be a Config and not a dict"
            )
        # 1) Handle `update_mode`.
        is_key_present = key in self
        _LOG.debug(hprint.to_str("is_key_present"))
        _LOG.debug("Checking update_mode...")
        if update_mode == "assert_on_overwrite":
            # It is not allowed to overwrite a value.
            if is_key_present:
                # Key already exists, thus we need to assert.
                marked_as_used, writer, old_val = super().__getitem__(key)
                msg = []
                msg.append(
                    f"Trying to overwrite old value '{old_val}' with new value '{val}'"
                    f" for key '{key}' when update_mode={update_mode}"
                )
                msg.append("self=\n" + hprint.indent(str(self)))
                msg = "\n".join(msg)
                raise OverwriteError(msg)
            else:
                # Key doesn't exist, thus assign the value.
                assign_new_value = True
        elif update_mode == "overwrite":
            # Assign the value in any case.
            assign_new_value = True
        elif update_mode == "assign_if_missing":
            if is_key_present:
                # Key already exists, thus keep the old value and issue a warning
                # that we are not writing.
                marked_as_used, writer, old_val = super().__getitem__(key)
                msg: List[str] = []
                msg.append(
                    f"Value '{old_val}' for key '{key}' already exists."
                    f" Not overwriting with '{val}' since update_mode={update_mode}"
                )
                msg = "\n".join(msg)
                _LOG.warning(msg)
                assign_new_value = False
            else:
                # Key doesn't exist, thus assign the value.
                assign_new_value = True
        else:
            raise RuntimeError(f"Invalid update_mode='{update_mode}'")
        # 2) Handle `clobber_mode`.
        _LOG.debug("Checking clobber_mode...")
        if clobber_mode == "allow_write_after_use":
            # Nothing to do.
            pass
        elif clobber_mode == "assert_on_write_after_use":
            if is_key_present:
                marked_as_used, writer, old_val = super().__getitem__(key)
                # Sometimes it's not possible to compare objects, e.g., when
                # assigning (e.g., Series).
                try:
                    is_been_changed = old_val != val
                except ValueError as e:
                    _LOG.debug(
                        "Can't compute is_been_changed, assuming False: "
                        "exception=%s ",
                        str(e),
                    )
                    is_been_changed = True
                _LOG.debug(
                    hprint.to_str("marked_as_used old_val is_been_changed")
                )
                if marked_as_used and is_been_changed:
                    # The value has already been read and we are trying to change
                    # it, so we need to assert.
                    msg: List[str] = []
                    msg.append(
                        f"Trying to overwrite old value '{old_val}' with new value '{val}'"
                        f" for key '{key}' with clobber_mode={clobber_mode}"
                    )
                    msg.append("self=\n" + hprint.indent(str(self)))
                    msg = "\n".join(msg)
                    raise ClobberError(msg)
        else:
            raise RuntimeError(f"Invalid clobber_mode='{clobber_mode}'")
        # 3) Assign the value, if needed.
        _LOG.debug(hprint.to_str("assign_new_value"))
        if assign_new_value:
            if is_key_present:
                # If replacing value, use the same `mark_as_used` as the old value.
                marked_as_used, writer, old_val = super().__getitem__(key)
                _ = old_val
            else:
                # The key was not present, so we just mark it not read yet.
                marked_as_used = False
                writer = None
            # Check if the value has already been marked as used.
            #  Required for `copy()` method.
            if isinstance(val, tuple) and val and isinstance(val[0], bool):
                # Set new `marked_as_used` status with the same value.
                val = (marked_as_used, writer, val[2])
                super().__setitem__(key, val)
            else:
                super().__setitem__(key, (marked_as_used, writer, val))

    # /////////////////////////////////////////////////////////////////////////////
    # Get.
    # /////////////////////////////////////////////////////////////////////////////

    def __getitem__(
        self, key: ScalarKey, *, mark_key_as_used: bool = False
    ) -> ValueTypeHint:
        """
        Retrieve the value corresponding to `key`.
        """
        hdbg.dassert_isinstance(key, ScalarKeyValidTypes)
        # Retrieve the value from the dictionary itself.
        marked_as_used, writer, val = super().__getitem__(key)
        if mark_key_as_used:
            self._mark_as_used(key)
        return val

    # /////////////////////////////////////////////////////////////////////////////
    # Print.
    # /////////////////////////////////////////////////////////////////////////////

    def __str__(self) -> str:
        """
        Return Config as string with only values.
        """
        mode = "only_values"
        ret = self.to_string(mode)
        return ret

    def __repr__(self) -> str:
        """
        Return Config as string with value types.
        """
        mode = "verbose"
        ret = self.to_string(mode)
        return ret

    def str_debug(self) -> str:
        mode = "debug"
        ret = self.to_string(mode)
        return ret

    def to_string(self, mode: str) -> str:
        """
        Return a string representation of this `Config`.

        :param mode: `only_values` or `verbose`
            - `only_values` for simple string representation
            - `verbose` for values with `val_type` and `mark_as_used`
        """
        txt = []
        for key, (marked_as_used, writer, val) in self.items():
            # 1) Process key.
            if mode == "only_values":
                key_as_str = str(key)
            elif mode == "verbose":
                # E.g., `nrows (marked_as_used=False, val_type=core.config.config_.Config)`
                key_as_str = f"{key} (marked_as_used={marked_as_used}, writer={str(writer)}, "
                key_as_str += "val_type=%s)" % hprint.type_to_string(type(val))
            elif mode == "debug":
                # Show full stacktrace of the writer.
                stacktrace = repr(writer)
                key_as_str = f"{key} (marked_as_used={marked_as_used}, writer={stacktrace}, "
                key_as_str += "val_type=%s)" % hprint.type_to_string(type(val))
            # 2) Process value.
            if isinstance(val, (pd.DataFrame, pd.Series, pd.Index)):
                # Data structures that can be printed in a fancy way.
                val_as_str = hpandas.df_to_str(val, print_shape_info=True)
                val_as_str = "\n" + hprint.indent(val_as_str)
            elif isinstance(val, Config) or isinstance(val, _OrderedConfig):
                # Convert Configs recursively.
                val_as_str = val.to_string(mode)
                val_as_str = "\n" + hprint.indent(val_as_str)
            else:
                # Normal Python data structures.
                val_as_str = str(val)
                if len(val_as_str.split("\n")) > 1:
                    # Indent a string that spans multiple lines like:
                    # ```
                    # portfolio_object:
                    #   # historical holdings=
                    #   egid                        10365    -1
                    #   2022-06-27 09:45:02-04:00    0.00  1.00e+06
                    #   2022-06-27 10:00:02-04:00  -44.78  1.01e+06
                    #   ...
                    #   # historical holdings marked to market=
                    #   ...
                    # ```
                    val_as_str = "\n" + hprint.indent(val_as_str)
            # 3) Print.
            txt.append(f"{key_as_str}: {val_as_str}")
        # Assemble the result.
        ret = "\n".join(txt)
        # Remove memory locations of functions, if config contains them, e.g.,
        #   `<function _filter_relevance at 0x7fe4e35b1a70>`.
        memory_loc_pattern = r"(<function \w+.+) at \dx\w+"
        ret = re.sub(memory_loc_pattern, r"\1", ret)
        # Remove memory locations of objects, if config contains them, e.g.,
        #   `<dataflow.task2538_pipeline.ArPredictor object at 0x7f7c7991d390>`
        memory_loc_pattern = r"(<\w+.+ object) at \dx\w+"
        ret = re.sub(memory_loc_pattern, r"\1", ret)
        return ret

    def _mark_as_used(self, key: ScalarKey, *, used_state: bool = True) -> None:
        """
        Mark value as used.

        The value is a tuple of (marked_as_used, value), where `marked_as_used`== True
        if the user reported that the value will be used to build other objects,
        and it should not be subsequently modified.

        :param used_state: whether to mark the value as used.
                 Values are not marked e.g. when accessed through `__contains__` method.
        """
        # Retrieve the value and the metadata.
        hdbg.dassert_isinstance(key, ScalarKeyValidTypes)
        marked_as_used, writer, val = super().__getitem__(key)
        _LOG.debug(hprint.to_str("marked_as_used val used_state"))
        if used_state:
            if isinstance(val, (Config, _OrderedConfig)):
                # If a value is a subconfig, mark all values down the tree.
                for key in val._config.keys():
                    val._config._mark_as_used(key, used_state=used_state)
            else:
                # Update the metadata, accounting that this data was used.
                marked_as_used = True
                # Get info on who used this data.
                writer = _ConfigWriterInfo()
                super().__setitem__(key, (marked_as_used, writer, val))

    def _get_marked_as_used(self, key: ScalarKey) -> bool:
        """
        Get the value for `marked_as_used` for a leaf value.
        """
        hdbg.dassert_isinstance(key, ScalarKeyValidTypes)
        marked_as_used, writer, val = super().__getitem__(key)
        _ = writer, val
        return marked_as_used


# #############################################################################
# Config
# #############################################################################


class ReadOnlyConfigError(RuntimeError):
    """
    Trying to write on a Config marked read-only.
    """


class Config:
    """
    A nested ordered dictionary storing configuration information.

    - Keys can only be strings or ints.
    - Values can be a Python type or another `Config`, but not a `dict`.

    We refer to configs as:
    - "flat" when they have a single level
        - E.g., `config = {"hello": "world"}`
    - "nested" when there are multiple levels
        - E.g., `config = {"hello": {"cruel", "world"}}`
    """

    def __init__(
        self,
        # We can't make this as mandatory kwarg because  of
        # `Config.from_python()`.
        array: Optional[List[Tuple[CompoundKey, Any]]] = None,
        *,
        # By default we use safe behaviors.
        update_mode: str = "assert_on_overwrite",
        clobber_mode: str = "assert_on_write_after_use",
        report_mode: str = "verbose_log_error",
        unused_variables_mode: str = "warning_on_error",
    ) -> None:
        """
        Build a config from a list of (key, value).

        :param array: list of (compound key, value)
        :param update_mode: define the policy used for updates (see above)
        :param clobber_mode: define the policy used for controlling
            write-after-read (see above)
        :param report_mode: define the policy used for reporting errors (see above)
        :param unused_variables_mode: define the policy used for reporting
            variables that were not used by the time `check_unused_variables`
            is called (see above)
        """
        _LOG.debug(hprint.to_str("update_mode clobber_mode report_mode"))
        self._config = _OrderedConfig()
        self.update_mode = update_mode
        self.clobber_mode = clobber_mode
        self.report_mode = report_mode
        self.unused_variables_mode = unused_variables_mode
        # Control whether a config can be modified or not. This needs to be
        # initialized before assigning values with `__setitem__()`, since this
        # function needs to check `_read_only`.
        self._read_only = False
        # Initialize from array.
        # TODO(gp): This might be a separate constructor, but it gives problems
        #  with `Config.from_python()`.
        if array is not None:
            for key, val in array:
                hdbg.dassert_isinstance(key, ScalarKeyValidTypes)
                self.__setitem__(
                    key, val, update_mode=update_mode, clobber_mode=clobber_mode
                )

    # ////////////////////////////////////////////////////////////////////////////
    # Print
    # ////////////////////////////////////////////////////////////////////////////

    def __str__(self) -> str:
        """
        Return Config as string with only values.
        """
        mode = "only_values"
        return self.to_string(mode)

    def __repr__(self) -> str:
        """
        Return Config as string with value types.
        """
        mode = "verbose"
        return self.to_string(mode)

    # ////////////////////////////////////////////////////////////////////////////
    # Dict-like methods.
    # ////////////////////////////////////////////////////////////////////////////

    def __contains__(self, key: CompoundKey) -> bool:
        """
        Implement membership operator like `key in config`.

        If `key` is nested, the hierarchy of Config objects is
        navigated.
        """
        _LOG.debug("key=%s self=\n%s", key, self)
        # This is implemented lazily (or Pythonically) with a
        #  try-catch around accessing the key.
        try:
            # When we test for existence we don't want to report the config
            # in case of error.
            report_mode = "none"
            # When we test for existence we don't want to mark a key as read by
            # the client, since we don't introduce a dependency from its value.
            mark_key_as_used = False
            val = self.__getitem__(
                key, report_mode=report_mode, mark_key_as_used=mark_key_as_used
            )
            _LOG.debug("Found val=%s", val)
            found = True
        except KeyError as e:
            _LOG.debug("e=%s", e)
            found = False
        return found

    def __len__(self) -> int:
        """
        Return number of keys, i.e., the length of the underlying dict.

        This enables calculating `len()` as with a dict and also enables
        bool evaluation of a `Config` object for truth value testing.
        """
        return len(self._config)

    # ////////////////////////////////////////////////////////////////////////////
    # Get / set.
    # ////////////////////////////////////////////////////////////////////////////

    # `__setitem__` and `__getitem__`
    #   - accept a compound key
    #   - invoke the internal methods `_set_item`, `_get_item` to do the
    #   actual work and handle exceptions based on `report_mode`.

    def __setitem__(
        self,
        key: CompoundKey,
        val: Any,
        *,
        update_mode: Optional[str] = None,
        clobber_mode: Optional[str] = None,
        report_mode: Optional[str] = None,
    ) -> None:
        """
        Set / update `key` to `val`, equivalent to `dict[key] = val`.

        If `key` is an iterable of keys, then the key hierarchy is navigated /
        created and the leaf value added/updated with `val`.

        :param update_mode: define the policy used for updates (see above)
            - `None` to use the value set in the constructor
        :param clobber_mode: define the policy used for controlling
            write-after-read (see above)
            - `None` to use the value set in the constructor
        """
        _LOG.debug("-> " + hprint.to_str("key val update_mode clobber_mode self"))
        clobber_mode = self._resolve_clobber_mode(clobber_mode)
        report_mode = self._resolve_report_mode(report_mode)
        try:
            self._set_item(key, val, update_mode, clobber_mode, report_mode)
        except Exception as e:
            self._raise_exception(e, key, report_mode)

    def __getitem__(
        self,
        key: CompoundKey,
        *,
        report_mode: Optional[str] = None,
        mark_key_as_used: bool = False,
    ) -> Any:
        """
        Get value for `key` or raise `KeyError` if it doesn't exist. If `key`
        is compound, then the hierarchy is navigated until the corresponding
        element is found or we raise if the element doesn't exist.

        :param mark_key_as_used: whether we mark the key as read by the client.
          Set to `False` due to accessing values from logging, and we want clients
          to explicitely say when they want the value to be marked as read.
        :raises KeyError: if the compound key is not found in the `Config`
        """
        _LOG.debug("-> " + hprint.to_str("key report_mode self"))
        report_mode = self._resolve_report_mode(report_mode)
        try:
            ret = self._get_item(key, level=0, mark_key_as_used=mark_key_as_used)
        except Exception as e:
            # After the recursion is done, in case of error print information
            # about the offending key.
            # The Config-specific exceptions are handled by an internal method,
            # hence the broad `except` statement. All non-Config exceptions
            # are reported separately.
            self._raise_exception(e, key, report_mode)
        return ret

    def get_marked_as_used(
        self,
        key: CompoundKey,
        *,
        report_mode: Optional[str] = None,
    ) -> bool:
        """
        Return whether `key` is marked as used.
        """
        _LOG.debug("-> " + hprint.to_str("key report_mode self"))
        try:
            ret = self._get_item(
                key, level=0, mark_key_as_used=False, get_marked_as_used=True
            )
        except Exception as e:
            report_mode = self._resolve_report_mode(report_mode)
            self._raise_exception(e, key, report_mode)
        return ret

    def to_string(self, mode: str) -> str:
        return self._config.to_string(mode)

    def check_unused_variables(
        self, *, unused_variables_mode: Optional[str] = None
    ) -> List[str]:
        """
        Check if variables in the config were not used.
        """
        unused_variables = []
        # Get scalar and compound keys in the dict.
        keys = list(self.flatten().keys())
        for key in keys:
            # Get the value and whether it was marked as used.
            val = self[key]
            marked_as_used = self.get_marked_as_used(key)
            # Save `get_marked_as_used` for leaves, ignoring subconfigs.
            if (
                not isinstance(val, (Config, _OrderedConfig))
                and not marked_as_used
            ):
                unused_variables.append(key)
        if unused_variables:
            mode = self._resolve_unused_variables_mode(unused_variables_mode)
            if mode == "warning_on_error":
                _LOG.warning(hprint.to_str("unused_variables"))
            elif mode == "assert_on_error":
                raise ValueError(unused_variables)
        return unused_variables

    def get_and_mark_as_used(
        self,
        key: ScalarKeyValidTypes,
        *,
        mark_key_as_used: bool = True,
        default_value: Optional[Any] = _NO_VALUE_SPECIFIED,
    ) -> Any:
        """
        Get the value and mark it as used.

        Similar to the `get` method. The value is not marked unless it is a leaf.

        :param mark_key_as_used: see `_mark_as_used()` for description
        :param default_value: value to return if key was not found

        This should be used as the only way of accessing values from configs
        except for purposes of logging and transformation to string.

        Examples of use:
        - When the value is used inside another constructor:
            ```
            process_forecasts_node_dict = system.config.get_and_mark_as_used(
                "process_forecasts_node_dict"
            ).to_dict()
            dag = dtfsys.adapt_dag_to_real_time(
                dag,
                market_data,
                market_data_history_lookback,
                process_forecasts_node_dict,
                ts_col_name,
            )
            ```
        - When the value determines the behavior of the function:
            ```
            fast_prod_setup = system.config.get_and_mark_as_used(
                ("dag_builder_config", "fast_prod_setup"), default_value=False
            )
            ...
            if fast_prod_setup:
                system.config["dag_config"] = dag_builder.convert_to_fast_prod_setup(
                    system.config["dag_config"]
                )
            ```

        Examples of when it should not be used:
            - Logging and printing:
                ```
                fast_prod_setup = config["dag_builder_config", "fast_prod_setup"]
                _LOG.debug(hprint.to_str("fast_prod_setup"))
                ```
            - If the value is a subconfig with multiple values inside:
                ```
                # Note that `dag_config` is a subconfig so we just get it
                # without marking as used.
                dag_config = system.config["dag_config"]
                ```
        """
        try:
            ret = self.__getitem__(key, mark_key_as_used=mark_key_as_used)
        except KeyError as e:
            # If a default value is provided, return.
            if default_value != _NO_VALUE_SPECIFIED:
                ret = default_value
            else:
                # No default value found, then raise.
                raise e
        return ret

    def get(
        self,
        key: CompoundKey,
        default_value: Optional[Any] = _NO_VALUE_SPECIFIED,
        expected_type: Optional[Any] = _NO_VALUE_SPECIFIED,
        *,
        report_mode: Optional[str] = None,
    ) -> Any:
        """
        Equivalent to `dict.get(key, default_val)`.

        It has the same functionality as `__getitem__()` but returning `val`
        if the value corresponding to `key` doesn't exist.

        :param default_value: default value to return if key is not in `config`
        :param expected_type: expected type of `value`
        :return: config[key] if available, else `default_value`
        """
        _LOG.debug(hprint.to_str("key default_value expected_type report_mode"))
        # The implementation of this function is similar to `hdict.typed_get()`.
        report_mode = self._resolve_report_mode(report_mode)
        try:
            ret = self.__getitem__(key, report_mode=report_mode)
        except KeyError as e:
            # No key: use the default val if it was passed or asserts.
            # We can't use None since None can be a valid default value,
            # so we use another value.
            if default_value != _NO_VALUE_SPECIFIED:
                ret = default_value
            else:
                # No default value found, then raise.
                raise e
        if expected_type != _NO_VALUE_SPECIFIED:
            hdbg.dassert_isinstance(ret, expected_type)
        return ret

    # ////////////////////////////////////////////////////////////////////////////
    # Update.
    # ////////////////////////////////////////////////////////////////////////////

    def update(
        self,
        config: "Config",
        *,
        update_mode: Optional[str] = None,
        clobber_mode: Optional[str] = None,
        report_mode: Optional[str] = None,
    ) -> None:
        """
        Equivalent to `dict.update(config)`.

        Some features of `update()`:
            - updates leaf values in self from values in `config`
            - recursively creates paths to leaf values if needed
            - `config` values overwrite any existing values, assert depending on the
            value of `mode`
        """
        _LOG.debug(hprint.to_str("config update_mode"))
        # `update()` is just a series of set.
        flattened_config = config.flatten()
        for key, val in flattened_config.items():
            _LOG.debug(hprint.to_str("key val"))
            self.__setitem__(
                key,
                val,
                update_mode=update_mode,
                clobber_mode=clobber_mode,
                report_mode=report_mode,
            )

    # TODO(gp): Add also iteritems()
    def keys(self) -> List[str]:
        return self._config.keys()

    def pop(self, key: str) -> Any:
        """
        Equivalent to `dict.pop()`.
        """
        return self._config.pop(key)

    def copy(self) -> "Config":
        """
        Create a deep copy of the Config object.
        """
        return copy.deepcopy(self)

    # ////////////////////////////////////////////////////////////////////////////
    # Accessors.
    # ////////////////////////////////////////////////////////////////////////////

    def add_subconfig(self, key: CompoundKey) -> "Config":
        _LOG.debug(hprint.to_str("key"))
        hdbg.dassert_not_in(key, self._config.keys(), "Key already present")
        config = Config(
            update_mode=self._update_mode,
            clobber_mode=self._clobber_mode,
            report_mode=self._report_mode,
        )
        self.__setitem__(
            key,
            config,
            update_mode=self._update_mode,
            clobber_mode=self._clobber_mode,
            report_mode=self._report_mode,
        )
        return config

    @property
    def update_mode(self) -> str:
        return self._update_mode

    @update_mode.setter
    def update_mode(self, update_mode: str) -> None:
        hdbg.dassert_in(update_mode, _VALID_UPDATE_MODES)
        self._update_mode = update_mode

    @property
    def clobber_mode(self) -> str:
        return self._clobber_mode

    @clobber_mode.setter
    def clobber_mode(self, clobber_mode: str) -> None:
        hdbg.dassert_in(clobber_mode, _VALID_CLOBBER_MODES)
        self._clobber_mode = clobber_mode

    @property
    def report_mode(self) -> str:
        return self._report_mode

    @report_mode.setter
    def report_mode(self, report_mode: str) -> None:
        hdbg.dassert_in(report_mode, _VALID_REPORT_MODES)
        self._report_mode = report_mode

    # TODO(gp): Consider turning this into a property.
    def mark_read_only(self, value: bool = True) -> None:
        """
        Force a Config object to become read-only.

        Note: the read-only mode is applied recursively, i.e. for all sub-configs.
        """
        _LOG.debug(hprint.to_str("value"))
        self._read_only = value
        for v in self._config.values():
            if isinstance(v, Config):
                v.mark_read_only(value)

    # TODO(Dan): Centralize the config file names in CmTask7795.
    def save_to_file(self, log_dir: str, tag: str) -> None:
        """
        Save config as a string and pickle.

        Save files in a log dir:
        - ${log_dir}/{tag}.txt
        - ${log_dir}/{tag}.values_as_strings.pkl
        - ${log_dir}/{tag}.all_values_picklable.pkl

        :param tag: basename of the files to save (e.g., "system_config.input")
        """
        # 0) Save txt file with config version.
        file_name = os.path.join(log_dir, "config_version.txt")
        hio.to_file(file_name, CONFIG_VERSION)
        # 1) As a string.
        file_name = os.path.join(log_dir, f"{tag}.txt")
        hio.to_file(file_name, repr(self))
        # 2) As a pickle containing all values as string.
        file_name = os.path.join(log_dir, f"{tag}.values_as_strings.pkl")
        force_values_to_string = True
        config = self.to_pickleable(force_values_to_string)
        hpickle.to_pickle(config, file_name)
        # 3) As a pickle containing all values in pickleable format.
        file_name = os.path.join(log_dir, f"{tag}.all_values_picklable.pkl")
        force_values_to_string = False
        config = self.to_pickleable(force_values_to_string)
        hpickle.to_pickle(config, file_name)

    def to_pickleable(self, force_values_to_string: bool) -> "Config":
        """
        Transform this Config into a pickle-able one where all values are
        replaced with their string representation.

        :param force_values_to_string: if True, store all the object
            values as strings
        """
        config_out = Config()
        # TODO(Grisha): do we need to save `writer_info` and `mark_as_used`?
        for key, (_, _, val) in self._config.items():
            if isinstance(val, Config):
                # Call the method recursively on a value of a `Config` type.
                config_out[key] = val.to_pickleable(force_values_to_string)
            else:
                # Add processed value to the result config.
                config_out[key] = hpickle.to_pickleable(
                    val, force_values_to_string
                )
        return config_out

    # /////////////////////////////////////////////////////////////////////////////
    # From / to functions.
    # /////////////////////////////////////////////////////////////////////////////

    @classmethod
    def from_python(cls, code: str) -> Optional["Config"]:
        """
        Create an object from the code returned by `to_python()`.
        """
        _LOG.debug("code=\n%s", code)
        hdbg.dassert_isinstance(code, str)
        try:
            # eval function need unknown globals to be set.
            val = eval(code, {"nan": np.nan, "Config": Config})
            hdbg.dassert_isinstance(val, Config)
        except SyntaxError as e:
            _LOG.error("Error deserializing: %s", str(e))
            return None
        return val  # type: ignore

    def to_python(self, check: bool = True) -> str:
        """
        Return python code that builds, when executed, the current object.

        :param check: check that the Config can be
            serialized/deserialized correctly.
        """
        config_as_str = str(self.to_dict())
        # We don't need `cconfig.` since we are inside the config module.
        config_as_str = config_as_str.replace("OrderedDict", "Config")
        if check:
            # Check that the object can be reconstructed.
            config_tmp = Config.from_python(config_as_str)
            # Compare.
            hdbg.dassert_eq(str(self), str(config_tmp))
        _LOG.debug("config_as_str=\n%s", config_as_str)
        return config_as_str

    @classmethod
    def from_env_var(cls, env_var: str) -> Optional["Config"]:
        if env_var in os.environ:
            python_code = os.environ[env_var]
            config = cls.from_python(python_code)
        else:
            _LOG.warning(
                "Environment variable '%s' not defined: no config retrieved",
                env_var,
            )
            config = None
        return config

    def to_dict(self, *, keep_leaves: bool = True) -> Dict[ScalarKey, Any]:
        """
        Convert the Config to nested ordered dicts.

        :param keep_leaves: keep or skip empty leaves
        """
        _LOG.debug(hprint.to_str("self keep_leaves"))
        # pylint: disable=unsubscriptable-object
        dict_: _OrderedDictType[ScalarKey, Any] = collections.OrderedDict()
        for key, (marked_as_used, writer, val) in self._config.items():
            _ = marked_as_used, writer
            if keep_leaves:
                if isinstance(val, Config):
                    # If a value is a `Config` convert to dictionary recursively.
                    val = val.to_dict(keep_leaves=keep_leaves)
                hdbg.dassert(not isinstance(val, Config))
                dict_[key] = val
            else:
                if isinstance(val, Config):
                    if val:
                        # If a value is a `Config` convert to dictionary recursively.
                        val = val.to_dict(keep_leaves=keep_leaves)
                    else:
                        continue
                hdbg.dassert(not isinstance(val, Config))
                dict_[key] = val
            if isinstance(val, dict) and not val:
                # Convert empty leaves from OrderedDict to Config.
                #  Temporary measure to keep back compatibility
                #  with Config string representations (CMTask2689).
                dict_[key] = Config()
        return dict_

    @classmethod
    def from_dict(cls, nested_dict: Dict[str, Any]) -> "Config":
        """
        Build a `Config` from a nested dict.

        :param nested_dict: nested dict, with certain restrictions:
          - only leaf nodes may not be a dict
          - every nonempty dict must only have keys of type `str`
        """
        hdbg.dassert_isinstance(nested_dict, dict)
        hdbg.dassert(nested_dict)
        iter_ = hdict.get_nested_dict_iterator(nested_dict)
        flattened_config = collections.OrderedDict(iter_)
        config_from_dict = Config._get_config_from_flattened_dict(
            flattened_config
        )
        _LOG.debug("config_from_dict=%s", str(config_from_dict))
        return config_from_dict

    # /////////////////////////////////////////////////////////////////////////////

    def is_serializable(self) -> bool:
        """
        Make sure the config can be serialized and deserialized correctly.
        """
        code = self.to_python(check=False)
        config = self.from_python(code)
        ret = str(config) == str(self)
        return ret

    def flatten(self) -> Dict[Tuple[str], Any]:
        """
        Return a dict path to leaf -> value.
        """
        dict_ = self.to_dict(keep_leaves=True)
        iter_ = hdict.get_nested_dict_iterator(dict_)
        return collections.OrderedDict(iter_)

    def check_params(self, keys: Iterable[str]) -> None:
        """
        Check whether all the `keys` are present in the object, otherwise
        raise.
        """
        missing_keys = []
        for key in keys:
            if key not in self._config:
                missing_keys.append(key)
        if missing_keys:
            msg = "Missing %s vars (from %s) in config=\n%s" % (
                ",".join(missing_keys),
                ",".join(keys),
                str(self),
            )
            _LOG.error(msg)
            raise KeyError(msg)

    # /////////////////////////////////////////////////////////////////////////////
    # Private methods.
    # /////////////////////////////////////////////////////////////////////////////

    @staticmethod
    def _parse_compound_key(key: CompoundKey) -> Tuple[str, Iterable[str]]:
        """
        Separate the first element of a compound key from the rest.
        """
        hdbg.dassert(hintros.is_iterable(key), "Key='%s' is not iterable", key)
        head_scalar_key, tail_compound_key = key[0], key[1:]  # type: ignore
        _LOG.debug(
            "key='%s' -> head_scalar_key='%s', tail_compound_key='%s'",
            key,
            head_scalar_key,
            tail_compound_key,
        )
        hdbg.dassert_isinstance(
            head_scalar_key, ScalarKeyValidTypes, "Keys can only be string or int"
        )
        return head_scalar_key, tail_compound_key

    @staticmethod
    def _get_config_from_flattened_dict(
        flattened_config: Dict[Tuple[str], Any]
    ) -> "Config":
        """
        Build a config from the flattened config representation.

        :param flattened_config: flattened config like result from `config.flatten()`
        :return: `Config` object initialized from flattened representation
        """
        hdbg.dassert_isinstance(flattened_config, dict)
        hdbg.dassert(flattened_config)
        config = Config()
        for k, v in flattened_config.items():
            if isinstance(v, dict):
                if v:
                    # Convert each dict-value to `Config` recursively because we
                    # cannot use dict as value in a `Config`.
                    v = Config.from_dict(v)
                else:
                    # TODO(Grisha): maybe move to `from_dict`, i.e.
                    # return empty `Config` right away without passing further.
                    # If dictionary is empty convert to an empty `Config`.
                    v = Config()
            config[k] = v
        return config

    @staticmethod
    def _resolve_mode(
        value: Optional[str],
        ctor_value: str,
        valid_values: Iterable[str],
        tag: str,
    ) -> str:
        if value is None:
            # Use the value from the constructor.
            value = ctor_value
            _LOG.debug("resolved: %s=%s", tag, value)
        # The result should be a valid string.
        hdbg.dassert_isinstance(value, str)
        hdbg.dassert_in(value, valid_values)
        return value

    # /////////////////////////////////////////////////////////////////////////////

    def _set_item(
        self,
        key: CompoundKey,
        val: Any,
        update_mode: Optional[str],
        clobber_mode: Optional[str],
        report_mode: Optional[str],
    ) -> None:
        """
        Set / update `key` to `val`, equivalent to `dict[key] = val`.

        If `key` is an iterable of keys, then the key hierarchy is navigated /
        created and the leaf value added / updated with `val`.

        :param update_mode: define the policy used for updates (see above)
            - `None` to use the value set in the constructor
        :param clobber_mode: define the policy used for controlling
            write-after-use (see above)
            - `None` to use the value set in the constructor
        """
        _LOG.debug(hprint.to_str("key val update_mode clobber_mode self"))
        # # Used to debug who is setting a certain key.
        # if False:
        #     _LOG.info("key.set=%s", str(key))
        #     if key == ("dag_runner_config", "wake_up_timestamp"):
        #         assert 0
        # A read-only config cannot be changed.
        if self._read_only:
            msg = []
            msg.append(
                f"Can't set key='{key}' to val='{val}' in read-only config"
            )
            msg.append("self=\n" + hprint.indent(str(self)))
            msg = "\n".join(msg)
            # TODO(Danya): Remove after enabling `mark_as_used` method.
            raise ReadOnlyConfigError(msg)
        update_mode = self._resolve_update_mode(update_mode)
        clobber_mode = self._resolve_clobber_mode(clobber_mode)
        report_mode = self._resolve_report_mode(report_mode)
        # If the key is compound, then recurse.
        if hintros.is_iterable(key):
            head_key, tail_key = self._parse_compound_key(key)
            if not tail_key:
                # There is no tail_key so `__setitem__()` was called on a tuple of a
                # single element, then set the value.
                self._set_item(
                    head_key, val, update_mode, clobber_mode, report_mode
                )
            else:
                # Compound key: recurse on the tail of the key.
                _LOG.debug(
                    "head_key='%s', self._config=\n%s",
                    head_key,
                    self._config,
                )
                if head_key in self:
                    # We mark a key as read only when it's read from a client of
                    # Config, not from the Config itself.
                    mark_key_as_used = False
                    subconfig = self.__getitem__(
                        head_key,
                        report_mode="none",
                        mark_key_as_used=mark_key_as_used,
                    )
                else:
                    subconfig = self.add_subconfig(head_key)
                hdbg.dassert_isinstance(subconfig, Config)
                subconfig._set_item(
                    tail_key, val, update_mode, clobber_mode, report_mode
                )
            return
        # Base case: write the config.
        self._dassert_base_case(key)
        self._config.__setitem__(
            key, val, update_mode=update_mode, clobber_mode=clobber_mode
        )

    def _get_item(
        self,
        key: CompoundKey,
        level: int,
        mark_key_as_used: bool,
        *,
        get_marked_as_used: Optional[bool] = False,
    ) -> Any:
        """
        Implement `__getitem__()` but keeping track of the depth of the key to
        report an informative message reporting the entire config on
        `KeyError`.

        This method is a helper for `__getitem__()` and
        `get_marked_as_used()`.

        :param get_marked_as_used: if True, return if the value is
            marked as used, instead of the value itself.
        :return: value associated to the key (or mark_as_used)
        """
        _LOG.debug("key=%s level=%s self=\n%s", key, level, self)
        # Check if the key is compound.
        if hintros.is_iterable(key):
            head_key, tail_key = self._parse_compound_key(key)
            if not tail_key:
                # Tuple of a single element, then return the value.
                ret = self._get_item(
                    head_key,
                    level + 1,
                    mark_key_as_used,
                    get_marked_as_used=get_marked_as_used,
                )
            else:
                # Compound key: recurse on the tail of the key.
                if head_key not in self._config:
                    # msg = self._get_error_msg("head_key", head_key)
                    keys_as_str = str(list(self._config.keys()))
                    msg = f"head_key='{head_key}' not in {keys_as_str} at level {level}"
                    raise KeyError(msg)
                subconfig = self._config[head_key]
                _LOG.debug("subconfig\n=%s", self._config)
                if isinstance(subconfig, Config):
                    # Recurse.
                    ret = subconfig._get_item(
                        tail_key,
                        level + 1,
                        mark_key_as_used,
                        get_marked_as_used=get_marked_as_used,
                    )
                else:
                    # There are more keys to process but we have reached the leaves
                    # of the config, then we assert.
                    # msg = self._get_error_msg("tail_key", tail_key)
                    msg = f"tail_key={tail_key} at level {level}"
                    raise KeyError(msg)
            return ret
        # Base case: key is a string, config is a dict.
        self._dassert_base_case(key)
        if key not in self._config:
            # msg = self._get_error_msg("key", key)
            keys_as_str = str(list(self._config.keys()))
            msg = f"key='{key}' not in {keys_as_str} at level {level}"
            raise KeyError(msg)
        if get_marked_as_used:
            # Return `get_marked_as_used` for the key.
            ret = self._config._get_marked_as_used(key)  # type: ignore
        else:
            # Return the value associated to the key.
            ret = self._config.__getitem__(key, mark_key_as_used=mark_key_as_used)  # type: ignore
        return ret

    def _resolve_update_mode(self, value: Optional[str]) -> str:
        update_mode = self._resolve_mode(
            value, self._update_mode, _VALID_UPDATE_MODES, "update_mode"
        )
        return update_mode

    def _resolve_clobber_mode(self, value: Optional[str]) -> str:
        clobber_mode = self._resolve_mode(
            value, self._clobber_mode, _VALID_CLOBBER_MODES, "clobber_mode"
        )
        return clobber_mode

    def _resolve_report_mode(self, value: Optional[str]) -> str:
        report_mode = self._resolve_mode(
            value, self._report_mode, _VALID_REPORT_MODES, "report_mode"
        )
        return report_mode

    def _resolve_unused_variables_mode(self, value: Optional[str]) -> str:
        unused_variables_mode = self._resolve_mode(
            value,
            self.unused_variables_mode,
            _VALID_UNUSED_VARIABLES_MODES,
            "unused_variable_mode",
        )
        return unused_variables_mode

    def _dassert_base_case(self, key: CompoundKey) -> None:
        """
        Check that a leaf config is valid.
        """
        _LOG.debug("key=%s", key)
        hdbg.dassert_isinstance(
            key, ScalarKeyValidTypes, "Keys can only be string or int"
        )
        hdbg.dassert_isinstance(self._config, dict)

    def _raise_exception(
        self, exception: Exception, key: CompoundKey, report_mode: str
    ) -> None:
        """
        Handle Config get/set exceptions.

        These include:
        - KeyError
        - OverwriteError
        - ReadOnlyConfigError
        """
        _LOG.debug(hprint.to_str("exception key report_mode"))
        hdbg.dassert_in(report_mode, _VALID_REPORT_MODES)
        if report_mode in ("verbose_log_error", "verbose_exception"):
            msg = []
            msg.append("exception=" + str(exception))
            msg.append(f"key='{key}'")
            msg.append("config=\n" + hprint.indent(str(self)))
            msg = "\n".join(msg)
            if report_mode == "verbose_log_error":
                _LOG.error(msg)
            elif report_mode == "verbose_exception":
                # TODO(gp): It's not clear how to create an exception with a
                #  different message, so we resort to an ugly switch.
                if isinstance(exception, KeyError):
                    exception = KeyError(msg)
                elif isinstance(exception, OverwriteError):
                    exception = OverwriteError(msg)
                elif isinstance(exception, ReadOnlyConfigError):
                    exception = ReadOnlyConfigError(msg)
                else:
                    raise RuntimeError(f"Invalid exception: {exception}")
        raise exception
