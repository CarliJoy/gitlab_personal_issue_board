import uuid
from datetime import datetime
from typing import Literal, NewType

from pydantic import BaseModel, ConfigDict, Field

IssueID = NewType("IssueID", int)
UserID = NewType("UserID", int)


class User(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UserID
    username: str
    name: str
    avatar_url: str


class Label(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    text_color: str
    color: str
    description: str | None = None


class Reference(BaseModel):
    model_config = ConfigDict(frozen=True)
    short: str
    full: str


class Issue(BaseModel):
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


class CardDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: Label | Literal["opened", "closed"]


class Card(CardDefinition):
    issues: tuple[IssueID, ...]


class Board(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_config = ConfigDict(frozen=True)
    name: str
    cards: tuple[Card, ...]
