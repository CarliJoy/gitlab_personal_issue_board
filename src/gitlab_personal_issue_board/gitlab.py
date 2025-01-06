"""
Handling data loading/updates from/to gitlab.
"""

import functools
import getpass
import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Literal

import gitlab

from gitlab_personal_issue_board import caching, models, settings

logger = logging.getLogger(__name__)


@functools.cache
def get_gitlab() -> gitlab.Gitlab:
    config = settings.load_settings()
    return gitlab.Gitlab.from_config(gitlab_id=config.gitlab.config_section)


@functools.cache
def get_gitlab_user() -> models.User:
    gl = get_gitlab()
    try:
        gl.auth()
    except Exception as e:
        logger.error(
            f"Failed to authenticate to Gitlab. Fallback to login user. "
            f"Error was: {type(e).__name__}: {e}"
        )
        username = getpass.getuser()
        return models.User(
            username=username, id=models.UserID(-1), name=username, avatar_url=""
        )
    if gl.user is None:
        raise RuntimeError("Could not determine GitLab user")
    return models.User.model_validate(gl.user.attributes)


def not_assigned_to_me(issue: models.Issue) -> bool:
    """
    Return True if the given issue is not assigned to the user holding the connection
    """
    assigned_to_me = any(
        assignee.username == get_gitlab_user().username for assignee in issue.assignees
    )
    return not assigned_to_me


class Issues:
    """
    Handles issues assigned to a user
    """

    #: time the issues were last retrieved from gitlab
    _last_updated: datetime | None

    def __init__(self) -> None:
        self._gl = get_gitlab()
        self._cache = caching.IssueCacheDict()
        self._cache.remove(not_assigned_to_me)
        # initialized with the last time the cache was updated
        # currently this is the time the last issues was updated.
        # TODO: Change it to the last time refresh was executed
        self._last_updated = self._cache.last_updated

    def assign_new_labels(
        self,
        issue: models.Issue,
        new_label: models.Label | Literal["opened", "closed"],
        old_labels: Iterable[models.Label],
    ) -> None:
        """
        Assign *issue* with *new_label* while removing *old_labels*
        """
        # can only retreive single issues from project not from complese instance
        gl_project = self._gl.projects.get(issue.project_id)
        project_labels: dict[str, dict[str, Any]] = {
            label.name: label.attributes
            for label in gl_project.labels.list(get_all=True)
        }
        gl_issue = gl_project.issues.get(issue.iid)
        old_label_names = {label.name for label in old_labels}
        new_labels = set(gl_issue.labels) - old_label_names
        if isinstance(new_label, models.Label):
            # handle adding a real new label
            new_labels |= {new_label.name}
            if new_label.name not in project_labels:
                new_label_data = new_label.model_dump()
                gl_project.labels.create(new_label_data)
                project_labels[new_label.name] = new_label_data
        if new_label == "closed":
            if gl_issue.state != "closed":
                # close issues that need to be closed
                gl_issue.state_event = "close"
        elif gl_issue.state == "closed":
            # reopen closed issue if moved from closed
            gl_issue.state_event = "reopen"
        gl_issue.labels = sorted(new_labels)
        new_issue: dict[str, Any] = gl_issue.save() or {}
        if not new_issue:
            return
        # replace the label names with label attributes
        new_issue["labels"] = [
            project_labels[label] for label in tuple(new_issue["labels"])
        ]
        self._cache.update(new_issue, not_assigned_to_me)

    def __getitem__(self, item: models.IssueID) -> models.Issue:
        return self._cache[item]

    def __len__(self) -> int:
        return len(self._cache)

    def values(self) -> Iterable[models.Issue]:
        yield from self._cache.values()

    def keys(self) -> tuple[models.IssueID, ...]:
        return self._cache.keys()

    def refresh(self) -> str | Literal[True]:
        """
        Refresh data from gitlab

        Return True is success else return the error message
        """
        self._cache.refresh_from_disk()
        start = datetime.now(UTC)
        try:
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
        except Exception as e:
            msg = f"Failed to refresh issues: {type(e).__name__}: {e}"
            logger.warning(msg)
            return msg
        self._last_updated = start
        return True
