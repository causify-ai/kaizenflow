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


"""The match_hostname() function from Python 3.3.3, essential when using SSL."""

import re

__version__ = "3.4.0.2"


class CertificateError(ValueError):
    pass


def _dnsname_match(domain_name, hostname, max_wildcards=1):
    """Matching according to RFC 6125, section 6.4.3

    http://tools.ietf.org/html/rfc6125#section-6.4.3
    """
    pats = []
    if not domain_name:
        return False

    # Ported from python3-syntax:
    # leftmost, *remainder = domain_name.split(r'.')
    parts = domain_name.split(r".")
    leftmost = parts[0]
    remainder = parts[1:]

    wildcards = leftmost.count("*")
    if wildcards > max_wildcards:
        # Issue #17980: avoid denials of service by refusing more
        # than one wildcard per fragment.  A survey of established
        # policy among SSL implementations showed it to be a
        # reasonable choice.
        raise CertificateError(
            "too many wildcards in certificate DNS name: " + repr(domain_name)
        )

    # speed up common case w/o wildcards
    if not wildcards:
        return domain_name.lower() == hostname.lower()

    # RFC 6125, section 6.4.3, subitem 1.
    # The client SHOULD NOT attempt to match a presented identifier in which
    # the wildcard character comprises a label other than the left-most label.
    if leftmost == "*":
        # When '*' is a fragment by itself, it matches a non-empty dotless
        # fragment.
        pats.append("[^.]+")
    elif leftmost.startswith("xn--") or hostname.startswith("xn--"):
        # RFC 6125, section 6.4.3, subitem 3.
        # The client SHOULD NOT attempt to match a presented identifier
        # where the wildcard character is embedded within an A-label or
        # U-label of an internationalized domain name.
        pats.append(re.escape(leftmost))
    else:
        # Otherwise, '*' matches any dotless string, e.g. www*
        pats.append(re.escape(leftmost).replace(r"\*", "[^.]*"))

    # add the remaining fragments, ignore any wildcards
    for frag in remainder:
        pats.append(re.escape(frag))

    pat = re.compile(r"\A" + r"\.".join(pats) + r"\Z", re.IGNORECASE)
    return pat.match(hostname)


def match_hostname(cert, hostname):
    """Verify that *cert* (in decoded format as returned by
    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125
    rules are followed, but IP addresses are not accepted for *hostname*.

    CertificateError is raised on failure. On success, the function
    returns nothing.
    """

    if not cert:
        raise ValueError("empty or no certificate")

    dnsnames = []
    san = cert.get("subjectAltName", ())
    for key, value in san:
        if key == "DNS":
            if _dnsname_match(value, hostname):
                return
            dnsnames.append(value)

    if not dnsnames:
        # The subject is only checked when there is no dNSName entry
        # in subjectAltName
        for sub in cert.get("subject", ()):
            for key, value in sub:
                # XXX according to RFC 2818, the most specific Common Name
                # must be used.
                if key == "commonName":
                    if _dnsname_match(value, hostname):
                        return
                    dnsnames.append(value)

    if len(dnsnames) > 1:
        raise CertificateError(
            "hostname %r doesn't match either of %s"
            % (hostname, ", ".join(map(repr, dnsnames)))
        )
    elif len(dnsnames) == 1:
        raise CertificateError("hostname %r doesn't match %r" % (hostname, dnsnames[0]))
    else:
        raise CertificateError(
            "no appropriate commonName or subjectAltName fields were found"
        )
