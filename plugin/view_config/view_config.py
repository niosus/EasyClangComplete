"""A module that stores classes related ot view configuration.

Attributes:
    log (logging.Logger): Logger for this module.
"""
import time
import logging
from os import path

from ..utils.file import File
from ..utils.subl.subl_bridge import SublBridge

from ..utils.flag import Flag
from ..utils.unique_list import UniqueList
from ..utils.search_scope import ListSearchScope
from ..utils.search_scope import TreeSearchScope

from ..completion import lib_complete
from ..completion import bin_complete

from ..error_vis.popup_error_vis import PopupErrorVis

from ..flags_sources.flags_file import FlagsFile
from ..flags_sources.cmake_file import CMakeFile
from ..flags_sources.makefile import Makefile
from ..flags_sources.c_cpp_properties import CCppProperties
from ..flags_sources.CppProperties import CppProperties
from ..flags_sources.compilation_db import CompilationDb
from ..settings.settings_storage import SettingsStorage

log = logging.getLogger("ECC")

TOO_MANY_STD_FLAGS_ERROR_MSG = """
Your {which_settings} define too many std flags:
{std_flags}

Please fix your settings.
"""


class ViewConfig(object):
    """A bundle representing a view configuration.

    Stores everything needed to perform completion tasks on a given view with
    given settings.
    """

    def __init__(self, view, settings):
        """Initialize a view configuration.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.
        """
        # initialize with nothing
        self.completer = None
        if not SublBridge.is_valid_view(view):
            return

        # init creation time
        self.__last_usage_time = time.time()

        # set up a proper object
        completer, flags, include_folders = ViewConfig.__generate_essentials(
            view, settings)
        if not completer:
            log.warning(" could not generate completer for view %s",
                        view.buffer_id())
            return

        self.completer = completer
        self.completer.clang_flags = flags
        self.completer.update(view, settings)
        self.include_folders = include_folders

    def update_if_needed(self, view, settings):
        """Check if the view config has changed.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.

        Returns:
            ViewConfig: Current view config, updated if needed.
        """
        # update usage time
        self.touch()
        # update if needed
        completer, flags, include_folders = ViewConfig.__generate_essentials(
            view, settings)
        if self.needs_update(completer, flags):
            log.debug("config needs new completer.")
            self.completer = completer
            self.completer.clang_flags = flags
            self.completer.update(view, settings)
            self.include_folders = include_folders
            File.update_mod_time(view.file_name())
            return self
        if ViewConfig.needs_reparse(view):
            log.debug("config updates existing completer.")
            self.completer.update(view, settings)
        return self

    def needs_update(self, completer, flags):
        """Check if view config needs update.

        Args:
            completer (Completer): A new completer.
            flags (str[]): Flags as string list.

        Returns:
            bool: True if update is needed, False otherwise.
        """
        if not self.completer:
            log.debug("no completer. Need to update.")
            return True
        if completer.name != self.completer.name:
            log.debug("different completer class. Need to update.")
            return True
        if flags != self.completer.clang_flags:
            log.debug("different completer flags. Need to update.")
            return True
        log.debug("view config needs no update.")
        return False

    def is_older_than(self, age_in_seconds):
        """Check if this view config is older than some time in secs.

        Args:
            age_in_seconds (float): time in seconds

        Returns:
            bool: True if older, False otherwise
        """
        if time.time() - self.__last_usage_time > age_in_seconds:
            return True
        return False

    def get_age(self):
        """Return age of config."""
        return time.time() - self.__last_usage_time

    def touch(self):
        """Update time of usage of this config."""
        self.__last_usage_time = time.time()

    @staticmethod
    def needs_reparse(view):
        """Check if view config needs update.

        Args:
            view (View): Current view.

        Returns:
            bool: True if reparse is needed, False otherwise.
        """
        if not File.is_unchanged(view.file_name()):
            return True
        log.debug("view config needs no reparse.")
        return False

    @staticmethod
    def __generate_essentials(view, settings):
        """Generate essentials. Flags and empty Completer. This is fast.

        Args:
            view (View): Current view.
            settings (SettingStorage): Current settings.

        Returns:
            (Completer, str[]): A completer bundled with flags as str list.
        """
        import fnmatch
        if not SublBridge.is_valid_view(view):
            log.warning(" no flags for an invalid view %s.", view)
            return (None, [])
        completer = ViewConfig.__init_completer(settings)
        prefixes = completer.compiler_variant.include_prefixes

        init_flags = completer.compiler_variant.init_flags
        lang_flags = ViewConfig.__get_default_flags(
            view, settings, completer.compiler_variant.need_lang_flags)
        log.debug("Common")
        common_flags = ViewConfig.__get_common_flags(prefixes, settings)
        log.debug("Source")
        source_flags = ViewConfig.__load_source_flags(view, settings, prefixes)
        log.debug("Merge")
        flags = ViewConfig.__merge_flags(
            init_flags, lang_flags, common_flags, source_flags)

        flags_as_str_list = []
        log.debug("Appending and filtering flags with ignore patterns: %s",
                  settings.ignore_flags)
        for flag in flags:
            ignore_this_flag = False
            for pattern in settings.ignore_flags:
                if fnmatch.fnmatch(flag.body, pattern):
                    log.debug("Ignoring flag: %s", flag)
                    ignore_this_flag = True
                    break
            if ignore_this_flag:
                continue
            flags_as_str_list += flag.as_list()

        include_folders = ViewConfig.__get_include_folders(prefixes, flags)
        return completer, flags_as_str_list, include_folders

    @staticmethod
    def __get_include_folders(include_prefixes, all_flags):
        include_folders = []
        for flag in all_flags:
            for prefix in include_prefixes:
                if flag.prefix.startswith(prefix):
                    include_folders.append(flag.body)
                    continue
                if flag.body.startswith(prefix):
                    include_folders.append(flag.body[len(prefix):])
                    continue
        return include_folders

    @staticmethod
    def __merge_flags(init_flags, lang_flags, common_flags, source_flags):
        """Merge the flags together.

        This function accounts for the priority and duplicates.

        Args:
            init_flags (str[]): Initial flags for compiler
            lang_flags (str[]): Language-specific default flags
            common_flags (str[]): User flags included to every TU compilation
            source_flags (str[]): Flags generated by the flag source file

        Returns:
            TYPE: Description
        """
        log.debug("lang flags: %s", lang_flags)
        lang_std_flag_indices = [
            i for i, flag in enumerate(lang_flags)
            if flag.body.startswith('-std=')]
        source_std_flags_indices = [
            i for i, flag in enumerate(source_flags)
            if flag.body.startswith('-std=')]

        # Perform checks for user's settings.
        if len(lang_std_flag_indices) > 1:
            std_flags = [lang_flags[i] for i in lang_std_flag_indices]
            error_msg = TOO_MANY_STD_FLAGS_ERROR_MSG.format(
                which_settings="`lang_flags` settings",
                std_flags=std_flags)
            SublBridge.show_error_dialog(error_msg)
        if len(source_std_flags_indices) > 1:
            std_flags = [source_flags[i] for i in source_std_flags_indices]
            error_msg = TOO_MANY_STD_FLAGS_ERROR_MSG.format(
                which_settings="source generated settings",
                std_flags=std_flags)
            # TODO(igor): Do not show an error here, discussion in issue #417
            log.error(error_msg)

        # Replace default flags with generated ones if needed.
        if source_std_flags_indices and lang_std_flag_indices:
            # Remove the lang flags std flag, leave only source one.
            log.debug("Removing default std flag: '%s' in favor of: '%s'",
                      lang_flags[lang_std_flag_indices[0]],
                      source_flags[source_std_flags_indices[0]])
            del lang_flags[lang_std_flag_indices[0]]

        # Combine all flags into a unique list and return it.
        flags = UniqueList()
        flags += init_flags + lang_flags + source_flags + common_flags
        return flags

    @staticmethod
    def __load_source_flags(view, settings, include_prefixes):
        """Generate flags from source.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.
            include_prefixes (str[]): Valid include prefixes.

        Returns:
            Flag[]: flags generated from a flags source.
        """
        current_dir = path.dirname(view.file_name())
        default_search_scope = TreeSearchScope(
            from_folder=current_dir,
            to_folder=settings.project_folder)
        for source_dict in settings.flags_sources:
            if SettingsStorage.FILE_TAG not in source_dict:
                log.critical("Flag source %s has no '%s' entry",
                             source_dict, SettingsStorage.FILE_TAG)
                continue
            search_scope = default_search_scope
            file_name = source_dict[SettingsStorage.FILE_TAG]
            search_folders = []
            if SettingsStorage.SEARCH_IN_TAG in source_dict:
                # The user knows where to search for the flags source.
                search_folders = source_dict[SettingsStorage.SEARCH_IN_TAG]
                search_scope = ListSearchScope(search_folders)
            if file_name == "CMakeLists.txt":
                prefix_paths = source_dict.get(
                    SettingsStorage.PREFIX_PATHS_TAG, None)
                cmake_flags = source_dict.get(SettingsStorage.FLAGS_TAG, None)
                flag_source = CMakeFile(
                    include_prefixes,
                    prefix_paths,
                    cmake_flags,
                    settings.cmake_binary,
                    settings.header_to_source_mapping,
                    settings.target_compilers,
                    settings.lazy_flag_parsing)
            elif file_name == "Makefile":
                flag_source = Makefile(include_prefixes)
            elif file_name == "compile_commands.json":
                flag_source = CompilationDb(
                    include_prefixes,
                    settings.header_to_source_mapping,
                    settings.lazy_flag_parsing
                )
            elif file_name == ".clang_complete":
                flag_source = FlagsFile(include_prefixes)
            elif file_name == "c_cpp_properties.json":
                flag_source = CCppProperties(include_prefixes)
            elif file_name == "CppProperties.json":
                flag_source = CppProperties(include_prefixes)
            # try to get flags (uses cache when needed)
            flags = flag_source.get_flags(view.file_name(), search_scope)
            if flags:
                # don't load anything more if we have flags
                log.debug("flags generated from '%s'.", file_name)
                return flags
        return []

    @staticmethod
    def __get_common_flags(include_prefixes, settings):
        """Get common flags as list of flags."""
        return settings.common_flags

    @staticmethod
    def __init_completer(settings):
        """Initialize completer.

        Args:
            settings (SettingsStorage): Current settings.

        Returns:
            Completer: A completer. Can be lib completer or bin completer.
        """
        error_vis = PopupErrorVis(settings)

        completer = None
        if settings.use_libclang:
            log.info("init completer based on libclang")
            completer = lib_complete.Completer(settings, error_vis)
            if not completer.valid:
                log.error("cannot initialize completer with libclang.")
                log.info("falling back to using clang in a subprocess.")
                completer = None
        if not completer:
            log.info("init completer based on clang from cmd")
            completer = bin_complete.Completer(settings, error_vis)
        return completer

    @staticmethod
    def __get_default_flags(view, settings, need_lang_flags):
        """Get language flags.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.
            need_lang_flags (bool): Decides if we add language flags

        Returns:
            Flag[]: A list of language-specific flags.
        """
        from ..flags_sources.compiler_builtins import CompilerBuiltIns
        lang_tag, lang = SublBridge.get_view_lang(view, settings)
        lang_flags = []
        if need_lang_flags:
            lang_flags += ["-x", lang]
        lang_flags += settings.lang_flags[lang_tag]

        # If the user provided explicit target compilers, retrieve their
        # default flags and append them to the list:
        target_compiler = settings.target_compilers[lang_tag]
        if target_compiler is None and settings.use_default_includes:
            target_compiler = settings.clang_binary
        if target_compiler is not None:
            built_ins = CompilerBuiltIns(compiler=target_compiler,
                                         lang_flags=lang_flags,
                                         filename=None)
            if settings.use_default_definitions:
                lang_flags += built_ins.defines
            lang_flags += built_ins.includes
        log.debug("Tokeninzing default flags")
        return Flag.tokenize_list(lang_flags)
