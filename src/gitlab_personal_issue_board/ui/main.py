from typing import TypeVar

import click
from nicegui import run, ui

from gitlab_personal_issue_board import data, gitlab, models, settings, view_model
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


T = TypeVar("T", bound=click.Command)


def no_wrap_help(command: T) -> T:
    """Decorator to disable wrapping in help text for a click.Command."""

    class NoWrapFormatter(click.HelpFormatter):
        def write_text(self, text: str) -> None:
            if text:
                self.write_paragraph()
                self.write(text)
                self.write_paragraph()

    class NoWrapContext(click.Context):
        def make_formatter(self) -> click.HelpFormatter:
            return NoWrapFormatter(width=1000)

    # Patch the command's context class
    command.context_class = NoWrapContext
    return command


@no_wrap_help
@click.command(
    epilog="The gitlab access needs to be configured as described here:\n"
    "https://python-gitlab.readthedocs.io/en/stable/cli-usage.html#configuration-file-format"
)
@click.option(
    "--reload",
    help="Reload UI in case source file changes (for development)",
    is_flag=True,
)
@click.option(
    "--show/--background",
    help="Open in browser or start UI in background",
    is_flag=True,
    default=True,
    show_default=True,
)
def start_ui(reload: bool, show: bool) -> None:
    """
    Start board web view containing all personal gitlab issues.
    """
    settings.debug_settings()
    ui.run(title="GL Personal Board", show=show, reload=reload)


if __name__ == "__mp_main__":
    start_ui()

if __name__ == "__main__":
    start_ui()
