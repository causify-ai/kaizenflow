#!/usr/bin/env python

"""
Import as:

import dev_scripts.git.git_hooks.commit-msg as dsgghoco
"""

import re
import sys


def _main():
    message_file = sys.argv[1]
    try:
        f = open(message_file, "r")
        commit_message = f.read()
    finally:
        f.close()
    regex = r"^Merge\sbranch|#(\d+)\s\S+"
    if not re.match(regex, commit_message):
        print(("Your commit message doesn't match regex '%s'" % regex))
        print("E.g., '#101 Awesomely fix this and that' or 'Merge branch ...'")
        print()
        print(
            "If you think there is a problem commit with --no-verify and "
            "file a bug with commit line and error"
        )
        sys.exit(1)


if __name__ == "__main__":
    print("git commit-msg hook ...")
    _main()
    sys.exit(0)
