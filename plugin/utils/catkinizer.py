"""Catkinize the project if needed."""

import logging
from os import path

log = logging.getLogger("ECC")


class Catkinizer:
    """Catkinize the sublime project if needed.

    This is done by adding the appropriate entries to the project settings that
    ensure that 'prefix_paths' get forwarded to CMakeLists.txt properly.
    """
    _SETTINGS_TAG = 'settings'
    _FLAGS_SOURCES_TAG = 'ecc_flags_sources'

    def __init__(self, cmake_file):
        """Initialize the catkinizer with a CMakeLists.txt file."""
        self.__cmake_file = cmake_file

    def catkinize_if_needed(self):
        """Add prefix_paths setting to the project file if needed."""
        import platform
        if platform.system() != 'Linux':
            log.debug("Auto-catkinize supports only Linux currently.")
            return False
        if not self.__cmake_file.contains('find_package(catkin'):
            log.debug("Not a catkin project.")
            return False

        project_data = Catkinizer.__get_sublime_project_data()
        if not project_data:
            log.debug("Cannot auto-catkinize: not using sublime project.")
            return False

        # Check if setting exists in the project.
        if Catkinizer._SETTINGS_TAG not in project_data:
            log.debug('Creating settings tag in sublime project data.')
            project_data[Catkinizer._SETTINGS_TAG] = {}
        project_settings = project_data[Catkinizer._SETTINGS_TAG]
        if Catkinizer._FLAGS_SOURCES_TAG not in project_settings:
            log.debug('Creating flag sources tag in sublime project settings.')
            project_settings[Catkinizer._FLAGS_SOURCES_TAG] = []
        flags_sources = project_settings[Catkinizer._FLAGS_SOURCES_TAG]
        cmake_entry = Catkinizer.__get_cmake_entry(flags_sources)
        cmake_entry = self.__update_prefix_paths(cmake_entry)
        # Now save all the results to the file.
        Catkinizer.__save_sublime_project_data(project_data)
        return True

    def __get_catkin_workspace_path(self):
        """Find the catkin workspace that contains current cmake project."""
        cmake_file_path = self.__cmake_file.full_path
        # Start searching from this file on and pick a folder one above the last
        # inclusion of /src/ in the current path.
        src_pos = cmake_file_path.rfind('src/')
        if src_pos < 0:
            log.debug('We did not find src/ in path "%s"', cmake_file_path)
            return None
        catkin_workspace_path = cmake_file_path[:src_pos]
        # If the path starts in home folder, replace it to tilda to make sure we
        # can transfer the resulting project file to other systems without any
        # changes.
        catkin_workspace_path = catkin_workspace_path.replace(
            path.expanduser('~'), '~', 1)
        catkin_devel_path = path.join(catkin_workspace_path, 'devel')
        log.debug('Found catkin devel space in "%s"', catkin_devel_path)
        return catkin_devel_path

    def __update_prefix_paths(self, cmake_entry):
        """Update the prefix paths in a given cmake_entry."""
        # Add new prefix paths to the project.
        prefix_paths_tag = 'prefix_paths'
        if prefix_paths_tag not in cmake_entry:
            cmake_entry[prefix_paths_tag] = []
        prefix_paths_entry = cmake_entry[prefix_paths_tag]
        ros_path = Catkinizer.__get_ros_distro_path()
        if ros_path and ros_path not in prefix_paths_entry:
            prefix_paths_entry.append(ros_path)
        ros_ws_path = self.__get_catkin_workspace_path()
        if ros_ws_path and ros_ws_path not in prefix_paths_entry:
            prefix_paths_entry.append(ros_ws_path)
        return cmake_entry

    @staticmethod
    def __get_cmake_entry(flags_sources):
        """Get the cmake entry from flag sources dict or return a new one."""
        # Check if the setting for CMakeLists already exists within the sources.
        if flags_sources:
            for flag_source in flags_sources:
                if flag_source['file'] == 'CMakeLists.txt':
                    return flag_source
        # Nothing found, so return a new dict.
        return {}

    @staticmethod
    def __get_sublime_project_data():
        """Get the sublime project data associated to the current window."""
        import sublime
        window = sublime.active_window()
        return window.project_data()

    @staticmethod
    def __save_sublime_project_data(project_data):
        """Get the sublime project data associated to the current window."""
        import sublime
        window = sublime.active_window()
        return window.set_project_data(project_data)

    @staticmethod
    def __get_ros_distro_path(glob_path='/opt/ros/*'):
        """Find an available version of ROS.

        This only supports the classic ROS location in /opt/ folder.
        """
        import glob
        all_paths = glob.glob(glob_path)
        if not all_paths:
            log.debug('No ROS installation found in "/opt/ros/".')
            return None
        if len(all_paths) > 1:
            log.warning('More than one ROS installation found. Using first.')
        log.debug('Using ROS in "%s"', all_paths[0])
        return all_paths[0]
