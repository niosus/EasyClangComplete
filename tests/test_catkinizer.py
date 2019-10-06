"""Test compilation database flags generation."""
import imp
import sublime
import platform

from os import path

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper
from EasyClangComplete.plugin.utils import catkinizer
from EasyClangComplete.plugin.utils import file
imp.reload(file)
imp.reload(catkinizer)

Catkinizer = catkinizer.Catkinizer
File = file.File


class BaseTestCatkinizer(object):
    """Test unique list."""

    def setUp(self):
        """Prepare the view and store the settings."""
        super(BaseTestCatkinizer, self).setUp()
        self.__project_data_backup = sublime.active_window().project_data()
        if not sublime.active_window().project_data():
            # Load a file and put it into current data.
            project_file = path.join(path.dirname(__file__),
                                     '..',
                                     'easy_clang_complete.sublime-project')
            import json
            with open(project_file) as f:
                project_json = json.load(f)
                sublime.active_window().set_project_data(project_json)

    def tearDown(self):
        """Restore project settings and close the view."""
        sublime.active_window().set_project_data(self.__project_data_backup)
        super(BaseTestCatkinizer, self).tearDown()

    def test_init(self):
        """Test initialization."""
        test_file = File(
            path.join(path.dirname(__file__), 'cmake_tests', 'CMakeLists.txt'))
        catkinizer = Catkinizer(test_file)
        self.assertEqual(catkinizer._Catkinizer__cmake_file.full_path,
                         test_file.full_path)

    def test_setting_getting_project_data(self):
        """Test setting and getting project data."""
        self.assertEqual(sublime.active_window().project_data(),
                         Catkinizer._Catkinizer__get_sublime_project_data())
        Catkinizer._Catkinizer__save_sublime_project_data({})
        self.assertEqual(sublime.active_window().project_data(), {})

    def test_get_ros_distro_path(self):
        """Check that we can get the paths to ros.

        Here we just check that we get the first path from a given folder."""
        cmake_tests_folder = path.join(path.dirname(__file__), 'cmake_tests')
        print(cmake_tests_folder)
        picked = Catkinizer._Catkinizer__get_ros_distro_path(
            cmake_tests_folder + '/*')
        self.assertEqual(path.dirname(picked), cmake_tests_folder)

    def test_get_cmake_entry(self):
        """Get cmake entry."""
        project_data = Catkinizer._Catkinizer__get_sublime_project_data()
        settings_entry = project_data[Catkinizer._SETTINGS_TAG]
        flags_sources = settings_entry[Catkinizer._FLAGS_SOURCES_TAG]
        cmake_entry = Catkinizer._Catkinizer__get_cmake_entry(flags_sources)
        expected_entry = {
            "file": "CMakeLists.txt",
            "flags":
                [
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-D XXXX=ON"
                ],
                "prefix_paths":
                [
                    "/opt/ros/indigo",
                    "~/Code/catkin_ws/devel",
                    "$project_base_path/catkin_ws/devel",
                ]
        }
        self.assertEqual(cmake_entry, expected_entry)

    def test_get_catkin_ws(self):
        """Test getting a catkin workspace."""
        catkin_proj_cmake_file = File(
            path.join(path.dirname(__file__),
                      'catkin_tests',
                      'catkin_ws',
                      'src',
                      'project',
                      'CMakeLists.txt'))
        catkinizer = Catkinizer(catkin_proj_cmake_file)
        ws_path = catkinizer._Catkinizer__get_catkin_workspace_path()
        catkin_ws = path.join(path.dirname(__file__),
                              'catkin_tests', 'catkin_ws', 'devel')
        catkin_ws = catkin_ws.replace(path.expanduser('~'), '~', 1)
        self.assertEqual(ws_path, catkin_ws)


print(platform.system())
if platform.system() is not 'Windows':
    class TestCatkinizer(BaseTestCatkinizer, GuiTestWrapper):
        """Test class for the binary based completer."""
        pass
