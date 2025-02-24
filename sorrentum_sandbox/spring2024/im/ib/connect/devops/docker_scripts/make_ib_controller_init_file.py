#!/usr/bin/env python
"""
Create IB controller config from parameters passed from command line.

Based on:
https://github.com/ib-controller/ib-controller/blob/master/resources/IBController.ini

# Create config with IB user/password:
> make_ib_controller_init_file.py --user username --password password

Import as:

import im.ib.connect.devops.docker_scripts.make_ib_controller_init_file as imicddsmicif
"""
import argparse
import logging
from typing import Any, Dict

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser

DEFAULT_CONFIG = dict(
    LogToConsole="yes",
    FIX="no",
    IbLoginId="edemo",
    IbPassword="demouser",
    PasswordEncrypted="no",
    FIXLoginId=None,
    FIXPassword=None,
    FIXPasswordEncrypted="yes",
    TradingMode="paper",
    IbDir=None,
    StoreSettingsOnServer="no",
    MinimizeMainWindow="no",
    ExistingSessionDetectedAction="secondary",
    AcceptIncomingConnectionAction="accept",
    ShowAllTrades="no",
    ForceTwsApiPort=4001,
    ReadOnlyLogin="no",
    AcceptNonBrokerageAccountWarning="yes",
    IbAutoClosedown="no",
    ClosedownAt=None,
    AllowBlindTrading="no",
    DismissPasswordExpiryWarning="yes",
    DismissNSEComplianceNotice="yes",
    SaveTwsSettingsAt=None,
    IbControllerPort=7462,
    IbControlFrom=None,
    IbBindAddress=None,
    CommandPrompt=None,
    SuppressInfoMessages="yes",
    LogComponents="yes",
)
PATH_TO_CONFIG = "/root/IBController/IBController.ini"
_LOG = logging.getLogger(__name__)


def _save_config_to_file(config: Dict[str, Any]) -> None:
    # Get text to save.
    string = "\n".join(
        [
            "%s=%s" % (param, value)
            for param, value in config.items()
            if value is not None
        ]
    )
    # Save text to file.
    hio.create_enclosing_dir(PATH_TO_CONFIG, incremental=True)
    hio.to_file(PATH_TO_CONFIG, string)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--user",
        type=str,
        help="IB user",
        action="store",
    )
    parser.add_argument(
        "--password",
        type=str,
        help="IB password",
        action="store",
    )
    parser.add_argument(
        "--stage",
        type=str,
        help="Stage: LOCAL or PROD",
        action="store",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    hdbg.shutup_chatty_modules()
    # Set up config to save.
    params = DEFAULT_CONFIG.copy()
    if args.user is not None:
        params["user"] = args.user
    if args.password is not None:
        params["password"] = args.password
    # TODO(gp): Not sure why it's needed.
    if args.stage == "PROD":
        params["ExistingSessionDetectedAction"] = "primary"
    # Save to file.
    _save_config_to_file(params)


if __name__ == "__main__":
    _main(_parse())
