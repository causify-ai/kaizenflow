"""
Import as:

import im.kibot.metadata.load.adjustments as imkmeload
"""

import os
from typing import List

import helpers.hpandas as hpandas
import helpers.hs3 as hs3
import im.kibot.metadata.config as imkimecon
import im.kibot.metadata.types as imkimetyp


class AdjustmentsLoader:
    @staticmethod
    def load(symbol: str) -> List[imkimetyp.Adjustment]:
        s3_path = os.path.join(
            imkimecon.S3_PREFIX, imkimecon.ADJUSTMENTS_SUB_DIR, f"{symbol}.txt"
        )
        sep = "\t"
        s3fs = hs3.get_s3fs("am")
        stream, kwargs = hs3.get_local_or_s3_stream(s3_path, s3fs=s3fs)
        df = hpandas.read_csv_to_df(stream, sep=sep, **kwargs)
        return [imkimetyp.Adjustment(*row) for row in df.values.tolist()]
