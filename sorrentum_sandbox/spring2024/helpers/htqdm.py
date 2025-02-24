"""
Import as:

import helpers.htqdm as htqdm
"""
import io
import logging
from typing import Any, Optional

# Avoid dependency from other `helpers` modules, such as `helpers.hjoblib`, to
# prevent import cycles.


# From https://github.com/tqdm/tqdm/issues/313
class TqdmToLogger(io.StringIO):
    """
    Output stream for `tqdm` which will output to logger module instead of the
    `stdout`.

    Use as:
    ```
    from tqdm.autonotebook import tqdm

    tqdm_out = TqdmToLogger(_LOG, level=logging.INFO)
    for ... tqdm(..., file=tqdm_out):
    ```
    """

    logger = None
    level = None
    buf = ""

    def __init__(self, logger: Any, level: Optional[int] = None):
        super().__init__()
        self.logger = logger
        self.level = level or logging.INFO

    def write(self, buf: str) -> None:
        self.buf = buf.strip("\r\n\t ")

    def flush(self) -> None:
        self.logger.log(self.level, self.buf)
