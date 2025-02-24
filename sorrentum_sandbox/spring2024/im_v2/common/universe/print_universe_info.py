#!/usr/bin/env python
"""
The script performs several actions:

    - converts asset id to a full symbol
    - prints universe as a list of asset ids
    - prints universe mapping as `{full_symbol1: asset_id1, full_symbol2: asset_id2, ...}`

The following command converts asset id to a full symbol:
    ```
    > im_v2/common/universe/print_universe_info.py \
        --action convert_to_full_symbol \
        --asset_id 3065029174 \
        --im_client ccxt_realtime
    ```
    Output: `Full symbol: ['binance::DOGE_USDT']`

The command below prints the universe as asset ids:
    ```
    > im_v2/common/universe/print_universe_info.py \
        --action print_universe \
        --im_client ccxt_realtime
    ```
    Output:
    ```
    Asset ids: (29) 1528092593 2601760471 4939988068 2476706208 1030828978 2540896331
    9872743573 3065029174 5118394986 1966583502 5115052901 2384892553 1776791608
    3303714233 8717633868 2425308589 3401245610 2061507978 1467591036 2683705052
    2099673105 4516629366 2484635488 1464553467 1891737434 8968126878 2237530510
    6051632686 1182743717
    ```

The command below prints the universe mapping:
    ```
    > im_v2/common/universe/print_universe_info.py \
        --action print_universe_mapping \
        --im_client ccxt_realtime
    ```
   Output:
   ```
   {
     'binance::ADA_USDT': 3303714233,
     'binance::APE_USDT': 6051632686,
      ...
     'binance::BAKE_USDT': 1528092593,
     'binance::BNB_USDT': 8968126878,
      ...
   }
   ```
"""
import argparse
import logging

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsql as hsql
import im_v2.ccxt.data.client as icdcl
import im_v2.common.data.client as icdc
import im_v2.common.universe.universe_utils as imvcuunut
import im_v2.im_lib_tasks as imvimlita

_LOG = logging.getLogger(__name__)

_ACTIONS = ["print_universe", "convert_to_full_symbol", "print_universe_mapping"]


def _get_ImClient(im_client: str) -> icdc.ImClient:
    """
    Get `ImClient` from its string representation.

    :param im_client: client as string, e.g., `ccxt_realtime`
    """
    if im_client == "ccxt_realtime":
        env_file = imvimlita.get_db_env_path("dev")
        universe_version = "infer_from_data"
        # Get login info.
        connection_params = hsql.get_connection_info_from_env_file(env_file)
        # Login.
        db_connection = hsql.get_connection(*connection_params)
        # Get the real-time `ImClient`.
        # TODO(Grisha): this will print only the `futures` universe, allow also
        # to print `spot` universe.
        table_name = "ccxt_ohlcv_futures"
        #
        im_client = icdcl.CcxtSqlRealTimeImClient(
            universe_version, db_connection, table_name, resample_1min=False
        )
    else:
        raise ValueError(f"Invalid im_client='{im_client}'.")
    return im_client


def _run(args: argparse.Namespace) -> None:
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    im_client = _get_ImClient(args.im_client)
    if args.action == "convert_to_full_symbol":
        try:
            full_symbol = im_client.get_full_symbols_from_asset_ids(
                [args.asset_id]
            )
            _LOG.info("Full symbol: %s", full_symbol)
        # TODO(gp): Catch a stricter exception.
        except Exception as e:
            _LOG.error("Asset id is not a part of the universe or invalid: %s", e)
    elif args.action == "print_universe":
        full_symbols = im_client.get_universe()
        asset_ids = im_client.get_asset_ids_from_full_symbols(full_symbols)
        # Print all asset ids.
        _LOG.info("Asset ids: %s ", hprint.format_list(asset_ids, max_n=100))
    elif args.action == "print_universe_mapping":
        full_symbols = im_client.get_universe()
        universe_mapping = imvcuunut.build_numerical_to_string_id_mapping(
            full_symbols
        )
        # Swap asset ids and full symbols to get `{full_symbol: asset_id}` mapping.
        universe_mapping = dict(
            (full_symbol, asset_id)
            for asset_id, full_symbol in universe_mapping.items()
        )
        # Sort for readability.
        universe_mapping = dict(sorted(universe_mapping.items()))
        _LOG.info(
            "\nUniverse mapping:\n%s", hprint.to_pretty_str(universe_mapping)
        )
    else:
        raise ValueError(f"Unsupported action={args.action}")


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--action",
        action="store",
        required=True,
        type=str,
        choices=_ACTIONS,
        help=f"Choose action to perfom: {_ACTIONS}",
    )
    parser.add_argument(
        "--asset_id",
        action="store",
        required=False,
        type=int,
        help="Required if --action is convert_to_full_symbol",
    )
    parser.add_argument(
        "--im_client",
        action="store",
        required=True,
        type=str,
        help="",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    _run(args)


if __name__ == "__main__":
    _main(_parse())