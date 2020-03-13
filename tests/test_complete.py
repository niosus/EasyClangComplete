"""Tests for autocompletion."""
import imp
import sublime
import platform
from os import path

from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin.utils import action_request
from EasyClangComplete.plugin.utils.subl import row_col
from EasyClangComplete.plugin.view_config import view_config_manager

from EasyClangComplete.tests import gui_test_wrapper

imp.reload(gui_test_wrapper)
imp.reload(row_col)
imp.reload(settings_manager)
imp.reload(view_config_manager)
imp.reload(action_request)

SettingsManager = settings_manager.SettingsManager
ActionRequest = action_request.ActionRequest
ViewConfigManager = view_config_manager.ViewConfigManager
GuiTestWrapper = gui_test_wrapper.GuiTestWrapper
ZeroIndexedRowCol = row_col.ZeroIndexedRowCol
OneIndexedRowCol = row_col.OneIndexedRowCol


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


# TODO(@kjteske): For now the tests seem to not be working for binary completer
def should_run_objc_tests():
    """Decide if Objective C tests should be run.

    For now, run only on Mac OS due to difficulties getting the GNUstep
    environment setup with GNUstep and clang to run properly in
    Windows and Linux CI's, and nearly all ObjC development is done on
    Mac OS anyway.
    """
    return platform.system() == "Darwin"


class BaseTestCompleter(object):
    """Base class for tests independent of the Completer implementation.

    Attributes:
        view (sublime.View): view
        use_libclang (bool): decides if we use libclang in tests
    """

    def set_up_completer(self):
        """Set up a completer for the current view.

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
        """Tear down completer for the current view.

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

    def test_init(self):
        """Test that the completer is properly initialized."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer = self.set_up_completer()

        self.assertIsNotNone(completer.version_str)
        self.tear_down_completer()

    def test_complete(self):
        """Test autocompletion for user type."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        cursor_row_col = ZeroIndexedRowCol.from_one_indexed(
            OneIndexedRowCol(9, 5))
        self.assertEqual(self.get_row(cursor_row_col.row), "  a.")
        location = cursor_row_col.as_1d_location(self.view)
        current_word = self.view.substr(self.view.word(location))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, location)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['foo\tvoid foo(double a)', 'foo(${1:double a})']

        self.assertIn(expected, completions)
        self.tear_down_completer()

    def test_excluded_private(self):
        """Test autocompletion for user type."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        cursor_row_col = ZeroIndexedRowCol.from_one_indexed(
            OneIndexedRowCol(9, 5))
        self.assertEqual(self.get_row(cursor_row_col.row), "  a.")
        location = cursor_row_col.as_1d_location(self.view)
        current_word = self.view.substr(self.view.word(location))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, location)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['foo\tvoid foo(double a)', 'foo(${1:double a})']
        unexpected = ['foo\tvoid foo(int a)', 'foo(${1:int a})']
        if self.use_libclang:
            self.assertIn(expected, completions)
            self.assertNotIn(unexpected, completions)
        self.tear_down_completer()

    def test_excluded_destructor(self):
        """Test autocompletion for user type."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        cursor_row_col = ZeroIndexedRowCol.from_one_indexed(
            OneIndexedRowCol(9, 5))
        self.assertEqual(self.get_row(cursor_row_col.row), "  a.")
        location = cursor_row_col.as_1d_location(self.view)
        current_word = self.view.substr(self.view.word(location))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, location)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        destructor = ['~A\tvoid ~A()', '~A()']
        if self.use_libclang:
            self.assertNotIn(destructor, completions)
        else:
            self.assertIn(destructor, completions)
        self.tear_down_completer()

    def test_complete_vector(self):
        """Test that we can complete vector members."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_vector.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        cursor_row_col = ZeroIndexedRowCol.from_one_indexed(
            OneIndexedRowCol(4, 7))
        self.assertEqual(self.get_row(cursor_row_col.row), "  vec.")
        location = cursor_row_col.as_1d_location(self.view)
        current_word = self.view.substr(self.view.word(location))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, location)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['clear\tvoid clear()', 'clear()']
        self.assertIn(expected, completions)
        self.tear_down_completer()

    def test_complete_objc_property(self):
        """Test that we can complete Objective C properties."""
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_property.m')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(6), "  foo.")
        pos = self.view.text_point(6, 6)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['boolProperty\tBOOL boolProperty', 'boolProperty']
        self.assertIn(expected, completions)
        self.tear_down_completer()

    def test_complete_objc_void_method(self):
        """Test that we can complete Objective C void methods."""
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_void_method.m')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(6), "  [foo ")
        pos = self.view.text_point(6, 7)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, " \n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['voidMethod\tvoid voidMethod', 'voidMethod']
        self.assertIn(expected, completions)
        self.tear_down_completer()

    def test_complete_objc_method_one_parameter(self):
        """Test that we can complete Objective C methods with one parameter."""
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_method_one_parameter.m')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(6), "  [foo ")
        pos = self.view.text_point(6, 7)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, " \n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['oneParameterMethod:\tvoid oneParameterMethod:(BOOL)',
                    'oneParameterMethod:${1:(BOOL)}']
        self.assertIn(expected, completions)
        self.tear_down_completer()

    def test_complete_objc_method_multiple_parameters(self):
        """Test that we can complete Objective C methods with 2+ parameters."""
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_method_two_parameters.m')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(6), "  [foo ")
        pos = self.view.text_point(6, 7)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, " \n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = [
            'bar:strParam:\tNSInteger * bar:(BOOL) strParam:(NSString *)',
            'bar:${1:(BOOL)} strParam:${2:(NSString *)}']

        self.assertIn(expected, completions)
        self.tear_down_completer()

    def test_complete_objcpp(self):
        """Test that we can complete code in Objective-C++ files."""
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_cpp.mm')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(3), "  str.")
        pos = self.view.text_point(3, 6)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        request = ActionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = [
            'clear\tvoid clear()', 'clear()']
        self.assertIn(expected, completions)
        self.tear_down_completer()

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

    def test_get_declaration_location(self):
        """Test getting declaration location."""
        if not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_location.cpp')
        self.set_up_view(file_name)

        completer = self.set_up_completer()

        # Check the current cursor position is completable.
        row = 10
        col = 15
        cursor_row_col = ZeroIndexedRowCol.from_one_indexed(
            OneIndexedRowCol(row, col))
        self.assertEqual(self.get_row(cursor_row_col.row),
                         "  cool_class.foo();")
        location = cursor_row_col.as_1d_location(self.view)
        current_word = self.view.substr(self.view.word(location))
        self.assertEqual(current_word, "foo")

        loc = completer.get_declaration_location(self.view, cursor_row_col)
        self.assertEqual(loc.file.name, file_name)
        self.assertEqual(loc.line, 3)
        self.assertEqual(loc.column, 8)

        self.tear_down_completer()


class TestBinCompleter(BaseTestCompleter, GuiTestWrapper):
    """Test class for the binary based completer."""
    use_libclang = False


if has_libclang():
    class TestLibCompleter(BaseTestCompleter, GuiTestWrapper):
        """Test class for the library based completer."""
        use_libclang = True
