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


@functools.cache
def load_settings() -> Settings:
    config_file = Path(platformdirs.user_config_dir(APP_NAME)) / "config.toml"
    return ts.load_settings(
        cls=Settings,
        loaders=(
            ts.FileLoader(
                files=(config_file,),
                formats={"*.toml": ts.TomlFormat(None)},
            ),
        ),
    )
