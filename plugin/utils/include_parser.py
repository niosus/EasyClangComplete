"""Find all includes."""
from os import path
import logging

log = logging.getLogger("ECC")


def get_all_headers(folders,
                    prefix,
                    force_unix_includes,
                    completion_request):
    """Parse all the folders and return all headers."""
    def get_match(filename, root, base_folder):
        """Get formated match as a relative path to the base_folder."""
        match = path.join(root, filename)
        match = path.relpath(match, base_folder)
        if force_unix_includes:
            match = match.replace(path.sep, '/')
        return "{}\t{}".format(match, base_folder), match

    def is_root_duplicate(root, query_folder, folders, start_idx):
        """Detect if this root can be covered by a more precise match.

        The idea here is that we go through all folders that we want to search
        in that have longer names than the one we process currently and check if
        they are included in the current root. If they are we do not want to
        include this root with respect to the current folder and want to skip it
        as it will be better explained by another folder.
        """
        for idx in range(start_idx, len(folders)):
            if root.startswith(folders[idx]):
                return True
        return False

    def to_platform_specific_paths(folders):
        """We might want to have back slashes intead of slashes."""
        for idx, folder in enumerate(folders):
            folders[idx] = path.normpath(folder)
        return folders

    import os
    import fnmatch
    matches = []
    folders.sort(key=len)
    if force_unix_includes:
        folders = to_platform_specific_paths(folders)
    for idx, folder in enumerate(folders):
        log.debug("Going through: %s", folder)
        for root, _, filenames in os.walk(folder):
            if is_root_duplicate(root, folder, folders, idx + 1):
                continue
            for filename in filenames:
                match = None
                if not fnmatch.fnmatch(filename, '*.*'):
                    # This file has no extension. It fits for us.
                    completion, match = get_match(filename, root, folder)
                if fnmatch.fnmatch(filename, '*.h*'):
                    # This file in an include file.
                    completion, match = get_match(filename, root, folder)
                if not match:
                    continue
                if not match.startswith(prefix):
                    continue
                matches.append([completion, match])
    log.debug("Includes completion list size: %s", len(matches))
    return completion_request, matches
