"""
Import as:

import oms.broker.replayed_data_reader as obredare
"""
from datetime import datetime
from typing import List, Optional

import pandas as pd


# TODO(gp): -> ReplayedRawDataReader
# TODO(gp): It should be close to RawDataReader.
# TODO(gp): Consider the big unification of ImClient and RawDataReader.
class ReplayDataReader:
    """
    Replay the behavior of an actual RawDataReader.

    This class allows advanced testing of broker behavior by replaying the data
    produced by `RawDataReader` during a particular experiment in the same
    sequential order.
    """

    def __init__(self, bid_ask_data_log_file_names: List[str]) -> None:
        """
        Initialize ReplayDataReader.

        :param bid_ask_data_log_file_names: sorted list of paths to
            bid_ask_data log files.
        """
        self._bid_ask_data_log_file_names = bid_ask_data_log_file_names

    # TODO(gp): Why all these params.
    def load_db_table(
        self,
        start_timestamp: Optional[pd.Timestamp],
        end_timestamp: Optional[pd.Timestamp],
        deduplicate: bool = False,
        *,
        currency_pairs: Optional[List[str]] = None,
        bid_ask_levels: Optional[List[int]] = None,
        bid_ask_format="wide",
        subset: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Load DB table data from a next log file in line.

        This method has the same signature as
        `RawDataReader.load_db_table()` in order to allow replayed
        behavior.
        """
        bid_ask_data = self._read_csv_file(
            self._bid_ask_data_log_file_names.pop(0)
        )
        return bid_ask_data

    # ///////////////////////////////////////////////////////////////////////////
    # Private interface.
    # ///////////////////////////////////////////////////////////////////////////

    # TODO(gp): Convert to staticmethod
    def _read_csv_file(self, path: str) -> pd.DataFrame:
        """
        Read data from requested CSV file and return the dataframe.
        """
        # TODO(gp): Use hio.from_file.
        with open(path, "r") as csv_file:
            df = pd.read_csv(csv_file)

        # Helper function to rectify precision of the timestamp when millisecond
        # part is missing.
        def _remove_datetime_outliers(value):
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f%z")
            except ValueError:
                # Handle outliers here, for example, you can return a default value or NaN
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S%z")

        df["knowledge_timestamp"] = df["knowledge_timestamp"].apply(
            _remove_datetime_outliers
        )
        df["end_download_timestamp"] = df["end_download_timestamp"].apply(
            _remove_datetime_outliers
        )
        df.set_index("timestamp", inplace=True)
        return df
