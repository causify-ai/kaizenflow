#!/usr/bin/env python

"""
- Rsync a git dir against a pycharm deploy dir
> grsync.py --src_dir $HOME/src/.../... --config amp --action rsync -v DEBUG --preview

- Diff
> grsync.py --src_dir $HOME/src/.../... --config amp --action diff
> grsync.py --src_dir $HOME/src/.../... --config amp --action diff_verb
> grsync.py --src_dir $HOME/src/.../.../tr --config amp --action diff_verb

Import as:

import dev_scripts.grsync as dscrgrsy
"""

import argparse
import logging
import os

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# TODO(gp):
# - Mount remote file system and then get info and sha1sum

# #############################################################################

_TO_EXCLUDE = [
    "*.pyc",
    ".git",
    ".idea",
    ".ipynb_checkpoints",
    "'*/my_venv/*'",
]


def _get_rsync_cmd(
    src_dir,
    dst_dir,
    remote_user_name,
    dst_ip,
    preview,
    force,
    execute,
    local_to_remote,
):
    cmd = "rsync"
    # -a: archive
    # -v: verbose
    # -i: itemize info
    # -z: compress
    # -u: if different keep oldest
    # -P: --partial(restart from middle if transfer was interrupted) and --progress
    # --suffix.old: use a suffix to keep old
    cmd_opts = ""
    if preview:
        # https://stackoverflow.com/questions/4493525
        cmd_opts += " --itemize-changes"
    if not execute:
        cmd_opts += " --dry-run"
    if force:
        cmd_opts += " -I --delete"
    cmd_opts += " -avzu"
    cmd_opts += "".join([" --exclude %s" % e for e in _TO_EXCLUDE])
    cmd += cmd_opts
    # Handle a quirk of rsync where the destination dir needs to have one
    # missing level.
    # > rsync --itemize-changes -avzu --exclude ... \
    #   /Users/saggese/src/.../.../tr
    #   gp@104.248.187.204:/home/gp/src/...
    #   --dry-run
    hdbg.dassert_eq(os.path.basename(src_dir), os.path.basename(dst_dir))
    dst_dir = os.path.dirname(dst_dir)
    dst = "%s@%s:%s" % (remote_user_name, dst_ip, dst_dir)
    if local_to_remote:
        cmd += " %s %s" % (src_dir, dst)
    else:
        cmd += " %s %s" % (dst, src_dir)
    return cmd


def _process_rsync_file_list(src_file, dst_file):
    # rsync --itemize-changes -n -avzu --exclude ... /Users/saggese/src/.../.../tr
    # rsync --itemize-changes -n -avzu --exclude ... gp@104.248.187.204:/home/gp/src/.../tr
    # Load.
    txt = hio.from_file(src_file).split("\n")
    _LOG.debug("Read file '%s'", src_file)
    # Process.
    txt_out = []
    for line in txt:
        if line == "":
            continue
        if "incremental file list" in line:
            continue
        # 1,140,347 5,571,728 bytes 4,474,716.67 bytes/sec
        # size speedup is 189.68 (DRY RUN)
        if ("bytes/sec" in line) or ("(DRY RUN)" in line):
            continue
        # _LOG.debug("line=%s", line)
        # 0                   1     2          3        4
        # drwxr-xr-x          1,312 2019/09/05 17:51:42 ...
        data = line.split()
        hdbg.dassert_lte(4, len(data), "line=%s", str(data))
        perms, size, date, time = data[:4]
        file_name = data[4:]
        _ = date, time
        if perms.startswith("d"):
            continue
        # Keep size and file name.
        data = [size] + file_name
        txt_out.append(" ".join(data))
    # Save.
    txt_out = "\n".join(txt_out)
    hio.to_file(dst_file, txt_out)
    _LOG.debug("Written file '%s'", dst_file)


def _get_list_files_cmd(
    src_dir, dst_dir, remote_user_name, dst_ip, local_to_remote, verbose
):
    """
    Only list files.
    """
    cmd = "rsync"
    cmd_opts = ""
    cmd_opts += " --itemize-changes"
    cmd_opts += " -n -avzu"
    cmd_opts += "".join([" --exclude %s" % e for e in _TO_EXCLUDE])
    cmd += cmd_opts
    if local_to_remote:
        cmd += " " + src_dir
    else:
        cmd += " %s@%s:%s" % (remote_user_name, dst_ip, dst_dir)
    dst_file = (
        "tmp.local_all.txt" if not local_to_remote else "tmp.remote_all.txt"
    )
    cmd += " >%s" % dst_file
    hsystem.system(cmd)
    #
    if not verbose:
        src_file = dst_file
        dst_file = dst_file.replace("_all.txt", ".txt")
        _process_rsync_file_list(src_file, dst_file)
    return dst_file


# #############################################################################


def _main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--src_dir", action="store", required=True, help="Local directory to sync"
    )
    parser.add_argument(
        "--dst_dir", action="store", default=None, help="Remote directory to sync"
    )
    parser.add_argument(
        "--action",
        action="store",
        required=True,
        choices="rsync rsync_both_ways diff diff_verb".split(),
        help="rsync from local to remote",
    )
    parser.add_argument("--force", action="store_true", help="Force the rsync")
    parser.add_argument("--no_check", action="store_true")
    parser.add_argument(
        "--preview", action="store_true", help="Use --itemize-changes"
    )
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument(
        "--config", action="store", required=True, help="IP of remote machine"
    )
    hparser.add_verbosity_arg(parser)
    #
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level)
    #
    src_dir = args.src_dir
    if args.config == "":
        # TODO(gp): Generalize this.
        remote_user_name = "gp"
        remote_ip = "104.248.187.204"
        dst_dir = "/home/gp/src"
        if args.src_dir:
            base_dir = ""
            hdbg.dassert_in(base_dir, src_dir)
            hdbg.dassert_in(base_dir, dst_dir)
            idx = src_dir.index(base_dir) + len(base_dir)
            sub_dir = src_dir[idx:]
            dst_dir += "/" + sub_dir
            dst_dir = os.path.abspath(dst_dir)
    else:
        raise ValueError("Invalid config='%s'" % args.config)
    hdbg.dassert_is_not(dst_dir, None)
    # Check that both dirs exist.
    hdbg.dassert_is_not(args.src_dir, None)
    src_dir = os.path.abspath(args.src_dir)
    hdbg.dassert_path_exists(src_dir)
    #
    print("src_dir=%s" % args.src_dir)
    print("dst_dir=%s" % dst_dir)
    print("remote=%s@%s" % (remote_user_name, remote_ip))
    #
    if not args.no_check:
        cmd = 'ssh %s@%s "ls %s"' % (remote_user_name, remote_ip, dst_dir)
        rc = hsystem.system(cmd, abort_on_error=False)
        if rc != 0:
            msg = "Can't find remote dir '%s' on '%s@%s'" % (
                dst_dir,
                remote_user_name,
                remote_ip,
            )
            _LOG.error(msg)
            raise RuntimeError(msg)
    #
    if args.action == "rsync":
        force = args.force
        preview = args.preview
        execute = not args.dry_run
        local_to_remote = True
        cmd = _get_rsync_cmd(
            src_dir,
            dst_dir,
            remote_user_name,
            remote_ip,
            preview,
            force,
            execute,
            local_to_remote,
        )
        hsystem.system(cmd, suppress_output=False)
    elif args.action == "rsync_both_ways":
        raise RuntimeError("Not implemented yet")
        force = False
        preview = args.preview
        execute = not args.dry_run
        #
        for local_to_remote in (True, False):
            cmd = _get_rsync_cmd(
                src_dir,
                dst_dir,
                remote_user_name,
                remote_ip,
                preview,
                force,
                execute,
                local_to_remote,
            )
            hsystem.system(cmd, suppress_output=False)
        #
    elif args.action in ("diff", "diff_verb"):
        files = []
        verbose = args.action == "diff_verb"
        for local_to_remote in (True, False):
            file = _get_list_files_cmd(
                src_dir,
                dst_dir,
                remote_user_name,
                remote_ip,
                local_to_remote,
                verbose,
            )
            files.append(file)
        # Save a script to diff.
        vimdiff_cmd = "vimdiff %s %s" % (files[0], files[1])
        diff_script = "./tmp_diff.sh"
        hio.to_file(diff_script, vimdiff_cmd)
        cmd = "chmod +x " + diff_script
        hsystem.system(cmd)
        msg = (
            "Diff with:",
            "> " + vimdiff_cmd,
            "or running:",
            "> " + diff_script,
        )
        msg = "\n".join(msg)
        _LOG.error(msg)
    else:
        hdbg.dfatal("Invalid action='%s'" % args.action)


if __name__ == "__main__":
    _main()
