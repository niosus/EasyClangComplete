"""EasyClangComplete plugin for Sublime Text 3.

Provides completion suggestions for C/C++ languages based on clang

Attributes:
    log (logging.Logger): logger for this module
"""

import sublime
import sublime_plugin
import logging
import shutil
import imp

from os import path

from .plugin import tools
from .plugin import error_vis
from .plugin import view_config
from .plugin import flags_sources
from .plugin.utils import thread_pool
from .plugin.settings import settings_manager
from .plugin.completion import lib_complete
from .plugin.completion import bin_complete

# reload the modules
imp.reload(tools)
imp.reload(settings_manager)
imp.reload(error_vis)
imp.reload(lib_complete)
imp.reload(bin_complete)
imp.reload(view_config)
imp.reload(thread_pool)
imp.reload(flags_sources)

# some aliases
SettingsManager = settings_manager.SettingsManager
ViewConfigManager = view_config.ViewConfigManager
SublBridge = tools.SublBridge
Tools = tools.Tools
PosStatus = tools.PosStatus
CMakeFile = flags_sources.cmake_file.CMakeFile
CMakeFileCache = flags_sources.cmake_file.CMakeFileCache
ThreadPool = thread_pool.ThreadPool
ThreadJob = thread_pool.ThreadJob

log = logging.getLogger(__name__)

handle_plugin_loaded_function = None


def plugin_loaded():
    """Called right after sublime api is ready to use.

    We need it to initialize all the different classes that encapsulate
    functionality. We can only properly init them after sublime api is
    available."""
    handle_plugin_loaded_function()


class CleanCmakeCommand(sublime_plugin.TextCommand):
    """Command that cleans cmake build directory."""

    def run(self, edit):
        """Run clean command.

        Detects if there is a CMakeLists.txt associated to current view and
        cleans all related information in case there is one.
        """
        if not Tools.is_valid_view(self.view):
            return
        file_path = self.view.file_name()
        cmake_cache = CMakeFileCache()
        try:
            cmake_file_path = cmake_cache[file_path]
            log.debug(" Cleaning file: '%s'", cmake_file_path)
            del cmake_cache[file_path]
            del cmake_cache[cmake_file_path]
            temp_proj_dir = CMakeFile.unique_folder_name(cmake_file_path)
            if path.exists(temp_proj_dir):
                log.debug(" Cleaning build directory: '%s'", temp_proj_dir)
                shutil.rmtree(temp_proj_dir, ignore_errors=True)
        except KeyError:
            log.debug(" Nothing to clean")


class EasyClangComplete(sublime_plugin.EventListener):
    """Base class for this plugin.

    Most of the functionality is delegated.
    """
    thread_pool = ThreadPool(max_workers=4)

    current_job_id = None
    current_completions = []

    CLEAR_JOB_TAG = "clear"
    COMPLETE_JOB_TAG = "complete"
    UPDATE_JOB_TAG = "update"
    INFO_JOB_TAG = "info"

    def __init__(self):
        """Initialize the object."""
        super().__init__()
        global handle_plugin_loaded_function
        handle_plugin_loaded_function = self.on_plugin_loaded
        # By default be verbose and limit on settings change if verbose flag is
        # not set.
        logging.basicConfig(level=logging.DEBUG)

    def on_plugin_loaded(self):
        """Called upon plugin load event."""
        # init settings manager
        self.settings_manager = SettingsManager()
        self.on_settings_changed()
        self.settings_manager.add_change_listener(self.on_settings_changed)
        # init view config manager
        self.view_config_manager = ViewConfigManager()
        # As the plugin have just loaded, we might have missed an activation
        # event for the active view so completion will not work for it until
        # re-activated. Force active view initialization in that case.
        self.on_activated_async(sublime.active_window().active_view())

    def on_settings_changed(self):
        """Called when any of the settings changes."""
        user_settings = self.settings_manager.user_settings()
        # If verbose flag is set then respect default DEBUG level.
        # Otherwise disable level DEBUG and allow INFO and higher levels.
        off_level = logging.NOTSET if user_settings.verbose else logging.DEBUG
        logging.disable(level=off_level)

    def on_activated_async(self, view):
        """Called upon activating a view. Execution in a worker thread.

        Args:
            view (sublime.View): current view

        """
        # disable on_activated_async when running tests
        if view.settings().get("disable_easy_clang_complete"):
            return
        if Tools.is_valid_view(view):
            log.debug(" on_activated_async view id %s", view.buffer_id())
            settings = self.settings_manager.settings_for_view(view)
            # All is taken care of. The view is built if needed.
            job = ThreadJob(name=EasyClangComplete.UPDATE_JOB_TAG,
                            callback=EasyClangComplete.config_updated,
                            function=self.view_config_manager.load_for_view,
                            args=[view, settings])
            EasyClangComplete.thread_pool.new_job(job)

    def on_selection_modified(self, view):
        """Called when selection is modified. Executed in gui thread.

        Args:
            view (sublime.View): current view
        """
        if Tools.is_valid_view(view):
            (row, _) = SublBridge.cursor_pos(view)
            view_config = self.view_config_manager.get_from_cache(view)
            if not view_config:
                return
            if not view_config.completer:
                return
            view_config.completer.error_vis.show_popup_if_needed(view, row)

    def on_modified_async(self, view):
        """Called in a worker thread when view is modified.

        Args:
            view (sublime.View): current view
        """
        if Tools.is_valid_view(view):
            log.debug(" on_modified_async view id %s", view.buffer_id())
            view_config = self.view_config_manager.get_from_cache(view)
            if not view_config:
                return
            if not view_config.completer:
                return
            view_config.completer.error_vis.clear(view)

    def on_post_save_async(self, view):
        """Executed in a worker thread on save.

        Args:
            view (sublime.View): current view

        """
        # disable on_activated_async when running tests
        if view.settings().get("disable_easy_clang_complete"):
            return
        if Tools.is_valid_view(view):
            log.debug(" saving view: %s", view.buffer_id())
            settings = self.settings_manager.settings_for_view(view)
            job = ThreadJob(name=EasyClangComplete.UPDATE_JOB_TAG,
                            callback=EasyClangComplete.config_updated,
                            function=self.view_config_manager.load_for_view,
                            args=[view, settings])
            EasyClangComplete.thread_pool.new_job(job)

    def on_close(self, view):
        """Called on closing the view.

        Args:
            view (sublime.View): current view

        """
        if Tools.is_valid_view(view):
            log.debug(" closing view %s", view.buffer_id())
            self.settings_manager.clear_for_view(view)
            file_path = view.buffer_id()
            job = ThreadJob(name=EasyClangComplete.CLEAR_JOB_TAG,
                            callback=EasyClangComplete.config_removed,
                            function=self.view_config_manager.clear_for_view,
                            args=[file_path])
            EasyClangComplete.thread_pool.new_job(job)

    @staticmethod
    def config_removed(future):
        """Callback called when config has been removed for a view.

        The corresponding view id is saved in future.result()

        Args:
            future (concurrent.Future): future holding id of removed view
        """
        if future.done():
            log.debug(" removed config for id: %s", future.result())
        elif future.cancelled():
            log.debug(" could not remove config -> cancelled")

    @staticmethod
    def config_updated(future):
        """Callback called when config has been updated for a view.

        Args:
            future (concurrent.Future): future holding config of updated view
        """
        if future.done():
            log.debug(" updated config: %s", future.result())
        elif future.cancelled():
            log.debug(" could not update config -> cancelled")

    @staticmethod
    def on_open_declaration(location):
        """Callback called when link to type is clicked in info popup.

        Opens location with type declaration

        """
        sublime.active_window().open_file(location, sublime.ENCODED_POSITION)

    def info_finished(self, future):
        """Callback called when additional information for tag is available.

        Creates popup containing information about text under the cursor

        """
        if not future.done():
            return
        (tooltip_request, result) = future.result()
        if result == "":
            return
        if not tooltip_request:
            return
        if tooltip_request.get_identifier() != self.current_job_id:
            return
        view = tooltip_request.get_view()
        view.show_popup(result,
                        location=tooltip_request.get_trigger_position(),
                        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                        max_width=1000,
                        on_navigate=self.on_open_declaration)

    def completion_finished(self, future):
        """Callback called when completion async function has returned.

        Checks if job id equals the one that is expected now and updates the
        completion list that is going to be used in on_query_completions

        Args:
            future (concurrent.Future): future holding completion result
        """
        if not future.done():
            return
        (completion_request, completions) = future.result()
        if not completion_request:
            return
        if completion_request.get_identifier() != self.current_job_id:
            return
        active_view = sublime.active_window().active_view()
        if completion_request.is_suitable_for_view(active_view):
            self.current_completions = completions
        else:
            log.debug(" ignoring completions")
            self.current_completions = []
        if self.current_completions:
            # we only want to trigger the autocompletion popup if there
            # are new completions to show there. Otherwise let it be.
            SublBridge.show_auto_complete(active_view)

    def on_hover(self, view, point, hover_zone):
        """Function that is called when mouse pointer hovers over text.

        Triggers showing popup with additional information about element under
        cursor.

        """
        if not Tools.is_valid_view(view):
            return

        settings = self.settings_manager.settings_for_view(view)
        if not settings.show_type_info:
            return
        if hover_zone != sublime.HOVER_TEXT:
            return
        tooltip_request = tools.ActionRequest(view, point)
        view_config = self.view_config_manager.get_from_cache(view)
        if not view_config:
            return
        self.current_job_id = tooltip_request.get_identifier()

        job = ThreadJob(name=EasyClangComplete.INFO_JOB_TAG,
                        callback=self.info_finished,
                        function=view_config.completer.info,
                        args=[tooltip_request])
        EasyClangComplete.thread_pool.new_job(job)

    def on_query_completions(self, view, prefix, locations):
        """Function that is called when user queries completions in the code.

        Args:
            view (sublime.View): current view
            prefix (TYPE): Description
            locations (list[int]): positions of the cursor (first if many).

        Returns:
            sublime.Completions: completions with a flag
        """
        if not Tools.is_valid_view(view):
            log.debug(" not a valid view")
            return Tools.SHOW_DEFAULT_COMPLETIONS

        log.debug(" on_query_completions view id %s", view.buffer_id())
        log.debug(" prefix: %s, locations: %s" % (prefix, locations))
        trigger_pos = locations[0] - len(prefix)
        completion_request = tools.ActionRequest(view, trigger_pos)
        current_pos_id = completion_request.get_identifier()
        log.debug(" this position has identifier: '%s'", current_pos_id)

        # get settings for this view
        settings = self.settings_manager.settings_for_view(view)
        # get view config
        view_config = self.view_config_manager.get_from_cache(view)
        if not view_config:
            log.debug(" no view config")
            return Tools.SHOW_DEFAULT_COMPLETIONS

        if self.current_completions and current_pos_id == self.current_job_id:
            log.debug(" returning existing completions")
            return SublBridge.format_completions(
                self.current_completions,
                settings.hide_default_completions)

        # Verify that character under the cursor is one allowed trigger
        pos_status = Tools.get_pos_status(trigger_pos, view, settings)
        if pos_status == PosStatus.WRONG_TRIGGER:
            # we are at a wrong trigger, remove all completions from the list
            log.debug(" wrong trigger")
            log.debug(" hiding default completions")
            return Tools.HIDE_DEFAULT_COMPLETIONS
        if pos_status == PosStatus.COMPLETION_NOT_NEEDED:
            log.debug(" completion not needed")
            # show default completions for now if allowed
            if settings.hide_default_completions:
                log.debug(" hiding default completions")
                return Tools.HIDE_DEFAULT_COMPLETIONS
            log.debug(" showing default completions")
            return Tools.SHOW_DEFAULT_COMPLETIONS

        self.current_job_id = current_pos_id
        log.debug(" starting async auto_complete with id: %s",
                  self.current_job_id)

        # submit async completion job
        job = ThreadJob(name=EasyClangComplete.COMPLETE_JOB_TAG,
                        callback=self.completion_finished,
                        function=view_config.completer.complete,
                        args=[completion_request])
        EasyClangComplete.thread_pool.new_job(job)

        # show default completions for now if allowed
        if settings.hide_default_completions:
            log.debug(" hiding default completions")
            return Tools.HIDE_DEFAULT_COMPLETIONS
        log.debug(" showing default completions")
        return Tools.SHOW_DEFAULT_COMPLETIONS
