#!/usr/bin/env python
"""
Handle backups / export / import of Google Drive directory.

# List content of a Google drive dir.
> infra/gdrive.py --action ls --src_dir gp_drive:alphamatic -v DEBUG

# Backup.
> infra/gdrive.py --action backup --src_dir gp_drive:alphamatic --dst_dir gdrive_backup -v DEBUG

# Test of moving data.
> infra/gdrive.py --action backup --src_dir gp_drive:alphamatic/LLC --dst_dir gdrive_backup
> infra/gdrive.py --action export --src_dir gp_drive:alphamatic/LLC --dst_dir tmp.LLC
> infra/gdrive.py --action import --src_dir tmp.LLC --dst_dir alphamatic_drive:test/LLC

# Moving data.
> infra/gdrive.py --action export --src_dir gp_drive:alphamatic --dst_dir tmp.alphamatic
> infra/gdrive.py --action import --src_dir tmp.alphamatic --dst_dir alphamatic_drive:alphamatic

Import as:

import dev_scripts.infra.gdrive as dscingdr
"""

#  Configure rclone
# > rclone config
#     new_remote (n)
#     name= (symbolic name of the drive)
#     type= (drive)
#     Google Application Client Id (blank)
#     Google Application Client Secret (blank)
#     scope = (drive)
#     root_folder_id> (blank)
#     service_account_file> (blank)
#     Edit advanced config? (n)
#     Use auto config? (y)
#     Then the browser asks for authorizing rclone
#     Configure this as a team drive? (n)

# The config file is ~/.config/rclone/rclone.conf

# The Google drives are:
# - "gp_drive:alphamatic"
# - "..._drive:"
# - "alphamatic:"

import argparse
import logging
import os
import sys

import helpers.hdatetime as hdateti
import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################


def _create_dst_dir(dst_dir):
    hdbg.dassert(dst_dir, msg="Need to specify --dst_dir")
    dst_dir = os.path.abspath(dst_dir)
    hio.create_dir(dst_dir, incremental=True)
    return dst_dir


def _rclone_ls(remote_src_dir, timestamp, log_dir):
    cmd = ["rclone ls", remote_src_dir]
    cmd = " ".join(cmd)
    output_file = "%s/gdrive.%s.txt" % (log_dir, timestamp)
    hsystem.system(cmd, output_file=output_file)


def _rclone_copy_from_gdrive(remote_src_dir, local_dst_dir, log_dir, dry_run):
    cmd = [
        "rclone copy",
        remote_src_dir,
        local_dst_dir,
        "--drive-export-formats docx,xlsx,pptx,svg",
        # "--drive-shared-with-me",
    ]
    verbosity = hdbg.get_logger_verbosity()
    if verbosity <= logging.DEBUG:
        cmd.append("-vv")
    #
    cmd = " ".join(cmd)
    #
    output_file = log_dir + "/rclone_copy_from_gdrive.txt"
    hsystem.system(
        cmd,
        output_file=output_file,
        tee=True,
        suppress_output=False,
        dry_run=dry_run,
    )


def _rclone_copy_to_gdrive(local_src_dir, remote_dst_dir, log_dir, dry_run):
    hdbg.dassert_path_exists(local_src_dir)
    cmd = [
        "rclone copy",
        local_src_dir,
        remote_dst_dir,
        "--drive-import-formats docx,xlsx,pptx,svg",
        "--drive-allow-import-name-change",
        # "--drive-shared-with-me"
    ]
    verbosity = hdbg.get_logger_verbosity()
    if verbosity <= logging.DEBUG:
        cmd.append("-vv")
    #
    cmd = " ".join(cmd)
    #
    output_file = log_dir + "/rclone_copy_to_gdrive.log"
    hsystem.system(
        cmd,
        output_file=output_file,
        tee=True,
        suppress_output=False,
        dry_run=dry_run,
    )


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--action",
        action="store",
        choices=["ls", "backup", "export", "import"],
        required=True,
    )
    parser.add_argument("--no_cleanup", action="store_true")
    parser.add_argument("--skip_tgz", action="store_true")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument(
        "--src_dir", action="store", default=None, help="Source dir"
    )
    parser.add_argument(
        "--dst_dir", action="store", default=None, help="Destination dir"
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    log_dir = "./tmp.gdrive.log"
    log_dir = os.path.abspath(log_dir)
    hio.create_dir(log_dir, incremental=not args.incremental)
    timestamp = hdateti.get_current_timestamp_as_string("naive_ET")
    if args.action == "ls":
        cmd = ["rclone ls", args.src_dir]
        cmd = " ".join(cmd)
        hsystem.system(cmd, suppress_output=False)
        sys.exit(0)
    if args.action == "backup":
        # Create temp dir.
        temp_dir = "./tmp.gdrive"
        temp_dir = os.path.abspath(temp_dir)
        hio.create_dir(temp_dir, incremental=not args.incremental)
        # Create dst dir.
        dst_dir = _create_dst_dir(args.dst_dir)
        # List files.
        hdbg.dassert(args.src_dir, msg="Need to specify --src__dir")
        _rclone_ls(args.src_dir, timestamp, log_dir)
        # Clone data inside the temp dir.
        _LOG.info("# Downloading data from %s to %s ...", args.src_dir, dst_dir)
        _rclone_copy_from_gdrive(args.src_dir, temp_dir, log_dir, args.dry_run)
        # Compress.
        if not args.skip_tgz:
            _LOG.info("# Archiving ...")
            tar_file = "%s/gdrive.%s.tgz" % (dst_dir, timestamp)
            hdbg.dassert_path_not_exists(tar_file)
            output_file = log_dir + "/tar.log"
            cmd = "tar -cf %s -C %s ." % (tar_file, temp_dir)
            hsystem.system(
                cmd, output_file=output_file, tee=True, dry_run=args.dry_run
            )
            _LOG.info("tar_file is at '%s'", tar_file)
        else:
            _LOG.info("# Skipping archiving")
        # Clean up.
        if args.incremental or args.no_cleanup:
            # No clean-up.
            _LOG.info("# Skipping clean up")
        else:
            _LOG.info("# Cleaning up ...")
            cmd = "rm -rf %s" % temp_dir
            hsystem.system(cmd, dry_run=args.dry_run)
        # Delete old ones.
        # find $base -type f -mtime +3 -delete
    if args.action == "export":
        # Create dst dir.
        dst_dir = _create_dst_dir(args.dst_dir)
        # List files.
        hdbg.dassert(args.src_dir, msg="Need to specify --src__dir")
        _rclone_ls(args.src_dir, timestamp, log_dir)
        # Clone data inside the temp dir.
        _LOG.info("# Exporting data from %s to %s ...", args.src_dir, dst_dir)
        _rclone_copy_from_gdrive(args.src_dir, dst_dir, log_dir, args.dry_run)
    if args.action == "import":
        # Clone data inside the temp dir.
        _LOG.info(
            "# Importing data from %s to %s ...", args.src_dir, args.dst_dir
        )
        _rclone_copy_to_gdrive(args.src_dir, args.dst_dir, log_dir, args.dry_run)


if __name__ == "__main__":
    _main(_parse())
