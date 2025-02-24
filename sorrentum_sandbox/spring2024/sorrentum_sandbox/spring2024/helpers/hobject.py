"""
Methods to introspect and print the state of an object.

Import as:

import helpers.hobject as hobject
"""

import abc
import logging
import pprint
from typing import Any, Dict, List, Optional

import pandas as pd

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hprint as hprint
import helpers.hstring as hstring

_LOG = logging.getLogger(__name__)
# Mute this module unless we want to debug it.
_LOG.setLevel(logging.INFO)

# #############################################################################
# _to_skip*
# #############################################################################


def _to_skip(is_: bool, mode: str) -> bool:
    """
    Return whether to skip the attribute.

    :param is_: if `True` the attribute is of the type we are checking
    :param mode: how to handle the attribute
    :return: whether to skip the attribute
    """
    hdbg.dassert_in(mode, ("skip", "only", "all"))
    skip = False
    if mode == "skip":
        if is_:
            # Skip everything.
            skip = True
    elif mode == "only":
        if not is_:
            # Keep only the callables.
            skip = True
    elif mode == "all":
        # Keep everything.
        skip = False
    else:
        raise ValueError(f"Invalid mode='{mode}'")
    return skip


def _to_skip_callable_attribute(attr_name: Any, mode: str) -> bool:
    """
    Decide whether to skip a callable attribute.
    """
    # Check whether the attribute is callable.
    is_callable = callable(attr_name)
    skip = _to_skip(is_callable, mode)
    return skip


def _to_skip_private_attribute(attr_name: str, mode: str) -> bool:
    """
    Decide whether to skip a private attribute.
    """
    # _Object__hello
    # TODO(gp): This can be improved by passing the name of the object.
    is_dunder = attr_name.startswith("_") and "__" in attr_name
    # We assume that private attributes start with `_` and are not dunder.
    is_private = not is_dunder and attr_name.startswith("_")
    skip = _to_skip(is_private, mode)
    return skip


def _to_skip_dunder_attribute(attr_name: str, mode: str) -> bool:
    """
    Decide whether to skip a double under attribute.
    """
    # Check if it is a dunder (i.e., double under method). E.g., `__hello__`.
    is_dunder = attr_name.startswith("_") and "__" in attr_name
    skip = _to_skip(is_dunder, mode)
    return skip


def _to_skip_attribute(
    attr_name: Any,
    attr_value: Any,
    callable_mode: str,
    private_mode: str,
    dunder_mode: str,
    attr_names_to_skip: Optional[List[str]],
) -> bool:
    """
    Decide whether to skip an attribute.

    :param attr_name: name of the attribute
    :param attr_value: value of the attribute
    :param callable_mode: how to handle attributes that are callable methods
    :param private_mode: how to handle attributes that are private (e.g.,
        `_hello`)
    :param dunder_mode: how to handle attributes that are dunder (e.g.,
        `__hello`)
    :param attr_names_to_skip: a list of attributes (e.g., private, callable, dunder)
        to skip. `None` to skip nothing.
    :return: whether to skip the attribute
    """
    # Check whether the attribute is one that was requested explicitly to skip.
    if attr_names_to_skip is not None:
        if attr_name in attr_names_to_skip:
            skip = True
            return skip
    # Handle callable methods.
    skip = _to_skip_callable_attribute(attr_value, callable_mode)
    if skip:
        _LOG.debug("Skip callable")
        return skip
    # Handle private methods.
    skip = _to_skip_private_attribute(attr_name, private_mode)
    if skip:
        _LOG.debug("Skip private")
        return skip
    # Handle dunder methods.
    skip = _to_skip_dunder_attribute(attr_name, dunder_mode)
    if skip:
        _LOG.debug("Skip dunder")
        return skip
    return False


# #############################################################################
# obj_to_str
# #############################################################################


def _type_to_str(attr_value: Any) -> str:
    """
    Print the attribute value together with its type.

    E.g., `a=False <bool>, b=hello <str>, c=3.14 <float>`
    """
    type_as_str = str(type(attr_value))
    # Convert from `<class 'str'>` to `str`.
    type_as_str = hstring.remove_prefix(type_as_str, "<class '")
    type_as_str = hstring.remove_suffix(type_as_str, "'>")
    # Add `<` and `>` around the type.
    type_as_str = f"<{type_as_str}>"
    return type_as_str


def _attr_to_str(attr_value: Any, print_type: bool) -> str:
    """
    Print the attribute value handling different types.
    """
    _LOG.debug("type(attr_value)=%s", type(attr_value))
    if isinstance(attr_value, pd.DataFrame):
        res = f"pd.df({attr_value.shape}"
    elif isinstance(attr_value, pd.Series):
        res = f"pd.srs({attr_value.shape}"
    elif isinstance(attr_value, dict):
        res = str(attr_value)
    else:
        res = str(attr_value)
    # Add the type, if needed.
    if print_type:
        res += " " + _type_to_str(attr_value)
    return res


def obj_to_str(
    obj: Any,
    *,
    attr_mode: str = "__dict__",
    sort: bool = False,
    print_type: bool = False,
    callable_mode: str = "skip",
    private_mode: str = "skip",
    dunder_mode: str = "skip",
    attr_names_to_skip: Optional[List[str]] = None,
) -> str:
    """
    Print the attributes of an object.

    An object is printed as name of its class and its attributes, e.g.,
    ```
    _Object1 at 0x...=(a=False, b=hello, c=3.14)
    ```

    :param attr_mode: use `__dict__` or `dir()`
        - It doesn't seem to make much difference
    :sort: sort the attributes in order of name, or not
    :param print_type: print the type of the attribute
    :param callable_mode: how to handle attributes that are callable (i.e.,
        methods)
        - `skip`: skip the callable methods
        - `only`: print only the callable methods
        - `all`: always print
    :param private_mode: how to handle private attributes. Same params as
        `callable_mode`
    :param dunder_mode: how to handle double under attributes. Same params as
        `callable_mode`
    :param attr_names_to_skip: a list of attributes (e.g., private, callable,
        dunder) to skip. This is used to avoid to print data that is redundant
        (e.g., a cached value)
    """
    ret = []
    if attr_mode == "__dict__":
        # Use `__dict__` to get the attributes of the object.
        values = obj.__dict__
    elif attr_mode == "dir":
        # Use `dir()` to get the attributes of the object.
        values = dir(obj)
    elif attr_mode == "config":
        # Use object method to get the attributes to print info for.
        values = obj.get_config_attributes()
    else:
        raise ValueError(f"Invalid attr_mode='{attr_mode}'")
    if sort:
        values = sorted(values)
    for attr_name in values:
        if attr_mode == "__dict__":
            attr_value = obj.__dict__[attr_name]
        elif attr_mode in ["dir", "config"]:
            attr_value = getattr(obj, attr_name)
        else:
            raise ValueError(f"Invalid attr_mode='{attr_mode}'")
        skip = _to_skip_attribute(
            attr_name,
            attr_value,
            callable_mode,
            private_mode,
            dunder_mode,
            attr_names_to_skip,
        )
        _LOG.debug(
            "attr_name=%s attr_value=%s -> skip", attr_name, attr_value, skip
        )
        if skip:
            continue
        #
        out = f"{attr_name}=" + _attr_to_str(attr_value, print_type)
        ret.append(out)
    #
    txt = hprint.to_object_str(obj) + "="
    txt += "(" + ", ".join(ret) + ")"
    return txt


# #############################################################################
# obj_to_repr
# #############################################################################


def _attr_to_repr(attr_name: Any, attr_value: Any, print_type: bool) -> str:
    """
    Print an object as name of its class and its attributes.

    E.g.,
    ```
    <helpers.test.test_hobject._Object1 at 0x...>:
          a='False' <bool>
          b='hello' <str>
          c='3.14' <float>
    ```
    """
    _LOG.debug("type(attr_value)=%s", type(attr_value))
    if isinstance(attr_value, (pd.DataFrame, pd.Series)):
        attr_value_as_str = hpandas.df_to_str(attr_value)
    elif isinstance(attr_value, dict):
        attr_value_as_str = pprint.pformat(attr_value)
    else:
        attr_value_as_str = repr(attr_value)
    #
    if len(attr_value_as_str.split("\n")) > 1:
        # The string representing the attribute value spans multiple lines, so
        # print like:
        # ```
        # attr_name= (type)
        #   attr_value
        # ```
        out = f"{attr_name}="
        if print_type:
            out += " " + _type_to_str(attr_value)
        out += "\n" + hprint.indent(attr_value_as_str)
    else:
        # The string representing the attribute value is a single line, so print
        # like:
        # ```
        # attr_name='attr_value' (type)
        # ```
        out = f"{attr_name}='{str(attr_value)}'"
        if print_type:
            out += " " + _type_to_str(attr_value)
    return out


# TODO(gp): Merge the code with obj_to_repr() using a switch for the different
#  code.
def obj_to_repr(
    obj: Any,
    *,
    attr_mode: str = "__dict__",
    sort: bool = False,
    print_type: bool = False,
    callable_mode: str = "skip",
    private_mode: str = "skip",
    dunder_mode: str = "skip",
    attr_names_to_skip: Optional[List[str]] = None,
) -> str:
    """
    Same interface and behavior as `obj_to_str()`.

    Use `_attr_to_repr()` instead of a simple `attr_name = attr_value`
    like in `obj_to_str()`.
    """
    ret = []
    # TODO(Grisha): factor out the logic in a function `get_class_attributes(attr_mode)`.
    if attr_mode == "__dict__":
        values = obj.__dict__
    elif attr_mode == "dir":
        values = dir(obj)
    elif attr_mode == "config":
        values = obj.get_config_attributes()
    else:
        raise ValueError(f"Invalid attr_mode='{attr_mode}'")
    if sort:
        values = sorted(values)
    for attr_name in values:
        if attr_mode == "__dict__":
            attr_value = obj.__dict__[attr_name]
        elif attr_mode in ["dir", "config"]:
            attr_value = getattr(obj, attr_name)
        else:
            raise ValueError(f"Invalid attr_mode='{attr_mode}'")
        skip = _to_skip_attribute(
            attr_name,
            attr_value,
            callable_mode,
            private_mode,
            dunder_mode,
            attr_names_to_skip,
        )
        _LOG.debug(
            "attr_name=%s attr_value=%s -> skip", attr_name, attr_value, skip
        )
        if skip:
            continue
        #
        out = _attr_to_repr(attr_name, attr_value, print_type)
        ret.append(out)
    #
    txt = []
    txt.append(hprint.to_object_repr(obj) + ":")
    txt.append(hprint.indent("\n".join(ret)))
    return "\n".join(txt)


# #############################################################################
# PrintableMixin
# #############################################################################


class PrintableMixin:
    """
    Implement `__str__()` and `__repr__()` to print the state of an object.

    These methods can be overridden with more specific methods by
    derived classes.
    """

    def __str__(
        self,
        *,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        """
        Used for creating output for end user and need to be readable.
        """
        txt = obj_to_str(
            self,
            print_type=True,
            private_mode="all",
            attr_names_to_skip=attr_names_to_skip,
        )
        return txt

    def __repr__(
        self,
        *,
        attr_names_to_skip: Optional[List[str]] = None,
    ) -> str:
        """
        Used for debugging and development and need to be unambiguous.
        """
        txt = obj_to_repr(
            self,
            print_type=True,
            private_mode="all",
            attr_names_to_skip=attr_names_to_skip,
        )
        return txt

    @staticmethod
    @abc.abstractmethod
    def get_config_attributes() -> List[str]:
        """
        Get list of attributes that are relevant to the configuration of each
        block.
        """
        ...

    # TODO(Grisha): decide if we need this method: what are the use-cases?
    #  Ideally we should just save `SystemConfig` and load it when needed.
    def to_config_dict(self) -> Dict[str, Any]:
        """
        Get class configuration as dict.
        """
        res_dict = {}
        # Get class attribute names to print.
        attributes = self.get_config_attributes()
        hdbg.dassert_is_subset(attributes, self.__dict__.keys())
        # Iterate over attributes and add their state to the dict.
        for attr in attributes:
            value = getattr(self, attr)
            # Get a list of types the value class is derived from.
            value_parent_classes = value.__class__.__mro__
            if any(
                "helpers.hobject.PrintableMixin" in str(parent_class)
                for parent_class in value_parent_classes
            ):
                # Call the function recursively if value is also
                # a `PrintableMixin` descendant.
                dict_val = value.to_config_dict()
            else:
                # Get attribute value representation.
                dict_val = _attr_to_repr(attr, value, print_type=True)
            # Put value in the result dict.
            res_dict[attr] = dict_val
        return res_dict

    def to_config_str(self) -> str:
        """
        Get class configuration as string.
        """
        ret = []
        attributes = self.get_config_attributes()
        hdbg.dassert_is_subset(attributes, self.__dict__.keys())
        # Iterate over attributes and add their state to the dict.
        for attr in attributes:
            value = getattr(self, attr)
            if isinstance(value, PrintableMixin):
                # Call the function recursively if value is also
                # a `PrintableMixin` descendant.
                dict_val = value.to_config_str()
                # Add attribute name for string representation.
                dict_val = f"{attr}={dict_val}"
            else:
                dict_val = _attr_to_repr(attr, value, print_type=True)
            # Put value in the result dict.
            ret.append(dict_val)
        txt = []
        txt.append(hprint.to_object_repr(self) + ":")
        txt.append(hprint.indent("\n".join(ret)))
        txt = "\n".join(txt)
        return txt


# #############################################################################


# TODO(gp): CleanUp. This is for testing and should be in hobject_test.py.
# TODO(gp): -> check_object_signature
def test_object_signature(
    self_: Any, obj: Any, *, remove_lines_regex: Optional[str] = None
) -> None:
    """
    Print a string representation of an object using both `str()` and `repr()`.

    :param obj: the object to print
    :param remove_lines_regex: a regex to remove certain lines from the
        output
    """
    txt = []
    #
    txt.append(hprint.frame("str:"))
    txt.append(str(obj))
    #
    txt.append(hprint.frame("repr:"))
    txt.append(repr(obj))
    #
    txt = "\n".join(txt)
    # Remove certain lines, if needed.
    if remove_lines_regex:
        txt = hprint.filter_text(remove_lines_regex, txt)
    #
    self_.check_string(txt, purify_text=True)
