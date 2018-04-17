"""Module contains options for various compiler variants.

Attributes:
    log (logging.Logger): logger for this module
"""
import re
import logging

from ..utils.flag import Flag

log = logging.getLogger("ECC")


class CompilerVariant(object):
    """Encapsulation of a compiler specific options."""

    need_lang_flags = True
    init_flags = [Flag("-c"), Flag("-fsyntax-only")]

    def errors_from_output(self, output):
        """Parse errors received from the compiler.

        Args:
            output (object): opaque output to be parsed by compiler variant

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")


class ClangCompilerVariant(CompilerVariant):
    """Encapsulation of clang/clang++ specific options.

    Attributes:
        error_regex (re): regex to find contents of an error
    """
    include_prefixes = ["-isystem", "-I", "-isysroot"]
    error_regex = re.compile(r"(?P<file>.*)" +
                             r":(?P<row>\d+):(?P<col>\d+)" +
                             r":\s*.*error: (?P<error>.*)")

    def errors_from_output(self, output):
        """Parse errors received from clang binary output.

        Args:
            view (sublime.View): current view
            clang_output (string): list of unparsed errors

        Returns:
            list(dict): a list of parsed errors
        """
        errors = []
        for line in output.splitlines():
            error_search = self.error_regex.search(line)
            if not error_search:
                continue
            error_dict = error_search.groupdict()
            errors.append(error_dict)
        return errors


class ClangClCompilerVariant(ClangCompilerVariant):
    """Encapsulation of clang-cl specific options.

    Attributes:
        error_regex (re): regex to find contents of an error
    """
    need_lang_flags = False
    include_prefixes = ["-I", "/I", "-msvc", "/msvc"]
    error_regex = re.compile(r"(?P<file>.*)" +
                             r"\((?P<row>\d+),(?P<col>\d+)\)\s*" +
                             r":\s*.*error: (?P<error>.*)")


class LibClangCompilerVariant(ClangCompilerVariant):
    """Encapsulation of libclang specific options.

    Attributes:
        pos_regex (re): regex to find position of an error
        msg_regex (re): regex to find error message
    """
    pos_regex = re.compile(r"'(?P<file>.+)'.*" +  # file
                           r"line\s(?P<row>\d+), " +  # row
                           r"column\s(?P<col>\d+)")  # col
    msg_regex = re.compile(r'[b\"|\"]*(?P<error>[^"]+)\"*')
    SEVERITY_TAG = 'severity'

    def errors_from_output(self, output):
        """Parse errors received from diagnostics of a translation unit.

        This is used with libclang.

        Args:
            output (diagnostics): diagnostics from a translation unit

        Returns:
            list(dict): a list of parsed errors
        """
        errors = []
        for diag in output:
            location = str(diag.location)
            spelling = str(diag.spelling)
            severity = diag.severity
            # [HACK]: have found no other way as there seems to be no option to
            # pass to libclang to avoid producing this error
            if "#pragma once" in spelling:
                log.debug("explicitly omit warning about pragma once.")
                continue
            pos_search = self.pos_regex.search(location)
            msg_search = self.msg_regex.search(spelling)
            if not pos_search:
                # not valid, continue
                log.debug("regex %s failed to match location: %s",
                          self.pos_regex.pattern, location)
                continue
            if not msg_search:
                # maybe there was no error word, so show everything there is
                log.debug("regex %s failed to match error: %s",
                          self.msg_regex.pattern, spelling)
                continue
            error_dict = pos_search.groupdict()
            error_dict.update(msg_search.groupdict())
            error_dict[LibClangCompilerVariant.SEVERITY_TAG] = severity
            errors.append(error_dict)
        return errors
