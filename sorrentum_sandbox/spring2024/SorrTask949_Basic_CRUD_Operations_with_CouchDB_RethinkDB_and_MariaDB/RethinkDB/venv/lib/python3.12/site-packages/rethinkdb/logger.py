# Copyright 2018 RethinkDB
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Wrap logging package to not repeat general logging steps.
"""


import logging
import sys


class DriverLogger(object):
    """
    DriverLogger is a wrapper for logging's debug, info, warning and error functions.
    """

    def __init__(self, level=logging.INFO):
        """
        Initialize DriverLogger

        :param level: Minimum logging level
        :type level: int
        """

        super(DriverLogger, self).__init__()

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level)

        self.write_to_console = False

    @staticmethod
    def _convert_message(message):
        """
        Convert any message to string.

        :param message: Message to log
        :type message: any
        :return: String representation of the message
        :rtype: str
        """

        return str(message)

    def _print_message(self, level, message):
        if self.write_to_console:
            if level <= logging.WARNING:
                sys.stdout.write(message)
            else:
                sys.stderr.write(message)

    def _log(self, level, message, *args, **kwargs):
        self._print_message(level, message)
        self.logger.log(level, message, *args, **kwargs)

    def debug(self, message):
        """
        Log debug messages.

        :param message: Debug message
        :type message: str
        :rtype: None
        """

        self._log(logging.DEBUG, message)

    def info(self, message):
        """
        Log info messages.

        :param message: Info message
        :type message: str
        :rtype: None
        """

        self._log(logging.INFO, message)

    def warning(self, message):
        """
        Log warning messages.

        :param message: Warning message
        :type message: str
        :rtype: None
        """

        self._log(logging.WARNING, message)

    def error(self, message):
        """
        Log error messages.

        :param message: Error message
        :type message: str
        :rtype: None
        """

        self._log(logging.ERROR, message)

    def exception(self, exc, with_raise=False):
        """
        Log an exception with its traceback and the message if possible.

        :param exc: Exception
        :type exc: str
        :rtype: None
        """

        self._log(logging.ERROR, self._convert_message(exc), exc_info=1)

        if with_raise and isinstance(exc, Exception):
            raise exc


default_logger = DriverLogger()
