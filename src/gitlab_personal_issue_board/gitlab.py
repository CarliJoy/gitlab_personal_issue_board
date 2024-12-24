import functools
import logging
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

import gitlab
import orjson as json
from pydantic import ValidationError

from . import settings
from .file_cache import FileCacheInfo, get_file_cache_info
from .models import Issue, IssueID, User

if TYPE_CHECKING:
    from gitlab.base import RESTObject


logger = logging.getLogger(__name__)


@functools.cache
def get_gitlab() -> gitlab.Gitlab:
    config = settings.load_settings()
    return gitlab.Gitlab.from_config(gitlab_id=config.gitlab.config_section)


@functools.cache
def get_gitlab_user() -> User:
    gl = get_gitlab()
    gl.auth()
    if gl.user is None:
        raise RuntimeError("Could not determine GitLab user")
    return User.model_validate(gl.user.attributes)


class IssueCacheDict:
    """
    A dictionary holding all issues

    It caches the full issue attributes but only returns `Issue` objects.
    It automatically reloads Issues if the cache file is updated.
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

    def values(self) -> Iterable[Issue]:
        for _, issue in self._cache.values():
            yield issue

    def keys(self) -> tuple[IssueID, ...]:
        return tuple(self._cache.keys())

    def refresh_from_disk(self) -> None:
        for elm in self._cache.keys():
            self._refresh_item(elm)

    def update(self, gl_issue: "RESTObject", remove: Callable[[Issue], bool]) -> None:
        """
        Update the gl_issue state in cache.

        Write in as file or if remove resolve into True, remove it

        Args:
            gl_issue: The gitlab issue to put in cache
            remove: Callable, if True, will remove the issue from cache

        """
        content = json.dumps(gl_issue.attributes, option=json.OPT_INDENT_2)
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
        """Path to cache folder, ensuring existence"""
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
        """Load all existing cache file"""
        for path in cls._cache_folder().glob(cls.file_name.format(issue_id="*")):
            cache_info, issue = cls._load_from_file(path)
            yield issue.id, (cache_info, issue)

    def clean(self) -> None:
        """Clean the cache"""
        self._cache.clear()
        for file in self._cache_folder().glob(self.file_name.format(issue_id="*")):
            file.unlink()


def not_assigned_to_me(issue: Issue) -> bool:
    """
    Return True if the given issue is not assigned to the user holding the connection
    """
    return all(assignee.id == get_gitlab_user().id for assignee in issue.assignees)


class Issues:
    """
    Handles issues assigned to a user
    """

    _last_updated: datetime | None

    def __init__(self) -> None:
        self._gl = get_gitlab()
        self._cache = IssueCacheDict()
        self._last_updated = self._cache.last_updated

    def values(self) -> Iterable[Issue]:
        yield from self._cache.values()

    def keys(self) -> tuple[IssueID, ...]:
        return self._cache.keys()

    def refresh(self) -> None:
        self._cache.refresh_from_disk()
        start = datetime.now(UTC)
        if self._last_updated:
            # we already have some issues inside the cache
            # so new changed issues could have been unassigned,
            # so we need to load all changed issues to account for this
            for issue in self._gl.issues.list(
                iterator=True,
                scope="all",
                updated_after=self._last_updated,
                with_labels_details=True,
            ):
                self._cache.update(issue, remove=not_assigned_to_me)
        else:
            for issue in self._gl.issues.list(
                iterator=True, scope="assigned_to_me", with_labels_details=True
            ):
                # we know that the issues are assigned to me, no more checks needd
                self._cache.update(issue, remove=lambda _: False)
        self._last_updated = start
