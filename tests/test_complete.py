"""Tests for autocompletion."""
import sublime
import platform
from os import path

from EasyClangComplete.plugin.settings.settings_manager import SettingsManager
from EasyClangComplete.plugin.tools import ActionRequest
from EasyClangComplete.plugin.view_config import ViewConfigManager


from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper


def has_libclang():
    """Ensure libclang tests will run only on platforms that support this.

    Returns:
        str: row contents
    """
    # Older version of Sublime Text x64 have ctypes crash bug.
    if platform.system() == "Windows" and sublime.arch() == "x64" and \
            int(sublime.version()) < 3123:
        return False
    return True


class BaseTestCompleter(object):
    """
    Base class for tests that are independent of the Completer implementation.

    Attributes:
        view (sublime.View): view
        use_libclang (bool): decides if we use libclang in tests
    """

    use_libclang = None

    def set_up_completer(self):
        """Utility method to set up a completer for the current view.

        Returns:
            BaseCompleter: completer for the current view.
        """
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        settings.use_libclang = self.use_libclang

        view_config_manager = ViewConfigManager()
        view_config = view_config_manager.load_for_view(self.view, settings)
        completer = view_config.completer
        return completer

    def tear_down_completer(self):
        """Utility method to set up a completer for the current view.

        Returns:
            BaseCompleter: completer for the current view.
        """
        view_config_manager = ViewConfigManager()
        view_config_manager.clear_for_view(self.view.buffer_id())

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_name)
        self.tear_down()

    def test_init(self):
        """Test that the completer is properly initialized."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer = self.set_up_completer()

        self.assertIsNotNone(completer.version_str)
        self.tear_down_completer()
        self.tear_down()

    def test_complete(self):
        """Test autocompletion for user type."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(8), "  a.")
        pos = self.view.text_point(8, 4)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['foo\tvoid foo(double a)', 'foo(${1:double a})']

        self.assertIn(expected, completions)
        self.tear_down_completer()
        self.tear_down()

    def test_excluded_private(self):
        """Test autocompletion for user type."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(8), "  a.")
        pos = self.view.text_point(8, 4)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['foo\tvoid foo(double a)', 'foo(${1:double a})']
        unexpected = ['foo\tvoid foo(int a)', 'foo(${1:int a})']
        if self.use_libclang:
            self.assertIn(expected, completions)
            self.assertNotIn(unexpected, completions)
        self.tear_down_completer()
        self.tear_down()

    def test_excluded_destructor(self):
        """Test autocompletion for user type."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(8), "  a.")
        pos = self.view.text_point(8, 4)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        destructor = ['~A\tvoid ~A()', '~A()']
        if self.use_libclang:
            self.assertNotIn(destructor, completions)
        else:
            self.assertIn(destructor, completions)
        self.tear_down_completer()
        self.tear_down()

    def test_complete_vector(self):
        """Test that we can complete vector members."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_vector.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(3), "  vec.")
        pos = self.view.text_point(3, 6)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        if platform.system() == "Windows":
            # disable the windows tests for now until AppVeyor fixes things
            self.tear_down()
            return
        expected = ['begin\titerator begin()', 'begin()']
        self.assertIn(expected, completions)
        self.tear_down_completer()
        self.tear_down()

    def test_unsaved_views(self):
        """Test that we gracefully handle unsaved views."""
        # Construct an unsaved scratch view.
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)

        # Manually set up a completer.
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        view_config_manager = ViewConfigManager()
        view_config = view_config_manager.load_for_view(self.view, settings)
        self.assertIsNone(view_config)
        self.tear_down()

    def test_cooperation_with_default_completions(self):
        """Empty clang completions should not hide default completions."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_errors.cpp')
        self.set_up_view(file_name)

        self.set_up_completer()

        # Undefined foo object has no completions.
        self.assertEqual(self.get_row(1), "  foo.")
        pos = self.view.text_point(1, 6)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Trigger default completions popup.
        self.view.run_command('auto_complete')
        self.assertTrue(self.view.is_auto_complete_visible())
        self.tear_down_completer()
        self.tear_down()


class TestBinCompleter(BaseTestCompleter, GuiTestWrapper):
    """Test class for the binary based completer."""

    use_libclang = False


if has_libclang():
    class TestLibCompleter(BaseTestCompleter, GuiTestWrapper):
        """Test class for the library based completer."""

        use_libclang = True
