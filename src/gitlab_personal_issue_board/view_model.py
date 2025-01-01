"""
Handling the interaction between Models and UI using our controller
"""

import contextlib
import types
from collections.abc import Callable, Generator, Mapping
from copy import deepcopy

from nicegui import run, ui

from . import controller, gitlab, models
from .data import boards
from .ui import sortable

type ElementID = int


class LabelView(ui.html):
    _tooltip: ui.tooltip

    def __init__(self, label: models.Label) -> None:
        super().__init__(label.name)
        self.label = label
        self.classes.append("rounded-full")
        self.tailwind.padding("px-2")
        with self:
            self._tooltip = ui.tooltip(label.description or "")
        self.update_properties()

    def update_properties(self) -> None:
        self.style["background-color"] = self.label.color
        self.style["color"] = self.label.text_color
        self.content = self.label.name
        self._tooltip.text = self.label.description or ""


class LabelIssueCard(sortable.MoveableCard):
    def __init__(self, issue: models.Issue) -> None:
        super().__init__()
        self.issue = deepcopy(issue)

        with self:
            self.tailwind.width("full")
            self.tailwind.padding("p-0.5")
            self.header = ui.link(issue.title, issue.web_url, new_tab=True)
            with ui.row() as label_row:
                self.label_row = label_row
                self.label_row_elements = tuple(
                    LabelView(label) for label in issue.labels
                )
            self.reference = ui.label(issue.references.full)

    def refresh(self, issue: models.Issue) -> None:
        if issue != self.issue:
            self.issue = issue
            self.set_content()

    def set_content(self) -> None:
        self.header.props["text"] = self.issue.title
        self.header.props["target"] = self.issue.web_url
        # any missmatch in labels, regenerate labels
        if len(self.label_row_elements) != len(self.issue.labels) or any(
            label_view.label != label
            for label_view, label in zip(
                self.label_row_elements, self.issue.labels, strict=False
            )
        ):
            for label_view in self.label_row_elements:
                label_view.delete()

            with self.label_row:
                self.label_row_elements = tuple(
                    LabelView(label) for label in self.issue.labels
                )
        self.reference.set_text(self.issue.references.full)


class LabelColumn(ui.column):
    """Render a column with sortable Labels inside"""

    def __init__(self, card: models.LabelCard, parent_board: "LabelBoard") -> None:
        self.card = card
        self.parent_board = parent_board
        super().__init__(wrap=False)

        with self.classes("bg-blue-grey-2 rounded shadow-2"):
            with ui.row():
                if card.label == "opened":
                    self.header = ui.html("Opened")
                elif card.label == "closed":
                    self.header = ui.html("Closed")
                else:
                    self.header = LabelView(card.label)
                self.count_label = ui.label("")
                self.set_count_label()
            self.tailwind.height("full")
            self.tailwind.padding("p-0")
            self.tailwind.width("96")
            with ui.scroll_area() as area:
                area.tailwind.height("full")
                area.tailwind.width("96")
                with sortable.SortableColumn(
                    name=str(self.card), on_change_id=self._update_position
                ) as card_column:
                    self.card_column = card_column
                    card_column.style("width: 22rem")
                    card_column.tailwind.padding("p-0")

    def set_count_label(self) -> None:
        self.count_label.text = f" ({len(self.card.issues)})"

    def refresh_card_by_ui(self) -> None:
        """Set the card state from the UI state"""
        self.card = self.card.evolve(
            [card.issue.id for card in self.card_column.cards(LabelIssueCard)]
        )
        self.set_count_label()

    def _update_position(
        self, element_id: ElementID, new_place: int, new_list: ElementID
    ) -> None:
        self.refresh_card_by_ui()
        if self.id != new_list:
            self.parent_board.id2column[new_list].refresh_card_by_ui()
        self.parent_board.update_and_save()

    def __str__(self) -> str:
        return f"<Label Column {self.id} {self.card}>"


class ColumnCardUpdater:
    """
    This is an Helper to update/refresh the ui with the current data from gitlab

    Unfortunately we can't use ui.refreshable as it doesn't mix with sortable.
    It leads too high CPU load in the browser and makes it hard to identify the
    correct element to move thing to.

    It is intended to be used as a context manager
    """

    def __init__(self) -> None:
        # an issue could appear in multiple columns
        self._issues_cards: dict[tuple[models.IssueID, ElementID], LabelIssueCard] = {}

    @contextlib.contextmanager
    def __call__(
        self, issues: gitlab.Issues
    ) -> Generator[Callable[[LabelColumn], None]]:
        used_issued_cards: set[ElementID] = set()

        def update_column(column: LabelColumn) -> None:
            """
            Set the correct label cards for the given *column*
            """

            def get_or_create(issue_id: models.IssueID) -> LabelIssueCard:
                """
                Return an existing LabelIssueCard or create a new one
                """
                try:
                    issue_card = self._issues_cards[(issue_id, column.id)]
                except KeyError:
                    # Issue card not found create a new on
                    issue_card = LabelIssueCard(issues[issue_id])
                    self._issues_cards[(issue_id, column.id)] = issue_card
                else:
                    # update Existing issue crd
                    issue_card.refresh(issues[issue_id])

                used_issued_cards.add(issue_card.id)
                return issue_card

            with column.card_column:
                issue_cards: list[ui.element] = [
                    get_or_create(issue_id) for issue_id in column.card.issues
                ]
                if issue_cards == column.card_column.default_slot.children:
                    print(f"{column} is up to date")
                else:
                    print(f"{column} needs updating new Issues: {column.card.issues}")
                    column.card_column.default_slot.children = issue_cards
                    column.card_column.update()

        yield update_column

        # remove unused cards
        card_id2key = {card.id: k for k, card in self._issues_cards.items()}
        unused_cards = set(card_id2key.keys()) - used_issued_cards
        for unused_card in unused_cards:
            self._issues_cards[card_id2key[unused_card]].delete()
            del self._issues_cards[card_id2key[unused_card]]


class LabelBoard(ui.element):
    columns: tuple[LabelColumn, ...]
    id2column: Mapping[ElementID, LabelColumn]
    issues: gitlab.Issues

    def __init__(self, board: models.LabelBoard, issues: gitlab.Issues) -> None:
        super().__init__()
        sorted_cards = controller.sort_issues_in_cards_by_label(
            tuple(issues.values()), board.cards
        )
        self.board = board.evolve(*sorted_cards)
        self.issues = issues
        self.id2column = {}
        self._updater = ColumnCardUpdater()

        with self:
            self.tailwind.height("screen")
            self.top_row = ui.row(wrap=False)
            with self.top_row:
                self.top_row.tailwind.width("full")
                self.top_row.tailwind.padding("p-4")
                ui.button("Refresh", on_click=self.refresh)

            self.card_row = ui.row(wrap=False)
            with self.card_row:
                self.card_row.tailwind.height("full")
                self.card_row.tailwind.width("screen")
                self.columns = tuple(
                    LabelColumn(card, self) for card in self.board.cards
                )

                # empty column at the end in order to prevent some view bug
                ui.column().tailwind.width("1")
        self.id2column = types.MappingProxyType(
            {column.id: column for column in self.columns}
            | {column.card_column.id: column for column in self.columns}
        )

        print(f"{self.id} Init Update start")
        self.update_cards()
        print(f"{self.id} Init Update end")

    @property
    def column_cards(self) -> tuple[models.LabelCard, ...]:
        """Cards as display by the ui"""
        return tuple(column.card for column in self.columns)

    def update_cards(self) -> None:
        with self._updater(self.issues) as update:
            for column in self.columns:
                update(column)

    async def refresh(self) -> None:
        ui.notify(
            "Starting to load new issues from gitlab", position="center", type="info"
        )
        print("Start Refresh")
        await run.io_bound(self.issues.refresh)
        print("Loaded issues")
        sorted_cards = controller.sort_issues_in_cards_by_label(
            tuple(self.issues.values()), self.column_cards
        )
        self.board = self.board.evolve(*sorted_cards)
        for column, card in zip(self.columns, self.board.cards, strict=True):
            column.card = card
        self.update_cards()
        print("Finished refreshing")
        ui.notify("Refreshed Cards", position="center", type="positive")

    def update_and_save(self) -> None:
        """
        Save current state of the board as shown the UI
        """
        self.board = self.board.evolve(*self.column_cards)
        boards.save_label_board(self.board)
