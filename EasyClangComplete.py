"""EasyClangComplete plugin for Sublime Text 3.

Provides completion suggestions for C/C++ languages based on clang

Attributes:
    log (logging.Logger): logger for this module
"""

import sublime
import sublime_plugin
import imp
import logging

from concurrent import futures

from .plugin import tools
from .plugin import error_vis
from .plugin.settings import settings_manager
from .plugin.completion import lib_complete
from .plugin.completion import bin_complete

# reload the modules
imp.reload(tools)
imp.reload(settings_manager)
imp.reload(error_vis)
imp.reload(lib_complete)
imp.reload(bin_complete)

# some aliases
SettingsManager = settings_manager.SettingsManager
SublBridge = tools.SublBridge
Tools = tools.Tools
PosStatus = tools.PosStatus

log = logging.getLogger(__name__)

handle_plugin_loaded_function = None


def plugin_loaded():
    """ Called right after sublime api is ready to use. We need it to initialize
    all the different classes that encapsulate functionality. We can only
    properly init them after sublime api is available."""
    handle_plugin_loaded_function()


class EasyClangComplete(sublime_plugin.EventListener):
    """Base class for this plugin.

    Most of the functionality is delegated.

    Attributes:
        settings (plugin_settings.Settings): class that encapsulates settings
        completer (plugin.completion.base_completion.BaseCompleter):
            This object handles auto completion.
            It can be one of the following:
            - bin_complete.Completer
            - lib_complete.Completer
    """
    settings = None
    completer = None

    pool_read = futures.ThreadPoolExecutor(max_workers=4)

    current_job_id = None
    current_completions = []

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
        self.settings_manager = SettingsManager()
        self.on_settings_changed()
        self.settings_manager.add_change_listener(self.on_settings_changed)
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

        # init everything else
        self.completer = None
        if user_settings.use_libclang:
            log.info(" init completer based on libclang")
            self.completer = lib_complete.Completer(user_settings.clang_binary)
            if not self.completer.valid:
                log.error(" cannot initialize completer with libclang.")
                log.info(" falling back to using clang in a subprocess.")
                self.completer = None
        if not self.completer:
            log.info(" init completer based on clang from cmd")
            self.completer = bin_complete.Completer(user_settings.clang_binary)

    def on_activated_async(self, view):
        """Called upon activating a view. Execution in a worker thread.

        Args:
            view (sublime.View): current view

        """
        log.debug(" on_activated_async view id %s", view.buffer_id())
        if Tools.is_valid_view(view):
            if not self.completer:
                return
            # TODO(igor): reintroduce check if we need a new completer here
            settings = self.settings_manager.settings_for_view(view)
            log.debug("init completer for view id: %s", view.buffer_id())
            self.completer.init_for_view(view, settings)

    def on_selection_modified(self, view):
        """Called when selection is modified. Executed in gui thread.

        Args:
            view (sublime.View): current view
        """
        if Tools.is_valid_view(view):
            (row, _) = SublBridge.cursor_pos(view)
            if not self.completer:
                return
            self.completer.error_vis.show_popup_if_needed(view, row)

    def on_modified_async(self, view):
        """Called in a worker thread when view is modified.

        Args:
            view (sublime.View): current view
        """
        if Tools.is_valid_view(view):
            log.debug(" on_modified_async view id %s", view.buffer_id())
            if not self.completer:
                return
            self.completer.error_vis.clear(view)

    def on_post_save_async(self, view):
        """Executed in a worker thread on save.

        Args:
            view (sublime.View): current view

        """
        if Tools.is_valid_view(view):
            log.debug(" saving view: %s", view.buffer_id())
            if not self.completer:
                return
            settings = self.settings_manager.settings_for_view(view)
            self.completer.error_vis.erase_regions(view)
            self.completer.update(view, settings.errors_on_save)

    def on_close(self, view):
        """Called on closing the view.

        Args:
            view (sublime.View): current view

        """
        if Tools.is_valid_view(view):
            log.debug(" closing view %s", view.buffer_id())
            self.settings_manager.clear_for_view(view)
            if not self.completer:
                return
            future = EasyClangComplete.pool_read.submit(
                self.completer.remove, view.buffer_id())
            future.add_done_callback(EasyClangComplete.completer_removed)

    @staticmethod
    def completer_removed(future):
        """Callback called when completer has closed object for a view.

        The corresponding view id is saved in future.result()

        Args:
            future (concurrent.Future): future holding id of removed view
        """
        if future.done():
            log.debug(" removed completer for id: %s", future.result())
        elif future.cancelled():
            log.debug(" could not remove completer -> cancelled")

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
        completion_request = tools.CompletionRequest(view, trigger_pos)
        current_pos_id = completion_request.get_identifier()
        log.debug(" this position has identifier: '%s'", current_pos_id)

        # get settings for this view
        settings = self.settings_manager.settings_for_view(view)

        if not self.completer:
            log.debug(" no completer")
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
        future = EasyClangComplete.pool_read.submit(
            self.completer.complete, completion_request)
        future.add_done_callback(self.completion_finished)

        # show default completions for now if allowed
        if settings.hide_default_completions:
            log.debug(" hiding default completions")
            return Tools.HIDE_DEFAULT_COMPLETIONS
        log.debug(" showing default completions")
        return Tools.SHOW_DEFAULT_COMPLETIONS
