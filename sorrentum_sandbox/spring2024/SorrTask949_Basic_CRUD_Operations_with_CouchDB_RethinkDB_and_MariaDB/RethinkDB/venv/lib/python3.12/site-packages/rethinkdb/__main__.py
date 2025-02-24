#!/usr/bin/env python

# Copyright 2018 RethinkDB
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file incorporates work covered by the following copyright:
# Copyright 2010-2016 RethinkDB, all rights reserved.

"""Dispatcher for interactive functions such as repl and backup"""

import code
import sys
import traceback

from rethinkdb import errors, net, utils_common


def startInterpreter(argv=None, prog=None):
    repl_variables = {"r": net.Connection._r, "rethinkdb": net.Connection._r}
    banner = "The RethinkDB driver has been imported as `r`."

    # -- get host/port setup

    # - parse command line
    parser = utils_common.CommonOptionsParser(
        prog=prog,
        description="An interactive Python shell (repl) with the RethinkDB driver imported",
    )
    options, args = parser.parse_args(
        argv if argv is not None else sys.argv[1:], connect=False
    )

    if args:
        parser.error(
            "No positional arguments supported. Unrecognized option(s): %s" % args
        )

    # -- open connection

    try:
        repl_variables["conn"] = options.retryQuery.conn()
        repl_variables["conn"].repl()
        banner += """
    A connection to %s:%d has been established as `conn`
    and can be used by calling `run()` on a query without any arguments.""" % (
            options.hostname,
            options.driver_port,
        )
    except errors.ReqlDriverError as e:
        banner += "\nWarning: %s" % str(e)
        if options.debug:
            banner += "\n" + traceback.format_exc()

    # -- start interpreter

    code.interact(banner=banner + "\n==========", local=repl_variables)


if __name__ == "__main__":
    if __package__ is None:
        __package__ = "rethinkdb"

    # -- figure out which mode we are in
    modes = ["dump", "export", "import", "index_rebuild", "repl", "restore"]

    if len(sys.argv) < 2 or sys.argv[1] not in modes:
        sys.exit(
            "ERROR: Must be called with one of the following verbs: %s"
            % ", ".join(modes)
        )

    verb = sys.argv[1]
    prog = "python -m rethinkdb"
    if sys.version_info < (2, 7) or (
        sys.version_info >= (3, 0) and sys.version_info < (3, 4)
    ):
        prog += ".__main__"  # Python versions 2.6, 3.0, 3.1 and 3.3 do not support running packages
    prog += " " + verb
    argv = sys.argv[2:]

    if verb == "dump":
        from . import _dump

        exit(_dump.main(argv, prog=prog))
    elif verb == "export":
        from . import _export

        exit(_export.main(argv, prog=prog))
    elif verb == "import":
        from . import _import

        exit(_import.main(argv, prog=prog))
    elif verb == "index_rebuild":
        from . import _index_rebuild

        exit(_index_rebuild.main(argv, prog=prog))
    elif verb == "repl":
        startInterpreter(argv, prog=prog)
    elif verb == "restore":
        from . import _restore

        exit(_restore.main(argv, prog=prog))
