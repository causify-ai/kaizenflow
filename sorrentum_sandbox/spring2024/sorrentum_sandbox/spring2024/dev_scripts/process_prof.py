#!/usr/bin/env python

"""
Process the output of Python profiling output.
"""

# To run:
#   python -m cProfile -o prof.bin CMD
#   python -m cProfile -o prof.bin test/run_tests.py -v 10 TestComputeDerivedFeatures2.test3

# # cProfile
# - Profile functions
#   > profile $CMD
# - Follow instruction on screen to plot call graph and or post process the
#   profiling data
#
# # line_profiler
# - Profile a function line by line
# - Decorate target function with @profile (or check kernprof.py -h for more
#   ways of marking the interesting parts of code)
#   > kernprof -l -o line_profile.lprof $CMD
#   > python -m line_profiler line_profile.lprof

import argparse
import logging
import os
import pstats

import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_verbosity_arg(parser)
    parser.add_argument(
        "--file_name",
        action="store",
        default="prof.bin",
        help="Path to the .bin file produced by profiling",
    )
    parser.add_argument(
        "--ext", action="store", default="png", help="File format for the graph"
    )
    parser.add_argument(
        "--action",
        default="stats",
        action="store",
    )
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=False)
    prof_file = args.file_name
    _LOG.info("Processing %s", prof_file)
    hdbg.dassert_file_exists(prof_file)
    p = pstats.Stats(prof_file).strip_dirs()
    if args.action == "stats":
        _LOG.info("Basic stats")
        # From http://docs.python.org/2/library/profile.html
        # - ncalls: for the number of calls
        # - tottime: for the total time spent in the given function (and excluding
        #   time made in calls to sub-functions)
        # - cumtime: is the cumulative time spent in this and all subfunctions
        #   (from invocation till exit). This figure is accurate even for recursive
        #   functions.
        p.sort_stats("cumulative").print_stats(50)
        # p.sort_stats(-1).print_stats()
        # p.sort_stats('cum').print_stats()
        # p.sort_stats('time', 'cum').print_stats()
        # p.sort_stats('cum', 'time').print_stats(50)
        # p.sort_stats('time').print_stats()
        # p.sort_stats('time', 'cum').print_stats('getStats')
        # p.sort_stats('time', 'cum').print_stats('portfolio_stats')
    elif args.action == "plot":
        _LOG.info("Generating plot")
        # Graph.
        # Note that 'pdf' doesn't work since we don't have Cairo renderer installed.
        # Use 'ps' or 'png'.
        dir_name = os.path.dirname(prof_file)
        if dir_name == "":
            dir_name = "."
        graph_file = os.path.abspath(dir_name + "/output." + args.ext)
        dot_cmd = (
            f"gprof2dot -f pstats {prof_file} | dot -T{args.ext} -o {graph_file}"
        )
        hsystem.system(dot_cmd)
        _LOG.info("Output profile graph: %s", graph_file)
        hdbg.dassert(os.path.exists(graph_file), msg=f"Can't find {graph_file}")
        # > eog output.png
    elif args.action == "custom_code":
        # Custom code for profiling.
        # Functions to analyze.
        funcs = ["_helper_table_extraction"]
        # Show ranked contributors.
        show_rank = True
        # Show who is called by <funcs>.
        show_callees = True
        # Show who calls <funcs>.
        show_callers = False
        if show_rank:
            # From http://docs.python.org/2/library/profile.html
            # - ncalls: for the number of calls,
            # - tottime: for the total time spent in the given function (and
            #   excluding time made in calls to sub-functions)
            # - cumtime: is the cumulative time spent in this and all
            #   subfunctions (from invocation till exit). This figure is
            #   accurate even for recursive functions.
            p.sort_stats("cumulative").print_stats(50)
            # p.sort_stats(-1).print_stats()
            # p.sort_stats('cum').print_stats()
            # p.sort_stats('time', 'cum').print_stats()
            # p.sort_stats('cum', 'time').print_stats(50)
            # p.sort_stats('time').print_stats()
            # p.sort_stats('time', 'cum').print_stats('getStats')
            # p.sort_stats('time', 'cum').print_stats('portfolio_stats')
        hdbg.dassert_type_is(funcs, list)
        if show_callees:
            for func in funcs:
                p.print_callees(func)
        if show_callers:
            for func in funcs:
                p.print_callers(func)
    else:
        raise ValueError(f"Invalid action='{args.action}'")


if __name__ == "__main__":
    _main(_parse())
