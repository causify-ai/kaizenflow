#!/usr/bin/env python

"""
Read EODData symbol list for exchanges from a directory.

Import as:

import im.eoddata.metadata.load.loader as imemelolo
"""
import csv
import io
import logging
import os
from typing import List

import helpers.hio as hio
import im.eoddata.metadata.types as imeometyp

_LOG = logging.getLogger(__name__)

# #############################################################################


class MetadataLoader:
    @staticmethod
    def read_symbols_from_file(file_: str) -> List[imeometyp.Symbol]:
        _LOG.debug("Processing file: '%s' ...", file_)
        exchange_code, _ = os.path.basename(file_).split(".")

        reader = csv.DictReader(io.StringIO(hio.from_file(file_)))
        symbols = [
            imeometyp.Symbol.from_csv_row(row=row, exchange_code=exchange_code)
            for row in reader
        ]
        _LOG.debug("Found %s symbols in '%s'", len(symbols), file_)
        return symbols
