"""
General utilities that can be used across multiple IG datasets.

Import as:

import im_v2.ig.ig_utils as imvigigut
"""

import datetime
import logging
import re
from typing import List, Optional

import pandas as pd

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg

_LOG = logging.getLogger(__name__)


# This represents a date in the format for the IG TAQ data on S3, as
# YYYYMMDD (e.g., "20031002").
# NOTE: We keep the dates as `datetime.date` and convert them into `IgDate`
# only right before accessing the data.
IgDate = str


def is_valid_IG_date(ig_date: IgDate) -> bool:
    # TODO(gp): We should check that it's a valid date, rather than just
    #  a sequence of numbers.
    return re.search(r"^\d{8}$", ig_date)


def dassert_is_valid_IG_date(ig_date: IgDate) -> None:
    hdbg.dassert(is_valid_IG_date(ig_date), "Invalid IG_date '%s'", ig_date)


def convert_to_date(date: hdateti.Datetime) -> datetime.date:
    return pd.Timestamp(date).date()


def convert_to_ig_date(date: hdateti.Datetime) -> IgDate:
    """
    Convert a date into the IG YYYYMMDD representation (e.g., "20031002").
    """
    return convert_to_date(date).strftime("%Y%m%d")


def filter_dates(
    start_date: Optional[hdateti.Datetime],
    end_date: Optional[hdateti.Datetime],
    dates: List[datetime.date],
) -> List[datetime.date]:
    """
    Filter `dates` using [`start_date`, `end_date`], where `None` means no
    boundary.
    """
    if start_date is not None:
        start_date = convert_to_date(start_date)
    else:
        start_date = min(dates)
    if end_date is not None:
        end_date = convert_to_date(end_date)
    else:
        end_date = max(dates)
    hdbg.dassert_lte(start_date, end_date)
    #
    dates = [d for d in dates if start_date <= d <= end_date]
    hdbg.dassert_lte(
        1,
        len(dates),
        "No dates were selected for start_date=%s, end_date=%s",
        start_date,
        end_date,
    )
    _LOG.debug("Filtered dates=%s [%s, %s]", len(dates), min(dates), max(dates))
    return dates


def intersect_dates(
    dates: List[datetime.date],
    valid_dates: List[datetime.date],
) -> List[datetime.date]:
    """
    Filter `valid_dates` using `dates`.
    """
    hdbg.dassert_lte(1, len(dates))
    hdbg.dassert_lte(1, len(valid_dates))
    #
    valid_dates = set(valid_dates)
    dates = [d for d in dates if d in valid_dates]
    hdbg.dassert_lte(1, len(dates), "No dates were selected")
    _LOG.debug(
        "Intersected dates=%s [%s, %s]", len(dates), min(dates), max(dates)
    )
    return dates
