import six


def decode_utf8(string, encoding="utf-8"):
    if hasattr(string, "decode"):
        return string.decode(encoding)

    return string


def chain_to_bytes(*strings):
    return b"".join(
        [
            six.b(string) if isinstance(string, six.string_types) else string
            for string in strings
        ]
    )
