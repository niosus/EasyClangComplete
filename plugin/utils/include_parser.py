"""Find all includes."""
from os import path
import logging

log = logging.getLogger("ECC")


def get_all_headers(folders, prefix, completion_request):
    """Parse all the folders and return all headers."""
    def get_match(filename, root, base_folder):
        match = path.join(root, filename)
        match = path.relpath(match, base_folder)
        return "{}\t{}".format(match, folder), match

    import os
    import fnmatch
    matches = []
    for folder in folders:
        log.debug("Going through: %s", folder)
        for root, _, filenames in os.walk(folder):
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
