"""A module that stores classes related ot view configuration.

Attributes:
    log (logging.Logger): Logger for this module.
"""
import time
import logging
import weakref
from os import path
from threading import RLock
from threading import Timer

from .tools import File
from .tools import Tools
from .tools import SublBridge
from .tools import SearchScope

from .utils.flag import Flag
from .utils.unique_list import UniqueList
from .utils.singleton import ViewConfigCache
from .utils.singleton import ThreadCache

from .completion import lib_complete
from .completion import bin_complete

from .error_vis.popup_error_vis import PopupErrorVis

from .flags_sources.flags_file import FlagsFile
from .flags_sources.cmake_file import CMakeFile
from .flags_sources.makefile import Makefile
from .flags_sources.flags_source import FlagsSource
from .flags_sources.c_cpp_properties import CCppProperties
from .flags_sources.CppProperties import CppProperties
from .flags_sources.compilation_db import CompilationDb

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
        if not Tools.is_valid_view(view):
            return

        # init creation time
        self.__last_usage_time = time.time()

        # set up a proper object
        completer, flags = ViewConfig.__generate_essentials(view, settings)
        if not completer:
            log.warning(" could not generate completer for view %s",
                        view.buffer_id())
            return

        self.completer = completer
        self.completer.clang_flags = flags
        self.completer.update(view, settings)

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
        completer, flags = ViewConfig.__generate_essentials(view, settings)
        if self.needs_update(completer, flags):
            log.debug("config needs new completer.")
            self.completer = completer
            self.completer.clang_flags = flags
            self.completer.update(view, settings)
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
        if not Tools.is_valid_view(view):
            log.warning(" no flags for an invalid view %s.", view)
            return (None, [])
        completer = ViewConfig.__init_completer(settings)
        prefixes = completer.compiler_variant.include_prefixes

        init_flags = completer.compiler_variant.init_flags
        lang_flags = ViewConfig.__get_lang_flags(
            view, settings, completer.compiler_variant.need_lang_flags)
        common_flags = ViewConfig.__get_common_flags(prefixes, settings)
        source_flags = ViewConfig.__load_source_flags(view, settings, prefixes)
        flags = ViewConfig.__merge_flags(
            init_flags, lang_flags, common_flags, source_flags)

        flags_as_str_list = []
        for flag in flags:
            flags_as_str_list += flag.as_list()
        return (completer, flags_as_str_list)

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
        flags += init_flags + lang_flags + common_flags + source_flags
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
        search_scope = SearchScope(
            from_folder=current_dir,
            to_folder=settings.project_folder)
        for source_dict in settings.flags_sources:
            if "file" not in source_dict:
                log.critical(" flag source %s has not 'file'", source_dict)
                continue
            file_name = source_dict["file"]
            search_folder = None
            if "search_in" in source_dict:
                # the user knows where to search for the flags source
                search_folder = source_dict["search_in"]
                if search_folder:
                    search_scope = SearchScope(
                        from_folder=path.normpath(search_folder))
            if file_name == "CMakeLists.txt":
                prefix_paths = source_dict.get("prefix_paths", None)
                cmake_flags = source_dict.get("flags", None)
                flag_source = CMakeFile(
                    include_prefixes,
                    prefix_paths,
                    cmake_flags,
                    settings.cmake_binary,
                    settings.header_to_source_mapping,
                    settings.use_target_compiler_built_in_flags,
                    settings.target_compilers)
            elif file_name == "Makefile":
                flag_source = Makefile(include_prefixes)
            elif file_name == "compile_commands.json":
                flag_source = CompilationDb(
                    include_prefixes,
                    settings.header_to_source_mapping,
                    settings.use_target_compiler_built_in_flags
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
        """Get common flags as list of flags.

        Additionally expands local paths into global ones based on folder.

        Args:
            include_prefixes (str[]): List of valid include prefixes.
            settings (SettingsStorage): Current settings.

        Returns:
            Flag[]: Common flags.
        """
        home_folder = path.expanduser('~')
        return FlagsSource.parse_flags(home_folder,
                                       settings.common_flags,
                                       include_prefixes)

    @staticmethod
    def __init_completer(settings):
        """Initialize completer.

        Args:
            settings (SettingsStorage): Current settings.

        Returns:
            Completer: A completer. Can be lib completer or bin completer.
        """
        error_vis = PopupErrorVis(settings.gutter_style)

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
    def __get_lang_flags(view, settings, need_lang_flags):
        """Get language flags.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.
            need_lang_flags (bool): Decides if we add language flags

        Returns:
            Flag[]: A list of language-specific flags.
        """
        from .utils.compiler_builtins import CompilerBuiltIns
        current_lang = Tools.get_view_lang(view, settings)
        lang_flags = []
        target_compilers = settings.target_compilers
        target_lang = None
        lang_args = list()
        if current_lang == Tools.LANG_OBJECTIVE_C_TAG:
            target_lang = "objective-c"
        elif current_lang == Tools.LANG_OBJECTIVE_CPP_TAG:
            target_lang = "objective-c++"
        elif current_lang == Tools.LANG_C_TAG:
            target_lang = "c"
        elif current_lang == Tools.LANG_CPP_TAG:
            target_lang = "c++"
        else:
            log.error("unrecognized language '%s'!", target_lang)
        lang_args = settings.lang_flags[current_lang]
        if need_lang_flags:
            lang_flags += ["-x", target_lang]
        lang_flags += lang_args

        # If the user provided explicit target compilers, retrieve their
        # default flags and append them to the list:
        if target_lang in target_compilers:
            target_compiler = target_compilers[target_lang]
            if target_compiler is not None:
                target_compiler_args = [target_compiler, "-x", target_lang]
                builtIns = CompilerBuiltIns(target_compiler_args, None)
                for builtin_flag in builtIns.flags:
                    # Note: Only append new flags; this is done as depending
                    # on the user's configuration we already might have
                    # added appropriate flags from another flag source.
                    # The approach assumes that each entry in the built-in
                    # flags consists of a single argument (which is true
                    # for the ones we expect to be in, i.e. only -Dxxx and
                    # -Ixxx flags). Note that it shouldn't do any harm
                    # if flags appear multiple times.
                    if builtin_flag not in lang_flags:
                        lang_flags.append(builtin_flag)

        return Flag.tokenize_list(lang_flags)


class ViewConfigManager(object):
    """A utility class that stores a cache of all view configurations."""

    TAG = "view_config_progress"

    def __init__(self, timer_period=30, max_config_age=60):
        """Initialize view config manager.

        All the values are given in seconds and can be overridden by settings.

        Args:
            timer_period (int, optional): How often to run timer in seconds.
            max_config_age (int, optional): How long should a TU stay alive.
        """
        self.__timer_period = timer_period      # Seconds.
        self.__max_config_age = max_config_age  # Seconds.
        self.__rlock = RLock()

        with self.__rlock:
            self.__cache = ViewConfigCache()
            self.__timer_cache = ThreadCache()

        # Run the timer thread correctly.
        self.__run_timer()

    def get_from_cache(self, view):
        """Get config from cache with no modifications."""
        if not Tools.is_valid_view(view):
            log.error("view %s is not valid. Cannot get config.", view)
            return None
        v_id = view.buffer_id()
        if v_id in self.__cache:
            log.debug("config exists for view: %s", v_id)
            self.__cache[v_id].touch()
            log.debug("config: %s", self.__cache[v_id])
            return self.__cache[v_id]
        return None

    def load_for_view(self, view, settings):
        """Get stored config for a view or generate a new one.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.

        Returns:
            ViewConfig: Config for current view and settings.
        """
        if not Tools.is_valid_view(view):
            log.error("view %s is not valid. Cannot get config.", view)
            return None
        try:
            v_id = view.buffer_id()
            res = None
            # we need to protect this with mutex to avoid race condition
            # between creating and removing a config.
            with self.__rlock:
                if v_id in self.__cache:
                    log.debug("config exists for path: %s", v_id)
                    res = self.__cache[v_id].update_if_needed(view, settings)
                else:
                    log.debug("generate new config for path: %s", v_id)
                    config = ViewConfig(view, settings)
                    self.__cache[v_id] = config
                    res = config

                # Set the internal max config age.
                self.__max_config_age = settings.max_cache_age

            # now return the needed config
            return weakref.proxy(res)
        except AttributeError as e:
            import traceback
            tb = traceback.format_exc()
            log.error("view became invalid while loading config: %s", e)
            log.error("traceback: %s", tb)
            return None

    def clear_for_view(self, v_id):
        """Clear config for a view id."""
        import gc
        log.debug("trying to clear config for view: %s", v_id)
        with self.__rlock:
            if v_id in self.__cache:
                del self.__cache[v_id]
                gc.collect()  # Explicitly collect garbage.
        return v_id

    def trigger_get_declaration_location(self, view):
        """Return location to object declaration."""
        config = self.get_from_cache(view)
        if not config:
            log.debug("Config is not ready yet. No reference is available.")
            return None
        (row, col) = SublBridge.cursor_pos(view)
        return config.completer.get_declaration_location(view, row, col)

    def trigger_info(self, view, tooltip_request, settings):
        """Handle getting info from completer.

        The main purpose of this function is to ensure that python correctly
        collects garbage. Before, a direct call to info of the completer was
        made as part of async job, which prevented garbage collection.
        """
        config = self.get_from_cache(view)
        if not config:
            log.debug("Config is not ready yet. No info tooltip shown.")
            return tooltip_request, ""
        return config.completer.info(tooltip_request, settings)

    def trigger_completion(self, view, completion_request):
        """Get completions.

        This function is needed to ensure that python can get everything
        properly garbage collected. Before we passed a function of a completer
        to an async task. This left a reference to a completer forever active.
        """
        view_config = self.get_from_cache(view)
        return view_config.completer.complete(completion_request)

    def __run_timer(self):
        """We make sure we run a single thread."""
        if ViewConfigManager.TAG in self.__timer_cache:
            # We need to kill the old thread before starting the new one.
            self.__timer_cache[ViewConfigManager.TAG].cancel()
            del self.__timer_cache[ViewConfigManager.TAG]
        self.__timer_cache[ViewConfigManager.TAG] = Timer(
            interval=self.__timer_period, function=self.__remove_old_configs)
        self.__timer_cache[ViewConfigManager.TAG].start()

    def __remove_old_configs(self):
        """Remove old configs if they are older than max age.

        This function is called by a thread that keeps running forever checking
        if there are any new configs to remove based on a timer.
        """
        import gc
        with self.__rlock:
            for v_id in list(self.__cache.keys()):
                if self.__cache[v_id].is_older_than(self.__max_config_age):
                    log.debug("Remove old config: %s", v_id)
                    del self.__cache[v_id]
                    gc.collect()  # Explicitly collect garbage
                else:
                    log.debug("Skip young config: Age %s < %s. View: %s.",
                              self.__cache[v_id].get_age(),
                              self.__max_config_age,
                              v_id)
        # Run the timer again.
        self.__run_timer()
