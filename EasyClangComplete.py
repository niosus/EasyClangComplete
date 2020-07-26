"""EasyClangComplete plugin for Sublime Text 3.

Provides completion suggestions for C/C++ languages based on clang

Attributes:
    log (logging.Logger): logger for this module

"""

import sublime
import sublime_plugin
import logging
import shutil

from os import path

from .plugin.utils import tools
from .plugin.view_config import view_config_manager
from .plugin import flags_sources
from .plugin.utils import singleton_thread_pool
from .plugin.utils import thread_job
from .plugin.utils import progress_status
from .plugin.utils import quick_panel_handler
from .plugin.utils import action_request
from .plugin.utils import module_reloader
from .plugin.utils import singleton
from .plugin.utils import include_parser
from .plugin.utils import file
from .plugin.settings import settings_manager
from .plugin.settings import settings_storage
from .plugin.utils.subl import subl_bridge
from .plugin.utils.subl import row_col
from .plugin.flags_sources import bazel


# Reload all modules modules ignoring those that contain the given string.
module_reloader.ModuleReloader.reload_all(ignore_string='singleton')

# Set some aliases for simplicity.
SettingsManager = settings_manager.SettingsManager
SettingsStorage = settings_storage.SettingsStorage
ViewConfigManager = view_config_manager.ViewConfigManager
SublBridge = subl_bridge.SublBridge
Tools = tools.Tools
File = file.File
MoonProgressStatus = progress_status.MoonProgressStatus
ColorSublimeProgressStatus = progress_status.ColorSublimeProgressStatus
NoneSublimeProgressStatus = progress_status.NoneSublimeProgressStatus
PosStatus = subl_bridge.PosStatus
CMakeFile = flags_sources.cmake_file.CMakeFile
CMakeFileCache = singleton.CMakeFileCache
GenericCache = singleton.GenericCache
ThreadPool = singleton_thread_pool.ThreadPool
ThreadJob = thread_job.ThreadJob
QuickPanelHandler = quick_panel_handler.QuickPanelHandler
ActionRequest = action_request.ActionRequest
ZeroIndexedRowCol = row_col.ZeroIndexedRowCol
Bazel = bazel.Bazel

log = logging.getLogger("ECC")
log.setLevel(logging.DEBUG)
log.propagate = False
formatter_default = logging.Formatter(
    '[%(name)s:%(levelname)-7s]: %(message)s')
formatter_verbose = logging.Formatter(
    '[%(name)s:%(levelname)s]:[%(filename)s]:[%(funcName)s]:'
    '[%(threadName)s]: %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter_default)
if not log.hasHandlers():
    log.addHandler(ch)


handle_plugin_loaded_function = None
handle_plugin_unloaded_function = None


def plugin_loaded():
    """Call right after sublime api is ready to use.

    We need it to initialize all the different classes that encapsulate
    functionality. We can only properly init them after sublime api is
    available."""
    module_reloader.ModuleReloader.reload_all(ignore_string='singleton')
    GenericCache.clear_all_caches()
    handle_plugin_loaded_function()


def plugin_unloaded():
    """Call right before the package was unloaded."""
    handle_plugin_unloaded_function()


class EccShowAllErrorsCommand(sublime_plugin.TextCommand):
    """Handle easy_clang_goto_declaration command."""

    def run(self, edit):
        """Show all errors available in this view.

        This function shows all errors that are available from within a view.
        Note that the errors can be from different files.
        """
        if not SublBridge.is_valid_view(self.view):
            return
        config_manager = EasyClangComplete.view_config_manager
        if not config_manager:
            log.error("No ViewConfigManager available.")
            return
        config = config_manager.get_from_cache(self.view)
        log.debug("config: %s", config)
        if not config:
            log.error("No ViewConfig for view: %s.", self.view.buffer_id())
            return
        if not config.completer:
            log.error("No Completer for view: %s.", self.view.buffer_id())
        handler = QuickPanelHandler(self.view, config.completer.latest_errors)
        start_idx = 0
        self.view.window().show_quick_panel(
            handler.items_to_show(),
            handler.on_done,
            sublime.MONOSPACE_FONT,
            start_idx,
            handler.on_highlighted)


class EccGotoDeclarationCommand(sublime_plugin.TextCommand):
    """Handle easy_clang_goto_declaration command."""

    def run(self, edit):
        """Run goto declaration command.

        Navigates to delcaration of entity located by current position
        of cursor.
        """
        if not SublBridge.is_valid_view(self.view):
            return
        config_manager = EasyClangComplete.view_config_manager
        if not config_manager:
            return
        location = config_manager.trigger_get_declaration_location(self.view)
        if location:
            loc = location.file.name
            loc += ":" + str(location.line)
            loc += ":" + str(location.column)
            log.debug("Navigating to declaration: %s", loc)
            sublime.active_window().open_file(loc, sublime.ENCODED_POSITION)


class CleanCmakeCommand(sublime_plugin.TextCommand):
    """Command that cleans cmake build directory."""

    def run(self, edit):
        """Run clean command.

        Detects if there is a CMakeLists.txt associated to current view and
        cleans all related information in case there is one.
        """
        if not SublBridge.is_valid_view(self.view):
            return
        import gc
        file_path = self.view.file_name()
        cmake_cache = CMakeFileCache()
        try:
            cmake_file_path = cmake_cache[file_path]
            log.debug("Cleaning file: '%s'", cmake_file_path)
            del cmake_cache[file_path]
            del cmake_cache[cmake_file_path]
            EasyClangComplete.view_config_manager.clear_for_view(
                self.view.buffer_id())
            # Better safe than sorry. Cleanup!
            gc.collect()
            temp_proj_dir = CMakeFile.unique_folder_name(cmake_file_path)
            if path.exists(temp_proj_dir):
                log.debug("Cleaning build directory: '%s'", temp_proj_dir)
                shutil.rmtree(temp_proj_dir, ignore_errors=True)
        except KeyError:
            log.debug("Nothing to clean")


class GenerateBazelCompDbCommand(sublime_plugin.TextCommand):
    """Command that generates a compilation database with bazel."""

    def run(self, edit):
        """Run compdb generation command.

        Find a WORKSPACE file up the directory tree and run the compilation
        database generation command there.
        """
        log.debug("Starting generating compilation database.")
        if not SublBridge.is_valid_view(self.view):
            return
        job = ThreadJob(
            name=ThreadJob.GENERATE_DB_TAG,
            function=Bazel.generate_compdb,
            callback=Bazel.compdb_generated,
            args=[self.view])
        EasyClangComplete.thread_pool.new_job(job)


class EccShowPopupInfoCommand(sublime_plugin.TextCommand):
    """Command that shows popup info on current cursor location."""

    def run(self, edit):
        """Run show popup info command."""
        position = self.view.sel()[0].begin()
        EasyClangComplete.begin_show_info_job(self.view, position)


class EasyClangComplete(sublime_plugin.EventListener):
    """Base class for this plugin.

    Most of the functionality is delegated.
    """
    thread_pool = ThreadPool()

    view_config_manager = None
    settings_manager = None
    current_job_id = None

    def __init__(self):
        """Initialize the object."""
        super().__init__()
        global handle_plugin_loaded_function
        global handle_plugin_unloaded_function
        handle_plugin_loaded_function = self.on_plugin_loaded
        handle_plugin_unloaded_function = self.on_plugin_unloaded

        # init instance variables to reasonable defaults
        self.current_completions = None
        self.loaded = False

    def on_plugin_unloaded(self):
        """Manage what we do when the plugin is unloaded."""
        log.debug("plugin unloaded")
        self.loaded = False

    def on_plugin_loaded(self):
        """Call upon plugin load event."""
        # init settings manager
        self.loaded = True
        log.debug("handle plugin loaded")
        EasyClangComplete.settings_manager = SettingsManager()
        # self.on_settings_changed()
        EasyClangComplete.settings_manager.add_change_listener(
            self.on_settings_changed)
        self.on_settings_changed()
        # init view config manager
        EasyClangComplete.view_config_manager = ViewConfigManager()

        # As the plugin has just loaded, we might have missed an activation
        # event for the active view so completion will not work for it until
        # re-activated. Force active view initialization in that case.
        self.on_activated_async(sublime.active_window().active_view())

    def on_settings_changed(self):
        """Call when any of the settings changes."""
        log.debug("on settings changed handle")
        if not self.loaded:
            log.warning(
                " cannot process settings change as plugin is not loaded")
            return
        if not EasyClangComplete.settings_manager:
            EasyClangComplete.settings_manager = SettingsManager()
        user_settings = EasyClangComplete.settings_manager.user_settings()
        if user_settings.verbose:
            ch.setFormatter(formatter_verbose)
            ch.setLevel(logging.DEBUG)
        else:
            ch.setFormatter(formatter_default)
            ch.setLevel(logging.INFO)

        if user_settings.need_reparse():
            # stop processing this if the settings are still invalid
            return

        # set progress status
        progress_style_tag = user_settings.progress_style
        if progress_style_tag == SettingsStorage.MOON_STYLE_TAG:
            progress_style = MoonProgressStatus()
        elif progress_style_tag == SettingsStorage.COLOR_SUBLIME_STYLE_TAG:
            progress_style = ColorSublimeProgressStatus()
        else:
            progress_style = NoneSublimeProgressStatus()
        EasyClangComplete.thread_pool.progress_status = progress_style

    def on_activated_async(self, view):
        """Call upon activating a view. Execution in a worker thread.

        Args:
            view (sublime.View): current view

        """
        # disable on_activated_async when running tests
        if view.settings().get("disable_easy_clang_complete"):
            return
        if not SublBridge.is_valid_view(view):
            try:
                EasyClangComplete.thread_pool.progress_status.erase_status()
            except AttributeError as e:
                log.debug("cannot clear status, %s", e)
            return

        settings = EasyClangComplete.settings_manager.settings_for_view(view)
        if (not SublBridge.has_valid_syntax(view, settings)) \
                or File.is_ignored(
                    view.file_name(), settings.ignore_list):
            try:
                EasyClangComplete.thread_pool.progress_status.erase_status()
            except AttributeError as e:
                log.debug("cannot clear status, %s", e)
            return
        EasyClangComplete.thread_pool.progress_status.showing = True
        log.debug("on_activated_async view id %s", view.buffer_id())
        # All is taken care of. The view is built if needed.
        job = ThreadJob(
            name=ThreadJob.UPDATE_TAG,
            callback=EasyClangComplete.config_updated,
            function=EasyClangComplete.view_config_manager.load_for_view,
            args=[view, settings])
        EasyClangComplete.thread_pool.new_job(job)

    def on_selection_modified_async(self, view):
        """Call when selection is modified. Executed in gui thread.

        Args:
            view (sublime.View): current view
        """
        if not SublBridge.is_valid_view(view):
            return
        settings = EasyClangComplete.settings_manager.settings_for_view(view)
        if not SublBridge.has_valid_syntax(view, settings):
            return
        if File.is_ignored(view.file_name(), settings.ignore_list):
            return
        row_col = ZeroIndexedRowCol.from_current_cursor_pos(view)
        view_config = EasyClangComplete.view_config_manager.get_from_cache(
            view)
        if not view_config:
            return
        if not view_config.completer:
            return
        view_config.completer.error_vis.show_popup_if_needed(view, row_col.row)

    def on_modified_async(self, view):
        """Call in a worker thread when view is modified.

        Args:
            view (sublime.View): current view
        """
        if SublBridge.is_valid_view(view):
            log.debug("on_modified_async view id %s", view.buffer_id())
            view_config = EasyClangComplete.view_config_manager.get_from_cache(
                view)
            if not view_config:
                return
            if not view_config.completer:
                return
            view_config.completer.error_vis.clear(view)

    def on_post_save_async(self, view):
        """Execute in a worker thread on save.

        Args:
            view (sublime.View): current view

        """
        # disable on_activated_async when running tests
        if view.settings().get("disable_easy_clang_complete"):
            return
        if not SublBridge.is_valid_view(view):
            return
        if view.file_name().endswith('.sublime-project'):
            if not EasyClangComplete.settings_manager:
                log.error("no settings manager, no cannot reload settings")
                return
            log.debug("Project file changed. Reloading settings.")
            EasyClangComplete.settings_manager.on_settings_changed()
        settings = EasyClangComplete.settings_manager.settings_for_view(view)
        if not SublBridge.has_valid_syntax(view, settings):
            return
        if File.is_ignored(view.file_name(), settings.ignore_list):
            return
        log.debug("saving view: %s", view.buffer_id())
        job = ThreadJob(
            name=ThreadJob.UPDATE_TAG,
            callback=EasyClangComplete.config_updated,
            function=EasyClangComplete.view_config_manager.load_for_view,
            args=[view, settings])
        EasyClangComplete.thread_pool.new_job(job)
        # invalidate current completions
        self.current_completions = None

    def on_close(self, view):
        """Call on closing the view.

        Args:
            view (sublime.View): current view

        """
        if not SublBridge.is_valid_view(view):
            # View is invalid, so just ignore it.
            return
        if not EasyClangComplete.settings_manager.has_settings_for_view(view):
            # View is valid, but is temporary and was never actually opened.
            # This mostly happens when previewing views while in Ctrl + P
            # environment. Do nothing for such a view.
            return
        # Now we know that the view is valid and we need to clear it.
        log.debug("closing view %s", view.buffer_id())
        EasyClangComplete.settings_manager.clear_for_view(view)
        file_id = view.buffer_id()
        job = ThreadJob(
            name=ThreadJob.CLEAR_TAG,
            callback=EasyClangComplete.config_removed,
            function=EasyClangComplete.view_config_manager.clear_for_view,
            args=[file_id])
        EasyClangComplete.thread_pool.new_job(job)

    @staticmethod
    def config_removed(future):
        """Call this callback when config has been removed for a view.

        The corresponding view id is saved in future.result()

        Args:
            future (concurrent.Future): future holding id of removed view
        """
        if future.done() and not future.cancelled():
            log.debug("removed config for id: %s", future.result())
        else:
            log.debug("could not remove config -> cancelled")

    @staticmethod
    def config_updated(future):
        """Call this callback when config has been updated for a view.

        Args:
            future (concurrent.Future): future holding config of updated view
        """
        if future.done() and not future.cancelled():
            log.debug("updated config: %s", future.result())
        else:
            log.debug("could not update config -> cancelled")

    @staticmethod
    def on_open_declaration(location):
        """Call this callback when link to type is clicked in info popup.

        Opens location with type declaration

        """
        sublime.active_window().open_file(location, sublime.ENCODED_POSITION)

    @staticmethod
    def info_finished(future):
        """Call this callback when additional information for tag is available.

        Creates popup containing information about text under the cursor

        """
        if not future.done():
            return
        if future.cancelled():
            return
        (tooltip_request, current_popup) = future.result()
        if not tooltip_request:
            return
        if tooltip_request.get_identifier() != EasyClangComplete.current_job_id:
            return
        if not current_popup:
            return
        view = tooltip_request.get_view()
        current_popup.show(view,
                           location=tooltip_request.get_trigger_position(),
                           on_navigate=EasyClangComplete.on_open_declaration)

    def completion_finished(self, future):
        """Call this callback when completion async function has returned.

        Checks if job id equals the one that is expected now and updates the
        completion list that is going to be used in on_query_completions

        Args:
            future (concurrent.Future): future holding completion result
        """
        if not future.done():
            return
        if future.cancelled():
            return
        (completion_request, completions) = future.result()
        if not completion_request:
            return
        current_job_id = EasyClangComplete.current_job_id
        if completion_request.get_identifier() != current_job_id:
            return
        active_view = sublime.active_window().active_view()
        if completion_request.is_suitable_for_view(active_view):
            self.current_completions = completions
        else:
            log.debug("ignoring completions")
            self.current_completions = []
        if self.current_completions:
            # we only want to trigger the autocompletion popup if there
            # are new completions to show there. Otherwise let it be.
            SublBridge.show_auto_complete(active_view)

    def on_hover(self, view, point, hover_zone):
        """Call this when mouse pointer hovers over text.

        Triggers showing popup with additional information about element under
        cursor.

        """
        if hover_zone != sublime.HOVER_TEXT:
            return
        EasyClangComplete.begin_show_info_job(view, point)

    @staticmethod
    def begin_show_info_job(view, position):
        """Start thead job to show popup info.

        Triggers showing popup with additional information about about
        element at position.
        """
        if not SublBridge.is_valid_view(view):
            return

        settings = EasyClangComplete.settings_manager.settings_for_view(view)
        if not SublBridge.has_valid_syntax(view, settings):
            return
        if not settings.show_type_info:
            return

        tooltip_request = ActionRequest(view, position)
        EasyClangComplete.current_job_id = tooltip_request.get_identifier()

        job = ThreadJob(
            name=ThreadJob.INFO_TAG,
            callback=EasyClangComplete.info_finished,
            function=EasyClangComplete.view_config_manager.trigger_info,
            args=[view, tooltip_request, settings])
        EasyClangComplete.thread_pool.new_job(job)

    def on_query_completions(self, view, prefix, locations):
        """Call this when user queries completions in the code.

        Args:
            view (sublime.View): current view
            prefix (TYPE): Description
            locations (list[int]): positions of the cursor (first if many)

        Returns:
            sublime.Completions: completions with a flag.

        """
        if not SublBridge.is_valid_view(view):
            log.debug("not a valid view")
            return SublBridge.SHOW_DEFAULT_COMPLETIONS

        # get settings for this view
        settings = EasyClangComplete.settings_manager.settings_for_view(view)

        if not SublBridge.has_valid_syntax(view, settings):
            log.debug("we don't work with this syntax")
            return SublBridge.SHOW_DEFAULT_COMPLETIONS

        if File.is_ignored(view.file_name(), settings.ignore_list):
            log.debug("This file matches 'ignore_list' setting. Ignoring.")
            return SublBridge.SHOW_DEFAULT_COMPLETIONS

        log.debug("on_query_completions view id %s", view.buffer_id())
        log.debug("prefix: %s, locations: %s" % (prefix, locations))
        trigger_pos = locations[0] - len(prefix)
        completion_request = ActionRequest(view, trigger_pos)
        current_pos_id = completion_request.get_identifier()
        pos_status = SublBridge.get_pos_status(trigger_pos, view, settings)
        log.debug("this position has identifier: '%s'", current_pos_id)

        current_job_id = EasyClangComplete.current_job_id
        if self.current_completions and current_pos_id == current_job_id:
            log.debug("returning existing completions")
            return SublBridge.format_completions(
                self.current_completions,
                settings.hide_default_completions)

        # Verify that character under the cursor is one allowed trigger
        if pos_status == PosStatus.WRONG_TRIGGER:
            # we are at a wrong trigger, remove all completions from the list
            log.debug("wrong trigger")
            log.debug("hiding default completions")
            return SublBridge.HIDE_DEFAULT_COMPLETIONS
        if pos_status == PosStatus.COMPLETION_NOT_NEEDED:
            log.debug("completion not needed")
            # show default completions for now if allowed
            if settings.hide_default_completions:
                log.debug("hiding default completions")
                return SublBridge.HIDE_DEFAULT_COMPLETIONS
            log.debug("showing default completions")
            return SublBridge.SHOW_DEFAULT_COMPLETIONS

        EasyClangComplete.current_job_id = current_pos_id
        log.debug("starting async auto_complete with id: %s",
                  EasyClangComplete.current_job_id)

        if pos_status == PosStatus.COMPLETION_NEEDED:
            # submit async completion job
            config_manager = EasyClangComplete.view_config_manager
            job = ThreadJob(
                name=ThreadJob.COMPLETE_TAG,
                callback=self.completion_finished,
                function=config_manager.trigger_completion,
                args=[view, completion_request])
            EasyClangComplete.thread_pool.new_job(job)
        elif pos_status == PosStatus.COMPLETE_INCLUDES:
            log.debug("Completing includes")
            # submit async completion job
            config_manager = EasyClangComplete.view_config_manager
            view_config = config_manager.get_from_cache(view)
            include_folders = view_config.include_folders
            # submit async completion job for getting headers
            job = ThreadJob(
                name=ThreadJob.COMPLETE_INCLUDES_TAG,
                callback=self.completion_finished,
                function=include_parser.get_all_headers,
                args=[include_folders,
                      prefix,
                      settings.force_unix_includes,
                      completion_request])
            EasyClangComplete.thread_pool.new_job(job)

        # show default completions for now if allowed
        if settings.hide_default_completions:
            log.debug("hiding default completions")
            return SublBridge.HIDE_DEFAULT_COMPLETIONS
        log.debug("showing default completions")
        return SublBridge.SHOW_DEFAULT_COMPLETIONS
