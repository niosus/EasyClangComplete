"""Catkinize the project if needed."""

import logging
from os import path

log = logging.getLogger("ECC")


class Catkinizer:
    """Catkinize the sublime project if needed.

    This is done by adding the appropriate entries to the project settings that
    ensure that 'prefix_paths' get forwarded to CMakeLists.txt properly.
    """
    ROS_DISTRO_NAMES = ['melodic', 'lunar', 'kinetic', 'jade', 'indigo']

    def __init__(self, cmake_file):
        """Initialize the catkinizer with a CMakeLists.txt file."""
        self.__cmake_file = cmake_file

    def catkinize_if_needed(self):
        """Add prefix_paths setting to the project file if needed."""
        if not self.__cmake_file.contains('find_package(catkin'):
            log.debug("Not a catkin project.")
            return
        # Check if project exists (???)

        # Check if setting exists in the project.

        # Add a setting to the project.

    @staticmethod
    def __get_catkin_workspace_path(cmake_file_path):
        """Find the catkin workspace that contains current cmake project."""
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
        catkin_workspace_path.replace(path.expanduser('~'), '~', 1)
        return catkin_workspace_path

    @staticmethod
    def __get_ros_distro_path():
        """Find an available version of ROS.

        This only supports the classic ROS location in /opt/ folder.
        """
        path_template = '/opt/ros/{distro}'
        for ros_name in Catkinizer.ROS_DISTRO_NAMES:
            test_path = path_template.format(distro=ros_name)
            if path.exists(test_path):
                log.debug('Found ROS in "%s"', test_path)
                return test_path
        log.debug('Cannot find ROS in /opt/ros/')
        return None
