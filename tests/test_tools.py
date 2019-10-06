"""Test tools.

Attributes:
    easy_clang_complete (module): this plugin module
    SublBridge (SublBridge): class for subl bridge
"""
import imp
from unittest import TestCase
from os import path

from EasyClangComplete.plugin.utils import tools
from EasyClangComplete.plugin.utils import file

imp.reload(tools)
imp.reload(file)

File = file.File
Tools = tools.Tools

PKG_NAME = tools.PKG_NAME


class test_tools(TestCase):
    """Test other things."""

    def test_pkg_name(self):
        """Test if the package name is correct."""
        self.assertEqual(PKG_NAME, "EasyClangComplete")

    def test_seconds_from_string(self):
        """Test that we can convert time to seconds."""
        self.assertEqual(60, Tools.seconds_from_string('00:00:60'))
        self.assertEqual(60, Tools.seconds_from_string('00:01:00'))
        self.assertEqual(120, Tools.seconds_from_string('00:02:00'))
        self.assertEqual(60 * 60, Tools.seconds_from_string('01:00:00'))
        self.assertEqual(60 * 60 + 1, Tools.seconds_from_string('01:00:01'))

    def test_run_command(self):
        """Test if the commands are run correctly."""
        import platform
        if platform.system() == 'Windows':
            return
        temp_dir = File.get_temp_dir()
        temp_file_name = 'test_run_command.log'
        temp_file_path = path.join(temp_dir, temp_file_name)
        if path.exists(temp_file_path):
            import os
            os.remove(temp_file_path)
        self.assertFalse(path.exists(temp_file_path))
        cmd_list = ['touch', temp_file_name]
        Tools.run_command(cmd_list, cwd=temp_dir)
        self.assertTrue(path.exists(temp_file_path))
        cmd = 'rm {}'.format(temp_file_path)
        Tools.run_command(cmd, shell=True)
        self.assertFalse(path.exists(temp_file_path))
