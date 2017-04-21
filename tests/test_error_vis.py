"""Tests for error visualizer."""
import imp
from os import path

from EasyClangComplete.plugin.error_vis import popup_error_vis
from EasyClangComplete.plugin.error_vis import phantom_error_vis
from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin import view_config

from EasyClangComplete.tests import gui_test_wrapper

imp.reload(gui_test_wrapper)
imp.reload(popup_error_vis)
imp.reload(phantom_error_vis)
imp.reload(settings_manager)
imp.reload(view_config)

PopupErrorVis = popup_error_vis.PopupErrorVis
PhantomErrorVis = phantom_error_vis.PhantomErrorVis
GuiTestWrapper = gui_test_wrapper.GuiTestWrapper
SettingsManager = settings_manager.SettingsManager
ViewConfigManager = view_config.ViewConfigManager

PHANTOMS = "phantoms"
POPUPS = "popups"


class TestErrorVis:
    """Test error visualization."""

    def set_up_completer(self, error_style):
        """Utility method to set up a completer for the current view.

        Returns:
            BaseCompleter: completer for the current view.
        """
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        settings.use_libclang = self.use_libclang

        settings.show_phantoms_for_errors = bool(error_style == PHANTOMS)

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

    def test_phantoms_init(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer = self.set_up_completer(PHANTOMS)
        completer.error_vis.err_regions = {}
        self.assertIsNotNone(completer.error_vis)
        self.assertTrue(isinstance(completer.error_vis, PhantomErrorVis))
        self.tear_down_completer()
        self.tear_down()

    def test_popups_init(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer = self.set_up_completer(POPUPS)
        self.assertIsNotNone(completer.error_vis)
        self.assertTrue(isinstance(completer.error_vis, PopupErrorVis))
        self.tear_down_completer()
        self.tear_down()

    def test_generate_errors(self):
        """Test that setup view correctly sets up the view."""
        for err_type in [PHANTOMS, POPUPS]:
            file_name = path.join(path.dirname(__file__),
                                  'test_files',
                                  'test.cpp')
            self.set_up_view(file_name)
            completer = self.set_up_completer(err_type)
            self.assertIsNotNone(completer.error_vis)
            err_dict = completer.error_vis.err_regions
            v_id = self.view.buffer_id()
            self.assertTrue(v_id in err_dict)
            self.assertEqual(len(err_dict[v_id]), 1)
            self.assertTrue(10 in err_dict[v_id])
            self.assertEqual(len(err_dict[v_id][10]), 1)
            self.assertEqual(err_dict[v_id][10][0]['row'], '10')
            self.assertEqual(err_dict[v_id][10][0]['col'], '3')
            expected_error = "expected unqualified-id"
            self.assertTrue(expected_error in err_dict[v_id][10][0]['error'])

            self.tear_down_completer()
            self.tear_down()

    def test_show_phantoms(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer = self.set_up_completer(PHANTOMS)
        self.assertIsNotNone(completer.error_vis)
        phantom_sets = completer.error_vis.phantom_sets
        v_id = self.view.buffer_id()
        self.assertTrue(v_id in phantom_sets)
        self.tear_down_completer()
        self.tear_down()


class TestErrorVisBin(TestErrorVis, GuiTestWrapper):
    """Test class for the binary based completer."""
    use_libclang = False


class TestErrorVisLib(TestErrorVis, GuiTestWrapper):
    """Test class for the binary based completer."""
    use_libclang = True
