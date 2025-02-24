"""
Import as:

import helpers.telegram_notify.telegram_notify as htnoteno
"""

import json
import logging
import os
import os.path
import re
import sys
from typing import Optional

import requests

# Alternative that works for both Python 2 and 3:
import requests.compat as rcompa

import helpers.telegram_notify.config as htenocon

_LOG = logging.getLogger(__name__)

# #############################################################################
# TelegramNotebookNotify.
# #############################################################################


class TelegramNotebookNotify:
    """
    Sends notifications.
    """

    def __init__(self) -> None:
        self.launcher_name = _get_launcher_name()
        self.token, self.chat_id = htenocon.get_info()

    @staticmethod
    def send(
        text: str, token: Optional[str], chat_id: Optional[str]
    ) -> Optional[bytes]:
        if chat_id is None or token is None:
            _LOG.warning(
                "Not sending notifications. To send notifications, both "
                "`chat_id` and `token` need to be specified. Go to README.md"
                "for more information."
            )
            return None
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        return requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
        ).content

    def notify(self, message: str) -> None:
        msg = f"<pre>{self.launcher_name}</pre>: {message}"
        self.send(msg, self.token, self.chat_id)


def _get_launcher_name() -> str:
    """
    Return the name of jupyter notebook or path to python file you are running.
    """
    import ipykernel

    try:  # Python 3 (see Edit2 below for why this may not work in Python 2)
        import notebook.notebookapp as ihnb
    except ImportError:  # Python 2
        import warnings

        import IPython.utils.shimmodule as iush

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=iush.ShimWarning)
            import IPython.html.notebookapp as ihnb
    launcher = sys.argv[0]
    if os.path.basename(launcher) == "ipykernel_launcher.py":
        match = re.search(
            "kernel-(.*).json", ipykernel.connect.get_connection_file()
        )
        if match is None:
            return launcher
        kernel_id = match.group(1)
        servers = ihnb.list_running_servers()
        for ss in servers:
            response = requests.get(
                rcompa.urljoin(ss["url"], "api/sessions"),  # type: ignore
                params={"token": ss.get("token", "")},
            )
            for nn in json.loads(response.text):
                if nn["kernel"]["id"] == kernel_id:
                    relative_path = nn["notebook"]["path"]
                    return str(os.path.basename(relative_path))
    return launcher


class _RequestsHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> bytes:  # type: ignore
        token, chat_id = htenocon.get_info()
        log_entry = self.format(record)
        payload = {"chat_id": chat_id, "text": log_entry, "parse_mode": "HTML"}
        return requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
        ).content


class _LogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        launcher_name = _get_launcher_name()
        return f"<pre>{launcher_name}</pre>: {record.msg}"


def init_tglogger(log_level: int = logging.DEBUG) -> None:
    """
    Send notifications using logging.
    """
    _tg_log = logging.getLogger("telegram_notify")
    _tg_log.setLevel(log_level)
    handler = _RequestsHandler()
    formatter = _LogFormatter()
    handler.setFormatter(formatter)
    _tg_log.handlers = [handler]


# #############################################################################
# TelegramNotify.
# #############################################################################


class TelegramNotify:
    """
    Send notifications.
    """

    def __init__(self) -> None:
        self.token, self.chat_id = htenocon.get_info()

    def send(self, text: str) -> Optional[bytes]:
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        return requests.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=payload,
        ).content
