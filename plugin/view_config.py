"""A module that stores classes related ot view configuration.

Attributes:
    log (logging.Logger): Logger for this module.
"""
import logging
from os import path
from time import time
from threading import RLock
from threading import Timer

from .tools import File
from .tools import Tools
from .tools import singleton
from .tools import SearchScope

from .utils.flag import Flag
from .utils.unique_list import UniqueList

from .completion import lib_complete
from .completion import bin_complete

from .flags_sources.flags_file import FlagsFile
from .flags_sources.cmake_file import CMakeFile
from .flags_sources.flags_source import FlagsSource
from .flags_sources.compilation_db import CompilationDb

log = logging.getLogger(__name__)


class ViewConfig(object):
    """A bundle representing a view configuration.

    Stores everything needed to perform completion tasks on a given view with
    given settings.

    Attributes:
        completer (Completer): A completer for each view configuration.
        flag_source (FlagsSource): FlagsSource that was used to generate flags.
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
        self.__last_usage_time = time()

        # set up a proper object
        completer, flags = ViewConfig.__generate_essentials(view, settings)
        if not completer:
            log.warning(" could not generate completer for view %s",
                        view.buffer_id())
            return

        self.completer = completer
        self.completer.clang_flags = flags
        self.completer.update(view, settings.errors_on_save)

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
            log.debug(" config needs new completer.")
            self.completer = completer
            self.completer.clang_flags = flags
            self.completer.update(view, settings.errors_on_save)
            File.update_mod_time(view.file_name())
            return self
        if ViewConfig.needs_reparse(view):
            log.debug(" config updates existing completer.")
            self.completer.update(view, settings.errors_on_save)
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
        log.debug(" view config needs no update.")
        return False

    def is_older_than(self, age_in_seconds):
        """Check if this view config is older than some time in secs.

        Args:
            age_in_seconds (float): time in seconds

        Returns:
            bool: True if older, False otherwise
        """
        if time() - self.__last_usage_time > age_in_seconds:
            return True
        return False

    def get_age(self):
        """Return age of config."""
        return time() - self.__last_usage_time

    def touch(self):
        """Update time of usage of this config."""
        self.__last_usage_time = time()

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
        log.debug(" view config needs no reparse.")
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

        flags = UniqueList()
        flags += completer.compiler_variant.init_flags
        flags += ViewConfig.__get_lang_flags(
            view, settings, completer.compiler_variant.need_lang_flags)
        flags += ViewConfig.__get_common_flags(prefixes, settings)
        flags += ViewConfig.__load_source_flags(view, settings, prefixes)

        flags_as_str_list = []
        for flag in flags:
            flags_as_str_list += flag.as_list()
        return (completer, flags_as_str_list)

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
                    include_prefixes, prefix_paths, cmake_flags)
            elif file_name == "compile_commands.json":
                flag_source = CompilationDb(include_prefixes)
            elif file_name == ".clang_complete":
                flag_source = FlagsFile(include_prefixes)
            # try to get flags (uses cache when needed)
            flags = flag_source.get_flags(view.file_name(), search_scope)
            if flags:
                # don't load anything more if we have flags
                log.debug(" flags generated from '%s'.", file_name)
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
        completer = None
        if settings.use_libclang:
            log.info(" init completer based on libclang")
            completer = lib_complete.Completer(settings.clang_binary,
                                               settings.clang_version)
            if not completer.valid:
                log.error(" cannot initialize completer with libclang.")
                log.info(" falling back to using clang in a subprocess.")
                completer = None
        if not completer:
            log.info(" init completer based on clang from cmd")
            completer = bin_complete.Completer(settings.clang_binary,
                                               settings.clang_version)
        return completer

    @staticmethod
    def __get_lang_flags(view, settings, need_lang_flags):
        """Get language flags.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.

        Returns:
            Flag[]: A list of language-specific flags.
        """
        current_lang = Tools.get_view_lang(view)
        lang_flags = []
        if current_lang == 'C':
            if need_lang_flags:
                lang_flags += ["-x"] + ["c"]
            lang_flags += settings.c_flags
        else:
            if need_lang_flags:
                lang_flags += ["-x"] + ["c++"]
            lang_flags += settings.cpp_flags
        return Flag.tokenize_list(lang_flags)


@singleton
class ViewConfigCache(dict):
    """Singleton for view configurations cache."""
    pass


class ViewConfigManager(object):
    """A utility class that stores a cache of all view configurations."""

    __rlock = RLock()

    __timers = {}
    __timer_period = 60  # seconds

    def __init__(self):
        """Initialize view config manager."""
        with ViewConfigManager.__rlock:
            self._cache = ViewConfigCache()

    def get_from_cache(self, view):
        """Get config from cache with no modifications."""
        if not Tools.is_valid_view(view):
            log.error(" view %s is not valid. Cannot get config.", view)
            return None
        v_id = view.buffer_id()
        if v_id in self._cache:
            log.debug(" config exists for path: %s", v_id)
            self._cache[v_id].touch()
            return self._cache[v_id]
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
            log.error(" view %s is not valid. Cannot get config.", view)
            return None
        try:
            v_id = view.buffer_id()
            res = None
            # we need to protect this with mutex to avoid race condition
            # between creating and removing a config.
            with ViewConfigManager.__rlock:
                if v_id in self._cache:
                    log.debug(" config exists for path: %s", v_id)
                    res = self._cache[v_id].update_if_needed(view, settings)
                else:
                    log.debug(" generate new config for path: %s", v_id)
                    config = ViewConfig(view, settings)
                    self._cache[v_id] = config
                    res = config

                # start timer if it is not set yet
                log.debug(" starting timer to remove old configs.")
                if v_id in ViewConfigManager.__timers:
                    log.debug(" cancel old timer.")
                    ViewConfigManager.__cancel_timer(v_id)
                ViewConfigManager.__start_timer(
                    self.__remove_old_config, v_id, settings.max_cache_age)
            # now return the needed config
            return res
        except AttributeError:
            log.error(" view became invalid in process of loading config.")
            return None

    def clear_for_view(self, v_id):
        """Clear config for path."""
        log.debug(" trying to clear config for view: %s", v_id)
        with ViewConfigManager.__rlock:
            if v_id in self._cache:
                del self._cache[v_id]
            ViewConfigManager.__cancel_timer(v_id)
        return v_id

    @staticmethod
    def __start_timer(callback, v_id, max_age):
        """Start timer for file path and callback."""
        log.debug(" [timer]: start for view: %s", v_id)
        ViewConfigManager.__timers[v_id] = Timer(
            ViewConfigManager.__timer_period,
            callback, [v_id, max_age])
        ViewConfigManager.__timers[v_id].start()
        log.debug(" [timer]: active for views: %s",
                  ViewConfigManager.__timers.keys())

    @staticmethod
    def __cancel_timer(v_id):
        """Stop timer for file path."""
        with ViewConfigManager.__rlock:
            if v_id in ViewConfigManager.__timers:
                log.debug(" [timer]: stop for view: %s", v_id)
                ViewConfigManager.__timers[v_id].cancel()
                del ViewConfigManager.__timers[v_id]
                log.debug(" [timer]: active for views: %s",
                          ViewConfigManager.__timers.keys())

    def __remove_old_config(self, v_id, max_config_age):
        """Remove old config if it is older than max age.

        Args:
            v_id (str): Path to a file
            max_config_age (int): Max config age in seconds.
        """
        with ViewConfigManager.__rlock:
            ViewConfigManager.__cancel_timer(v_id)
            if self._cache[v_id].is_older_than(max_config_age):
                log.debug(" [delete] old config: %s", v_id)
                del self._cache[v_id]
            else:
                log.debug(" [skip] young config: Age %s < %s. View: %s.",
                          self._cache[v_id].get_age(),
                          max_config_age,
                          v_id)
                log.debug(" [timer]: restart.")
                ViewConfigManager.__start_timer(
                    self.__remove_old_config, v_id, max_config_age)
