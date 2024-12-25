"""
Handling data loading/updates from/to gitlab.
"""

import functools
from collections.abc import Iterable
from datetime import UTC, datetime

import gitlab

from . import settings
from .caching import IssueCacheDict
from .models import Issue, IssueID, User


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


def not_assigned_to_me(issue: Issue) -> bool:
    """
    Return True if the given issue is not assigned to the user holding the connection
    """
    return all(assignee.id == get_gitlab_user().id for assignee in issue.assignees)


class Issues:
    """
    Handles issues assigned to a user
    """

    #: time the issues were last retrieved from gitlab
    _last_updated: datetime | None

    def __init__(self) -> None:
        self._gl = get_gitlab()
        self._cache = IssueCacheDict()
        # initialized with the last time the cache was updated
        # currently this is the time the last issues was updated.
        # TODO: Change it to the last time refresh was executed
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
