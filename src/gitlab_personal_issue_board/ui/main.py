from collections.abc import Callable

from nicegui import ui

from gitlab_personal_issue_board import data, gitlab, models, view_model


def navigate_to(url: str, new_tab: bool = False) -> Callable[[], None]:
    def _do_navigate() -> None:
        ui.navigate.to(url, new_tab=new_tab)

    return _do_navigate


@ui.page("/")
def main() -> None:
    boards = data.load_label_boards()
    with ui.list().props("bordered separator"):
        ui.separator()
        ui.item_label("Boards").props("header").classes("text-bold text-center")
        for board in boards:
            with ui.item(on_click=navigate_to(f"/boards/{board.id}")):
                with ui.item_section().props("avatar"):
                    ui.icon("developer_board")
                with ui.item_section():
                    ui.item_label(board.name)
                    ui.item_label(board.id).props("caption")
                with ui.item_section().props("side"):
                    ui.icon("label")
        with ui.item(on_click=navigate_to("/new_board")):
            with ui.item_section().props("avatar"):
                ui.icon("add")
            with ui.item_section():
                ui.item_label("Add new label board")
            with ui.item_section().props("side"):
                ui.icon("label")


@ui.page("/boards/{board_id:str}")
def board(board_id: models.LabelBoardID) -> None:
    board = data.load_label_board(board_id)
    issues = gitlab.Issues()
    view_model.LabelBoard(board, issues=issues)


@ui.page("/new_board")
def new_board() -> None:
    ui.label("New board")


def start_ui() -> None:
    ui.run(title="GL Personal Board", show=False, reload=True)


if __name__ == "__mp_main__":
    start_ui()

if __name__ == "__main__":
    start_ui()
