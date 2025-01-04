import uuid
from collections.abc import Container, Iterable, Mapping
from datetime import datetime
from itertools import chain
from typing import TYPE_CHECKING, Annotated, Literal, NewType, assert_never

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from .model_validators import uniq, validate_label_cards

IssueID = NewType("IssueID", int)
UserID = NewType("UserID", int)
LabelBoardID = NewType("LabelBoardID", str)


class User(BaseModel):
    """A gitlab user"""

    model_config = ConfigDict(frozen=True)
    id: UserID
    username: str
    name: str
    avatar_url: str


class Label(BaseModel):
    """A gitlab label"""

    model_config = ConfigDict(frozen=True)
    name: str
    text_color: str
    color: str
    description: str | None = None

    def __str__(self) -> str:
        return f"Label ~{self.name}"


class Reference(BaseModel):
    """A gitlab issue reference"""

    model_config = ConfigDict(frozen=True)
    short: str
    full: str


class Issue(BaseModel):
    """A gitlab issue"""

    model_config = ConfigDict(frozen=True)
    id: IssueID
    title: str
    description: str | None = None
    iid: int
    labels: tuple[Label, ...]
    assignees: tuple[User, ...]
    created_at: datetime
    updated_at: datetime
    references: Reference
    project_id: int
    web_url: str
    state: Literal["opened", "closed"]
    due_at: datetime | None = None


class LabelCard(BaseModel):
    """A card for issues defined by labels"""

    model_config = ConfigDict(frozen=True)
    label: Label | Literal["opened", "closed"]
    issues: Annotated[tuple[IssueID, ...], AfterValidator(uniq)]

    @property
    def is_opened(self) -> bool:
        return self.label == "opened"

    @property
    def is_closed(self) -> bool:
        return self.label == "closed"

    @property
    def is_label(self) -> bool:
        return isinstance(self.label, Label)

    def valid(self, issue: Issue, distributed_issues: Container[IssueID]) -> bool:
        """
        Return True if the given issue is a valid on for this card

        See *filter_issues_by_label*
        """
        if isinstance(self.label, Label):
            return issue.state != "closed" and any(
                label.name == self.label.name for label in issue.labels
            )
        elif self.label == "opened":
            return issue.state == "opened" and issue.id not in distributed_issues
        elif self.label == "closed":
            return issue.state == "closed"
        else:  # pragma: no cover
            assert_never(issue.state)

    def filtered_issues(
        self,
        gitlab_issues: Mapping[IssueID, Issue],
        distributed_issues: Container[IssueID],
    ) -> Iterable[IssueID]:
        """
        Return list of *self.issues* that belong to this card.

        Any not IssueID of issues that is not part of gitlab_issues is excluded.
        Only issues are return for which the self.label the issue's label.

        If label is `opened` all issues are excluded that are part of
          *distributed_issues* are excluded as well.

        Args:
            gitlab_issues: Issues received from gitlab
            distributed_issues: IDs of issues already distributed to any card
        """

        for issue_id in self.issues:
            if (issue := gitlab_issues.get(issue_id)) and self.valid(
                issue, distributed_issues
            ):
                yield issue.id

    def evolve(self, *issues: Iterable[IssueID]) -> "LabelCard":
        """
        Create a new LabelCard the new *issues* given based on existing label

        If issues haven't changed return self
        """
        new_issues = tuple(chain(*issues))
        if self.issues == new_issues:
            del new_issues
            return self
        return LabelCard(label=self.label, issues=new_issues)

    def __str__(self) -> str:
        return f"Label Card {self.label}"


class LabelBoard(BaseModel):
    """
    A board of issues that is defined by the labels (or state) of the issues

    This is the same definition of a board as in gitlab.
    """

    model_config = ConfigDict(frozen=True)
    id: LabelBoardID = Field(default_factory=lambda: LabelBoardID(str(uuid.uuid4())))
    name: str
    cards: Annotated[tuple[LabelCard, ...], AfterValidator(validate_label_cards)]

    @property
    def card_labels(self) -> tuple[Label, ...]:
        labels: Iterable[Label | str] = (card.label for card in self.cards)
        return tuple(label for label in labels if isinstance(label, Label))

    @property
    def has_opened(self) -> bool:
        return bool(self.cards) and self.cards[0].is_opened

    @property
    def has_closed(self) -> bool:
        return bool(self.cards) and self.cards[-1].is_closed

    @property
    def edit_link(self) -> str:
        return f"/boards/{self.id}/edit"

    @property
    def view_link(self) -> str:
        return f"/boards/{self.id}/view"

    def evolve(self, *cards: LabelCard) -> "LabelBoard":
        return LabelBoard(id=self.id, name=self.name, cards=cards)


if TYPE_CHECKING:
    from .model_validators import CardLike

    # Ensure that CardLike is actually a protocol for LabelCard
    foo: CardLike = LabelCard(label="opened", issues=())
