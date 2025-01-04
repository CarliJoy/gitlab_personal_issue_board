import pytest
from pydantic import ValidationError

from gitlab_personal_issue_board.models import (
    Label,
    LabelBoard,
    LabelBoardID,
    LabelCard,
)

from .conftest import gen_label_card_data


def test_label_board_multiple_labels() -> None:
    """
    Duplicated definitions of labels raise a ValidationError.
    """
    data = {
        "name": "test",
        "cards": [
            gen_label_card_data("opened"),
            gen_label_card_data("label_fabel"),
            gen_label_card_data("label_fabel"),
            gen_label_card_data("label_fabel"),
            gen_label_card_data("closed"),
        ],
    }

    with pytest.raises(ValidationError, match=".*duplicate.*label_fabel.*3x.*") as e:
        LabelBoard.model_validate(data)

    print(e.value)
    assert e.value.error_count() == 1


def test_label_board_closed_must_last() -> None:
    """If closed is not last raise a ValdiationError."""
    data = {
        "name": "test",
        "cards": [
            gen_label_card_data("foo"),
            gen_label_card_data("label_fabel"),
            gen_label_card_data("closed"),
            gen_label_card_data("a_label"),
        ],
    }

    with pytest.raises(ValidationError, match=".*closed.*only.*last.*") as e:
        LabelBoard.model_validate(data)

    print(e.value)
    assert e.value.error_count() == 1


def test_label_board_closed_must_first() -> None:
    """If closed is not last raise a ValdiationError."""
    data = {
        "name": "test",
        "cards": [
            gen_label_card_data("foo"),
            gen_label_card_data("opened"),
            gen_label_card_data("label_fabel"),
            gen_label_card_data("a_label"),
        ],
    }

    with pytest.raises(ValidationError, match=".*opened.*only.*first.*") as e:
        LabelBoard.model_validate(data)

    print(e.value)
    assert e.value.error_count() == 1


def test_valid_board() -> None:
    """
    If nothing a duplicated and closed/opened are last the board is parsed and valid
    """
    data = {
        "name": "test",
        "cards": [
            gen_label_card_data("opened"),
            gen_label_card_data("foo"),
            gen_label_card_data("label_fabel"),
            gen_label_card_data("closed"),
        ],
    }

    board = LabelBoard.model_validate(data)
    assert board.cards[0].is_opened
    assert isinstance(board.cards[1].label, Label)
    assert board.cards[1].label.name == "foo"
    assert isinstance(board.cards[2].label, Label)
    assert board.cards[2].label.name == "label_fabel"
    assert board.cards[3].is_closed


def test_label_card_deduplication() -> None:
    """
    Duplicated issue ids are removed, first occurrence is kept
    """
    data = {"label": "opened", "issues": [1, 2, 3, 4, 1, 2, 3, 5, 6, 4, 3, 7]}
    obj = LabelCard.model_validate(data)

    assert obj.issues == (1, 2, 3, 4, 5, 6, 7)


def test_label_board_with_no_cards() -> None:
    """
    Properties has_opened and has_closed return False for empty LabelBoards
    """
    board = LabelBoard(id=LabelBoardID("fake"), name="fake", cards=())
    assert board.has_opened is False
    assert board.has_closed is False
