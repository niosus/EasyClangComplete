"""Holds a class that encapsulates plugin settings.

Attributes:
    log (logging.Logger): logger for this module
"""
import logging

from ..utils.tools import Tools
from ..utils.file import File
from ..utils.flag import Flag
from ..utils.clang_utils import ClangUtils
from ..utils.subl.subl_bridge import SublBridge

log = logging.getLogger("ECC")


class Wildcards:
    """Enum class of supported wildcards.

    Attributes:
        CLANG_VERSION (str): a wildcard to be replaced with a clang version
        PROJECT_NAME (str): a wildcard to be replaced by the project name
        PROJECT_PATH (str): a wildcard to be replaced by the project path
    """
    PROJECT_PATH = "project_base_path"
    PROJECT_NAME = "project_name"
    CLANG_VERSION = "clang_version"
    HOME_PATH = "~"


class SettingsStorage:
    """A class that stores all loaded settings.

    Attributes:
        max_cache_age (int): maximum cache age in seconds
        FLAG_SOURCES (str[]): possible flag sources
        NAMES_ENUM (str[]): all supported settings names
        PREFIXES (str[]): setting prefixes supported by this plugin
    """
    FLAG_SOURCES = ["CMakeLists.txt",
                    "Makefile",
                    "compile_commands.json",
                    "CppProperties.json",
                    "c_cpp_properties.json",
                    ".clang_complete"]

    SEARCH_IN_TAG = "search_in"
    PREFIX_PATHS_TAG = "prefix_paths"
    FLAGS_TAG = "flags"
    FILE_TAG = "file"
    FLAG_SOURCES_ENTRIES_WITH_PATHS = [SEARCH_IN_TAG,
                                       PREFIX_PATHS_TAG,
                                       FLAGS_TAG]

    PREFIXES = ["ecc_", "easy_clang_complete_"]

    COLOR_SUBLIME_STYLE_TAG = "ColorSublime"
    MOON_STYLE_TAG = "Moon"
    NONE_STYLE_TAG = "None"

    PROGRESS_STYLES = [COLOR_SUBLIME_STYLE_TAG, MOON_STYLE_TAG, NONE_STYLE_TAG]

    GUTTER_COLOR_STYLE = "color"
    GUTTER_MONO_STYLE = "mono"
    GUTTER_DOT_STYLE = "dot"
    NONE_STYLE = "none"

    GUTTER_STYLES = [GUTTER_COLOR_STYLE,
                     GUTTER_MONO_STYLE,
                     GUTTER_DOT_STYLE,
                     NONE_STYLE]

    MARK_STYLE_OUTLINE = "outline"
    MARK_STYLE_FILL = "fill"
    MARK_STYLE_SOLID_UNDERLINE = "solid_underline"
    MARK_STYLE_STIPPLED_UNDERLINE = "stippled_underline"
    MARK_STYLE_SQUIGGLY_UNDERLINE = "squiggly_underline"
    MARK_STYLE_NONE = "none"

    LINTER_MARK_STYLES = [MARK_STYLE_OUTLINE,
                          MARK_STYLE_FILL,
                          MARK_STYLE_SOLID_UNDERLINE,
                          MARK_STYLE_STIPPLED_UNDERLINE,
                          MARK_STYLE_SQUIGGLY_UNDERLINE,
                          MARK_STYLE_NONE]

    # refer to Preferences.sublime-settings for usage explanation
    NAMES_ENUM = [
        "autocomplete_all",
        "clang_binary",
        "cmake_binary",
        "common_flags",
        "flags_sources",
        "force_unix_includes",
        "gutter_style",
        "header_to_source_mapping",
        "hide_default_completions",
        "ignore_flags",
        "ignore_list",
        "lang_flags",
        "lazy_flag_parsing",
        "libclang_path",
        "linter_mark_style",
        "max_cache_age",
        "popup_maximum_height",
        "popup_maximum_width",
        "progress_style",
        "show_errors",
        "show_index_references",
        "show_type_body",
        "show_type_info",
        "target_compilers",
        "triggers",
        "use_default_definitions",
        "use_default_includes",
        "use_libclang",
        "use_libclang_caching",
        "valid_lang_syntaxes",
        "verbose",
    ]

    def __init__(self, settings_handle):
        """Initialize settings storage with default settings handle.

        Args:
            settings_handle (sublime.Settings): handle to sublime settings
        """
        log.debug("creating new settings storage object")
        self.clang_version = ''
        self.libclang_path = ''
        self.clang_binary = ''
        self.cmake_binary = ''
        self.project_folder = ''
        self.project_name = ''
        self._wildcard_values = {}
        self.__load_vars_from_settings(settings_handle,
                                       project_specific=False)

    def update_from_view(self, view, project_specific=True):
        """Update from view using view-specific settings.

        Args:
            view (sublime.View): current view
        """
        try:
            # Init current and parent folders.
            if not SublBridge.is_valid_view(view):
                log.error("no view to populate common flags from")
                return
            self.__load_vars_from_settings(view.settings(),
                                           project_specific=project_specific)
            # Initialize wildcard values with view.
            self.__update_wildcard_values(view)
            # Replace wildcards in various paths.
            self.__populate_common_flags()
            self.__populate_flags_source_paths()
            if not self.__expand_setting(self.ignore_list):
                log.critical("Cannot expand ignore_list")
            if not self.__expand_setting(self.ignore_flags):
                log.critical("Cannot expand ignore_flags")
            if not self.__expand_setting(self.header_to_source_mapping):
                log.critical("Cannot expand header_to_source_mapping")
            self.libclang_path = self.__replace_wildcard_if_needed(
                self.libclang_path)[0]
            self.clang_binary = self.__replace_wildcard_if_needed(
                self.clang_binary)[0]
            self.cmake_binary = self.__replace_wildcard_if_needed(
                self.cmake_binary)[0]
        except AttributeError as e:
            log.error("view became None. Do not continue.")
            log.error("original error: %s", e)

    def need_reparse(self):
        """Define a very hacky check that there was an incomplete load.

        This is needed because of something I believe is a bug in sublime text
        plugin handling. When we enable the plugin and load its settings with
        on_plugin_loaded() function not all settings are active.
        'progress_style' is one of the missing settings. The settings will
        just need to be loaded at a later time then.

        Returns:
            bool: True if needs reparsing, False otherwise

        """
        if 'progress_style' in self.__dict__:
            log.debug('settings complete')
            return False
        log.debug('settings incomplete and will be reloaded a bit later')
        return True

    def is_valid(self):
        """Check settings validity.

        If any of the settings is None the settings are not valid.

        Returns:
            (bool, str): validity of settings + error message.
        """
        error_msg = ""
        for key, value in self.__dict__.items():
            if key.startswith('__') or callable(key):
                continue
            if value is None:
                error_msg = "No value for setting '{}' found!".format(key)
                return False, error_msg

        if self.progress_style not in SettingsStorage.PROGRESS_STYLES:
            error_msg = "Progress style '{}' is not one of {}".format(
                self.progress_style, SettingsStorage.PROGRESS_STYLES)
            return False, error_msg
        if self.gutter_style not in SettingsStorage.GUTTER_STYLES:
            error_msg = "Gutter style '{}' is not one of {}".format(
                self.gutter_style, SettingsStorage.GUTTER_STYLES)
            return False, error_msg
        if self.linter_mark_style not in SettingsStorage.LINTER_MARK_STYLES:
            error_msg = "Linter mark style '{}' is not one of {}".format(
                self.linter_mark_style, SettingsStorage.LINTER_MARK_STYLES)
            return False, error_msg
        flags_sources_valid, error_msg = self.__flag_sources_are_valid()
        if not flags_sources_valid:
            return False, error_msg
        lang_tags_valid, error_msg = self.__are_language_tags_valid()
        if not lang_tags_valid:
            return False, error_msg
        return True, None

    def __flag_sources_are_valid(self):
        """Check that flag sources are valid."""
        for source_dict in self.flags_sources:
            if SettingsStorage.FILE_TAG not in source_dict:
                error_msg = "No '%s' setting in a flags source '{}'".format(
                    SettingsStorage.FILE_TAG,
                    source_dict)
                return False, error_msg
            if source_dict[SettingsStorage.FILE_TAG] not in \
                    SettingsStorage.FLAG_SOURCES:
                error_msg = "flag source '{}' is not one of {}".format(
                    source_dict[SettingsStorage.FILE_TAG],
                    SettingsStorage.FLAG_SOURCES)
                return False, error_msg
        return True, None

    def __are_language_tags_valid(self):
        """Check that language tags are valid."""
        for lang_tag in SublBridge.LANG_TAGS:
            if lang_tag not in self.lang_flags.keys():
                error_msg = "lang '{}' is not in {}".format(
                    lang_tag, self.lang_flags)
                return False, error_msg
            if lang_tag not in self.valid_lang_syntaxes:
                error_msg = "No '{}' in syntaxes '{}'".format(
                    lang_tag, self.valid_lang_syntaxes)
                return False, error_msg
            if lang_tag not in self.target_compilers:
                error_msg = "No '{}' in syntaxes '{}'".format(
                    lang_tag, self.target_compilers)
                return False, error_msg
        return True, None

    def __load_vars_from_settings(self, settings, project_specific=False):
        """Load all settings and add them as attributes of self.

        Args:
            settings (dict): settings from sublime
            project_specific (bool, optional): defines if the settings are
                project-specific and should be read with appropriate prefixes
        """
        if project_specific:
            log.debug("Overriding settings by project ones if needed:")
            log.debug("Valid prefixes: %s", SettingsStorage.PREFIXES)
        log.debug("Reading settings...")
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
                log.debug("%-26s <-- '%s'", setting_name, val)
        log.debug("Settings sucessfully read...")

        # initialize max_cache_age if is it not yet, default to 30 minutes
        self.max_cache_age = getattr(self, "max_cache_age", "00:30:00")
        # get seconds from string if needed
        if isinstance(self.max_cache_age, str):
            self.max_cache_age = Tools.seconds_from_string(self.max_cache_age)

    def __populate_flags_source_paths(self):
        """Populate variables inside flags sources."""
        def expand_paths_in_flags_if_needed(flags):
            """Expand paths in flags if they are present."""
            from os import path
            new_flags = []
            for flag in flags:
                if '=' not in flag:
                    new_flags.append(flag)
                split_flag = flag.split('=')
                prefix = split_flag[0].strip()
                value = split_flag[1].strip()
                expanded_values = self.__replace_wildcard_if_needed(
                    value)
                if not expanded_values:
                    continue
                joined_values = ';'.join(expanded_values)
                if path.isabs(expanded_values[0]):
                    new_flags.append(
                        prefix + '="' + joined_values + '"')
                else:
                    new_flags.append(prefix + '=' + joined_values)
            return new_flags

        if not self.flags_sources:
            log.critical(" Cannot update paths of flag sources.")
            return
        for idx, source_dict in enumerate(self.flags_sources):
            for option in SettingsStorage.FLAG_SOURCES_ENTRIES_WITH_PATHS:
                if option not in source_dict:
                    continue
                if not source_dict[option]:
                    continue
                if option == SettingsStorage.FLAGS_TAG:
                    source_dict[option] = expand_paths_in_flags_if_needed(
                        source_dict[option])
                else:
                    source_dict[option] = self.__replace_wildcard_if_needed(
                        source_dict[option])

    def __populate_common_flags(self):
        """Populate the variables inside common_flags with real values."""
        log.debug("Populating common_flags with current variables.")
        new_common_flags = []
        for raw_flag_str in self.common_flags:
            new_common_flags += Flag.Builder()\
                .from_unparsed_string(raw_flag_str).build_with_expansion(
                    wildcard_values=self._wildcard_values,
                    current_folder=self.project_folder)
        self.common_flags = new_common_flags

    def __expand_setting(self, setting):
        """Populate variables inside of the ignore list."""
        if not setting:
            return False
        self.ignore_list = self.__replace_wildcard_if_needed(
            query=self.ignore_list,
            expand_globbing=False)
        return True

    def __replace_wildcard_if_needed(self, query, expand_globbing=True):
        if isinstance(query, str):
            return self.__replace_wildcard_if_needed([query])
        if not isinstance(query, list):
            log.critical("We can only update wildcards in a list!")
            return None
        result = []
        for query_path in query:
            result += File.expand_all(input_path=query_path,
                                      wildcard_values=self._wildcard_values,
                                      expand_globbing=expand_globbing)
        return result

    def __update_wildcard_values(self, view):
        """Update values for wildcard variables."""
        variables = view.window().extract_variables()
        self._wildcard_values.update(variables)

        self._wildcard_values[Wildcards.PROJECT_PATH] = \
            variables.get("folder", "").replace("\\", "\\\\")

        self._wildcard_values[Wildcards.PROJECT_NAME] = \
            variables.get("project_base_name", "")

        # We need to expand clang binary path *before* we set all wildcards.
        self.clang_binary = self.__replace_wildcard_if_needed(
            query=self.clang_binary,
            expand_globbing=False)[0]
        # get clang version string
        version_str = ClangUtils.get_clang_version_str(self.clang_binary)
        self._wildcard_values[Wildcards.CLANG_VERSION] = version_str

        # duplicate as fields
        self.project_folder = self._wildcard_values[Wildcards.PROJECT_PATH]
        self.project_name = self._wildcard_values[Wildcards.PROJECT_NAME]
        self.clang_version = self._wildcard_values[Wildcards.CLANG_VERSION]
