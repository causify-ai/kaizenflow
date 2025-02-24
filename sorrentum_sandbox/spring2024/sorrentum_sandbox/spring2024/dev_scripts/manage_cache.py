#!/usr/bin/env python
"""
Import as:

import dev_scripts.manage_cache as dscmacac
"""

import argparse

import helpers.hcache as hcache
import helpers.hdbg as hdbg
import helpers.hparser as hparser

# Example functions for testing.


@hcache.cache(set_verbose_mode=True)
def _func() -> str:
    txt = "#" * 1024**2
    return txt


def _test1() -> None:
    """
    Call the intrinsic function.
    """
    _ = _func()


def _test2() -> None:
    tag = "manage_cache"
    hcache.clear_global_cache("all", tag=tag)
    # Create a function-specific cache on disk only.
    path = "/tmp/cache.function"
    _func.set_function_cache_path(path)
    _func.clear_function_cache()
    #
    _func()
    print(_func.get_info())
    hcache.clear_global_cache("mem", tag=tag)
    #
    _func()


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--action", required=True, type=str)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    action = args.action
    tag = None
    actions = [
        "clear_global_cache",
        "clear_global_mem_cache",
        "clear_global_disk_cache",
        "list",
        "print_cache_info",
        "test",
    ]
    hdbg.dassert_in(action, actions)
    if action == "clear_global_cache":
        hcache.clear_global_cache("all", tag=tag)
    elif action == "clear_global_mem_cache":
        hcache.clear_global_cache("mem", tag=tag)
    elif action == "clear_global_disk_cache":
        hcache.clear_global_cache("disk", tag=tag)
    elif action == "print_cache_info":
        txt = hcache.get_global_cache_info()
        print(txt)
    elif action == "test":
        _test2()
    elif action == "list":
        print("Valid actions are:\n%s" % "\n".join(actions))
    else:
        hdbg.dfatal("Invalid action='%s'" % action)


if __name__ == "__main__":
    _main(_parse())
