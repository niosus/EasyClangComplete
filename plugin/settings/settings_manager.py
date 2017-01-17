"""This module holds a class that manages access to plugin settings.

Attributes:
    log (logging.Logger): logger for current module
"""
import sublime
import logging
import copy

from ..tools import PKG_NAME

from .settings_storage import SettingsStorage

log = logging.getLogger(__name__)
log.debug(" reloading module %s", __name__)


class SettingsManager:
    """A class that manages the plugin settings.

    It has default settings initialized from generic user settings and stores
    a dictionary of view-specific settings. It also manages access to those.

    Args:
        __default_settings (settings.SettingsStorage): default user settings
        __settings_dict (dict): dictionary of view-specific settings
        __change_listeners (function[]): list of change listeners

    """
    __default_settings = None
    __settings_dict = {}

    __change_listeners = []

    def __init__(self):
        """Initialize the class by loading the default user settings."""
        self.__init_default_settings()

    def settings_for_view(self, view):
        """Get settings stored for a view.

        Args:
            view (sublime.View): current view

        Returns:
            settings.SettingsStorage: settings for view
        """
        view_id = view.buffer_id()
        if view_id not in self.__settings_dict:
            log.debug(" no settings for view %s. Reinitializing.", view_id)
            self.__init_for_view(view)
        if view_id in self.__settings_dict:
            # when the view is closed quickly there can be an error here
            return self.__settings_dict[view_id]
        return None

    def clear_for_view(self, view):
        """Clear settings stored for view.

        Args:
            view (sublime.View): current view
        """
        view_id = view.buffer_id()
        if view_id in self.__settings_dict:
            log.debug(" clearing settings for view: %s", view_id)
            del self.__settings_dict[view_id]

    def user_settings(self):
        """Get default user settings (not influenced by a current view).

        Returns:
            settings.SettingsStorage: default user settings
        """
        return self.__default_settings

    def add_change_listener(self, listener):
        """Register given listener to be notified whenever settings change.

        Args:
            listener (function): function to call on settings change
        """
        if listener in self.__change_listeners:
            log.error(' this settings listener was already added before')
        self.__change_listeners.append(listener)

    def __init_for_view(self, view):
        """Generate new SettingsStorage for a view.

        Builds upon default settings, updating the values from the current
        view project.

        Args:
            view (sublime.View): current View
        """
        view_id = view.buffer_id()
        self.__settings_dict[view_id] = copy.deepcopy(self.__default_settings)
        self.__settings_dict[view_id].update_from_view(view)
        log.debug(" settings initialized for view: %s", view_id)

    def __on_settings_changed(self):
        """When user changes settings, trigger this."""
        self.__init_default_settings()

        # clear all saved view-specific settings.
        self.__settings_dict.clear()

        # notify all the listeners
        for listener in self.__change_listeners:
            listener()
        log.info(" settings changed and reloaded")

    def __init_default_settings(self):
        """Initialize default user settings.

        Raises:
            RuntimeError: If settings are not loaded, throw an error
        """
        self.__subl_settings = sublime.load_settings(
            PKG_NAME + ".sublime-settings")
        self.__subl_settings.clear_on_change(PKG_NAME)
        self.__subl_settings.add_on_change(PKG_NAME,
                                           self.__on_settings_changed)

        # initialize default settings
        self.__default_settings = SettingsStorage(self.__subl_settings)

        # check validity
        if not self.__default_settings.is_valid():
            log.critical(" Could not load settings!")
            log.critical(" NO AUTOCOMPLETE WILL BE AVAILABLE")
            raise RuntimeError("Settings could not be loaded.")
