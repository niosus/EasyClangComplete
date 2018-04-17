"""Find all includes."""
from os import path
import logging

log = logging.getLogger("ECC")


def get_all_headers(folders, prefix, completion_request):
    """Parse all the folders and return all headers."""
    import os
    import fnmatch
    matches = []
    for folder in folders:
        log.debug("Going through: %s", folder)
        for root, _, filenames in os.walk(folder):
            for filename in fnmatch.filter(filenames, '*.h*'):
                match = path.join(root, filename)
                match = path.relpath(match, folder)
                if not match.startswith(prefix):
                    continue
                matches.append(
                    ["{}\t{}".format(match, folder), match])
    return completion_request, matches
