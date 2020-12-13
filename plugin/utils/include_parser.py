"""Find all includes."""
import os
import logging
from os import path

log = logging.getLogger("ECC")


def get_all_headers(folders, force_unix_includes):
    """Parse all the folders and return all headers."""
    def to_platform_specific_paths(folders):
        """We might want to have back slashes intead of slashes."""
        for idx, folder in enumerate(folders):
            folders[idx] = path.normpath(folder)
        return folders

    matches = set()
    if force_unix_includes:
        folders = to_platform_specific_paths(folders)
    for folder in folders:
        if not path.exists(folder) or not path.isdir(folder):
            continue
        log.debug("Going through: %s", folder)
        for file_or_folder in os.listdir(folder):
            _, ext = path.splitext(file_or_folder)
            if not ext:
                # This file has no extension. It fits for us.
                matches.add(path.join(folder, file_or_folder))
                continue
            if ext.startswith(".h"):
                # This file in an include file.
                matches.add(path.join(folder, file_or_folder))
                continue
    log.debug("Includes completion list size: %s", len(matches))
    return list(matches)
