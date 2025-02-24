import logging
import os
from typing import List

import dev_scripts.documentation.render_md as dsdoremd
import helpers.hio as hio
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)
# #############################################################################


class Test_render_md1(hunitest.TestCase):
    """
    Test _uml_file_names method that returns output pathes.
    """

    def test_uml_file_names1(self) -> None:
        """
        Check output dir and file names correctness for absolute destination
        path.
        """
        dest_file = "/a/b/c/d/e.md"
        idx = 8
        extension = "png"
        pathes = dsdoremd._uml_file_names(dest_file, idx, extension)
        self.check_string("\n".join(pathes))


class Test_render_md2(hunitest.TestCase):
    """
    Test _render_command method that construct plantuml command.
    """

    def test_render_command1(self) -> None:
        """
        Check correctness of the command to render.
        """
        uml_file = "/a/b/c.puml"
        dest = "/d/e/f"
        extension = "png"
        cmd = dsdoremd._render_command(uml_file, dest, extension)
        self.check_string(cmd)

    def test_render_command2(self) -> None:
        """
        Check assertion if extension is unknown when render command is
        building.
        """
        uml_file = "/a/b/c.puml"
        dest = "/d/e/f"
        extension = "bmp"
        with self.assertRaises(AssertionError) as cm:
            dsdoremd._render_command(uml_file, dest, extension)
        # Check error text.
        self.assertIn("bmp", str(cm.exception))


class Test_render_md3(hunitest.TestCase):
    """
    Test _render_plantuml method that adds strings with links to rendered
    images.
    """

    def test_render_plantuml1(self) -> None:
        """
        Check correctness of rendering just UML text.
        """
        in_text = [
            "```plantuml",
            "Alice --> Bob",
            "```",
        ]
        self._check_str_after_render(in_text)

    def test_render_plantuml2(self) -> None:
        """
        Check correctness of rendering UML with another text.
        """
        in_text = [
            "A",
            "```plantuml",
            "Alice --> Bob",
            "```",
            "B",
        ]
        self._check_str_after_render(in_text)

    def test_render_plantuml3(self) -> None:
        """
        Check correctness of rendering text without UML.
        """
        in_text = [
            "A",
            "```bash",
            "Alice --> Bob",
            "```",
            "B",
        ]
        self._check_str_after_render(in_text)

    def test_render_plantuml4(self) -> None:
        """
        Check correctness of rendering UML text already pre-formatted.
        """
        in_text = [
            "```plantuml",
            "@startuml",
            "Alice --> Bob",
            "@enduml",
            "```",
        ]
        self._check_str_after_render(in_text)

    def test_render_plantuml_playback1(self) -> None:
        """
        Test real usage for im_architecture.md.
        """
        # Define input variables
        file_name = "im_architecture.md.test"
        in_file = os.path.join(self.get_input_dir(), file_name)
        in_txt = hio.from_file(in_file).split("\n")
        out_file = os.path.join(self.get_scratch_space(), file_name)
        extension = "png"
        dry_run = True
        # Call function to test
        act = dsdoremd._render_plantuml(
            in_txt=in_txt, out_file=out_file, extension=extension, dry_run=dry_run
        )
        act = "\n".join(act)
        # Check output
        self.check_string(act)

    def _check_str_after_render(self, in_text: List[str]) -> None:
        out_file = os.path.join(self.get_scratch_space(), "out.md")
        extension = "png"
        out_text = dsdoremd._render_plantuml(
            in_text, out_file, extension, dry_run=True
        )
        self.check_string("\n".join(out_text))
