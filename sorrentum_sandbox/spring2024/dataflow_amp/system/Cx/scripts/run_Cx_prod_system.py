#!/usr/bin/env python

import argparse
import logging

import core.config as cconfig
import dataflow_amp.system.Cx.Cx_prod_system as dtfasccprsy
import helpers.hasyncio as hasynci
import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# TODO(gp): Maybe we can share some of this code with E8.
async def _run_real_time_pipeline(
    args: argparse.Namespace,
) -> None:
    system = dtfasccprsy.get_Cx_ProdSystem_instance_v1_20220727(args)
    # TODO(gp): In an ideal design here would have the config with a bunch
    # callbacks that are specified to build the objects. Now we build the config
    # and the object at the same time.
    # config = ...
    # config = apply_config_overrides_from_command_line(config, args)
    # system = build_system_from_config(config)
    # dag_runner = system.dag_runner
    dag_runner = system.dag_runner
    _LOG.info(
        "\n"
        + hprint.frame("Final system config")
        + "\n"
        + hprint.indent(str(system.config))
        + "\n"
        + hprint.frame("End config")
    )
    if args.print_config:
        _LOG.error("Stopping as per user request")
        assert 0
    # Run.
    await dag_runner.predict()


# TODO(gp): Maybe we can share some of this code with E8.
def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # TODO(Grisha): review the params set, not sure everything is used.
    parser.add_argument(
        "--dag_builder_ctor_as_str",
        action="store",
        required=True,
        help="Pointer to a `DagBuilder` constructor, e.g., `dataflow_orange.pipelines.C1.C1b_pipeline.C1b_DagBuilder`",
    )
    parser.add_argument(
        "--run_mode",
        action="store",
        default="prod",
        choices=["prod", "paper_trading"],
        help="System run mode",
    )
    # TODO(Grisha): consider removing `strategy` since it does not affect
    #  anything.
    parser.add_argument("--strategy", action="store")
    parser.add_argument("--liveness", action="store", default="candidate")
    parser.add_argument("--instance_type", action="store", default="prod")
    parser.add_argument("--trade_date", action="store", required=True)
    parser.add_argument(
        "--dst_dir",
        action="store",
        default="system_log_dir",
        help="Destination dir",
    )
    parser.add_argument(
        "--print_config", action="store_true", help="Print config and stop"
    )
    parser.add_argument(
        "--exchange",
        action="store",
        help="Exchange to trade on: i.e. 'binance'",
        default="binance",
        required=True,
    )
    parser.add_argument(
        "--stage",
        action="store",
        help="Stage to run at: local, preprod, prod. Also applies to a DB stage.",
        required=True,
    )
    # TODO(gp): Factor out account_type and secret_id into a "hparser" like
    #  function. Maybe also exchange.
    parser.add_argument(
        "--account_type",
        action="store",
        required=True,
        help="Exchange account, launches broker either in 'sandbox' (testing) or 'trading' (prod) mode.",
    )
    parser.add_argument(
        "--secret_id",
        action="store",
        required=True,
        help="ID of the API Keys to use as they are stored in AWS SecretsManager.",
    )
    #
    parser.add_argument(
        "--start_time",
        action="store",
        help="Start time of the system in datetime format, if None, immediate start is assumed",
        default=None,
    )
    parser.add_argument(
        "--run_duration",
        action="store",
        help="Duration of the real time loop (in seconds), if None, the system runs indefinitely",
        default=None,
        type=int,
    )
    parser.add_argument(
        "--log_file_name",
        action="store",
        help="Name of the file to store logs",
        default="./system_log.txt",
        type=str,
    )
    parser = cconfig.add_config_override_args(parser)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    # This is needed when doing re-runs. E.g., the first run started and then
    # failed, when kicking off the second run in order not to lose the previous
    # logs, rename the log file for the previous run and keep it.
    log_file_name = args.log_file_name
    suffix = hdateti.get_current_time(tz="UTC").strftime("%Y%m%d_%H%M%S")
    hio.rename_file_if_exists(log_file_name, suffix)
    hdbg.init_logger(
        verbosity=args.log_level,
        use_exec_path=True,
        log_filename=log_file_name,
        report_memory_usage=True,
    )
    event_loop = None
    hasynci.run(_run_real_time_pipeline(args), event_loop)


if __name__ == "__main__":
    _main(_parse())
