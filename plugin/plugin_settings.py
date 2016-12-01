"""This module encapsulates communication with sublime settings

Attributes:
    log (logging.Logger): logger
"""
import sublime
import logging
import re

import os.path as path
import os

from .tools import PKG_NAME
from .tools import Tools

log = logging.getLogger(__name__)
log.debug(" reloading module")


class Settings:

    """ Encapsulates sublime settings

    Attributes:
        CMAKE_PRIORITIES (list): possible priorities for generating
            .clang_complete file
        max_tu_age (int): lifetime of any translation unit in seconds
        NAMES_ENUM (list): list of all setting names of this plugin
        PREFIXES (list): prefixes to be used in project specific settings
        project_base_folder (str): root folder of current project
        project_base_name (str): name of the current project
        subl_settings (sublime.settings): link to sublime text settings dict
    """
    CMAKE_PRIORITIES = ["ask", "merge", "overwrite", "keep_old"]
    PREFIXES = ["ecc_", "easy_clang_complete_"]

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
        "copy_to_clipboard"
    ]

    __change_listeners = []

    def __init__(self):
        """Initialize the class.
        """
        self.load_settings()
        if not self.is_valid():
            log.critical(" Could not load settings!")
            log.critical(" NO AUTOCOMPLETE WILL BE AVAILABLE")
            return

    def add_change_listener(self, listener):
        """Registers given listener to be notified whenever settings change.

        Args:
            listener (function): function to call on settings change
        """
        if listener in self.__change_listeners:
            log.error(' this settings listener was already added before')
        self.__change_listeners.append(listener)

    def on_settings_changed(self):
        """When user changes settings, trigger this.
        """
        self.load_settings()
        for listener in self.__change_listeners:
            listener()
        log.info(" settings changed and reloaded")

    def load_settings(self):
        """ Load settings from sublime dictionary to internal variables
        """
        self.subl_settings = sublime.load_settings(
            PKG_NAME + ".sublime-settings")
        self.__load_vars_from_settings(self.subl_settings)

        self.subl_settings.clear_on_change(PKG_NAME)
        self.subl_settings.add_on_change(PKG_NAME, self.on_settings_changed)

        self.project_base_name = ""
        self.project_base_folder = ""
        variables = sublime.active_window().extract_variables()
        if 'folder' in variables:
            self.project_base_folder = variables['folder']
        if 'project_base_name' in variables:
            self.project_base_name = variables['project_base_name']

        # override nessesary settings from projects
        self.__update_settings_from_project_if_needed()

    def __update_settings_from_project_if_needed(self):
        """ Get clang flags for the current project

        Returns:
            list(str): flags for clang, None if no project found
        """
        log.debug(" Overriding settings by project ones if needed:")
        log.debug(" Valid prefixes: %s", Settings.PREFIXES)
        settings_handle = sublime.active_window().active_view().settings()
        self.__load_vars_from_settings(settings_handle, project_specific=True)
        log.debug(" All overrides applied.")

    def __load_vars_from_settings(self, settings, project_specific=False):
        """
        Load all settings and add them as attributes of self

        Args:
            settings (dict): settings from sublime
            prefixes (list, optional): package-specific prefixes to
                disambiguate settings when loading them from project settings

        """
        log.debug(" Reading settings...")
        # project settings are all prefixed to disambiguate them from others
        if project_specific:
            prefixes = Settings.PREFIXES
        else:
            prefixes = [""]
        for setting_name in Settings.NAMES_ENUM:
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

        # process some special settings
        if isinstance(self.max_tu_age, str):
            self.max_tu_age = Tools.seconds_from_string(self.max_tu_age)

    def is_valid(self):
        """Check settings validity. If any of the settings is None the settings
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
        if self.cmake_flags_priority not in Settings.CMAKE_PRIORITIES:
            log.critical(" priority: '%s' is not one of allowed ones!",
                         self.cmake_flags_priority)
            return False
        return True

    def populate_common_flags(self, view):
        """ Populate the variables inside common_flags with real values

        Args:
            view (sublime.View): current view

        Returns:
            str[]: clang common flags with variables expanded

        """
        # init folders needed:
        file_current_folder = path.dirname(view.file_name())
        file_parent_folder = path.dirname(file_current_folder)

        log.debug(" populating common_flags with current variables:")
        log.debug(" project_base_name = %s", self.project_base_name)
        log.debug(" project_base_folder = %s", self.project_base_folder)
        log.debug(" file_parent_folder = %s", file_parent_folder)

        clang_ver_number_str = Tools.get_clang_version_str(self.clang_binary)

        # populate variables to real values
        common_flags = []
        for flag in self.common_flags:
            flag = re.sub(r"\$project_base_path",
                          self.project_base_folder.replace('\\', '\\\\'), flag)
            flag = re.sub(r"\$project_name",
                          self.project_base_name.replace('\\', '\\\\'), flag)
            flag = re.sub(r"\$clang_version", clang_ver_number_str, flag)
            common_flags.append(flag)

        if self.include_file_folder:
            common_flags.append("-I" + file_current_folder)
        if self.include_file_parent_folder:
            common_flags.append("-I" + file_parent_folder)

        return common_flags
