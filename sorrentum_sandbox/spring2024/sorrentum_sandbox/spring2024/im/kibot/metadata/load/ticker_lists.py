"""
Import as:

import im.kibot.metadata.load.ticker_lists as imkmltili
"""

import enum
import os
from typing import List, Tuple

import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import im.kibot.metadata.config as imkimecon
import im.kibot.metadata.types as imkimetyp


class ParsingState(enum.Enum):
    # Started parsing the file, no keywords encountered.
    Started = 0
    # A listed section header was found.
    ListedSectionStarted = 1
    # The column headers were skipped.
    HeaderSkipped = 2
    # A delisted section header was found.
    DelistedSectionStarted = 3


class TickerListsLoader:
    # pylint: disable=line-too-long
    """
    Parse text in the following form:

    ```
    Listed: 43 symbols and 4 gigabytes
    Delisted: 3 symbols and 204 megabytes
    List last updated on: 8/31/2020

    Listed:

    - #    Symbol    StartDate    Size(MB)    Description    Exchange    Industry    Sector
    - 1    AA    4/27/2007    68    "Alcoa Corporation"    NYSE    "Aluminum"    "Basic Industries"

    Delisted:

    - 1    XOM    12/1/1999    102    "Exxon Mobil Corporation"    NYSE    "Integrated oil Companies"    "Energy"
    ```
    """
    # pylint: enable=line-too-long

    def get(
        self, ticker_list: str, listed: bool = True
    ) -> List[imkimetyp.Ticker]:
        s3_path = os.path.join(
            imkimecon.S3_PREFIX,
            imkimecon.TICKER_LISTS_SUB_DIR,
            f"{ticker_list}.txt",
        )
        lines = self._get_lines(s3_path=s3_path)
        listed_tickers, delisted_tickers = self._parse_lines(lines=lines)
        return listed_tickers if listed else delisted_tickers

    @staticmethod
    def _get_lines(s3_path: str) -> List[str]:
        aws_profile = "am"
        s3fs = hs3.get_s3fs(aws_profile)
        # TODO(gp): Is it \t?
        sep = "/t"
        # This call was broken during a refactoring and this fix is not
        # guaranteed to work.
        try:
            lines = hpandas.read_csv_to_df(s3_path, sep=sep).values.tolist()
        except Exception:  # pylint: disable=broad-except
            lines = hpandas.read_csv_to_df(s3fs, sep=sep).values.tolist()
        res = [line[0] for line in lines]
        return res

    @staticmethod
    def _get_ticker_from_line(line: str) -> imkimetyp.Ticker:
        # pylint: disable=line-too-long
        """
        Get a ticker from a line.

        - Example line:
        1    AA     4/27/2007    68    "Alcoa Corporation"    NYSE    "Aluminum"    "Basic Industries"
        """
        # pylint: enable=line-too-long
        args = line.split("\t")
        # Remove new line from last element. Note: if we strip before splitting,
        # the tab delimiters would be removed as well if a column is empty.
        args[-1] = args[-1].strip()
        # Skip index col.
        args = args[1:]
        ret = imkimetyp.Ticker(*args)
        return ret

    def _parse_lines(
        self, lines: List[str]
    ) -> Tuple[List[imkimetyp.Ticker], List[imkimetyp.Ticker]]:
        """
        Get a list of listed & delisted tickers from lines.
        """
        listed_tickers: List[imkimetyp.Ticker] = []
        delisted_tickers: List[imkimetyp.Ticker] = []
        state = ParsingState.Started
        for line in lines:
            if not line.strip():
                # Skip empty lines.
                continue
            if state == ParsingState.Started:
                if line.strip() == "Listed:":
                    state = ParsingState.ListedSectionStarted
            elif state == ParsingState.ListedSectionStarted:
                # First non-empty line after 'listed' section header is always the header.
                state = ParsingState.HeaderSkipped
            elif state == ParsingState.HeaderSkipped:
                if line.strip() == "Delisted:":
                    state = ParsingState.DelistedSectionStarted
                else:
                    listed_tickers.append(self._get_ticker_from_line(line))
            elif state == ParsingState.DelistedSectionStarted:
                delisted_tickers.append(self._get_ticker_from_line(line))
        return listed_tickers, delisted_tickers
