from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from gitlab_personal_issue_board.models import Issue, LabelCard

from .conftest import gen_issue, gen_label_card

type Label = str
type IssueID = int


@dataclass
class CardLabelTestData:
    name: str
    issues: Sequence[tuple[IssueID, Iterable[Label]]]
    cards: Sequence[Label | tuple[Label, Sequence[IssueID]]]
    expected: Sequence[Label | tuple[Label, Sequence[IssueID]]]

    def __str__(self) -> str:
        return self.name

    @property
    def fake_issues(self) -> tuple[Issue, ...]:
        return tuple(
            gen_issue(issue_id, labels=labels) for issue_id, labels in self.issues
        )

    @property
    def fake_cards(self) -> tuple[LabelCard, ...]:
        return tuple(
            gen_label_card(label)
            if isinstance(label, str)
            else gen_label_card(label[0], label[1])
            for label in self.cards
        )

    @property
    def expected_cards(self) -> tuple[LabelCard, ...]:
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
    )
    fake_cards = test_data.fake_cards
    fake_expected = test_data.expected_cards

    assert fake_cards[1:-1] == fake_expected[1:-1]


# @pytest.mark.parametrize("test_data", [
#     CardLabelTestData(
#         name="unchanged",
#
#     )
# ]
#
# )
#
#
# def test_sort_issues_in_cards_by_labels(test_data: CardLabelTestData) -> None:
#     issues = [gen_issue(issue_data) for issue_data in test_data.issues]
