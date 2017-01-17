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
    HOME = "~"


class SettingsStorage:
    """A class that stores all loaded settings.

    Attributes:
        max_cache_age (int): maximum cache age in seconds
        FLAG_SOURCES (str[]): possible flag sources
        NAMES_ENUM (str[]): all supported settings names
        PREFIXES (str[]): setting prefixes supported by this plugin
    """
    FLAG_SOURCES = ["CMakeLists.txt",
                    "compile_commands.json",
                    ".clang_complete"]
    FLAG_SOURCES_ENTRIES_WITH_PATHS = ["search_in", "prefix_paths"]
    PREFIXES = ["ecc_", "easy_clang_complete_"]

    # refer to Preferences.sublime-settings for usage explanation
    NAMES_ENUM = [
        "autocomplete_all",
        "c_flags",
        "clang_binary",
        "common_flags",
        "cpp_flags",
        "errors_on_save",
        "flags_sources",
        "hide_default_completions",
        "include_file_folder",
        "include_file_parent_folder",
        "max_cache_age",
        "triggers",
        "use_libclang",
        "verbose",
        "show_type_info",
    ]

    def __init__(self, settings_handle):
        """Initialize settings storage with default settings handle.

        Args:
            settings_handle (sublime.Settings): handle to sublime settings
        """
        self._wildcard_values = {
            Wildcards.PROJECT_PATH: "",
            Wildcards.PROJECT_NAME: "",
            Wildcards.CLANG_VERSION: "",
            Wildcards.HOME: ""
        }
        self.__load_vars_from_settings(settings_handle,
                                       project_specific=False)

    def update_from_view(self, view):
        """Update from view using view-specific settings.

        Args:
            view (sublime.View): current view
        """
        try:
            # init current and parrent folders:
            if not Tools.is_valid_view(view):
                log.error(" no view to populate common flags from")
                return
            self.__load_vars_from_settings(view.settings(),
                                           project_specific=True)
            # initialize wildcard values with view
            self.__update_widcard_values(view)
            # replace wildcards
            self.__populate_common_flags(view)
            self.__populate_flags_source_paths(view)
        except AttributeError as e:
            log.error(" view became None. Do not continue.")
            log.error(" original error: %s", e)

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
        for source_dict in self.flags_sources:
            if "file" not in source_dict:
                log.critical(" no 'file' in a flags source: %s", source_dict)
                return False
            if source_dict["file"] not in SettingsStorage.FLAG_SOURCES:
                log.critical(" flag source: '%s' is not one of '%s'!",
                             source_dict["file"], SettingsStorage.FLAG_SOURCES)
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

        # initialize max_cache_age if is it not yet, default to 30 minutes
        self.max_cache_age = getattr(self, "max_cache_age", "00:30:00")
        # get seconds from string if needed
        if isinstance(self.max_cache_age, str):
            self.max_cache_age = Tools.seconds_from_string(self.max_cache_age)

    def __populate_flags_source_paths(self, view):
        """Populate variables inside flags sources.

        Args:
            view (View): Current view.
        """
        if not self.flags_sources:
            log.critical(" Cannot update paths of flag sources.")
            return
        for idx, source_dict in enumerate(self.flags_sources):
            for option in SettingsStorage.FLAG_SOURCES_ENTRIES_WITH_PATHS:
                if option not in source_dict:
                    continue
                if not source_dict[option]:
                    continue
                if isinstance(source_dict[option], str):
                    self.flags_sources[idx][option] =\
                        self.__replace_wildcard_if_needed(source_dict[option])
                elif isinstance(source_dict[option], list):
                    for i, entry in enumerate(source_dict[option]):
                        self.flags_sources[idx][option][i] =\
                            self.__replace_wildcard_if_needed(entry)

    def __populate_common_flags(self, view):
        """Populate the variables inside common_flags with real values.

        Args:
            view (sublime.View): current view
        """
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

    def __replace_wildcard_if_needed(self, line):
        """Replace wildcards in a line if they are present there.

        Args:
            line (str): line possibly with wildcards in it

        Returns:
            str: line with replaced wildcards
        """
        res = str(line)
        # replace all wildcards in the line
        for wildcard, value in self._wildcard_values.items():
            res = re.sub(re.escape(wildcard), value, res)
            res = path.expandvars(res)
        if res != line:
            log.debug(" populated '%s' to '%s'", line, res)
        return res

    def __update_widcard_values(self, view):
        """Update values for wildcard variables."""
        from os.path import expanduser
        self._wildcard_values[Wildcards.HOME] = expanduser("~")
        variables = view.window().extract_variables()
        if 'folder' in variables:
            project_folder = variables['folder'].replace('\\', '\\\\')
            self._wildcard_values[Wildcards.PROJECT_PATH] = project_folder
        if 'project_name' in variables:
            project_name = path.splitext(variables['project_name'])[0]
            self._wildcard_values[Wildcards.PROJECT_NAME] = project_name

        # duplicate as fields
        self.project_folder = self._wildcard_values[Wildcards.PROJECT_PATH]
        self.project_name = self._wildcard_values[Wildcards.PROJECT_NAME]

        # get clang version string
        self._wildcard_values[Wildcards.CLANG_VERSION] =\
            Tools.get_clang_version_str(self.clang_binary)
        self.clang_version = self._wildcard_values[Wildcards.CLANG_VERSION]
