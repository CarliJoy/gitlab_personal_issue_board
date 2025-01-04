from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Final, Literal

from gitlab_personal_issue_board.models import Issue, LabelCard, User, UserID

FAKE_USER: Final = User(
    id=UserID(0),
    username="FAKE_TEST_USER",
    name="FAKE_TEST_USER",
    avatar_url="https://missing.local/pic.png",
)
FAKE_GITLAB: Final = "https://gitlab.fake.example/"


def gen_label_data(label: str | dict[str, str]) -> str | dict[str, str]:
    if isinstance(label, str):
        if label in {"opened", "closed"}:
            return label
        return {"name": label, "text_color": "black", "color": "white"}
    return label


def gen_label_card_data(
    label: str | Literal["opened", "closed"], issues: Sequence[int] = ()
) -> dict[str, str | dict[str, str] | list[int]]:
    return {
        "label": gen_label_data(label),
        "issues": list(issues),
    }


def gen_label_card(
    label: str | Literal["opened", "closed"], issues: Sequence[int] = ()
) -> LabelCard:
    return LabelCard.model_validate(gen_label_card_data(label, issues))


def gen_issue(
    issue_id: int,
    title: str = "An Issue",
    labels: Iterable[str | dict[str, str]] = (),
    description: str = "Issue Description",
    project: str = "fake/project",
    project_id: int = 123,
    closed: bool = False,
    created_at: datetime = datetime(2024, 12, 12, 3, 12, tzinfo=UTC),
    updated_at: datetime = datetime(2024, 12, 12, 4, 15, tzinfo=UTC),
) -> Issue:
    labels = list(labels)
    if "opened" in labels:
        closed = False
        labels.remove("opened")
    if "closed" in labels:
        closed = True
        labels.remove("closed")
    data = {
        "id": issue_id,
        "title": title,
        "description": description,
        "iid": issue_id,
        "labels": [gen_label_data(label) for label in labels],
        "assignees": [FAKE_USER],
        "created_at": created_at,
        "updated_at": updated_at,
        "references": {
            "short": f"#{issue_id}",
            "full": f"{project}/#{issue_id}",
        },
        "state": "closed" if closed else "opened",
        "project_id": project_id,
        "web_url": f"{FAKE_GITLAB}/{project}/-/issues/{issue_id}",
    }

    return Issue.model_validate(data)


# Test our generator functions


def test_gen_issues_opened() -> None:
    """A label opened ensure the label is opened"""
    assert gen_issue(1, labels=["opened"], closed=True).state == "opened"


def test_gen_issues_closed() -> None:
    """A label closed ensure the label is closed"""
    assert gen_issue(1, labels=["closed"]).state == "closed"
