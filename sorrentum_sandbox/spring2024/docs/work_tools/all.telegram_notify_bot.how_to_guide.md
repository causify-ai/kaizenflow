

<!-- toc -->

- [telegram-notify](#telegram-notify)
  * [Configuring the Bot](#configuring-the-bot)
    + [Getting token and chat id](#getting-token-and-chat-id)
    + [Modifying config for your token and chat id](#modifying-config-for-your-token-and-chat-id)
  * [How to use](#how-to-use)
    + [Command line](#command-line)
    + [TelegramNotify](#telegramnotify)
    + [Logging](#logging)

<!-- tocstop -->

# telegram-notify

Send notifications via Telegram.

## Configuring the Bot

### Getting token and chat id

- Start messaging with either `https://t.me/NotifyJupyterBot` (or with a custom
  bot by sending it `/start` message)

- Run:
  ```bash
  > python helpers/telegram_notify/get_chat_id.py --username <your telegram username>
  ```
- Specify `--token <your bot token>` if you are using a custom bot

- This will display a message in your terminal with your chat id and also send a
  message with it through the bot
  ```bash
  User `saggese` is not in the config.py
  Your chat id is: 967103049
  ```

### Modifying config for your token and chat id

- Go to `config.py` and insert the following code
  ```python
  elif user == <your local user name>:
      TELEGRAM_TOKEN = <bot token>
      TELEGRAM_CHAT_ID = <chat id>
  ```
- You should push the modified file to the repo

## How to use

- There are 3 ways of getting notification from the bot:
  - Using command line
  - Through `TelegramNotify` class (e.g., from Python code or a Jupyter
    notebook)
  - Using logging

- In any case the bot will send you something like this:
  `<program name>: <your_message>`

### Command line

- You can use a command line wrapper to signal the end of a command line:

```bash
> cmd_to_check; tg.py -m "error=$?"
> ls; tg.py -m "error=$?"
> ls /I_do_not_exist; tg.py -m "error=$?"
```

### TelegramNotify

```python
import helpers.telegram_notify.telegram_notify as tg

tgn = tg.TelegramNotify()
tgn.notify('test message')
```

### Logging

```python
import logging
import helpers.telegram_notify.telegram_notify as tg

_TG_LOG = logging.getLogger('telegram_notify')
_TG_LOG.setLevel(logging.INFO)
tg.init_tglogger()

_TG_LOG.info('test message')
```
