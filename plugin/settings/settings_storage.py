"""Holds a class that encapsulates plugin settings.

Attributes:
    log (logging.Logger): logger for this module
"""
import logging
import re

from os import path

from ..tools import Tools

log = logging.getLogger(__name__)
log.debug(" reloading module %s", __name__)


class Wildcards:
    """Enum class of supported wildcards.

    Attributes:
        CLANG_VERSION (str): a wildcard to be replaced with a clang version
        PROJECT_NAME (str): a wildcard to be replaced by the project name
        PROJECT_PATH (str): a wildcard to be replaced by the project path
    """
    PROJECT_PATH = "$project_base_path"
    PROJECT_NAME = "$project_name"
    CLANG_VERSION = "$clang_version"


class SettingsStorage:
    """A class that stores all loaded settings.

    Attributes:
        max_tu_age (int): maximum TU age in seconds
        FLAG_SOURCES (str[]): possible flag sources
        NAMES_ENUM (str[]): all supported settings names
        PREFIXES (str[]): setting prefixes supported by this plugin
    """
    FLAG_SOURCES = ["cmake", "compilation_db", "clang_complete_file"]
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
        "cmake_prefix_paths",
        "common_flags",
        "cpp_flags",
        "errors_on_save",
        "flags_sources",
        "hide_default_completions",
        "include_file_folder",
        "include_file_parent_folder",
        "max_tu_age",
        "triggers",
        "use_libclang",
        "verbose",
    ]

    def __init__(self, settings_handle):
        """Initialize settings storage with default settings handle.

        Args:
            settings_handle (sublime.Settings): handle to sublime settings
        """
        self.__load_vars_from_settings(settings_handle,
                                       project_specific=False)

    def update_from_view(self, view):
        """Update from view using view-specific settings.

        Args:
            view (sublime.View): current view
        """
        self.__load_vars_from_settings(view.settings(), project_specific=True)
        self.__populate_common_flags(view)

    def is_valid(self):
        """Check settings validity.

        If any of the settings is None the settings are not valid.

        Returns:
            bool: validity of settings
        """
        for key, value in self.__dict__.items():
            if key.startswith('__') or callable(key):
                continue
            if value is None:
                log.critical(" no setting '%s' found!", key)
                return False
        for source in self.flags_sources:
            if source not in SettingsStorage.FLAG_SOURCES:
                log.critical(" flag source: '%s' is not one of '%s'!",
                             source, SettingsStorage.FLAG_SOURCES)
                return False
        return True

    def __load_vars_from_settings(self, settings, project_specific=False):
        """Load all settings and add them as attributes of self.

        Args:
            settings (dict): settings from sublime
            project_specific (bool, optional): defines if the settings are
                project-specific and should be read with appropriate prefixes
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
        """Populate the variables inside common_flags with real values.

        Args:
            view (sublime.View): current view
        """
        # init current and parrent folders:
        if not view.file_name():
            log.error(" no view to populate common flags from")
            return

        # init wildcard variables
        self.__update_widcard_values(view)

        # populate variables to real values
        log.debug(" populating common_flags with current variables.")
        for idx, flag in enumerate(self.common_flags):
            self.common_flags[idx] = self.__replace_wildcard_if_needed(flag)

        file_current_folder = path.dirname(view.file_name())
        if self.include_file_folder:
            self.common_flags.append("-I" + file_current_folder)
        file_parent_folder = path.dirname(file_current_folder)
        if self.include_file_parent_folder:
            self.common_flags.append("-I" + file_parent_folder)

    def __replace_wildcard_if_needed(self, flag):
        """Replace wildcards in a flag if they are present there.

        Args:
            flag (str): flag possibly with wildcards in it

        Returns:
            str: flag with replaced wildcards
        """
        # create a copy of a flag
        res = str(flag)
        # replace all wildcards in the flag
        for wildcard, value in self._wildcard_values.items():
            res = re.sub(re.escape(wildcard), value, res)
        if res != flag:
            log.debug(" populated '%s' to '%s'", flag, res)
        return res

    def __update_widcard_values(self, view):
        """Update values for wildcard variables."""
        variables = view.window().extract_variables()
        if 'folder' in variables:
            project_folder = variables['folder'].replace('\\', '\\\\')
            self._wildcard_values[Wildcards.PROJECT_PATH] = project_folder
        if 'project_name' in variables:
            project_name = variables['project_name'].replace('\\', '\\\\')
            self._wildcard_values[Wildcards.PROJECT_NAME] = project_name

        # duplicate as fields
        self.project_folder = self._wildcard_values[Wildcards.PROJECT_PATH]
        self.project_name = self._wildcard_values[Wildcards.PROJECT_NAME]

        # get clang version string
        self._wildcard_values[Wildcards.CLANG_VERSION] =\
            Tools.get_clang_version_str(self.clang_binary)
