import logging
from os import path


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


@singleton
class ViewConfigCache(dict):
    """Singleton for view configurations cache."""
    pass


class ViewConfig(object):

    def __init__(self, view, settings):
        self.__view_id = view.buffer_id()
        lang_flags = ViewConfig.__get_lang_flags(view, settings)
        self.completer = ViewConfig.__init_completer(settings)
        include_prefixes = self.completer.compiler_variant.include_prefixes
        common_flags = self.__get_common_flags(
            include_prefixes, settings)
        flag_source, source_flags = \
            ViewConfig.__generate_source_flags(
                view, settings, include_prefixes)
        all_flags = UniqueList() + lang_flags + common_flags + source_flags

        # initialize flags
        self.completer.clang_flags = []
        for flag in all_flags:
            self.completer.clang_flags += flag.as_list()
        self.completer.update(view, settings.errors_on_save)

    def has_changed(self, view, settings):
        pass

    @staticmethod
    def __generate_source_flags(view, settings, include_prefixes):
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
                return (source, flags)
        return (None, [])

    @staticmethod
    def __get_common_flags(include_prefixes, settings):
        home_folder = path.expanduser('~')
        return FlagsSource.parse_flags(home_folder,
                                       settings.common_flags,
                                       include_prefixes)

    @staticmethod
    def __init_completer(settings):
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
        current_lang = Tools.get_view_syntax(view)
        if current_lang == 'C' or current_lang == 'C99':
            lang_flags = settings.c_flags
        else:
            lang_flags = settings.cpp_flags
        return Flag.tokenize_list(lang_flags)


class ViewConfigManager(object):

    def __init__(self):
        self._cache = ViewConfigCache()

    def get_config_for_view(self, view, settings):
        view_id = view.buffer_id()
        if view_id in self._cache:
            return self._cache[view_id]
        return self.generate_new_config(view, settings)

    def generate_new_config(self, view, settings):
        config = ViewConfig(view, settings)
        self._cache[view.buffer_id()] = config
        return config
