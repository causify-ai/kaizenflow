#!/usr/bin/env python

"""
The script checks if a GH user is already a collaborator of a specific
repository, sends an invitation if not, and reports any pending invitations.

Example:
> github_permission.py \
    --github_username GITHUB_USERNAME \
    --owner_username OWNER_USERNAME \
    --repo_name REPO_NAME \
    --access_token ACCESS_TOKEN

Import as:

import dev_scripts.github_permission as descgipe
"""

import argparse
import logging
import os

import requests

import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


def _invite_collaborator(
    github_username: str,
    owner_username: str,
    repo_name: str,
    access_token: str,
) -> None:
    """
    Invite a collaborator to GitHub.
    """
    add_collaborator_endpoint = os.path.join(
        "https://api.github.com/repos",
        owner_username,
        repo_name,
        "collaborators/{collaborator}",
    )
    collaborator_check_url = os.path.join(
        "https://api.github.com/repos/",
        owner_username,
        repo_name,
        "collaborators/{github_username}",
    )
    headers = {"Authorization": "Bearer " + access_token}
    response = requests.get(collaborator_check_url, headers=headers, timeout=10)
    status_code = response.status_code
    if status_code == 204:
        # Get GH collaborator status.
        collaborator_permissions_url = "/".join(
            [collaborator_check_url, "permission"]
        )
        response = requests.get(
            collaborator_permissions_url, headers=headers, timeout=10
        )
        status_code = response.status_code
        if status_code == 200:
            # Get GH collaborator permission level.
            current_permission_level = response.json()["permission"]
            _LOG.debug(
                "%s is already a collaborator with %s permission level.",
                github_username,
                current_permission_level,
            )
        else:
            _LOG.debug(
                "Error retrieving permission level for %s. Status code: %s",
                github_username,
                status_code,
            )
    elif status_code == 404:
        # Get invitation status.
        invitation_check_url = os.path.join(
            "https://api.github.com/repos",
            owner_username,
            repo_name,
            "invitations",
        )
        response = requests.get(invitation_check_url, headers=headers, timeout=10)
        status_code = response.status_code
        if status_code == 200:
            # Check if an invitation was sent to a user that is already a GH collaborator.
            invitations = response.json()
            for invitation in invitations:
                invitee_login = invitation["invitee"]["login"]
                invitee_permission = invitation["permissions"]
                if invitee_login == github_username:
                    _LOG.debug(
                        "%s's invitation is pending to accept with %s permission level.",
                        github_username,
                        invitee_permission,
                    )
                    break
            else:
                # Send an invitation to a user that is not a GH collaborator.
                add_collaborator_url = add_collaborator_endpoint.format(
                    owner_username=owner_username,
                    repo_name=repo_name,
                    collaborator=github_username,
                )
                data = {"permission": "pull"}
                response = requests.put(
                    add_collaborator_url, headers=headers, json=data, timeout=10
                )
                status_code = response.status_code
                if status_code == 201:
                    _LOG.debug(
                        "New invitation sent to %s with permission level.",
                        github_username,
                    )
                else:
                    _LOG.debug(
                        "Error sending invitation to %s. Status code: %s",
                        github_username,
                        status_code,
                    )
        else:
            _LOG.debug(
                "Error retrieving invitations for %s/%s. Status code: %s Permission level: %s",
                owner_username,
                repo_name,
                status_code,
                current_permission_level,
            )
    else:
        _LOG.debug(
            "Error retrieving information for %s. Status code: %s",
            github_username,
            status_code,
        )


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--github_username",
        type=str,
        required=True,
        help="Collaborator's GH username",
    )
    parser.add_argument(
        "--owner_username",
        type=str,
        required=True,
        help="Repository owner GH username",
    )
    parser.add_argument(
        "--repo_name",
        type=str,
        required=True,
        help="Repository name to provide permission to",
    )
    parser.add_argument(
        "--access_token",
        type=str,
        required=True,
        help="Owner's generated access token",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    _invite_collaborator(
        args.github_username,
        args.owner_username,
        args.repo_name,
        args.access_token,
    )


if __name__ == "__main__":
    _main(_parse())
