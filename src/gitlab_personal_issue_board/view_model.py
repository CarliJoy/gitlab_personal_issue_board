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


class LabelIssueCard(sortable.MoveableCard):
    def __init__(self, issue: models.Issue) -> None:
        super().__init__()
        self.issue = issue


class LabelColumnOuter(ui.column):
    """Render a column with sortable Labels inside"""

    def __init__(self, card: models.LabelCard, parent_board: "LabelBoard") -> None:
        self.card = card
        self.parent_board = parent_board
        super().__init__(wrap=True)

        with self.classes("bg-blue-grey-2 w-60 p-4 rounded shadow-2"):
            ui.label(str(card)).classes("text-bold ml-1")
            self.inner = LabelColumnInner(self)

    def refresh_card_by_ui(self) -> None:
        self.inner.refresh_card_by_ui()


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
            for issue_id in self.card.issues:
                issue_card = LabelIssueCard(self.parent_board.issues[issue_id])
                self.parent_board.issue_cards[issue_card.id] = issue_card

    def update_position(
        self, element_id: ElementID, new_place: ElementID, new_list: ElementID
    ) -> None:
        super().update_position(element_id, new_place, new_list)
        self.refresh_card_by_ui()
        if self.id != new_list:
            self.parent_board.cards[new_list].refresh_card_by_ui()
        self.parent_board.update_and_save()

    def refresh_card_by_ui(self) -> None:
        """Set the card state"""
        self.card = self.card.evolve(
            [card.issue.id for card in self.cards(LabelIssueCard)]
        )


class LabelBoard(ui.row):
    cards: Mapping[ElementID, LabelColumnOuter]
    card_order: tuple[ElementID, ...]
    issues: gitlab.Issues
    issue_cards: dict[ElementID, LabelIssueCard]

    def __init__(self, board: models.LabelBoard, issues: gitlab.Issues) -> None:
        super().__init__()
        sorted_cards = controller.sort_issues_in_cards_by_label(
            tuple(issues.values()), board.cards
        )
        self.board = board.evolve(*sorted_cards)
        self.issues = issues

        cards: dict[ElementID, LabelColumnOuter] = {}
        card_order: list[ElementID] = []
        with self:
            for card in self.board.cards:
                label_card = LabelColumnOuter(card, self)
                cards[label_card.id] = label_card
                card_order.append(label_card.id)

        self.cards = MappingProxyType(cards)
        self.card_order = tuple(card_order)

    def update_and_save(self) -> None:
        """
        Save current state of the board as shown the UI
        """
        self.board = self.board.evolve(
            *[self.cards[element].card for element in self.card_order]
        )
        boards.save_label_board(self.board)
