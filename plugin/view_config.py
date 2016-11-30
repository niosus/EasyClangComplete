"""A module that stores classes related ot view configuration.

Attributes:
    log (logging.Logger): Logger for this module.
"""
import logging
from os import path
from threading import RLock


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
            return True
        if completer.name != self.completer.name:
            return True
        if flags != self.completer.clang_flags:
            return True
        log.debug(" view config needs no update.")
        return False

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
        flags += ViewConfig.__get_lang_flags(view, settings)
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
        prefix_paths = settings.cmake_prefix_paths
        if prefix_paths is None:
            prefix_paths = []
        current_dir = path.dirname(view.file_name())
        search_scope = SearchScope(
            from_folder=current_dir,
            to_folder=settings.project_folder)
        for source in settings.flags_sources:
            if source == "cmake":
                flag_source = CMakeFile(include_prefixes, prefix_paths)
            elif source == "compilation_db":
                flag_source = CompilationDb(include_prefixes)
            elif source == "clang_complete_file":
                flag_source = FlagsFile(include_prefixes)
            # try to get flags
            flags = flag_source.get_flags(view.file_name(), search_scope)
            if flags:
                # don't load anything more if we have flags
                log.debug(" flags generated with '%s' source.", source)
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
            completer = lib_complete.Completer(settings.clang_binary)
            if not completer.valid:
                log.error(" cannot initialize completer with libclang.")
                log.info(" falling back to using clang in a subprocess.")
                completer = None
        if not completer:
            log.info(" init completer based on clang from cmd")
            completer = bin_complete.Completer(settings.clang_binary)
        return completer

    @staticmethod
    def __get_lang_flags(view, settings):
        """Get language flags.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.

        Returns:
            Flag[]: A list of language-specific flags.
        """
        current_lang = Tools.get_view_syntax(view)
        if current_lang == 'C' or current_lang == 'C99':
            lang_flags = settings.c_flags
        else:
            lang_flags = settings.cpp_flags
        return Flag.tokenize_list(lang_flags)


@singleton
class ViewConfigCache(dict):
    """Singleton for view configurations cache."""
    pass


class ViewConfigManager(object):
    """A utility class that stores a cache of all view configurations."""

    _rlock = RLock()

    def __init__(self):
        """Initialize view config manager."""
        with ViewConfigManager._rlock:
            self._cache = ViewConfigCache()

    def get_from_cache(self, view):
        """Get config from cache with no modifications."""
        if not Tools.is_valid_view(view):
            log.error(" view %s is not valid. Cannot get config.", view)
            return None
        file_path = view.file_name()
        if file_path in self._cache:
            log.debug(" config exists for path: %s", file_path)
            return self._cache[file_path]
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
        # we need to protect it with mutex to avoid race condition between
        # creating and removing a config.
        file_path = view.file_name()
        with ViewConfigManager._rlock:
            if file_path in self._cache:
                log.debug(" config exists for path: %s", file_path)
                return self._cache[file_path].update_if_needed(view, settings)
            # generate new config
            log.debug(" generate new config for path: %s", file_path)
            config = ViewConfig(view, settings)
            self._cache[file_path] = config
            return config

    def clear_for_view(self, file_path):
        """Clear config for path."""
        log.debug(" trying to clear config for view: %s", file_path)
        with ViewConfigManager._rlock:
            del self._cache[file_path]
        return file_path
