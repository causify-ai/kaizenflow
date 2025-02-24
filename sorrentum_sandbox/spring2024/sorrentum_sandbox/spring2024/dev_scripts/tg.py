#!/usr/bin/env python

"""
Send a notification through Telegram. See README.md in helpers/telegram_notify.

> cmd_to_check; tg.py -m "error=$?"

> ls; htnoteno.py -m "error=$?"
> ls /I_do_not_exist; htnoteno.py -m "error=$?"

Import as:

import dev_scripts.tg as dscrtg
"""

import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hsystem as hsystem
import helpers.telegram_notify.telegram_notify as htnoteno

_LOG = logging.getLogger(__name__)

# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-m", "--msg", action="store", default="done", type=str)
    parser.add_argument(
        "--cmd",
        action="store",
        default=None,
        type=str,
        help="Command to execute",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    message = []
    message.append("user=%s" % hsystem.get_user_name())
    message.append("server=%s" % hsystem.get_server_name())
    #
    if args.cmd is not None:
        cmd = args.cmd
        _LOG.info("Executing: %s", cmd)
        rc = hsystem.system(cmd, suppress_output=False, abort_on_error=False)
        _LOG.info("rc=%s", rc)
        message.append("cmd='%s'" % cmd)
        message.append("rc=%s" % rc)
    else:
        message.append("msg=%s" % args.msg)
    message = "\n" + "\n".join(message)
    _LOG.info(message)
    #
    tgn = htnoteno.TelegramNotify()
    tgn.send(message)


if __name__ == "__main__":
    _main(_parse())
