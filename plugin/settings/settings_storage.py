""" Holds a class that encapsulates plugin settings

Attributes:
    log (logging.Logger): logger for this module
"""
import sublime
import logging
import re

from os import path

from ..tools import Tools

log = logging.getLogger(__name__)
log.debug(" reloading module %s", __name__)


class Wildcards:
    """ Enum class of supported wildcards

    Attributes:
        CLANG_VERSION (str): Description
        PROJECT_NAME (str): Description
        PROJECT_PATH (str): Description
    """
    PROJECT_PATH = "$project_base_path"
    PROJECT_NAME = "$project_name"
    CLANG_VERSION = "$clang_version"


class SettingsStorage:
    """ A class that stores all loaded settings

    Attributes:
        CMAKE_PRIORITIES (str[]): possible cmake properties
        max_tu_age (int): maximum TU age in seconds
        NAMES_ENUM (str[]): all supported settings names
        PREFIXES (str[]): setting prefixes supported by this plugin
    """
    CMAKE_PRIORITIES = ["ask", "merge", "overwrite", "keep_old"]
    PREFIXES = ["ecc_", "easy_clang_complete_"]

    _wildcard_values = {
        Wildcards.PROJECT_PATH: "",
        Wildcards.PROJECT_NAME: "",
        Wildcards.CLANG_VERSION: ""
    }

    # refer to Preferences.sublime-settings for usage explanation
    NAMES_ENUM = [
        "autocomplete_all",
        "c_flags",
        "clang_binary",
        "cmake_flags_priority",
        "cmake_prefix_paths",
        "common_flags",
        "cpp_flags",
        "errors_on_save",
        "generate_flags_with_cmake",
        "hide_default_completions",
        "include_file_folder",
        "include_file_parent_folder",
        "max_tu_age",
        "search_clang_complete_file",
        "triggers",
        "use_libclang",
        "verbose",
    ]

    def __init__(self, settings_handle):
        """ Initialize settings storage with default settings handle

        Args:
            settings_handle (sublime.Settings): handle to sublime settings
        """
        self.__load_vars_from_settings(settings_handle, project_specific=False)

    def update_from_view(self, view):
        """ Update from view using view-specific settings

        Args:
            view (sublime.View): current view
        """
        self.__populate_common_flags(view)
        self.__load_vars_from_settings(view.settings(), project_specific=True)

    def is_valid(self):
        """ Check settings validity. If any of the settings is None the settings
        are not valid.

        Returns:
            bool: validity of settings
        """
        for key, value in self.__dict__.items():
            if key.startswith('__') or callable(key):
                continue
            if value is None:
                log.critical(" no setting '%s' found!", key)
                return False
        if self.cmake_flags_priority not in SettingsStorage.CMAKE_PRIORITIES:
            log.critical(" priority: '%s' is not one of allowed ones!",
                         self.cmake_flags_priority)
            return False
        return True

    def __load_vars_from_settings(self, settings, project_specific=False):
        """ Load all settings and add them as attributes of self

        Args:
            settings (dict): settings from sublime
            project_specific (bool, optional): Description

        Deleted Parameters:
            prefixes (list, optional): package-specific prefixes to
                disambiguate settings when loading them from project settings

        """
        if project_specific:
            log.debug(" Overriding settings by project ones if needed:")
            log.debug(" Valid prefixes: %s", SettingsStorage.PREFIXES)
        log.debug(" Reading settings...")
        # project settings are all prefixed to disambiguate them from others
        if project_specific:
            prefixes = SettingsStorage.PREFIXES
        else:
            prefixes = [""]
        for setting_name in SettingsStorage.NAMES_ENUM:
            for prefix in prefixes:
                val = settings.get(prefix + setting_name)
                if val is not None:
                    # we don't want to override existing setting
                    break
            if val is not None:
                # set this value to this object too
                setattr(self, setting_name, val)
                # tell the user what we have done
                log.debug("  %-26s <-- '%s'", setting_name, val)
        log.debug(" Settings sucessfully read...")

        # initialize max_tu_age if is it not yet, default to 30 minutes
        self.max_tu_age = getattr(self, "max_tu_age", "00:30:00")
        # get seconds from string if needed
        if isinstance(self.max_tu_age, str):
            self.max_tu_age = Tools.seconds_from_string(self.max_tu_age)

    def __populate_common_flags(self, view):
        """ Populate the variables inside common_flags with real values

        Args:
            view (sublime.View): current view

        Returns:
            str[]: clang common flags with variables expanded

        """
        # init current and parrent folders:
        if not view.file_name():
            log.error(" no view to populate common flags from")
            return
        file_current_folder = path.dirname(view.file_name())
        file_parent_folder = path.dirname(file_current_folder)

        # init wildcard variables
        self.__update_widcard_values()

        # populate variables to real values
        log.debug(" populating common_flags with current variables.")
        for idx, flag in enumerate(self.common_flags):
            self.common_flags[idx] = self.__replace_wildcard_if_needed(flag)

        if self.include_file_folder:
            self.common_flags.append("-I" + file_current_folder)
        if self.include_file_parent_folder:
            self.common_flags.append("-I" + file_parent_folder)

    def __replace_wildcard_if_needed(self, flag):
        """ Replace wildcards in a flag if they are present there

        Args:
            flag (str): flag possibly with wildcards in it

        Returns:
            str: flag with replaced wildcards
        """
        for wildcard, value in self._wildcard_values.items():
            res = re.sub(re.escape(wildcard), value, flag)
            if res != flag:
                log.debug(" populating '%s': '%s'", wildcard, res)
                return res
        return flag

    def __update_widcard_values(self):
        """ Update values for wildcard variables
        """
        variables = sublime.active_window().extract_variables()
        if 'folder' in variables:
            project_folder = variables['folder'].replace('\\', '\\\\')
            self._wildcard_values[Wildcards.PROJECT_PATH] = project_folder
        if 'project_base_name' in variables:
            project_name = variables['project_base_name'].replace('\\', '\\\\')
            self._wildcard_values[Wildcards.PROJECT_NAME] = project_name

        # duplicate as fields
        self.project_base_folder = self._wildcard_values[Wildcards.PROJECT_PATH]
        self.project_base_name = self._wildcard_values[Wildcards.PROJECT_NAME]

        # get clang version string
        self._wildcard_values[Wildcards.CLANG_VERSION] =\
            Tools.get_clang_version_str(self.clang_binary)