#!/usr/bin/env python
"""
Import as:

import dev_scripts.notebooks.ipynb_format as dsnoipfo
"""

# -*- encoding: utf-8 -*-

# From https://github.com/fg1/ipynb_format

__version__ = "0.1.0"

import argparse
import os
import sys

import nbformat as nbf
from yapf.yapflib.file_resources import GetDefaultStyleForDir
from yapf.yapflib.yapf_api import FormatCode


def ipynb_format(fname, style=None):
    f = open(fname, "r")
    nb = nbf.read(f, as_version=nbf.NO_CONVERT)
    f.close()

    if style is None:
        style = GetDefaultStyleForDir(os.path.dirname(fname))

    modified = 0
    if True:
        for cell in nb["cells"]:
            if cell["cell_type"] != "code":
                continue
            if len(cell["source"]) == 0:
                continue

            modcell = False
            out = []
            q = []
            for i in cell["source"].splitlines(True):
                # print i
                if i.startswith("!"):
                    continue
                if i.startswith("?"):
                    continue
                if i.startswith("%"):
                    if len(q) > 0:
                        qf, mod = FormatCode("".join(q), style_config=style)
                        if mod:
                            modcell = True
                            out += qf.splitlines(True)
                        else:
                            out += q
                        q = []
                    out += [i]
                    continue
                q.append(i)

            if len(q) > 0:
                qf, mod = FormatCode("".join(q), style_config=style)
                if mod:
                    modcell = True
                    out += qf.splitlines(True)
                else:
                    out += q

            if len(out[-1]) == 0:
                modcell = True
                out = out[:-1]

            if out[-1][-1] == "\n":
                modcell = True
                out[-1] = out[-1][:-1]

            if modcell:
                out = [s.encode("ascii", "ignore") for s in out]
                cell["source"] = out
                modified += 1

    print(("Num of cells modified=%d" % modified))
    if modified:
        import io

        f = io.open(fname, "w", encoding="utf-8")
        nbf.write(nb, f)
        f.close()

    return modified


def cli():
    parser = argparse.ArgumentParser(
        description="Format ipython notebook using yapf"
    )
    parser.add_argument("--style", action="store", help="yapf style to use")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    if len(args.files) == 0:
        parser.print_help()
        sys.exit(1)

    mod = False
    for f in args.files:
        mod |= ipynb_format(f, args.style)


if __name__ == "__main__":
    cli()
