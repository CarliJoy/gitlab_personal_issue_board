"""
Handling the interaction between Models and UI using our controller
"""

from collections.abc import Mapping
from types import MappingProxyType

from nicegui import ui

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
        self.issue = issue

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
                    card_column.style("width: 22rem")
                    card_column.tailwind.padding("p-0")
                    self.create_cards()
                    self.card_column = card_column

    def set_count_label(self) -> None:
        self.count_label.text = f" ({len(self.card.issues)})"

    def refresh_card_by_ui(self) -> None:
        """Set the card state from the UI state"""
        self.card = self.card.evolve(
            [card.issue.id for card in self.card_column.cards(LabelIssueCard)]
        )
        self.set_count_label()

    def _update_position(
        self, element_id: ElementID, new_place: ElementID, new_list: ElementID
    ) -> None:
        self.refresh_card_by_ui()
        if self.id != new_list:
            self.parent_board.id2column[new_list].refresh_card_by_ui()
        self.parent_board.update_and_save()

    @ui.refreshable_method
    def create_cards(self) -> None:
        for issue_id in self.card.issues:
            LabelIssueCard(self.parent_board.issues[issue_id])

    def refresh(self) -> None:
        self.create_cards.refresh()
        self.set_count_label()


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

        self.id2column = MappingProxyType(
            {column.id: column for column in self.columns}
            | {column.card_column.id: column for column in self.columns}
        )

    @property
    def column_cards(self) -> tuple[models.LabelCard, ...]:
        """Cards as display by the ui"""
        return tuple(column.card for column in self.columns)

    def refresh(self) -> None:
        self.issues.refresh()
        sorted_cards = controller.sort_issues_in_cards_by_label(
            tuple(self.issues.values()), self.column_cards
        )
        self.board = self.board.evolve(*sorted_cards)
        for column, card in zip(self.columns, self.board.cards, strict=True):
            column.card = card
            column.refresh()
        ui.notify("Refreshed Cards")

    def update_and_save(self) -> None:
        """
        Save current state of the board as shown the UI
        """
        self.board = self.board.evolve(*self.column_cards)
        boards.save_label_board(self.board)
