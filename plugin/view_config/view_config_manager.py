"""A module that stores classes related ot view configuration.

Attributes:
    log (logging.Logger): Logger for this module.
"""
import logging
import weakref
from threading import RLock
from threading import Timer

from ..utils.subl.subl_bridge import SublBridge
from ..utils.subl.row_col import ZeroIndexedRowCol

from .view_config import ViewConfig

from ..utils.singleton import ViewConfigCache
from ..utils.singleton import ThreadCache

log = logging.getLogger("ECC")

TOO_MANY_STD_FLAGS_ERROR_MSG = """
Your {which_settings} define too many std flags:
{std_flags}

Please fix your settings.
"""


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
        if not SublBridge.is_valid_view(view):
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
        if not SublBridge.is_valid_view(view):
            log.error("View %s is not valid. Cannot get config.", view)
            return None
        try:
            v_id = view.buffer_id()
            res = None
            # we need to protect this with mutex to avoid race condition
            # between creating and removing a config.
            with self.__rlock:
                if v_id in self.__cache:
                    log.debug("Config exists for path: %s", v_id)
                    res = self.__cache[v_id].update_if_needed(view, settings)
                else:
                    log.debug("Generate new config for path: %s", v_id)
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
            log.error("View became invalid while loading config: %s", e)
            log.error("Traceback: %s", tb)
            return None

    def clear_for_view(self, v_id):
        """Clear config for a view id."""
        assert isinstance(v_id, int), "View id should be an int."
        import gc
        log.debug("Trying to clear config for view: %s", v_id)
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
        rowcol = ZeroIndexedRowCol.from_current_cursor_pos(view)
        return config.completer.get_declaration_location(view, rowcol)

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
