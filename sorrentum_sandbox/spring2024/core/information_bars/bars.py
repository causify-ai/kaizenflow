"""
Import as:

import core.information_bars.bars as cinbabar
"""

import logging
from typing import Generator, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)

# #############################################################################


def _crop_data_frame_in_batches(
    df: pd.DataFrame, chunksize: int
) -> List[pd.DataFrame]:
    """
    Split df into chunks of chunksize.

    :param df: Dataframe to split
    :param chunksize: Number of rows in chunk
    :return: Chunks
    """
    generator_object = []
    for _, chunk in df.groupby(np.arange(len(df)) // chunksize):
        generator_object.append(chunk)
    return generator_object


class _StandardBars:
    """
    Contains all of the logic to construct the standard bars from chapter 2.
    This class shouldn't be used directly. We have added functions to the
    package such as get_dollar_bars which will create an instance of this class
    and then construct the standard bars, to return to the user.

    This is because we wanted to simplify the logic as much as possible,
    for the end user.
    """

    def __init__(
        self,
        metric: str,
        threshold: Union[float, int, pd.Series] = 50000,
        batch_size: int = 20000000,
    ):
        """
        Construct the instance of the class.

        :param metric: Type of imbalance bar to create. Example: dollar_imbalance.
        :param threshold:
        :param batch_size: Number of rows to read in from the csv, per batch.
        """
        # Base properties.
        self.metric = metric
        self.batch_size = batch_size
        self.prev_tick_rule = 0
        # Cache properties.
        self.open_price: Optional[float] = None
        self.prev_price: Optional[float] = None
        self.close_price: Optional[float] = None
        self.high_price, self.low_price = -np.inf, np.inf
        self.cum_statistics = {
            "cum_ticks": 0,
            "cum_dollar_value": 0,
            "cum_volume": 0,
            "cum_buy_volume": 0,
        }
        # Tick number when bar was formed.
        self.tick_num = 0
        # Threshold at which to sample.
        self.threshold = threshold
        # Batch_run properties.
        # The first flag is false since the first batch doesn't use the cache.
        self.flag = False

    def batch_run(
        self,
        file_path_or_df: Union[str, Iterable[str], pd.DataFrame],
        to_csv: bool = False,
        output_path: Optional[str] = None,
    ) -> Union[pd.DataFrame, None]:
        """
        Read csv file(s) or pd.DataFrame in batches and then constructs the
        financial data structure in the form of a DataFrame. The csv file or
        DataFrame must have only 3 columns: date_time, price, & volume.

        :param file_path_or_df: Path to the csv file(s) or Pandas Data Frame containing
        raw tick data in the format[date_time, price, volume]
        :param to_csv: Flag for writing the results of bars generation to local csv file,
        or to in-memory DataFrame
        :param output_path: Path to results file, if to_csv = True

        :return: Financial data structure
        """
        if to_csv is True:
            # If to_csv is true, header should written on the first batch only.
            header = True
            if output_path:
                # Clean output csv file.
                open(output_path, "w").close()
        _LOG.debug("Reading data in batches:")
        # Read csv in batches.
        count = 0
        final_bars = []
        cols = [
            "date_time",
            "tick_num",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "cum_buy_volume",
            "cum_ticks",
            "cum_dollar_value",
        ]
        for batch in self._batch_iterator(file_path_or_df):
            _LOG.debug("Batch number: %d", count)
            list_bars = self.run(data=batch)
            if to_csv is True:
                pd.DataFrame(list_bars, columns=cols).to_csv(
                    output_path, header=header, index=False, mode="a"
                )
                header = False
            else:
                # Append to bars list.
                final_bars += list_bars
            count += 1
        _LOG.debug("Returning bars")
        # Return a DataFrame.
        if final_bars:
            bars_df = pd.DataFrame(final_bars, columns=cols)
            return bars_df
        # Processed DataFrame is stored in .csv file, return None.
        return None

    def run(self, data: Union[list, tuple, pd.DataFrame]) -> list:
        """
        Read a List, Tuple, or Dataframe and then constructs the financial data
        structure in the form of a list. The List, Tuple, or DataFrame must
        have only 3 attrs: date_time, price, & volume.

        :param data: Dict or ndarray containing raw tick data
        in the format[date_time, price, volume]
        :return: Financial data structure
        """
        if isinstance(data, (list, tuple)):
            values = data
        elif isinstance(data, pd.DataFrame):
            values = data.values
        else:
            raise ValueError("data is neither list nor tuple nor pd.DataFrame")
        list_bars = self._extract_bars(data=values)
        # Set flag to True: notify function to use cache.
        self.flag = True
        return list_bars

    @staticmethod
    def _assert_csv(test_batch: pd.DataFrame) -> None:
        """
        Test that the csv file read has the format: date_time, price, and
        volume. If not then the user needs to create such a file. This format
        is in place to remove any unwanted overhead.

        :param test_batch: The first row of the dataset.
        """
        hdbg.dassert_eq(
            test_batch.shape[1],
            3,
            "Must have only 3 columns in csv: date_time, price, & volume.",
        )
        hdbg.dassert_isinstance(
            test_batch.iloc[0, 1], float, "price column in csv not float."
        )
        try:
            pd.to_datetime(test_batch.iloc[0, 0])
        except ValueError as ex:
            raise ValueError(
                "csv file, column 0, not a date time format:",
                test_batch.iloc[0, 0],
            ) from ex

    def _batch_iterator(
        self, file_path_or_df: Union[str, Iterable[str], pd.DataFrame]
    ) -> Generator[pd.DataFrame, None, None]:
        """
        Iterate over rows.

        :param file_path_or_df: Path to the csv file(s) or Pandas Data Frame containing
        raw tick data in the format[date_time, price, volume]
        """
        if isinstance(file_path_or_df, (list, tuple)):
            # Assert format of all files.
            for file_path in file_path_or_df:
                self._read_first_row(file_path)
            for file_path in file_path_or_df:
                for batch in pd.read_csv(
                    file_path, chunksize=self.batch_size, parse_dates=[0]
                ):
                    yield batch
        elif isinstance(file_path_or_df, str):
            self._read_first_row(file_path_or_df)
            for batch in pd.read_csv(
                file_path_or_df, chunksize=self.batch_size, parse_dates=[0]
            ):
                yield batch
        elif isinstance(file_path_or_df, pd.DataFrame):
            for batch in _crop_data_frame_in_batches(
                file_path_or_df, self.batch_size
            ):
                yield batch
        else:
            raise ValueError(
                "file_path_or_df is neither string(path to a csv file), "
                "iterable of strings, nor pd.DataFrame"
            )

    def _read_first_row(self, file_path: str) -> None:
        """
        Read first row of the CSV file.

        :param file_path: Path to the csv file containing raw tick data
        in the format[date_time, price, volume]
        """
        # Read in the first row & assert format.
        first_row = pd.read_csv(file_path, nrows=1)
        self._assert_csv(first_row)

    def _extract_bars(self, data: Union[list, tuple, np.ndarray]) -> list:
        """
        Compile the various bars: dollar, volume, or tick, in a for loop.

        We did investigate the use of trying to solve this in a vectorised
        manner but found that a For loop worked well.

        :param data: (tuple) Contains 3 columns - date_time, price, and volume.
        :return: Extracted bars
        """
        # Iterate over rows.
        list_bars: List[list] = []
        for row in data:
            # Set variables.
            date_time = row[0]
            self.tick_num += 1
            price = float(row[1])
            volume = row[2]
            dollar_value = price * volume
            signed_tick = self._apply_tick_rule(price)
            if isinstance(self.threshold, (int, float)):
                # If the threshold is fixed, it's used for every sampling.
                threshold = self.threshold
            else:
                # If the threshold is changing, then the threshold defined just before
                # sampling time is used
                threshold = self.threshold.iloc[
                    self.threshold.index.get_loc(date_time, method="pad")
                ]
            if self.open_price is None:
                self.open_price = price
            # Update high low prices.
            self.high_price, self.low_price = self._update_high_low(price)
            # Calculations.
            self.cum_statistics["cum_ticks"] += 1
            self.cum_statistics["cum_dollar_value"] += dollar_value
            self.cum_statistics["cum_volume"] += volume
            if signed_tick == 1:
                self.cum_statistics["cum_buy_volume"] += volume
            # If threshold reached then take a sample.
            if self.cum_statistics[self.metric] >= threshold:
                self._create_bars(
                    date_time, price, self.high_price, self.low_price, list_bars
                )
                # Reset cache.
                self._reset_cache()
        return list_bars

    def _reset_cache(self) -> None:
        """
        Describe how cache should be reset when new bar is sampled.
        """
        self.open_price = None
        self.high_price, self.low_price = -np.inf, np.inf
        self.cum_statistics = {
            "cum_ticks": 0,
            "cum_dollar_value": 0,
            "cum_volume": 0,
            "cum_buy_volume": 0,
        }

    def _update_high_low(self, price: float) -> Tuple[float, float]:
        """
        Update the high and low prices using the current price.

        :param price: Current price
        :return: Updated high and low prices
        """
        if price > self.high_price:
            high_price = price
        else:
            high_price = self.high_price

        if price < self.low_price:
            low_price = price
        else:
            low_price = self.low_price
        return high_price, low_price

    def _create_bars(
        self,
        date_time: str,
        price: float,
        high_price: float,
        low_price: float,
        list_bars: list,
    ) -> None:
        """
        Construct a bar which has the following fields: date_time, open, high,
        low, close, volume, cum_buy_volume, cum_ticks, cum_dollar_value. These
        bars are appended to list_bars, which is later used to construct the
        final bars DataFrame.

        :param date_time: Timestamp of the bar
        :param price: The current price
        :param high_price: Highest price in the period
        :param low_price: Lowest price in the period
        :param list_bars: List to which we append the bars
        """
        # Create bars.
        open_price = self.open_price
        high_price = max(high_price, open_price)
        low_price = min(low_price, open_price)
        close_price = price
        volume = self.cum_statistics["cum_volume"]
        cum_buy_volume = self.cum_statistics["cum_buy_volume"]
        cum_ticks = self.cum_statistics["cum_ticks"]
        cum_dollar_value = self.cum_statistics["cum_dollar_value"]
        # Update bars.
        list_bars.append(
            [
                date_time,
                self.tick_num,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                cum_buy_volume,
                cum_ticks,
                cum_dollar_value,
            ]
        )

    def _apply_tick_rule(self, price: float) -> int:
        """
        Apply the tick rule as defined on page 29 of Advances in Financial
        Machine Learning.

        :param price: Price at time t
        :return: The signed tick
        """
        if self.prev_price is not None:
            tick_diff = price - self.prev_price
        else:
            tick_diff = 0
        if tick_diff != 0:
            signed_tick: int = np.sign(tick_diff)
            self.prev_tick_rule = signed_tick
        else:
            signed_tick = self.prev_tick_rule
        # Update previous price used for tick rule calculations.
        self.prev_price = price
        return signed_tick

    def _get_imbalance(
        self, price: float, signed_tick: int, volume: float
    ) -> float:
        """
        Get the imbalance at a point in time, denoted as Theta_t.

        :param price: Price at t
        :param signed_tick: signed tick, using the tick rule
        :param volume: Volume traded at t
        :return: Imbalance at time t
        """
        imbalance: float
        if self.metric == "tick_imbalance" or self.metric == "tick_run":
            imbalance = signed_tick
        elif self.metric == "dollar_imbalance" or self.metric == "dollar_run":
            imbalance = signed_tick * volume * price
        elif self.metric == "volume_imbalance" or self.metric == "volume_run":
            imbalance = signed_tick * volume
        else:
            raise ValueError(
                "Unknown imbalance metric, possible values are tick/dollar/volume imbalance/run"
            )
        return imbalance


def get_dollar_bars(
    file_path_or_df: Union[str, Iterable[str], pd.DataFrame],
    threshold: Union[float, int, pd.Series] = 70000000,
    batch_size: int = 20000000,
    to_csv: bool = False,
    output_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Create the dollar bars: date_time, open, high, low, close, volume,
    cum_buy_volume, cum_ticks, cum_dollar_value.

    :param file_path_or_df: Path to the csv file(s) or Pandas Data Frame containing
    raw tick data in the format[date_time, price, volume]
    :param threshold: A cumulative value above this threshold triggers a sample to be taken.
    If a series is given, then at each sampling time the closest previous threshold is used.
    Values in the series can only be at times when the threshold is changed,
    not for every observation.
    :param batch_size: The number of rows per batch. Less RAM = smaller batch size.
    :param to_csv: Save bars to csv after every batch run (True or False)
    :param output_path: Path to csv file, if to_csv is True
    :return: Dataframe of dollar bars
    """
    bars = _StandardBars(
        metric="cum_dollar_value", threshold=threshold, batch_size=batch_size
    )
    dollar_bars = bars.batch_run(
        file_path_or_df=file_path_or_df,
        to_csv=to_csv,
        output_path=output_path,
    )
    return dollar_bars


def get_volume_bars(
    file_path_or_df: Union[str, Iterable[str], pd.DataFrame],
    threshold: Union[float, int, pd.Series] = 70000000,
    batch_size: int = 20000000,
    to_csv: bool = False,
    output_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Create the volume bars: date_time, open, high, low, close, volume,
    cum_buy_volume, cum_ticks, cum_dollar_value.

    :param file_path_or_df: Path to the csv file(s) or Pandas Data Frame containing
    raw tick data in the format[date_time, price, volume]
    :param threshold: A cumulative value above this threshold triggers a sample to be taken.
    If a series is given, then at each sampling time the closest previous threshold is used.
    Values in the series can only be at times when the threshold is changed,
    not for every observation
    :param batch_size: The number of rows per batch. Less RAM = smaller batch size.
    :param to_csv: Save bars to csv after every batch run (True or False)
    :param output_path: Path to csv file, if to_csv is True
    :return: Dataframe of volume bars
    """
    bars = _StandardBars(
        metric="cum_volume", threshold=threshold, batch_size=batch_size
    )
    volume_bars = bars.batch_run(
        file_path_or_df=file_path_or_df,
        to_csv=to_csv,
        output_path=output_path,
    )
    return volume_bars


def get_tick_bars(
    file_path_or_df: Union[str, Iterable[str], pd.DataFrame],
    threshold: Union[float, int, pd.Series] = 70000000,
    batch_size: int = 20000000,
    to_csv: bool = False,
    output_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Create the tick bars: date_time, open, high, low, close, volume,
    cum_buy_volume, cum_ticks, cum_dollar_value.

    :param file_path_or_df: Path to the csv file(s) or Pandas Data Frame containing
    raw tick data in the format[date_time, price, volume]
    :param threshold: A cumulative value above this threshold triggers a sample to be taken.
    If a series is given, then at each sampling time the closest previous threshold is used.
    Values in the series can only be at times when the threshold is changed,
    not for every observation
    :param batch_size: The number of rows per batch. Less RAM = smaller batch size.
    :param to_csv: Save bars to csv after every batch run (True or False)
    :param output_path: Path to csv file, if to_csv is True
    :return: Dataframe of volume bars
    """
    bars = _StandardBars(
        metric="cum_ticks", threshold=threshold, batch_size=batch_size
    )
    tick_bars = bars.batch_run(
        file_path_or_df=file_path_or_df,
        to_csv=to_csv,
        output_path=output_path,
    )
    return tick_bars
