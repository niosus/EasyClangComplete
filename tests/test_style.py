"""Test conformance to pep8 and pep257."""
from unittest import TestCase
from os import path

from EasyClangComplete.plugin.utils.tools import Tools

PEP_257_IGNORE = [
    "D209",
    "D203",
    "D204",
    "D213",
    "D406",
    "D407"
]

PEP257_CMD = "pep257 '{}' --match-dir='^(?!clang|external).*' --ignore={}"
PEP8_CMD = 'pycodestyle --exclude=clang,external,.git '\
    '--show-source --show-pep8 --count --max-line-length=80 "{}"'

PLUGIN_SOURCE_FOLDER = path.dirname(path.dirname(__file__))

LINUX_MISSING_MSG = "command not found"
WINDOWS_MISSING_MSG = "is not recognized as an internal or external command"


class TestStyle(TestCase):
    """Test that the code conforms to pep8 and pep257."""

    def test_pep8(self):
        """Test conformance to pep8."""
        self.maxDiff = None
        cmd = PEP8_CMD.format(PLUGIN_SOURCE_FOLDER)
        output = Tools.run_command(cmd, shell=True)
        if LINUX_MISSING_MSG in output or WINDOWS_MISSING_MSG in output:
            print('no pep8 found in path!')
            return
        self.assertEquals(output, "")

    def test_pep257(self):
        """Test conformance to pep257."""
        self.maxDiff = None
        cmd = PEP257_CMD.format(PLUGIN_SOURCE_FOLDER, ','.join(PEP_257_IGNORE))
        output = Tools.run_command(cmd, shell=True)
        if LINUX_MISSING_MSG in output or WINDOWS_MISSING_MSG in output:
            print('no pep257 found in path!')
            return
        self.assertEquals(output, "")
