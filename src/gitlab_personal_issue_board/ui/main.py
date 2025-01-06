from nicegui import run, ui

from gitlab_personal_issue_board import data, gitlab, models, view_model
from gitlab_personal_issue_board.ui import navigate_to


def new_board() -> None:
    board = models.LabelBoard(name="", cards=())
    data.save_label_board(board)
    ui.navigate.to(f"/boards/{board.id}/edit")


issues = gitlab.Issues()


@ui.page("/")
def main() -> None:
    boards = data.load_label_boards()
    with ui.list().props("bordered separator"):
        ui.separator()
        ui.item_label("Boards").props("header").classes("text-bold text-center")
        for board in boards:
            with ui.item(on_click=navigate_to(board.view_link)):
                with ui.item_section().props("avatar"):
                    ui.icon("developer_board")
                with ui.item_section():
                    ui.item_label(board.name)
                    ui.item_label(board.id).props("caption")
                with ui.item_section().props("side"):
                    ui.icon("label")
        with ui.item(on_click=new_board):
            with ui.item_section().props("avatar"):
                ui.icon("add")
            with ui.item_section():
                ui.item_label("Add new label board")
            with ui.item_section().props("side"):
                ui.icon("label")


@ui.page("/boards/{board_id:str}/view")
def view_board(board_id: models.LabelBoardID) -> None:
    board = data.load_label_board(board_id)
    view_model.LabelBoard(board, issues=issues)


@ui.page("/boards/{board_id:str}/edit")
async def edit_board(board_id: models.LabelBoardID) -> None:
    board = data.load_label_board(board_id)
    spinner = ui.spinner()
    spinner.tailwind.align_self("center")
    res = await run.io_bound(issues.refresh)
    if isinstance(res, str):
        ui.notify(res, type="warning")
    spinner.delete()
    view_model.BoardConfiguration(board, issues=issues)


def start_ui(reload: bool = False) -> None:
    ui.run(title="GL Personal Board", show=not reload, reload=reload)


if __name__ == "__mp_main__":
    start_ui(reload=True)

if __name__ == "__main__":
    start_ui(reload=True)
