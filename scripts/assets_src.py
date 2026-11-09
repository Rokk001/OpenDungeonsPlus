"""Locates the asset sources (Blender files, source images) that are kept outside the repository."""
import os
from pathlib import Path

ENV_NAME = "ODP_ASSETS_SRC"
PREFIX = "assets-src"


# Returns the directory that holds the asset sources: the environment variable ODP_ASSETS_SRC if it is set, else <repo>/assets-src.
# repo is the repository root (str or Path); the result is a Path.
def assets_src_dir(repo):
    value = os.environ.get(ENV_NAME)
    if value:
        return Path(value)
    return Path(repo) / PREFIX


# Maps a repository-relative path to a real path: paths below "assets-src" are resolved through assets_src_dir(),
# all other paths stay below repo. Backslashes in relative are accepted.
def resolve(repo, relative):
    normalized = str(relative).replace("\\", "/")
    if normalized == PREFIX:
        return assets_src_dir(repo)
    if normalized.startswith(PREFIX + "/"):
        return assets_src_dir(repo) / normalized[len(PREFIX) + 1:]
    return Path(repo) / relative
