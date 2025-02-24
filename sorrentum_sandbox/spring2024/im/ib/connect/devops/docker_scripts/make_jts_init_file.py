#!/usr/bin/env python
"""
Create jts config file.

Based on:
https://github.com/mvberg/ib-gateway-docker/blob/master/ib/jts.ini

# Create default config file:
> make_jts_init_file.py

# Create config on server (use your local IP instead of 33.3.33.3):
> make_jts_init_file.py --trusted_ips 127.0.0.1,33.3.33.3

Import as:

import im.ib.connect.devops.docker_scripts.make_jts_init_file as imicddsmjif
"""
import argparse
import logging
from typing import Any, Dict

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)

_PATH_TO_CONFIG = "/root/Jts/jts.ini"
_DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    "IBGateway": {
        "WriteDebug": "false",
        "TrustedIPs": "127.0.0.1",
        "MainWindow.Height": 550,
        "RemoteHostOrderRouting": "hdc1.ibllc.com",
        "RemotePortOrderRouting": 4000,
        "LocalServerPort": 4000,
        "ApiOnly": "true",
        "MainWindow.Width": 700,
    },
    "Logon": {
        "useRemoteSettings": "false",
        "TimeZone": "UTC",
        "tradingMode": "p",
        "colorPalletName": "dark",
        "Steps": 6,
        "Locale": "en",
        "SupportsSSL": "gdc1.ibllc.com:4000,true,20210304,false",
        "UseSSL": "true",
        "os_titlebar": "false",
        "s3store": "true",
    },
    "ns": {
        "darykq": 1,
    },
    "Communication": {
        "SettingsDir": "/root/Jts",
        "Peer": "gdc1.ibllc.com:4001",
        "Region": "us",
    },
}


def _save_config_to_file(config: Dict[str, Dict[str, Any]]) -> None:
    """
    Save config from dictionary.

    Format:
        [Label_1]
        Var=Value
        [Label_2]
        ...
    """
    # Get text to save.
    string = ""
    for section in config:
        # I.e. "[Label]".
        string += "[%s]\n" % section
        for item, value in config[section].items():
            string += "%s=%s\n" % (item, value)
    # Save text to file.
    hio.create_enclosing_dir(_PATH_TO_CONFIG, incremental=True)
    hio.to_file(_PATH_TO_CONFIG, string)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--trusted_ips",
        type=str,
        help="Trusted IPs as a string separated by comma",
        action="store",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    hdbg.shutup_chatty_modules()
    # Set up config to save.
    params: Dict[str, Dict[str, Any]] = _DEFAULT_CONFIG.copy()
    # Add trusted IP-s.
    if args.trusted_ips is not None:
        params["IBGateway"]["TrustedIPs"] = args.trusted_ips
    # Save to file.
    _save_config_to_file(params)


if __name__ == "__main__":
    _main(_parse())
