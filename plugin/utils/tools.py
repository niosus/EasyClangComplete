"""Collection of various tools."""
from os import path
from os import environ

import sublime
import logging
import subprocess


PKG_NAME = path.basename(path.dirname(path.dirname(path.dirname(__file__))))
PKG_FOLDER = path.dirname(path.dirname(path.dirname(__file__)))

_log = logging.getLogger("ECC")


class Tools:
    """Just a bunch of helpful tools."""

    @staticmethod
    def seconds_from_string(time_str):
        """Get int seconds from string.

        Args:
            time_str (str): string in format 'HH:MM:SS'

        Returns:
            int: seconds
        """
        h, m, s = time_str.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)

    @staticmethod
    def run_command(command, shell=False, cwd=path.curdir, env=environ,
                    stdin=None, default=None):
        """Run a generic command in a subprocess.

        Args:
            command (str): command to run
            stdin: The standard input channel for the started process.
            default (andy): The default return value in case run fails.

        Returns:
            str: raw command output or default value
        """
        output_text = default
        try:
            startupinfo = None
            if sublime.platform() == "windows":
                # Don't let console window pop-up briefly.
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                if stdin is None:
                    stdin = subprocess.PIPE
            output = subprocess.check_output(command,
                                             stdin=stdin,
                                             stderr=subprocess.STDOUT,
                                             shell=shell,
                                             cwd=cwd,
                                             env=env,
                                             startupinfo=startupinfo)
            output_text = ''.join(map(chr, output))
        except subprocess.CalledProcessError as e:
            output_text = e.output.decode("utf-8")
            _log.debug("Command finished with code: %s", e.returncode)
            _log.debug("Command output: \n%s", output_text)
        except OSError:
            _log.debug(
                "Executable file not found executing: {}".format(command))
        return output_text

    @staticmethod
    def get_unique_str(init_string):
        """Generate md5 unique sting hash given init_string."""
        import hashlib
        augmented_string = init_string + path.expanduser('~')
        return hashlib.md5(augmented_string.encode('utf-8')).hexdigest()
