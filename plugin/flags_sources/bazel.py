"""Stores a class that manages genberation of compilation db with Bazel."""
from ..utils.output_panel_handler import OutputPanelHandler
from ..utils.search_scope import TreeSearchScope
from ..utils.tools import PKG_FOLDER
from ..utils.tools import Tools
from ..utils.file import File

from os import path

import logging
log = logging.getLogger("ECC")


class Bazel():
    """Collection of methods to generate a compilation database."""

    @staticmethod
    def generate_compdb(view):
        """Generate the compilation database."""
        OutputPanelHandler.hide_panel()
        output = ''
        workspace_file = File.search(
            'WORKSPACE', TreeSearchScope(path.dirname(view.file_name())))
        if not workspace_file:
            return None
        cmd = [path.join(PKG_FOLDER, 'external',
                         'bazel-compilation-database', 'generate.sh')]
        output = Tools.run_command(cmd, cwd=workspace_file.folder)
        return output

    @staticmethod
    def compdb_generated(future):
        """Generate a compilation database."""
        if future.done() and not future.cancelled():
            output_text = future.result()
            log.debug("Database generated. Output: \n%s", output_text)
            if "ERROR: " in output_text:
                log.error("Could not generate compilation database. Output: %s",
                          output_text)
                OutputPanelHandler.show(
                    "Could not generate compilation database.\n" + output_text)
        else:
            OutputPanelHandler.show("Could not generate compilation database.")
