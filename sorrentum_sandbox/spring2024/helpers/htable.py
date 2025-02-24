"""
Import as:

import helpers.htable as htable
"""

import copy
import csv
import logging
from typing import Any, List, Tuple

import helpers.hdbg as hdbg
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


TableType = List[List[str]]


class Table:
    """
    A simple (rectangular) table without introducing a dependency from Pandas.

    The element in the table can be anything.
    """

    def __init__(self, table: TableType, column_names: List[str]) -> None:
        # Check that the inputs are well-formed.
        self._check_table(table, column_names)
        # Save state.
        self._table = table
        self._column_names = column_names
        _LOG.debug("%s", self.__repr__())
        # Map a column name to the index of the corresponding column, to allow
        # indexing by column.
        self._col_to_idx = {
            col: idx for idx, col in enumerate(self._column_names)
        }
        _LOG.debug("col_to_idx=%s", str(self._col_to_idx))

    def __str__(self) -> str:
        """
        Return a string representing the table with columns aligned.
        """
        table = copy.deepcopy(self._table)
        table.insert(0, self._column_names)
        # Convert the cells to strings.
        table_as_str = [[str(cell) for cell in row] for row in table]
        # Find the length of each columns.
        lengths = [max(map(len, col)) for col in zip(*table_as_str)]
        _LOG.debug(hprint.to_str("lengths"))
        # Compute format for the columns.
        fmt = " ".join(f"{{:{x}}} |" for x in lengths)
        _LOG.debug(hprint.to_str("fmt"))
        # Add the row separating the column names.
        row_sep = ["-" * length for length in lengths]
        table.insert(1, row_sep)
        table_as_str = [[str(cell) for cell in row] for row in table]
        # Format rows.
        rows_as_str = [fmt.format(*row) for row in table_as_str]
        # Remove trailing spaces.
        rows_as_str = [row.rstrip() for row in rows_as_str]
        # Create string.
        res = "\n".join(rows_as_str)
        # res += "\nsize=%s" % str(self.size())
        return res

    def __repr__(self) -> str:
        res = ""
        res += f"cols={str(self._column_names)}"
        res += "\ntable=\n%s" % "\n".join(map(str, self._table))
        res += "\n" + f"size={str(self.size())}"
        return res

    @classmethod
    def from_text(cls, cols: List[str], txt: str, delimiter: str) -> "Table":
        """
        Build a table from a list of columns and the body of a CSV file.
        """
        hdbg.dassert_isinstance(txt, str)
        table = list(csv.reader(txt.split("\n"), delimiter=delimiter))
        return cls(table, cols)

    def size(self) -> Tuple[int, int]:
        """
        Return the size of the table.

        :return: number of rows x columns (i.e., numpy / Pandas convention)
        """
        return len(self._table), len(self._column_names)

    def filter_rows(self, column_name: str, value: str) -> "Table":
        """
        Return a Table filtered with rows filtered by the criteria "field ==
        value".
        """
        _LOG.debug("self=\n%s", repr(self))
        # Filter the rows.
        hdbg.dassert_in(column_name, self._col_to_idx.keys())
        rows_filter = [
            row
            for row in self._table
            if row[self._col_to_idx[column_name]] == value
        ]
        _LOG.debug(hprint.to_str("rows_filter"))
        # Build the resulting table.
        table_filter = Table(rows_filter, self._column_names)
        _LOG.debug("table_filter=\n%s", repr(table_filter))
        return table_filter

    def get_column(self, column_name: str) -> List[Any]:
        """
        Return the list of unique values for a row / field.
        """
        hdbg.dassert_in(column_name, self._column_names)
        column_idx = self._col_to_idx[column_name]
        # Scan the rows to extract the column.
        vals = []
        for row in self._table:
            vals.append(row[column_idx])
        return vals

    def unique(self, column_name: str) -> List[Any]:
        """
        Return a list of unique values for a field.
        """
        vals = self.get_column(column_name)
        vals = sorted(list(set(vals)))
        return vals

    @staticmethod
    def _check_table(table: TableType, column_names: List[str]) -> None:
        """
        Check that the table is well-formed (e.g., the list of lists is
        rectangular).
        """
        hdbg.dassert_isinstance(table, list)
        hdbg.dassert_isinstance(column_names, list)
        hdbg.dassert_no_duplicates(column_names)
        # Columns have no leading or trailing spaces.
        for column_name in column_names:
            hdbg.dassert_eq(column_name, column_name.rstrip().lstrip())
        # Check that the list of lists is rectangular.
        for row in table:
            hdbg.dassert_isinstance(table, list)
            hdbg.dassert_eq(
                len(row),
                len(column_names),
                "Invalid row='%s' for cols='%s'",
                row,
                column_names,
            )
