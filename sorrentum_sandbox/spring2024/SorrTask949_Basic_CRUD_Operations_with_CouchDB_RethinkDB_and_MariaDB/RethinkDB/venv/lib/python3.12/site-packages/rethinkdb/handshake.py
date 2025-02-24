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

import base64
import binascii
import hashlib
import hmac
import struct
import sys
import threading
from random import SystemRandom

import six

from rethinkdb import ql2_pb2
from rethinkdb.errors import ReqlAuthError, ReqlDriverError
from rethinkdb.helpers import chain_to_bytes, decode_utf8
from rethinkdb.logger import default_logger

try:
    xrange
except NameError:
    xrange = range


def compare_digest(digest_a, digest_b):
    if sys.version_info[0] == 3:

        def xor_bytes(digest_a, digest_b):
            return digest_a ^ digest_b

    else:

        def xor_bytes(digest_a, digest_b, _ord=ord):
            return _ord(digest_a) ^ _ord(digest_b)

    left = None
    right = digest_b
    if len(digest_a) == len(digest_b):
        left = digest_a
        result = 0
    if len(digest_a) != len(digest_b):
        left = digest_b
        result = 1

    for l, r in zip(left, right):
        result |= xor_bytes(l, r)

    return result == 0


def pbkdf2_hmac(hash_name, password, salt, iterations):
    if hash_name != "sha256":
        raise AssertionError(
            'Hash name {hash_name} is not equal with "sha256"'.format(
                hash_name=hash_name
            )
        )

    def from_bytes(value, hexlify=binascii.hexlify, int=int):
        return int(hexlify(value), 16)

    def to_bytes(value, unhexlify=binascii.unhexlify):
        try:
            return unhexlify(bytes("%064x" % value, "ascii"))
        except TypeError:
            return unhexlify(bytes("%064x" % value))

    cache_key = (password, salt, iterations)

    cache_result = HandshakeV1_0.PBKDF2_CACHE.get(cache_key)

    if cache_result is not None:
        return cache_result

    mac = hmac.new(password, None, hashlib.sha256)

    def digest(msg, mac=mac):
        mac_copy = mac.copy()
        mac_copy.update(msg)
        return mac_copy.digest()

    t = digest(salt + b"\x00\x00\x00\x01")
    u = from_bytes(t)
    for c in xrange(iterations - 1):
        t = digest(t)
        u ^= from_bytes(t)

    u = to_bytes(u)
    HandshakeV1_0.PBKDF2_CACHE.set(cache_key, u)
    return u


class LocalThreadCache(threading.local):
    def __init__(self):
        self._cache = dict()

    def set(self, key, val):
        self._cache[key] = val

    def get(self, key):
        return self._cache.get(key)


class HandshakeV1_0(object):
    """
    RethinkDB client drivers are responsible for serializing queries, sending them to the server using the
    ReQL wire protocol, and receiving responses from the server and returning them to the calling application.

    The client sends the protocol version, authentication method, and authentication as a null-terminated JSON
    response. RethinkDB currently supports only one authentication method, SCRAM-SHA-256, as specified in IETF
    RFC 7677 and RFC 5802. The RFC is followed with the exception of error handling (RethinkDB uses its own
    higher level error reporting rather than the e= field). RethinkDB does not support channel binding and clients
    should not request this. The value of "authentication" is the "client-first-message" specified in RFC 5802
    (the channel binding flag, optional SASL authorization identity, username (n=), and random nonce (r=).

    More info: https://rethinkdb.com/docs/writing-drivers/
    """

    VERSION = ql2_pb2.VersionDummy.Version.V1_0
    PROTOCOL = ql2_pb2.VersionDummy.Protocol.JSON
    PBKDF2_CACHE = LocalThreadCache()

    def __init__(self, json_decoder, json_encoder, host, port, username, password):
        """
        TODO:
        """

        self._json_decoder = json_decoder
        self._json_encoder = json_encoder
        self._host = host
        self._port = port
        self._username = (
            username.encode("utf-8").replace(b"=", b"=3D").replace(b",", b"=2C")
        )

        self._password = six.b(password)

        self._compare_digest = self._get_compare_digest()
        self._pbkdf2_hmac = self._get_pbkdf2_hmac()

        self._protocol_version = 0
        self._random_nonce = None
        self._first_client_message = None
        self._server_signature = None
        self._state = 0

    @staticmethod
    def _get_compare_digest():
        """
        Get the compare_digest function from hashlib if package contains it, else get
        our own function. Please note that hashlib contains this function only for
        Python 2.7.7+ and 3.3+.
        """

        return getattr(hmac, "compare_digest", compare_digest)

    @staticmethod
    def _get_pbkdf2_hmac():
        """
        Get the pbkdf2_hmac function from hashlib if package contains it, else get
        our own function. Please note that hashlib contains this function only for
        Python 2.7.8+ and 3.4+.
        """

        return getattr(hashlib, "pbkdf2_hmac", pbkdf2_hmac)

    @staticmethod
    def _get_authentication_and_first_client_message(response):
        """
        Get the first client message and the authentication related data from the
        response provided by RethinkDB.

        :param response: Response dict from the database
        :return: None
        """

        first_client_message = response["authentication"].encode("ascii")
        authentication = dict(
            x.split(b"=", 1) for x in first_client_message.split(b",")
        )
        return first_client_message, authentication

    def _next_state(self):
        """
        Increase the state counter.
        """

        self._state += 1

    def _decode_json_response(self, response, with_utf8=False):
        """
        Get decoded json response from response.

        :param response: Response from the database
        :param with_utf8: UTF-8 decode response before json decoding
        :raises: ReqlDriverError | ReqlAuthError
        :return: Json decoded response of the original response
        """

        if with_utf8:
            response = decode_utf8(response)

        json_response = self._json_decoder.decode(response)

        if not json_response.get("success"):
            if 10 <= json_response["error_code"] <= 20:
                raise ReqlAuthError(json_response["error"], self._host, self._port)

            raise ReqlDriverError(json_response["error"])

        return json_response

    def _init_connection(self, response):
        """
        Prepare initial connection message. We send the version as well as the initial
        JSON as an optimization.

        :param response: Response from the database
        :raises: ReqlDriverError
        :return: Initial message which will be sent to the DB
        """

        if response is not None:
            raise ReqlDriverError("Unexpected response")

        self._random_nonce = base64.standard_b64encode(
            bytes(bytearray(SystemRandom().getrandbits(8) for i in range(18)))
        )

        self._first_client_message = chain_to_bytes(
            "n=", self._username, ",r=", self._random_nonce
        )

        initial_message = chain_to_bytes(
            struct.pack("<L", self.VERSION),
            self._json_encoder.encode(
                {
                    "protocol_version": self._protocol_version,
                    "authentication_method": "SCRAM-SHA-256",
                    "authentication": chain_to_bytes(
                        "n,,", self._first_client_message
                    ).decode("ascii"),
                }
            ).encode("utf-8"),
            b"\0",
        )

        self._next_state()
        return initial_message

    def _read_response(self, response):
        """
        Read response of the server. Due to we've already sent the initial JSON, and only support a single
        protocol version at the moment thus we simply read the next response and return an empty string as a
        message.

        :param response: Response from the database
        :raises: ReqlDriverError | ReqlAuthError
        :return: An empty string
        """

        json_response = self._decode_json_response(response)
        min_protocol_version = json_response["min_protocol_version"]
        max_protocol_version = json_response["max_protocol_version"]

        if not min_protocol_version <= self._protocol_version <= max_protocol_version:
            raise ReqlDriverError(
                "Unsupported protocol version {version}, expected between {min} and {max}".format(
                    version=self._protocol_version,
                    min=min_protocol_version,
                    max=max_protocol_version,
                )
            )

        self._next_state()
        return ""

    def _prepare_auth_request(self, response):
        """
        Put tohether the authentication request based on the response of the database.

        :param response: Response from the database
        :raises: ReqlDriverError | ReqlAuthError
        :return: An empty string
        """

        json_response = self._decode_json_response(response, with_utf8=True)
        (
            first_client_message,
            authentication,
        ) = self._get_authentication_and_first_client_message(json_response)

        random_nonce = authentication[b"r"]
        if not random_nonce.startswith(self._random_nonce):
            raise ReqlAuthError("Invalid nonce from server", self._host, self._port)

        salted_password = self._pbkdf2_hmac(
            "sha256",
            self._password,
            base64.standard_b64decode(authentication[b"s"]),
            int(authentication[b"i"]),
        )

        message_without_proof = chain_to_bytes("c=biws,r=", random_nonce)
        auth_message = b",".join(
            (self._first_client_message, first_client_message, message_without_proof)
        )

        self._server_signature = hmac.new(
            hmac.new(salted_password, b"Server Key", hashlib.sha256).digest(),
            auth_message,
            hashlib.sha256,
        ).digest()

        client_key = hmac.new(salted_password, b"Client Key", hashlib.sha256).digest()
        client_signature = hmac.new(
            hashlib.sha256(client_key).digest(), auth_message, hashlib.sha256
        ).digest()
        client_proof = struct.pack(
            "32B",
            *(
                l ^ random_nonce
                for l, random_nonce in zip(
                    struct.unpack("32B", client_key),
                    struct.unpack("32B", client_signature),
                )
            )
        )

        authentication_request = chain_to_bytes(
            self._json_encoder.encode(
                {
                    "authentication": chain_to_bytes(
                        message_without_proof,
                        ",p=",
                        base64.standard_b64encode(client_proof),
                    ).decode("ascii")
                }
            ),
            b"\0",
        )

        self._next_state()
        return authentication_request

    def _read_auth_response(self, response):
        """
        Read the authentication request's response sent by the database
        and validate the server signature which was returned.

        :param response: Response from the database
        :raises: ReqlDriverError | ReqlAuthError
        :return: None
        """

        json_response = self._decode_json_response(response, with_utf8=True)

        (
            first_client_message,
            authentication,
        ) = self._get_authentication_and_first_client_message(json_response)
        server_signature = base64.standard_b64decode(authentication[b"v"])

        if not self._compare_digest(server_signature, self._server_signature):
            raise ReqlAuthError("Invalid server signature", self._host, self._port)

        self._next_state()

    def reset(self):
        self._random_nonce = None
        self._first_client_message = None
        self._server_signature = None
        self._state = 0

    def next_message(self, response):
        if response is not None:
            response = response.decode("utf-8")

        if self._state == 0:
            return self._init_connection(response)

        elif self._state == 1:
            return self._read_response(response)

        elif self._state == 2:
            return self._prepare_auth_request(response)

        elif self._state == 3:
            return self._read_auth_response(response)

        raise ReqlDriverError("Unexpected handshake state")
