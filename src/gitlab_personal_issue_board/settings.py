import functools
from pathlib import Path
from typing import Final

import attrs
import platformdirs
import typed_settings as ts

APP_NAME: Final[str] = "gitlab-personal-issue-board"


def cache_dir() -> Path:
    """
    Path to user cache directory (existence is ensured)
    """
    result = Path(platformdirs.user_cache_dir(APP_NAME))
    result.mkdir(parents=True, exist_ok=True)
    return result


def data_dir() -> Path:
    """
    Path to data directory (existence is ensured)
    """
    result = Path(platformdirs.user_data_dir(APP_NAME))
    result.mkdir(parents=True, exist_ok=True)
    return result


@attrs.frozen
class GitlabSettings:
    config_section: str | None = None


@attrs.frozen
class Settings:
    gitlab: GitlabSettings = GitlabSettings()  # noqa: RUF009


def get_config_file() -> Path:
    return Path(platformdirs.user_config_dir(APP_NAME)) / "config.toml"


@functools.cache
def load_settings() -> Settings:
    config_file = get_config_file()
    return ts.load_settings(
        cls=Settings,
        loaders=(
            ts.FileLoader(
                files=(config_file,),
                formats={"*.toml": ts.TomlFormat(None)},
            ),
        ),
    )


def debug_settings() -> None:
    """
    Print settings and paths
    """
    config = get_config_file()
    settings = load_settings()
    if not config.is_file():
        print(f"Settings file '{config}' does not exist, ignoring.")
    else:
        print(f"Settings loaded from '{config}'.")
    if settings.gitlab.config_section:
        print(f"Using python gitlab config section {settings.gitlab.config_section}")
    print(f"Data is saved in '{data_dir()}'")
    print(f"Cache files are stored in '{cache_dir()}'")
