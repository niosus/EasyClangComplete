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
    init_flags = [Flag(prefix="", body="-c"),
                  Flag(prefix="", body="-fsyntax-only")]

    def errors_from_output(self, output):
        """Parse errors received from the compiler.

        Args:
            output (object): opaque output to be parsed by compiler variant

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    @staticmethod
    def _to_zero_based_index(error_dict):
        for tag in ["row", "col"]:
            error_dict[tag] = int(error_dict[tag]) - 1
        return error_dict


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
            error_dict = CompilerVariant._to_zero_based_index(error_dict)
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
        POS_REGEX (re): regex to find position of an error
    """
    POS_REGEX = re.compile(r"'(?P<file>.+)'.*" +  # file
                           r"line\s(?P<row>\d+), " +  # row
                           r"column\s(?P<col>\d+)")  # col
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
            pos_search = self.POS_REGEX.search(location)
            if not pos_search:
                # not valid, continue
                continue
            error_dict = pos_search.groupdict()
            error_dict.update({'error': spelling})
            error_dict = CompilerVariant._to_zero_based_index(error_dict)
            error_dict[LibClangCompilerVariant.SEVERITY_TAG] = severity
            errors.append(error_dict)
        return errors
