from pathlib import Path

from .. import models, settings


def _label_board_path(board: models.LabelBoard | models.LabelBoardID | Path) -> Path:
    if isinstance(board, Path):
        return board
    board_id = board.id if isinstance(board, models.LabelBoard) else board
    return settings.data_dir() / f"label_board_{board_id}.json"


def save_label_board(board: models.LabelBoard) -> None:
    target = _label_board_path(board)
    target.write_text(board.model_dump_json())


def load_label_board(
    board: models.LabelBoard | models.LabelBoardID | Path,
) -> models.LabelBoard:
    source = _label_board_path(board)
    return models.LabelBoard.model_validate_json(source.read_text())
