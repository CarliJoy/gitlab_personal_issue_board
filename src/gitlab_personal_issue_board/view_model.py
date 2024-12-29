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


class LabelColumnOuter(ui.column):
    """Render a column with sortable Labels inside"""

    def __init__(self, card: models.LabelCard, parent_board: "LabelBoard") -> None:
        self.card = card
        self.parent_board = parent_board
        super().__init__(wrap=False)

        with self.classes("bg-blue-grey-2 rounded shadow-2"):
            if card.label == "opened":
                self.header = ui.html("Opened")
            elif card.label == "closed":
                self.header = ui.html("Closed")
            else:
                self.header = LabelView(card.label)
            self.tailwind.height("full")
            self.tailwind.padding("p-0")
            self.tailwind.width("96")
            with ui.scroll_area() as area:
                area.tailwind.height("full")
                area.tailwind.width("96")
                self.inner = LabelColumnInner(self)  # row


class LabelColumnInner(sortable.SortableColumn):
    @property
    def parent_board(self) -> "LabelBoard":
        return self.outer.parent_board

    @property
    def card(self) -> models.LabelCard:
        return self.outer.card

    @card.setter
    def card(self, value: models.LabelCard) -> None:
        self.outer.card = value

    def __init__(self, outer: LabelColumnOuter) -> None:
        self.outer = outer
        super().__init__(name=str(self.card))

        with self:
            self.style("width: 22rem")
            self.tailwind.padding("p-0")
            for issue_id in self.card.issues:
                issue_card = LabelIssueCard(self.parent_board.issues[issue_id])
                self.parent_board.issue_cards[issue_card.id] = issue_card

    def update_position(
        self, element_id: ElementID, new_place: ElementID, new_list: ElementID
    ) -> None:
        super().update_position(element_id, new_place, new_list)
        self.refresh_card_by_ui()
        if self.id != new_list:
            self.parent_board.inner_cards[new_list].refresh_card_by_ui()
        self.parent_board.update_and_save()

    def refresh_card_by_ui(self) -> None:
        """Set the card state"""
        self.card = self.card.evolve(
            [card.issue.id for card in self.cards(LabelIssueCard)]
        )


class LabelBoard(ui.row):
    cards: Mapping[ElementID, LabelColumnOuter]
    inner_cards: Mapping[ElementID, LabelColumnInner]
    card_order: tuple[ElementID, ...]
    issues: gitlab.Issues
    issue_cards: dict[ElementID, LabelIssueCard]

    def __init__(self, board: models.LabelBoard, issues: gitlab.Issues) -> None:
        super().__init__(wrap=False)
        sorted_cards = controller.sort_issues_in_cards_by_label(
            tuple(issues.values()), board.cards
        )
        self.board = board.evolve(*sorted_cards)
        self.issue_cards = {}
        self.issues = issues

        cards: dict[ElementID, LabelColumnOuter] = {}
        inner_cards: dict[ElementID, LabelColumnInner] = {}
        card_order: list[ElementID] = []
        with self:
            self.tailwind.height("screen")
            for card in self.board.cards:
                label_card = LabelColumnOuter(card, self)
                cards[label_card.id] = label_card
                inner_card = label_card.inner
                inner_cards[inner_card.id] = inner_card
                card_order.append(label_card.id)
            # empty column at the end in order to prevent some view bug
            ui.column().tailwind.width("1")

        self.cards = MappingProxyType(cards)
        self.inner_cards = MappingProxyType(inner_cards)
        self.card_order = tuple(card_order)

    def update_and_save(self) -> None:
        """
        Save current state of the board as shown the UI
        """
        self.board = self.board.evolve(
            *[self.cards[element].card for element in self.card_order]
        )
        boards.save_label_board(self.board)
