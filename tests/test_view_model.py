import pytest

from gitlab_personal_issue_board import view_model


@pytest.mark.parametrize(
    "got, expected", [("#FFFFFF", "black"), ("#000000", "white"), ("#1a5c60", "white")]
)
def test_get_background_color(got: str, expected: str) -> None:
    """white for dark font and black for light font colors"""
    got = view_model.get_background_color(got)

    assert got == expected
