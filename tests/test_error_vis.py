"""Tests for error visualizer."""
import imp
import platform
from os import path
from collections import namedtuple

from EasyClangComplete.plugin.error_vis import popup_error_vis
from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin.settings import settings_storage
from EasyClangComplete.plugin.error_vis import popups
from EasyClangComplete.plugin.view_config import view_config_manager
from EasyClangComplete.plugin.utils import action_request
from EasyClangComplete.plugin.utils.subl import row_col

from EasyClangComplete.tests import gui_test_wrapper


imp.reload(gui_test_wrapper)
imp.reload(popup_error_vis)
imp.reload(settings_manager)
imp.reload(settings_storage)
imp.reload(view_config_manager)
imp.reload(popups)
imp.reload(action_request)
imp.reload(row_col)

ActionRequest = action_request.ActionRequest
ZeroIndexedRowCol = row_col.ZeroIndexedRowCol
OneIndexedRowCol = row_col.OneIndexedRowCol
PopupErrorVis = popup_error_vis.PopupErrorVis
GuiTestWrapper = gui_test_wrapper.GuiTestWrapper
SettingsManager = settings_manager.SettingsManager
SettingsStorage = settings_storage.SettingsStorage
ViewConfigManager = view_config_manager.ViewConfigManager
Popup = popups.Popup

test_file = namedtuple('test_file', 'name')
test_cursor = namedtuple('test_cursor', 'file line')
test_extent = namedtuple('test_extent', 'start end')


def cleanup_trailing_spaces(message):
    """We need to cleanup trailing spaces as Sublime text removes them."""
    actual_msg_array = message.split('\n')
    actual_msg_array = [s.rstrip() for s in actual_msg_array]
    return '\n'.join(actual_msg_array)


def should_run_objc_tests():
    """Decide if Objective C tests should be run.

    For now, run only on Mac OS due to difficulties getting the GNUstep
    environment setup with GNUstep and clang to run properly in
    Windows and Linux CI's, and nearly all ObjC development is done on
    Mac OS anyway.
    """
    return platform.system() == "Darwin"


class TestErrorVis:
    """Test error visualization."""

    def set_up_completer(self):
        """Set up a completer for the current view.

        Returns:
            BaseCompleter: completer for the current view.
        """
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        settings.use_libclang = self.use_libclang

        view_config = ViewConfigManager().load_for_view(self.view, settings)
        return view_config.completer, settings

    def tear_down_completer(self):
        """Tear down a completer for the current view.

        Returns:
            BaseCompleter: completer for the current view.
        """
        view_config_manager = ViewConfigManager()
        view_config_manager.clear_for_view(self.view.buffer_id())

    def test_popups_init(self):
        """Test that setup view correctly sets up the popup."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer, _ = self.set_up_completer()
        self.assertIsNotNone(completer.error_vis)
        self.assertIsNotNone(completer.error_vis.err_regions)
        self.tear_down_completer()

    def test_generate_errors(self):
        """Test that errors get correctly generated and cleared."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer, _ = self.set_up_completer()
        self.assertIsNotNone(completer.error_vis)
        err_dict = completer.error_vis.err_regions
        v_id = self.view.buffer_id()

        cursor_row_col = ZeroIndexedRowCol.from_one_indexed(
            OneIndexedRowCol(10, 3))

        self.assertTrue(v_id in err_dict)
        self.assertEqual(len(err_dict[v_id]), 1)
        self.assertIn(cursor_row_col.row, err_dict[v_id])
        self.assertEqual(len(err_dict[v_id][cursor_row_col.row]), 1)
        self.assertEqual(err_dict[v_id][cursor_row_col.row][0]['row'],
                         cursor_row_col.row)
        self.assertEqual(err_dict[v_id][cursor_row_col.row][0]['col'],
                         cursor_row_col.col)
        expected_error = "expected unqualified-id"
        self.assertIn(expected_error,
                      err_dict[v_id][cursor_row_col.row][0]['error'])

        # not clear errors:
        completer.error_vis.clear(self.view)
        err_dict = completer.error_vis.err_regions
        self.assertFalse(v_id in err_dict)

        # cleanup
        self.tear_down_completer()

    def test_get_text_by_extent_multifile(self):
        """Test getting text from multifile extent."""
        file1 = test_file('file1.c')
        file2 = test_file('file2.c')
        cursor1 = test_cursor(file1, 1)
        cursor2 = test_cursor(file2, 6)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(Popup.get_text_by_extent(ext), None)

    def test_get_text_by_extent_oneline(self):
        """Test getting text from oneline extent."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        file1 = test_file(file_name)
        cursor1 = test_cursor(file1, 8)
        cursor2 = test_cursor(file1, 8)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(Popup.get_text_by_extent(ext), '  A a;\n')

    def test_get_text_by_extent_multiline(self):
        """Test getting text from multiline extent."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        file1 = test_file(file_name)
        cursor1 = test_cursor(file1, 8)
        cursor2 = test_cursor(file1, 9)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(Popup.get_text_by_extent(ext), '  A a;\n  a.\n')

    def test_get_text_by_extent_unicode(self):
        """Test getting text from file that contains unicode."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_unicode.cpp')
        file1 = test_file(file_name)
        cursor1 = test_cursor(file1, 4)
        cursor2 = test_cursor(file1, 4)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(Popup.get_text_by_extent(ext), 'class Foo {};\n')

    def test_error(self):
        """Test getting text from multiline extent."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        _, settings = self.set_up_completer()
        settings.popup_maximum_width = 1800
        settings.popup_maximum_height = 800
        error_popup = Popup.error("error_text", settings)
        md_text = error_popup.as_markdown()
        expected_error = """\
---
allow_code_wrap: true
---
!!! panel-error "ECC: Error"
    error_text
"""
        self.assertEqual(md_text, expected_error)

    def test_warning(self):
        """Test generating a simple warning."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        _, settings = self.set_up_completer()
        settings.popup_maximum_width = 1800
        settings.popup_maximum_height = 800
        error_popup = Popup.warning("warning_text", settings)
        md_text = error_popup.as_markdown()
        expected_error = """\
---
allow_code_wrap: true
---
!!! panel-warning "ECC: Warning"
    warning_text
"""
        self.assertEqual(md_text, expected_error)

    def test_error_to_list(self):
        """Test transforming an error dict into a list."""
        error_dicts = [
            {"error": "error_1", "severity": 1},
            {"error": "error_2", "severity": 2}
        ]
        max_severity, msg_list = PopupErrorVis._as_msg_list(error_dicts)
        self.assertEqual(max_severity, 2)
        self.assertEqual(len(msg_list), 2)
        self.assertEqual(msg_list[0], "error_1")
        self.assertEqual(msg_list[1], "error_2")

    def test_info_simple(self):
        """Test that info message is generated correctly."""
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        settings.show_index_references = False
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(6),
                         "int main(int argc, char const *argv[]) {")
        pos = self.view.text_point(6, 7)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    int [main]({file}:7:5) (int argc, const char *[] argv)
""".format(file=file_name)
        self.assertEqual(info_popup.as_markdown(), expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_no_full(self):
        """Test that doxygen comments are generated correctly."""
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_info.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        settings.show_index_references = False
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(17), "  MyCoolClass cool_class;")
        pos = self.view.text_point(17, 7)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [MyCoolClass]({file}:4:7)
    ### Brief documentation:
    ```
    Class for my cool class.
    ```
    ### Body:
    ```c++
    class MyCoolClass {{
     public:
      /**
       * @brief      This is short.
       *
       *             And this is a full comment.
       *
       * @param[in]  a     param a
       * @param[in]  b     param b
       */
      void foo(int a, int b);
    }};

    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_full(self):
        """Test that the full info message is generated correctly."""
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_info.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        settings.show_index_references = False
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(18), "  cool_class.foo(2, 2);")
        pos = self.view.text_point(18, 15)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    void [foo]({file}:14:8) (int a, int b)
    ### Brief documentation:
    ```
    This is short.
    ```
    ### Full doxygen comment:
    ```
    And this is a full comment.

    @param[in]  a     param a
    @param[in]  b     param b
    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_arguments_link(self):
        """Test that the info message with arg links is generated correctly."""
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_info_arguments_link.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        settings.show_index_references = False
        cursor_row_col = ZeroIndexedRowCol.from_one_indexed(
            OneIndexedRowCol(10, 15))
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(cursor_row_col.row),
                         "  cool_class.foo(Foo(), nullptr);")
        location = cursor_row_col.as_1d_location(self.view)
        action_request = ActionRequest(self.view, location)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    void [foo]({file}:5:8) ([Foo]({file}:1:7) a, [Foo]({file}:1:7) \\* b)
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_void_method(self):
        """Test that Objective-C info message is generated correctly.

        For void method with no parameters.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(65),
                         "  [interface interfaceMethodVoidNoParameters];")
        pos = self.view.text_point(65, 14)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    -(void)[interfaceMethodVoidNoParameters]({file}:19:10)
    ### Brief documentation:
    ```
    Brief comment.
    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_method_with_unnamed_parameter(self):
        """Test that Objective-C info message is generated correctly.

        For void method with an unnamed parameter.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(69),
                         ("  [interface "
                          "interfaceMethodVoidTwoParametersSecondUnnamed"
                          ":0 :0];"))
        pos = self.view.text_point(69, 14)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    -(void)[interfaceMethodVoidTwoParametersSecondUnnamed]\
({file}:24:10):(int)int1 :(int)int2
"""
        expected_info_msg = fmt.format(file=file_name)

        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_class_method_with_return_value_and_parameters(self):
        """Test that Objective-C info message is generated correctly.

        For class method that returns an object and has two object parameters.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(
            self.get_row(70),
            "  [Interface interfaceClassMethodFooTwoFooParameters:nil "
            + "fooParam2:nil];")
        pos = self.view.text_point(70, 14)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    +([Foo *]({file}:6:8))[interfaceClassMethodFooTwoFooParameters]\
({file}:26:10):([Foo *]({file}:6:8))f1 fooParam2:([Foo *]({file}:6:8))f2
"""
        expected_info_msg = fmt.format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_protocol_method_with_doxy_brief(self):
        """Test that Objective-C info message is generated correctly.

        For a Protocol method that has a doxygen brief comment.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(73),
                         "  [interface protocolMethodVoidNoParameters];")
        pos = self.view.text_point(73, 14)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    -(void)[protocolMethodVoidNoParameters]({file}:9:10)
    ### Brief documentation:
    ```
    Has a brief comment
    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_protocol_class_method(self):
        """Test that Objective-C info message is generated correctly.

        For a Protocol class method.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(77),
                         "  [Interface protocolClassMethod];")
        pos = self.view.text_point(77, 14)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    +(void)[protocolClassMethod]({file}:14:10)
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_category_method(self):
        """Test that Objective-C info message is generated correctly.

        For a Category method.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(80),
                         "  [interface categoryMethodVoidNoParameters];")
        pos = self.view.text_point(80, 14)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    -(void)[categoryMethodVoidNoParameters]({file}:54:10)
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_instance_method_decl(self):
        """Test that Objective-C info message is generated correctly.

        For an interface/protocol/category instance method decl.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(
            self.get_row(33),
            "  -(void)interfaceMethodVoidNoParameters {}")
        pos = self.view.text_point(33, 14)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    -(void)[interfaceMethodVoidNoParameters]({file}:34:10)
    ### Brief documentation:
    ```
    Brief comment.
    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_class_method_decl(self):
        """Test that Objective-C info message is generated correctly.

        For an interface/protocol/category class method decl.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(13),
                         "  +(void)protocolClassMethod;")
        pos = self.view.text_point(13, 14)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    +(void)[protocolClassMethod]({file}:14:10)
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_protocol_ref(self):
        """Test that Objective-C info message is generated correctly.

        For a protocol reference.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(17),
                         "@interface Interface : NSObject<Protocol>")
        pos = self.view.text_point(17, 34)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [Protocol]({file}:8:11)
    ### Body:
    ```objective-c++
    @protocol Protocol
      -(void)protocolMethodVoidNoParameters; ///< Has a brief comment
      -(BOOL)protocolMethodBoolNoParameters;
      -(void)protocolMethodVoidOneStringParameter:(NSString*)s1;
      -(void)protocolMethodVoidTwoStringParameters:(NSString*)s1
        stringParam2:(NSString*)s2;
      +(void)protocolClassMethod;
      @property (assign) BOOL protocolPropertyBool;
    @end

    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_category_impl(self):
        """Test that Objective-C info message is generated correctly.

        For a category implementation.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(52),
                         "@interface Interface (Category)")
        pos = self.view.text_point(52, 2)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [Category]({file}:53:12)
    ### Body:
    ```objective-c++
    @interface Interface (Category)
      -(void)categoryMethodVoidNoParameters;
    @end

    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_implementation_decl(self):
        """Test that Objective-C info message is generated correctly.

        For an implementation declaration.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(30),
                         "@implementation Interface")
        pos = self.view.text_point(30, 18)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [Interface]({file}:18:12)
    ### Body:
    ```objective-c++
    @interface Interface : NSObject<Protocol>
      -(void)interfaceMethodVoidNoParameters; ///< Brief comment.
      -(BOOL)interfaceMethodBoolNoParameters;
      -(void)interfaceMethodVoidOneStringParameter:(NSString*)s1;
      -(void)interfaceMethodVoidTwoStringParameters:(NSString*)s1
        stringParam2:(NSString*)s2;
      -(void)interfaceMethodVoidTwoParametersSecondUnnamed:(int)int1
        :(int)int2;
      +(Foo*)interfaceClassMethodFooTwoFooParameters:(Foo*)f1
        fooParam2:(Foo*)f2;
      @property (assign) NSString* interfacePropertyString;
    @end

    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_info_objc_covariant_method(self):
        """Test Objective-C info messages for covariant types.

        Covariant types like NSArray, NSDictionary are special cases
        because they have angle brackets that need special escaping.
        """
        if not should_run_objc_tests() or not self.use_libclang:
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_objective_c_covariant.m')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(3),
                         "-(MyCovariant<Foo*>*)covariantMethod;")
        pos = self.view.text_point(3, 22)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    -([MyCovariant&lt;Foo *&gt; *]({file}:3:12))[covariantMethod]({file}:4:22)
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_template_instance_class_and_builtin_type_and_number_value(self):
        """Test template instance with class, built-in types, and number types.

        E.g. hover over 'instance' of 'TemplateClass<Foo, int, 123> instance;'
        should link to Foo and properly display int and 123.
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(8),
                         "  TemplateClass<Foo, int, 123> instanceClassTypeInt;")
        pos = self.view.text_point(8, 32)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [TemplateClass]({file}:3:7)&lt;[Foo]({file}:1:7), int, \
123&gt; [instanceClassTypeInt]({file}:9:32)
"""
        expected_info_msg = fmt.format(file=file_name)

        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_template_instance_expand_templates(self):
        """Test simple types in expansion.

        E.g. hover over 'instance' of 'TemplateClass<Foo, int, 123> instance;'
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(8),
                         "  TemplateClass<Foo, int, 123> instanceClassTypeInt;")
        pos = self.view.text_point(8, 32)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [TemplateClass]({file}:3:7)\
&lt;[Foo]({file}:1:7), int, 123&gt; \
[instanceClassTypeInt]({file}:9:32)
"""
        expected_info_msg = fmt.format(file=file_name)

        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_template_instance_default_template_params(self):
        """Test template instance with some template args left empty.

        E.g. hover over 'instance' of 'TemplateClass<Foo, int> instance;'
        where TemplateClass has an option 3rd template argument.
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(9),
                         "  TemplateClass<Foo> instanceClassAndDefaults;")
        pos = self.view.text_point(9, 22)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [TemplateClass]({file}:3:7)&lt;[Foo]({file}:1:7)&gt; \
[instanceClassAndDefaults]({file}:10:22)
"""
        expected_info_msg = fmt.format(file=file_name)

        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_template_instance_nested_template_parameters(self):
        """Test instance with template arguments that are themselves templates.

        E.g. hover over 'instance' of the line:
        'std::shared_ptr<std::vector<Foo>>> instance;'
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(10),
                         "  TemplateClass<TemplateClass<Foo>> instanceNested;")
        pos = self.view.text_point(10, 37)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [TemplateClass]({file}:3:7)&lt;[TemplateClass]({file}:3:7)&lt;\
[Foo]({file}:1:7)&gt;&gt; [instanceNested]({file}:11:37)
"""
        expected_info_msg = fmt.format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_template_instance_pointer_to_class(self):
        """Test instance with a pointer template argument.

        E.g. hover over 'instance' of the line:
        'TemplateClass<Foo*> instance;'
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(11),
                         "  TemplateClass<Foo*> instancePointer;")
        pos = self.view.text_point(11, 23)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [TemplateClass]({file}:3:7)&lt;[Foo]({file}:1:7) \\*&gt; \
[instancePointer]({file}:12:23)
"""
        expected_info_msg = fmt.format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_template_instance_ref_to_class(self):
        """Test instance with a reference template argument.

        E.g. hover over 'instance' of the line:
        'TemplateClass<Foo&> instance;'
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(12),
                         "  TemplateClass<Foo&> instanceRef;")
        pos = self.view.text_point(12, 23)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [TemplateClass]({file}:3:7)&lt;[Foo]({file}:1:7) &amp;&gt; \
[instanceRef]({file}:13:23)
"""
        expected_info_msg = fmt.format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_template_instance_rvalueref_to_class(self):
        """Test instance with an r-value reference template argument.

        E.g. hover over 'instance' of the line:
        'TemplateClass<Foo&&> instance;'
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(13),
                         "  TemplateClass<Foo&&> instanceRValueRef;")
        pos = self.view.text_point(13, 24)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [TemplateClass]({file}:3:7)&lt;[Foo &amp;&amp;]({file}:1:7)&gt; \
[instanceRValueRef]({file}:14:24)
"""
        expected_info_msg = fmt.format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_template_instance_declaration(self):
        """Hovering over the template type in a variable declaration.

        E.g. hovering over 'TemplateClass<Foo>' of the line
        'TemplateClass<Foo> instance;'
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        settings.show_index_references = False
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(8),
                         "  TemplateClass<Foo, int, 123> instanceClassTypeInt;")
        pos = self.view.text_point(8, 3)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        expected_info_msg = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    [TemplateClass]({file}:3:7)
    ### Body:
    ```c++
    template <class TClass=Foo, typename TType=int, int TInt=12>
    class TemplateClass
    {{
    public:
      void foo(TemplateClass<TClass, TType, TInt>);
    }};

    ```
""".format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()

    def test_method_with_template_argument(self):
        """Hovering over method with argument that is a template type.

        E.g. hovering over 'void foo(TemplateClass<Bar> arg)'
        """
        if not self.use_libclang:
            # Ignore this test for binary completer.
            return
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_templates.cpp')
        self.set_up_view(file_name)
        completer, settings = self.set_up_completer()
        settings.show_index_references = False
        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(14),
                         "  instanceRValueRef.foo(instanceRValueRef);")
        pos = self.view.text_point(14, 21)
        action_request = ActionRequest(self.view, pos)
        request, info_popup = completer.info(action_request, settings)
        self.maxDiff = None
        fmt = """\
---
allow_code_wrap: true
---
!!! panel-info "ECC: Info"
    ## Declaration:
    void [foo]({file}:6:8) ([TemplateClass]({file}:3:7)&lt;Foo \
&amp;&amp;, int, 12&gt;)
"""
        expected_info_msg = fmt.format(file=file_name)
        # Make sure we remove trailing spaces on the right to comply with how
        # sublime text handles this.
        actual_msg = cleanup_trailing_spaces(info_popup.as_markdown())
        self.assertEqual(actual_msg, expected_info_msg)
        # cleanup
        self.tear_down_completer()


class TestErrorVisBin(TestErrorVis, GuiTestWrapper):
    """Test class for the binary based completer."""
    use_libclang = False


class TestErrorVisLib(TestErrorVis, GuiTestWrapper):
    """Test class for the libclang based completer."""
    use_libclang = True
