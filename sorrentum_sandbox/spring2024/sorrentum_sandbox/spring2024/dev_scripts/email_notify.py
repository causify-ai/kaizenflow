#!/usr/bin/env python

"""
Import as:

import dev_scripts.email_notify as dscemnot
"""

import helpers.hemail as hemail


def _main():
    subject = message = "done"

    # TODO(gp): Somehow retrieve the last command (e.g., using history | last -1)

    # TODO(gp): Generalize to multiple users using current user: we can use github
    # credentials.
    hemail.send_email(subject, message, "abc@xyz.com")


if __name__ == "main":
    _main()
