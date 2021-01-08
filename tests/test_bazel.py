"""Test OutputPanelHandler."""

from EasyClangComplete.plugin.flags_sources import bazel
from EasyClangComplete.plugin.utils import output_panel_handler
from EasyClangComplete.tests import gui_test_wrapper

from os import path

import platform
import sublime
import imp

imp.reload(bazel)
imp.reload(gui_test_wrapper)

Bazel = bazel.Bazel
GuiTestWrapper = gui_test_wrapper.GuiTestWrapper
OutputPanelHandler = output_panel_handler.OutputPanelHandler


class MockFuture():
    """A mock of a future to test our async code."""

    def __init__(self, content):
        """Initialize with some content."""
        self.content = content

    def result(self):
        """Get the content."""
        return self.content

    def cancelled(self):
        """Is never cancelled."""
        return False

    def done(self):
        """Is always done."""
        return True


class TestBazelDbGeneration(object):
    """Test that we can create an output panel."""

    def tearDown(self):
        """Cleanup method run after every test."""
        super().tearDown()
        window = sublime.active_window()
        window.run_command("show_panel", {"panel": "output.UnitTesting"})

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'bazel',
                              'good_project',
                              'app',
                              'main.cpp')
        self.check_view(file_name)

    def test_good_project(self):
        """Test we can generate a valid compilation database with bazel."""
        file_name = path.join(path.dirname(__file__),
                              'bazel',
                              'good_project',
                              'app',
                              'main.cpp')
        self.set_up_view(file_name)
        output = Bazel.generate_compdb(self.view)
        self.assertNotIn("ERROR: ", output)
        future = MockFuture(output)
        Bazel.compdb_generated(future)
        compdb_file = path.join(path.dirname(__file__),
                                'bazel',
                                'good_project',
                                'compile_commands.json')
        self.assertTrue(path.exists(compdb_file))
        import yaml
        with open(compdb_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            self.assertEquals(len(data), 1)
            data = data[0]
            self.assertIn('file', data)
            self.assertIn('command', data)
            self.assertEquals(data['file'], 'app/main.cpp')
            self.assertIn('-x c++', data['command'])
            self.assertIn('-c app/main.cpp', data['command'])

    def test_bad_project(self):
        """Test we can't generate from a wrong project."""
        self.maxDiff = None
        file_name = path.join(path.dirname(__file__),
                              'bazel',
                              'bad_project',
                              'app',
                              'main.cpp')
        self.set_up_view(file_name)
        output = Bazel.generate_compdb(self.view)
        self.assertIn("ERROR: ", output)
        future = MockFuture(output)
        Bazel.compdb_generated(future)
        window = sublime.active_window()
        panel_view = window.find_output_panel(OutputPanelHandler.PANEL_TAG)
        panel_content = panel_view.substr(sublime.Region(0, panel_view.size()))
        split_output = output.split('\n')
        split_panel_content = panel_content.split('\n')
        self.assertTrue(len(split_panel_content) > 1)
        self.assertTrue(len(split_output) > 1)
        del (split_panel_content[0])  # Ignore the first line.
        self.assertEquals(len(split_panel_content), len(split_output))
        for panel_str, output_str in zip(split_panel_content, split_output):
            self.assertEquals(panel_str, output_str)
        compdb_file = path.join(path.dirname(__file__),
                                'bazel',
                                'bad_project',
                                'compile_commands.json')
        if path.exists(compdb_file):
            import yaml
            with open(compdb_file) as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
                self.assertEquals(len(data), 0)


if platform.system() == "Linux":
    class BazelTestRunner(TestBazelDbGeneration, GuiTestWrapper):
        """Run only if we are not on windows."""
        pass
