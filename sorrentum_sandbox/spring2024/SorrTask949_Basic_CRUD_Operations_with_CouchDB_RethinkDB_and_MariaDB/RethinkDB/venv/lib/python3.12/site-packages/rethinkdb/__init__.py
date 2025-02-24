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

from rethinkdb import errors, version

# The builtins here defends against re-importing something obscuring `object`.
try:
    import __builtin__ as builtins  # Python 2
except ImportError:
    import builtins  # Python 3


__all__ = ["RethinkDB"] + errors.__all__
__version__ = version.VERSION


class RethinkDB(builtins.object):
    def __init__(self):
        super(RethinkDB, self).__init__()

        from rethinkdb import (
            _dump,
            _export,
            _import,
            _index_rebuild,
            _restore,
            ast,
            query,
            net,
        )

        self._dump = _dump
        self._export = _export
        self._import = _import
        self._index_rebuild = _index_rebuild
        self._restore = _restore

        # Re-export internal modules for backward compatibility
        self.ast = ast
        self.errors = errors
        self.net = net
        self.query = query

        net.Connection._r = self

        for module in (self.net, self.query, self.ast, self.errors):
            for function_name in module.__all__:
                setattr(self, function_name, getattr(module, function_name))

        self.set_loop_type(None)

    def set_loop_type(self, library=None):
        if library == "asyncio":
            from rethinkdb.asyncio_net import net_asyncio
            self.connection_type = net_asyncio.Connection

        if library == "gevent":
            from rethinkdb.gevent_net import net_gevent
            self.connection_type = net_gevent.Connection

        if library == "tornado":
            from rethinkdb.tornado_net import net_tornado
            self.connection_type = net_tornado.Connection

        if library == "trio":
            from rethinkdb.trio_net import net_trio
            self.connection_type = net_trio.Connection

        if library == "twisted":
            from rethinkdb.twisted_net import net_twisted
            self.connection_type = net_twisted.Connection

        if library is None or self.connection_type is None:
            self.connection_type = self.net.DefaultConnection

        return

    def connect(self, *args, **kwargs):
        return self.make_connection(self.connection_type, *args, **kwargs)


r = RethinkDB()
