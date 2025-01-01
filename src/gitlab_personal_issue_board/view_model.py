"""
Handling the interaction between Models and UI using our controller
"""

import types
from collections.abc import Mapping
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
        self._label_views: dict[models.Label, LabelView] = {}
        self.label_row_elements: tuple[LabelView, ...] = ()

        with self:
            # init issue card
            self.tailwind.width("full")
            self.tailwind.padding("p-0.5")
            self.header = ui.link(issue.title, issue.web_url, new_tab=True)
            self.label_row = ui.row()
            self.update_label_row()
            self.reference = ui.label(issue.references.full)

    def refresh(self, issue: models.Issue) -> None:
        if issue != self.issue:
            self.issue = issue
            self.set_content()

    def _get_or_create_label_view(self, label: models.Label) -> LabelView:
        try:
            return self._label_views[label]
        except KeyError:
            self._label_views[label] = LabelView(label)
            return self._label_views[label]

    def update_label_row(self) -> None:
        # any missmatch in labels, regenerate labels
        if len(self.label_row_elements) != len(self.issue.labels) or any(
            label_view.label != label
            for label_view, label in zip(
                self.label_row_elements, self.issue.labels, strict=True
            )
        ):
            with self:
                with self.label_row:
                    new_label_row = tuple(
                        self._get_or_create_label_view(label)
                        for label in self.issue.labels
                    )
            to_remove = [
                elem
                for elem in self._label_views.values()
                if elem.label not in self.issue.labels
            ]
            for elem in to_remove:
                self.label_row.client.remove_elements(
                    elem.descendants(include_self=True)
                )
                del self._label_views[elem.label]
            self.label_row.default_slot.children = list(new_label_row)
            self.label_row_elements = new_label_row
            self.label_row.update()

    def set_content(self) -> None:
        self.header.props["text"] = self.issue.title
        self.header.props["target"] = self.issue.web_url
        self.update_label_row()
        self.reference.set_text(self.issue.references.full)


class LabelColumn(ui.column):
    """Render a column with sortable Labels inside"""

    def __init__(self, card: models.LabelCard, parent_board: "LabelBoard") -> None:
        self.card = card
        self.parent_board = parent_board
        self._issue_cards: dict[models.IssueID, LabelIssueCard] = {}
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

    def _update_or_create_issue_card(self, issue: models.Issue) -> LabelIssueCard:
        """
        Return an updated existing LabelIssueCard or create a new one
        """
        try:
            issue_card = self._issue_cards[issue.id]
        except KeyError:
            # Issue card not found create a new on
            issue_card = LabelIssueCard(issue)
            self._issue_cards[issue.id] = issue_card
        else:
            # update Existing issue crd
            issue_card.refresh(issue)
        return issue_card

    def update_issue_cards(self) -> None:
        """
        Update/refresh the issue cards with the current data from gitlab

        Unfortunately we can't use ui.refreshable as it doesn't mix with sortable.
        It leads too high CPU load in the browser and makes it hard to identify the
        correct element to move thing to.
        """
        with self.card_column:
            issue_cards: list[ui.element] = [
                self._update_or_create_issue_card(self.parent_board.issues[issue_id])
                for issue_id in self.card.issues
            ]
            if issue_cards != self.card_column.default_slot.children:
                to_remove = set(self.card.issues) - set(self._issue_cards.keys())
                for issue_id in to_remove:
                    element = self._issue_cards[issue_id]
                    # based on element.remove(), but we handle overwriting the
                    # stack children and the update our self
                    self.card_column.client.remove_elements(
                        element.descendants(include_self=True)
                    )
                    del self._issue_cards[issue_id]
                self.card_column.default_slot.children = issue_cards
                self.card_column.update()

    def _update_position(
        self, element_id: ElementID, new_place: int, new_list: ElementID
    ) -> None:
        self.refresh_card_by_ui()
        if self.id != new_list:
            self.parent_board.id2column[new_list].refresh_card_by_ui()
        self.parent_board.update_and_save()

    def __str__(self) -> str:
        return f"<Label Column {self.id} {self.card}>"


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
        for column in self.columns:
            column.update_issue_cards()

    async def refresh(self) -> None:
        ui.notify(
            "Starting to load new issues from gitlab", position="center", type="info"
        )
        await run.io_bound(self.issues.refresh)
        sorted_cards = controller.sort_issues_in_cards_by_label(
            tuple(self.issues.values()), self.column_cards
        )
        self.board = self.board.evolve(*sorted_cards)
        for column, card in zip(self.columns, self.board.cards, strict=True):
            column.card = card
        self.update_cards()
        ui.notify("Refreshed Cards", position="center", type="positive")

    def update_and_save(self) -> None:
        """
        Save current state of the board as shown the UI
        """
        self.board = self.board.evolve(*self.column_cards)
        boards.save_label_board(self.board)
