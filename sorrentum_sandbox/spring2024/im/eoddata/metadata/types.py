"""
Import as:

import im.eoddata.metadata.types as imeometyp
"""

import dataclasses
import inspect
from typing import Dict


@dataclasses.dataclass
class BaseClass:
    # TODO(amr): the function is type ignored as I couldn't find an appropriate
    #  return type for subclasses, kept failing with List[Base] != List[Derived],
    #  I then tried a bunch of other collection types, none seemed to fix that
    #  warning, so ignored it for now.
    @classmethod
    def from_dict(cls, d: dict):  # type: ignore
        """
        Create a data class from a dict, ignoring additional arguments.

        The full object can always be viewed in the WSDL file, and we can add
        fields to our custom types as needed.

        Reference: https://stackoverflow.com/a/55096964/7178540
        """
        args = {
            k: v for k, v in d.items() if k in inspect.signature(cls).parameters
        }
        # Mypy has limited mixin support: https://github.com/python/mypy/issues/5887
        return cls(**args)  # type: ignore


# We use the same names (including case) as the EODData API.
# The transform stage will adapt the names to our internal names.
@dataclasses.dataclass
class Exchange(BaseClass):
    Code: str


@dataclasses.dataclass
class Symbol(BaseClass):
    Code: str
    Name: str
    LongName: str

    @classmethod
    def from_csv_row(cls, row: Dict[str, str], exchange_code: str) -> "Symbol":
        """
        Create a Symbol from a csv row, appends exchange code to symbol code.
        """
        return cls(
            Code=f"{exchange_code}:{row['Code']}",
            Name=row["Name"],
            LongName=row["LongName"],
        )
