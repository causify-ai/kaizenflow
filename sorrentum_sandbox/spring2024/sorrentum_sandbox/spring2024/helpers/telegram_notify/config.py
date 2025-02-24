"""
Import as:

import helpers.telegram_notify.config as htenocon
"""

import getpass
import os
from typing import Tuple

import helpers.hdbg as hdbg

NOTIFY_JUPYTER_TOKEN = os.environ["AM_TELEGRAM_TOKEN"]


def get_info() -> Tuple[str, str]:
    user = getpass.getuser()
    # telegram_token is the token of your bot
    # - You can use @NotifyJupyterBot, its token is
    #   '***REMOVED***'
    # chat_id: To get it, start messaging with the bot. Then go to
    # https://api.telegram.org/bot<telegram_token>/getUpdates and get your chat id.
    # (If you are using @NotifyJupyterBot, go to
    # https://api.telegram.org/bot***REMOVED***/getUpdates )
    if user in ("saggese", "gsaggese", "root"):
        telegram_token = NOTIFY_JUPYTER_TOKEN
        chat_id = "967103049"
    else:
        hdbg.dfatal(f"User `{user}` is not in the config.py")
    return telegram_token, chat_id
