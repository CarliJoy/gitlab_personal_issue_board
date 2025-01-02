"""
Handle caching of Issues retrieved from gitlab
"""

import logging
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Union

import orjson as json
from pydantic import ValidationError

from . import settings
from .models import Issue, IssueID

if TYPE_CHECKING:
    from gitlab.base import RESTObject

type Mtime = int
type Ctime = int
type FileSize = int
type FileCacheInfo = tuple[Mtime, Ctime, FileSize]


logger = logging.getLogger(__name__)


def get_file_cache_info(file: Path) -> FileCacheInfo:
    stat = file.stat()
    return stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size


class IssueCacheDict:
    """
    A dictionary like cache holding issues keeping data on disk.

    - caches the full issue attributes but only returns `Issue` objects on disk.
    - automatically reloads Issues if the cache file is updated.
    - loads all cached issues once initialized
    """

    file_name: Final[str] = "issue_{issue_id}.json"
    _cache: dict[IssueID, tuple[FileCacheInfo, Issue]]

    def __init__(self) -> None:
        self._cache = dict(self._load_cache_files())

    def __getitem__(self, item: IssueID) -> Issue:
        issue = self._refresh_item(item)
        if issue:
            return issue
        raise KeyError(item)

    def _refresh_item(self, item: IssueID) -> Issue | None:
        cache_info, issue = self._cache.get(item, (None, None))
        cache_file = self._issue_cache_file(item)
        if cache_file.exists():
            if get_file_cache_info(cache_file) != cache_info:
                cache_info, issue = self._load_from_file(item)
                self._cache[item] = cache_info, issue
        return issue

    @classmethod
    def _converter(cls, content: bytes) -> Issue:
        return Issue.model_validate_json(content)

    def __len__(self) -> int:
        return len(self._cache)

    def values(self) -> Iterable[Issue]:
        for _, issue in self._cache.values():
            yield issue

    def keys(self) -> tuple[IssueID, ...]:
        return tuple(self._cache.keys())

    def refresh_from_disk(self) -> None:
        for elm in self._cache.keys():
            self._refresh_item(elm)

    def remove(self, remove: Callable[[Issue], bool]) -> None:
        """
        Remove all issues that meet *remove*
        """
        for issue_id, (_, issue) in tuple(self._cache.items()):
            if remove(issue):
                file = self._issue_cache_file(issue_id)
                del self._cache[issue_id]
                if file.exists():
                    file.unlink()

    def update(
        self,
        gl_issue: Union["RESTObject", dict[str, Any]],
        remove: Callable[[Issue], bool],
    ) -> None:
        """
        Update the gl_issue state in cache.

        Write as file or if remove retruns True, remove it from dict and disk.

        Args:
            gl_issue: The gitlab issue to put in cache
            remove: Callable, if True, will remove the issue from cache

        """
        data = gl_issue if isinstance(gl_issue, dict) else gl_issue.attributes
        content = json.dumps(data, option=json.OPT_INDENT_2)
        try:
            issue = self._converter(content)
        except ValidationError:
            logger.exception(f"Failed to convert issue: {content.decode()}")
            raise
        file = self._issue_cache_file(issue.id)
        if remove(issue):
            if issue.id in self._cache:
                del self._cache[issue.id]
            if file.exists():
                file.unlink()
            del issue
            del content
        else:
            file.write_bytes(content)
            self._cache[issue.id] = (get_file_cache_info(file), issue)

    @property
    def last_updated(self) -> datetime | None:
        """
        Return the time the last issue was updated or none if no issues are loaded.
        """
        if self._cache:
            return max(issue.updated_at for _, issue in self._cache.values())
        return None

    @classmethod
    def _cache_folder(cls) -> Path:
        """Path to cache folder, ensuring existence."""
        cache_folder = settings.cache_dir() / "issues"
        cache_folder.mkdir(parents=True, exist_ok=True)
        return cache_folder

    @classmethod
    def _issue_cache_file(cls, issue_id: IssueID) -> Path:
        """Path to Cache file of the given issue."""
        return cls._cache_folder() / cls.file_name.format(issue_id=issue_id)

    @classmethod
    def _load_from_file(cls, elm: IssueID | Path) -> tuple[FileCacheInfo, Issue]:
        """Load the given issue by ID or Path."""
        if isinstance(elm, Path):
            file = elm
        else:
            file = cls._issue_cache_file(elm)
            if not file.exists():
                raise KeyError(elm)
        cache_info = get_file_cache_info(file)
        issue = cls._converter(file.read_bytes())
        return cache_info, issue

    @classmethod
    def _load_cache_files(cls) -> Iterable[tuple[IssueID, tuple[FileCacheInfo, Issue]]]:
        """
        Load all existing cache files.

        Intended only for initial loading when initialising the class
        """
        for path in cls._cache_folder().glob(cls.file_name.format(issue_id="*")):
            cache_info, issue = cls._load_from_file(path)
            yield issue.id, (cache_info, issue)

    def clean(self) -> None:
        """Clean the cache in memory and on disk."""
        self._cache.clear()
        for file in self._cache_folder().glob(self.file_name.format(issue_id="*")):
            file.unlink()
