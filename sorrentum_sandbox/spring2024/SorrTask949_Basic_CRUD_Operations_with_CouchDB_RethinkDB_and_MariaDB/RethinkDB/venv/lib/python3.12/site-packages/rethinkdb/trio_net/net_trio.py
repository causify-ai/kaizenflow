# Copyright 2019 RethinkDB
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
# Copyright 2010-2019 RethinkDB all rights reserved.

import collections
import contextlib
import socket
import ssl
import struct

import trio
import trio.abc

from rethinkdb import RethinkDB, ql2_pb2
from rethinkdb.errors import (
    ReqlAuthError,
    ReqlCursorEmpty,
    ReqlDriverError,
    ReqlTimeoutError,
    RqlCursorEmpty,
)
from rethinkdb.net import Connection as ConnectionBase
from rethinkdb.net import Cursor, Query, Response, make_connection, maybe_profile

__all__ = ["Connection"]


P_RESPONSE = ql2_pb2.Response.ResponseType
P_QUERY = ql2_pb2.Query.QueryType


class TrioFuture:
    """ Trio does not have a future class because Trio encourages the use of
    "coroutines all the way down", but the this driver was implemented by
    copying the net_asyncio code and transliterating it into the Trio API. The
    underlying code in net.py has the I/O intertwined with framing and state
    logic, making it difficult to cleanly write async code in the Trio style.
    Therefore I've taken the easy way out by writing up a simple future class.

    Similar to an asyncio future except without callbacks or cancellation.
    """

    def __init__(self):
        self._event = trio.Event()
        self._cancelled = False
        self._value = None
        self._exc = None

    async def wait(self):
        await self._event.wait()
        return self.result()

    def exception(self):
        if self._event.is_set():
            return self._exc
        else:
            raise Exception("Future value has not been set")

    def result(self):
        if self._event.is_set():
            if self._exc is not None:
                raise self._exc
            return self._value
        else:
            raise Exception("Future value has not been set")

    def set_result(self, value):
        self._value = value
        self._event.set()

    def set_exception(self, exc):
        self._exc = exc
        self._event.set()

    def done(self):
        return self._event.is_set()


@contextlib.contextmanager
def _reql_timeout(seconds):
    """
    Run a block with a timeout, raising `ReqlTimeoutError` if the block
    execution exceeds the timeout.

    :param float seconds: A timeout in seconds. If None, then no timeout is
        enforced.
    :raises ReqlTimeoutError: If execution time exceeds the timeout.
    """
    if seconds is None:
        yield
    else:
        try:
            with trio.fail_after(seconds):
                yield
        except trio.TooSlow:
            raise ReqlTimeoutError()


class TrioCursor(Cursor, trio.abc.AsyncResource):
    """ A cursor that allows async iteration within the Trio framework. """

    def __init__(self, *args, **kwargs):
        """ Constructor """
        self._new_response = trio.Event()
        self._nursery = kwargs.pop("nursery")
        Cursor.__init__(self, *args, **kwargs)

    def __aiter__(self):
        """ This object is an async iterator. """
        return self

    async def __anext__(self):
        """ Asynchronously get next item from this cursor. """
        try:
            return await self._get_next(timeout=None)
        except ReqlCursorEmpty:
            raise StopAsyncIteration

    async def close(self):
        """ Close this cursor. """
        if self.error is None:
            self.error = self._empty_error()
            if self.conn.is_open():
                self.outstanding_requests += 1
                await self.conn._parent._stop(self)

    aclose = close

    def _extend(self, res_buf):
        """ Override so that we can make this async, and also to wake up blocked
        tasks. """
        self.outstanding_requests -= 1
        self._maybe_fetch_batch()
        res = Response(self.query.token, res_buf, self._json_decoder)
        self._extend_internal(res)
        self._new_response.set()
        self._new_response = trio.Event()

    # Convenience function so users know when they've hit the end of the cursor
    # without having to catch an exception
    async def fetch_next(self, wait=True):
        timeout = Cursor._wait_to_timeout(wait)
        while len(self.items) == 0:
            self._maybe_fetch_batch()
            if self.error is not None:
                raise self.error
            with _reql_timeout(timeout):
                await self._new_response.wait()
        # If there is a (non-empty) error to be received, we return True, so the
        # user will receive it on the next `next` call.
        return len(self.items) != 0

    def _empty_error(self):
        # We do not have RqlCursorEmpty inherit from StopIteration as that interferes
        # with mechanisms to return from a coroutine.
        return RqlCursorEmpty()

    async def _get_next(self, timeout):
        while len(self.items) == 0:
            self._maybe_fetch_batch()
            if self.error is not None:
                raise self.error
            with _reql_timeout(timeout):
                await self._new_response.wait()
        item = self.items.popleft()
        if isinstance(item, Exception):
            raise item
        return item

    async def _parent_continue(self):
        return await self.conn._parent._continue(self)

    def _maybe_fetch_batch(self):
        if (
            self.error is None
            and len(self.items) < self.threshold
            and self.outstanding_requests == 0
        ):
            self.outstanding_requests += 1
            self._nursery.start_soon(self.conn._parent._continue, self)


class ConnectionInstance:
    def __init__(self, parent, nursery=None):
        self._stream = None
        self._stream_lock = trio.Lock()
        self._sockname = None
        self._parent = parent
        self._closing = False
        self._closed = False
        self._user_queries = {}
        self._cursor_cache = {}
        self._reader_ended_event = None
        self._nursery = nursery

    def client_port(self):
        if self.is_open():
            return self._sockname[1]

    def client_address(self):
        if self.is_open():
            return self._sockname[0]

    async def _send(self, data):
        async with self._stream_lock:
            try:
                await self._stream.send_all(data)
            except (trio.BrokenResourceError, trio.ClosedResourceError):
                self._closed = True

    async def _read_until(self, delimiter):
        """ Naive implementation of reading until a delimiter. """
        buffer = bytearray()

        try:
            while True:
                data = await self._stream.receive_some(1)
                buffer.append(data[0])
                if data == delimiter:
                    break
        except (trio.BrokenResourceError, trio.ClosedResourceError):
            self._closed = True

        return bytes(buffer)

    async def _read_exactly(self, num):
        data = b''
        try:
            while len(data) < num:
                data += await self._stream.receive_some(num - len(data))
            return data
        except (trio.BrokenResourceError, trio.ClosedResourceError):
            self._closed = True

    async def connect(self, timeout):
        try:
            ssl_context = None
            if len(self._parent.ssl) > 0:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                if hasattr(ssl_context, "options"):
                    ssl_context.options |= getattr(ssl, "OP_NO_SSLv2", 0)
                    ssl_context.options |= getattr(ssl, "OP_NO_SSLv3", 0)
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                ssl_context.check_hostname = True  # redundant with match_hostname
                ssl_context.load_verify_locations(self._parent.ssl["ca_certs"])
            if ssl_context:
                self._stream = await trio.open_ssl_over_tcp_stream(
                    self._parent.host, self._parent.port, ssl_context=ssl_context
                )
                socket_ = self._stream.transport_stream.socket
            else:
                self._stream = await trio.open_tcp_stream(
                    self._parent.host, self._parent.port
                )
                socket_ = self._stream.socket
            self._sockname = socket_.getsockname()
            socket_.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except Exception as err:
            raise ReqlDriverError(
                "Could not connect to %s:%s. Error: %s"
                % (self._parent.host, self._parent.port, str(err))
            )

        try:
            self._parent.handshake.reset()
            response = None
            while True:
                request = self._parent.handshake.next_message(response)
                if request is None:
                    break
                # This may happen in the `V1_0` protocol where we send two requests as
                # an optimization, then need to read each separately
                if request is not "":
                    await self._send(request)
                with _reql_timeout(timeout):
                    response = await self._read_until(b"\0")
                response = response[:-1]
        except ReqlAuthError:
            await self.close()
            raise
        except ReqlTimeoutError as err:
            await self.close()
            raise ReqlDriverError(
                "Connection interrupted during handshake with %s:%s. Error: %s"
                % (self._parent.host, self._parent.port, str(err))
            )
        except Exception as err:
            await self.close()
            raise ReqlDriverError(
                "Could not connect to %s:%s. Error: %s"
                % (self._parent.host, self._parent.port, str(err))
            )

        # Start a parallel function to perform reads
        self._nursery.start_soon(self._reader_task)
        return self._parent

    def is_open(self):
        return not (self._closing or self._closed)

    async def close(self, noreply_wait=False, token=None, exception=None):
        self._closing = True
        if exception is not None:
            err_message = "Connection is closed (%s)." % str(exception)
        else:
            err_message = "Connection is closed."

        # Cursors may remove themselves when errored, so copy a list of them
        for cursor in list(self._cursor_cache.values()):
            cursor._error(err_message)

        for _, future in self._user_queries.values():
            if not future.done():
                future.set_exception(ReqlDriverError(err_message))

        self._user_queries = {}
        self._cursor_cache = {}

        if noreply_wait:
            noreply = Query(P_QUERY.NOREPLY_WAIT, token, None, None)
            await self.run_query(noreply, False)

        try:
            await self._stream.aclose()
        except (trio.ClosedResourceError, trio.BrokenResourceError):
            pass
        # We must not wait for the _reader_task if we got an exception, because that
        # means that we were called from it. Waiting would lead to a deadlock.
        if self._reader_ended_event:
            await self._reader_ended_event.wait()

        return None

    async def run_query(self, query, noreply):
        await self._send(query.serialize(self._parent._get_json_encoder(query)))
        if noreply:
            return None

        response_future = TrioFuture()
        self._user_queries[query.token] = (query, response_future)
        return await response_future.wait()

    # The reader task runs in parallel, reading responses
    # off of the socket and forwarding them to the appropriate Future or Cursor.
    # This is shut down as a consequence of closing the stream, or an error in the
    # socket/protocol from the server. Unexpected errors in this coroutine will
    # close the ConnectionInstance and be passed to any open Futures or Cursors.
    async def _reader_task(self):
        self._reader_ended_event = trio.Event()
        try:
            while True:
                buf = await self._read_exactly(12)
                (token, length,) = struct.unpack("<qL", buf)
                buf = await self._read_exactly(length)

                cursor = self._cursor_cache.get(token)
                if cursor is not None:
                    cursor._extend(buf)
                elif token in self._user_queries:
                    # Do not pop the query from the dict until later, so
                    # we don't lose track of it in case of an exception
                    query, future = self._user_queries[token]
                    res = Response(token, buf, self._parent._get_json_decoder(query))
                    if res.type == P_RESPONSE.SUCCESS_ATOM:
                        future.set_result(maybe_profile(res.data[0], res))
                    elif res.type in (
                        P_RESPONSE.SUCCESS_SEQUENCE,
                        P_RESPONSE.SUCCESS_PARTIAL,
                    ):
                        cursor = TrioCursor(self, query, res, nursery=self._nursery)
                        future.set_result(maybe_profile(cursor, res))
                    elif res.type == P_RESPONSE.WAIT_COMPLETE:
                        future.set_result(None)
                    elif res.type == P_RESPONSE.SERVER_INFO:
                        future.set_result(res.data[0])
                    else:
                        future.set_exception(res.make_error(query))
                    del self._user_queries[token]
                elif not self._closing:
                    raise ReqlDriverError("Unexpected response received.")
        except Exception as ex:
            if not self._closing:
                await self.close(exception=ex)
        finally:
            self._reader_ended_event.set()


class Connection(ConnectionBase):
    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(ConnectionInstance, *args, **kwargs)
        try:
            self.port = int(self.port)
        except ValueError:
            raise ReqlDriverError(
                "Could not convert port %s to an integer." % self.port
            )

    async def _stop(self, cursor):
        self.check_open()
        query = Query(P_QUERY.STOP, cursor.query.token, None, None)
        return await self._instance.run_query(query, True)

    async def reconnect(self, noreply_wait=True, timeout=None):
        await self.close(noreply_wait)
        self._instance = self._conn_type(self, **self._child_kwargs)
        return await self._instance.connect(timeout)

    async def close(self, noreply_wait=True):
        if self._instance is None:
            return None
        return await ConnectionBase.close(self, noreply_wait=noreply_wait)


class AsyncTrioConnectionContextManager:
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._conn = None

    @classmethod
    def open(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    async def __aenter__(self):
        self._conn = await make_connection(Connection, *self._args, **self._kwargs)
        return self._conn

    async def __aexit__(self, exc_type, exc, traceback):
        await self._conn.close(False)


# Monkeypatch RethinkDB with an async context manager.
RethinkDB.open = AsyncTrioConnectionContextManager.open


class _TrioConnectionPoolContextManager:
    """
    A context manager for a trio connection pool. This automatically acquires
    a connection from the pool when entering the block, then releases it after
    exiting the block.

    This is not meant to be instantiated directly. Use
    TrioConnectionPool.connection() instead.
    """

    def __init__(self, pool):
        self._conn = None
        self._pool = pool

    async def __aenter__(self):
        """ Acquire a connection. """
        self._conn = await self._pool.acquire()
        return self._conn

    async def __aexit__(self, exc_type, exc, traceback):
        """ Release a connection. """
        await self._pool.release(self._conn)


class TrioConnectionPool:
    """ A RethinkDB connection pool for Trio framework. """

    def __init__(self, *args, **kwargs):
        """
        Constructor.

        :param int max_idle: The maximum number of idle connections to keep in
        the pool.
        """
        self._closed = False
        self._args = args
        self._kwargs = kwargs
        self._nursery = kwargs["nursery"]
        self._max_idle = kwargs.pop("maxidle", 10)
        self._connections = collections.deque()
        self._lent_out = set()

    def connection(self):
        return _TrioConnectionPoolContextManager(self)

    async def acquire(self):
        if self._closed:
            raise Exception("DB pool is closed!")

        try:
            conn = self._connections.popleft()
            while not conn.is_open():
                # Connections in the pool may timeout, so look for one that is
                # still connected.
                conn = self._connections.popleft()
        except IndexError:
            conn = await make_connection(Connection, *self._args, **self._kwargs)

        self._lent_out.add(conn)
        return conn

    async def release(self, conn):
        self._lent_out.remove(conn)
        if len(self._connections) < self._max_idle:
            self._connections.append(conn)
        else:
            await conn.close()

    async def close(self):
        async with trio.open_nursery() as nursery:
            for conn in self._connections:
                nursery.start_soon(conn.close)
            for conn in self._lent_out:
                nursery.start_soon(conn.close)

        self._closed = True


# Monkeypatch RethinkDB with a connection pool.
RethinkDB.ConnectionPool = TrioConnectionPool
