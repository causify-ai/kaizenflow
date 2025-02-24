#!/usr/bin/env python

"""
The script adds rendered images to all plantUML sections in the markdown files.

Usage:
    1. Include plantUML diagram picture to markdown:
    > render_md.py -i ABC.md -o XYZ.md --action render
    > render_md.py -i ABC.md -o XYZ.md

    2. Include plantUML diagram picture in place:
    > render_md.py -i ABC.md

    3. Open html to preview:
    > render_md.py -i ABC.md --action open

    4. Render with preview:
    > render_md.py -i ABC.md -o XYZ.md --all
    > render_md.py -i ABC.md --all

Import as:

import dev_scripts.documentation.render_md as dsdoremd
"""

import argparse
import logging
import os
import tempfile
from typing import List, Tuple

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)

# #############################################################################

_ACTION_OPEN = "open"
_ACTION_RENDER = "render"
_VALID_ACTIONS = [_ACTION_OPEN, _ACTION_RENDER]
_DEFAULT_ACTIONS = [_ACTION_RENDER]


def _open_html(md_file: str) -> None:
    """
    Pandoc markdown to html and open it.
    """
    _LOG.info("\n%s", hprint.frame("Process markdown to html"))
    # Get pandoc.py command.
    curr_path = os.path.abspath(os.path.dirname(__file__))
    tmp_dir = os.path.split(md_file)[0]
    cmd = (
        "%s/pandoc.py -t %s -i %s --skip_action %s --skip_action %s --tmp_dir %s"
        % (curr_path, "html", md_file, "copy_to_gdrive", "cleanup_after", tmp_dir)
    )
    hsystem.system(cmd)


def _uml_file_names(
    dest_file: str, idx: int, extension: str
) -> Tuple[str, str, str]:
    """
    Generate plantUML picture filename, temporary UML filename, full path to
    picture. We want to assign the name of the image relative to the
    originating file and index. In this way if we update the image, the name of
    the image doesn't change.

    :param dest_file: markdowm target file where diagrams should be included
    :param idx: order number of the UML appearence at the input file
    :param extension: extension for image file
    :return:
        - full path to UML picture dir
        - relative picture file name
        - temporary UML file name
    """
    sub_dir = "plantuml-images"
    dst_dir, dest_file_name = os.path.split(os.path.abspath(dest_file))
    file_name_body = os.path.splitext(dest_file_name)[0]
    # Create image name.
    img_name = "%s.%s.%s" % (file_name_body, idx, extension)
    # Get dir with images.
    abs_path = os.path.join(dst_dir, sub_dir)
    # Get relative path to image.
    rel_path = os.path.join(sub_dir, img_name)
    # Get temporary file name.
    tmp_name = "%s.%s.puml" % (file_name_body, idx)
    return (abs_path, rel_path, tmp_name)


def _render_command(uml_file: str, pic_dest: str, extension: str) -> str:
    """
    Create PlantUML rendering command.
    """
    available_extensions = ["svg", "png"]
    hdbg.dassert_in(extension, available_extensions)
    cmd = "plantuml -t%s -o %s %s" % (extension, pic_dest, uml_file)
    return cmd


def _render_plantuml_code(
    uml_text: str,
    out_file: str,
    idx: int,
    extension: str,
    dry_run: bool,
) -> str:
    """
    Render the PlantUML text into a file.

    :param uml_text: UML format text
    :param out_file: full path to output md file
    :param idx: index of UML appearence
    :param extension: type of rendered image
    :param dry_run: if True, doesn't execute plantulml command
    :return: related path to image
    """
    # Format UML text to render.
    uml_content = uml_text
    if not uml_content.startswith("@startuml"):
        uml_content = "@startuml\n%s" % uml_content
    if not uml_content.endswith("@enduml"):
        uml_content = "%s\n@enduml" % uml_content
    # Create the including directory, if needed.
    hio.create_enclosing_dir(out_file, incremental=True)
    # Get pathes.
    target_dir, rel_path, tmp_file_name = _uml_file_names(
        out_file, idx, extension
    )
    # Save text to temporary file.
    tmp_file = os.path.join(tempfile.gettempdir(), tmp_file_name)
    hio.to_file(tmp_file, uml_content)
    # Convert the plantUML txt.
    cmd = _render_command(tmp_file, target_dir, extension)
    _LOG.info("Creating uml diagram from %s source.", tmp_file)
    _LOG.info("Saving image to %s.", target_dir)
    _LOG.info("> %s", cmd)
    hsystem.system(cmd, dry_run=dry_run)
    return rel_path


def _render_plantuml(
    in_txt: List[str], out_file: str, extension: str, dry_run: bool
) -> List[str]:
    """
    Add rendered image after plantuml code blocks.

    :param in_txt: list of strings to process
    :param out_file: name of outcome file
    :param extension: extension for rendered images
    :param dry_run: only changes text skipping image creation
    """
    # Store the output.
    out_txt: List[str] = []
    # Store the plantuml code found so far.
    plantuml_txt: List[str] = []
    # Count the index of the plantuml found in the file.
    plantuml_idx = 0
    # Store the state of the parser.
    state = "searching"
    for i, line in enumerate(in_txt):
        _LOG.debug("%d: %s -> state=%s", i, line, state)
        out_txt.append(line)
        if line.strip() == "```plantuml":
            # Found the beginning of a plantuml text.
            hdbg.dassert_eq(state, "searching")
            plantuml_txt = []
            plantuml_idx += 1
            state = "found_plantuml"
            _LOG.debug(" -> state=%s", state)
        elif line.strip() == "```" and state == "found_plantuml":
            img_file_name = _render_plantuml_code(
                uml_text="\n".join(plantuml_txt),
                out_file=out_file,
                idx=plantuml_idx,
                extension=extension,
                dry_run=dry_run,
            )
            out_txt.append("![](%s)" % img_file_name)
            state = "searching"
            _LOG.debug(" -> state=%s", state)
        elif line.strip != "```" and state == "found_plantuml":
            plantuml_txt.append(line)
    return out_txt


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    hparser.add_input_output_args(parser)
    hparser.add_action_arg(parser, _VALID_ACTIONS, _DEFAULT_ACTIONS)
    # Debug arguments.
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Don't create images with plantuml command",
    )
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    # Insert your code here.
    # Read file arguments.
    in_file, out_file = hparser.parse_input_output_args(args, clear_screen=True)
    # Not support stdin and stdout.
    hdbg.dassert_ne(in_file, "-")
    hdbg.dassert_ne(out_file, "-")
    # Read actions argument.
    actions = hparser.select_actions(args, _VALID_ACTIONS, _DEFAULT_ACTIONS)
    # Set rendered image extension.
    extension = "png"
    # Save to temporary file and keep svg extension if only open.
    if actions == [_ACTION_OPEN]:
        out_file = tempfile.mktemp(suffix=".md")
        extension = "svg"
    # Read input file lines.
    in_lines = hio.from_file(in_file).split("\n")
    # Get updated lines after rendering.
    out_lines = _render_plantuml(in_lines, out_file, extension, args.dry_run)
    # Save the output into a file.
    hio.to_file(out_file, "\n".join(out_lines))
    # Open if needed.
    if _ACTION_OPEN in actions:
        _open_html(out_file)


if __name__ == "__main__":
    _main(_parse())
