from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import pytest

from gitlab_personal_issue_board import controller, models

from .conftest import gen_issue, gen_label_card

type Label = str
type IssueID = int


@dataclass
class CardLabelTestData:
    name: str
    issues: Sequence[tuple[IssueID, Iterable[Label]]]
    cards: Sequence[Label | tuple[Label, Sequence[IssueID]]]
    expected: Sequence[Label | tuple[Label, Sequence[IssueID]]]
    expected_identical: int = 0

    def __str__(self) -> str:
        return self.name

    @property
    def fake_issues(self) -> tuple[models.Issue, ...]:
        return tuple(
            gen_issue(issue_id, labels=labels) for issue_id, labels in self.issues
        )

    @property
    def fake_cards(self) -> tuple[models.LabelCard, ...]:
        return tuple(
            gen_label_card(label)
            if isinstance(label, str)
            else gen_label_card(label[0], label[1])
            for label in self.cards
        )

    @property
    def expected_cards(self) -> tuple[models.LabelCard, ...]:
        return tuple(
            gen_label_card(label)
            if isinstance(label, str)
            else gen_label_card(label[0], label[1])
            for label in self.expected
        )


def test_card_label_test_data_issues() -> None:
    """
    Our Testdate is correctly generated for issues
    """
    test_data = CardLabelTestData(
        name="",
        cards=(),
        issues=[(1, {"foo"}), (2, {"bar"}), (3, {"baz", "closed"})],
        expected=(),
    )
    fake_issues = test_data.fake_issues
    assert fake_issues[0].id == 1
    assert fake_issues[1].id == 2
    assert fake_issues[2].id == 3
    assert fake_issues[0].labels[0].name == "foo"
    assert fake_issues[1].labels[0].name == "bar"
    assert fake_issues[2].labels[0].name == "baz"
    assert fake_issues[0].state == "opened"
    assert fake_issues[1].state == "opened"
    assert fake_issues[2].state == "closed"


def test_card_label_test_data_cards() -> None:
    """
    Our Testdate is correctly generated for cards
    """
    test_data = CardLabelTestData(
        name="",
        issues=(),
        cards=["opened", ("foo", [1, 2]), ("bar", [2, 3]), "empty", ("closed", [4])],
        expected=[("opened", [4]), ("foo", [1, 2]), ("bar", [2, 3]), "empty", "closed"],
        expected_identical=5,
    )
    fake_cards = test_data.fake_cards
    fake_expected = test_data.expected_cards

    assert fake_cards[1:-1] == fake_expected[1:-1]

    assert fake_cards[0].is_opened
    assert fake_cards[-1].is_closed

    assert fake_cards[0].issues == ()
    assert fake_expected[0].issues == (4,)
    assert fake_cards[1].issues == (1, 2)
    assert fake_cards[2].issues == (2, 3)
    assert fake_cards[3].issues == ()
    assert fake_cards[4].issues == (4,)
    assert fake_expected[4].issues == ()

    assert fake_cards[1].label.name == "foo"  # type: ignore[union-attr]
    assert fake_cards[2].label.name == "bar"  # type: ignore[union-attr]
    assert fake_cards[3].label.name == "empty"  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "test_data",
    [
        CardLabelTestData(
            name="all_unchanged",
            issues=[
                (1, {"foo"}),
                (2, {"bar"}),
                (3, {"foo", "closed"}),
                (4, {"baz", "foo", "bar"}),
                (0, {"baz"}),
            ],
            cards=[
                ("opened", [0]),
                ("foo", [1, 4]),
                ("bar", [2, 4]),
                "empty",
                ("closed", [3]),
            ],
            expected=[
                ("opened", [0]),
                ("foo", [1, 4]),
                ("bar", [2, 4]),
                "empty",
                ("closed", [3]),
            ],
            expected_identical=5,
        ),
        CardLabelTestData(
            name="fill_by_issue_order",
            issues=[
                (12, {"foo"}),
                (14, {"foo"}),
                (8, {"foo", "bar"}),
                (10000, {"foo"}),
                (2000, {"bar"}),
                (300, {"foo", "closed"}),
                (40, {"baz", "foo", "bar"}),
                (0, {"baz"}),
            ],
            cards=["opened", "foo", "bar", "empty", "closed"],
            expected=[
                ("opened", [0]),
                ("foo", [12, 14, 8, 10000, 40]),
                ("bar", [8, 2000, 40]),
                "empty",
                ("closed", [300]),
            ],
            expected_identical=1,  # empty isn't changed
        ),
        CardLabelTestData(
            name="prepend_new_issues",
            issues=[
                (8, {"foo", "bar"}),  # new issue
                (10000, {"foo"}),
                (12, {"foo"}),  # new issue
                (2000, {"bar"}),
                (300, {"foo", "closed"}),
                (14, {"foo"}),  # new issue
                (40, {"baz", "foo", "bar"}),
                (0, {"baz"}),
            ],
            cards=[
                ("opened", [0]),
                ("foo", [10000, 40]),
                ("bar", [2000, 40]),
                "empty",
                ("closed", [300]),
            ],
            expected=[
                ("opened", [0]),
                ("foo", [8, 12, 14, 10000, 40]),
                ("bar", [8, 2000, 40]),
                "empty",
                ("closed", [300]),
            ],
            expected_identical=3,  # opened, empty & closed aren't changed
        ),
    ],
    ids=str,
)
def test_sort_issues_in_cards_by_labels(test_data: CardLabelTestData) -> None:
    """
    Our test cases generate the expected cards

    If a card is not changed the same card is returned
    """
    issues = test_data.fake_issues
    cards = test_data.fake_cards
    expected = test_data.expected_cards

    got = tuple(controller.sort_issues_in_cards_by_label(issues, cards))

    assert got == expected

    identical: int = 0
    for card_got, card_before in zip(got, cards, strict=True):
        if card_got.issues == card_before.issues:
            # If issues haven't changed it should be exactly the same object
            assert id(card_got) == id(card_before)
            identical += 1

    assert identical == test_data.expected_identical


def label(name: str, text_color: str = "black", color: str = "white") -> dict[str, str]:
    return {"name": name, "text_color": text_color, "color": color}


def test_get_labels_from_issues() -> None:
    """
    The labels with the most occurrences are selected
    """
    issues = [
        gen_issue(
            3, labels=(label("foo", "red", "black"), label("bar", "red", "black"))
        ),
        gen_issue(1, labels=(label("foo"), label("bar"))),
        gen_issue(2, labels=(label("foo"), label("bar"))),
        gen_issue(
            4, labels=(label("foo", "black", "white"), label("boom", "yellow", "green"))
        ),
    ]

    expected = {
        "foo": models.Label(name="foo", text_color="black", color="white"),
        "bar": models.Label(name="bar", text_color="black", color="white"),
        "boom": models.Label(name="boom", text_color="yellow", color="green"),
    }
    got = controller.get_labels_from_issues(issues)
    assert got == expected
