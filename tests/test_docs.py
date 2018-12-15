"""Test that all docs are there."""
from os import path
from unittest import TestCase


def parse_code_headers(md_file_path):
    """Parse all settings names from the markdown."""
    import re
    all_settings_headers_regex = re.compile(r"###\s\*\*`(\w+)`\*\*.*")
    with open(md_file_path) as f:
        contents = f.read()
        matches = all_settings_headers_regex.findall(contents)
        return matches


def parse_settings(json_file_path):
    """Parse all settings names from the json file."""
    import re
    all_settings_regex = re.compile(r'^  "(\w+)"\s*:.+$', flags=re.MULTILINE)
    with open(json_file_path) as f:
        contents = f.read()
        matches = all_settings_regex.findall(contents)
        return matches


class TestSomething(TestCase):
    """Test that the settings have descriptions in the docs."""

    def test_all_settings(self):
        """Test that all settings have docs."""
        project_folder = path.dirname(path.dirname(__file__))
        md_file = path.join(project_folder, 'docs', 'settings.md')
        settings_file = path.join(
            project_folder, 'EasyClangComplete.sublime-settings')
        self.assertEqual(set(parse_code_headers(md_file)),
                         set(parse_settings(settings_file)))
