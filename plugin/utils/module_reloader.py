"""A class needed to reload modules."""
import sys
import imp
import logging

from .tools import PKG_NAME

log = logging.getLogger("ECC")


class ModuleReloader:
    """Reloader for all dependencies."""

    MAX_RELOAD_TRIES = 10

    @staticmethod
    def reload_all(ignore_string='singleton'):
        """Reload all loaded modules."""
        prefix = PKG_NAME + '.plugin.'
        # reload all twice to make sure all dependencies are satisfied
        log.debug(
            "Reloading modules that start with '%s' and don't contain '%s'",
            prefix, ignore_string)
        log.debug("Reload all modules first time")
        ModuleReloader.reload_once(prefix, ignore_string)
        log.debug("Reload all modules second time")
        ModuleReloader.reload_once(prefix, ignore_string)
        log.debug("All modules reloaded")

    @staticmethod
    def reload_once(prefix, ignore_string):
        """Reload all modules once."""
        try_counter = 0
        try:
            for name, module in sys.modules.items():
                if name.startswith(prefix) and ignore_string not in name:
                    log.debug("Reloading module: '%s'", name)
                    imp.reload(module)
        except OSError as e:
            if try_counter >= ModuleReloader.MAX_RELOAD_TRIES:
                log.fatal("Too many tries to reload and no success. Fail.")
                return
            try_counter += 1
            log.error("Received an error: %s on try %s. Try again.",
                      e, try_counter)
            ModuleReloader.reload_once(prefix, ignore_string)
