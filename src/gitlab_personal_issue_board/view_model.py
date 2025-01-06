"""
Handling the interaction between Models and UI using our controller
"""

import contextlib
import functools
import types
from collections.abc import Iterable, Mapping
from copy import deepcopy

from nicegui import run, ui

from gitlab_personal_issue_board import controller, data, gitlab, models
from gitlab_personal_issue_board.ui import navigate_to, sortable

type ElementID = int


def html_to_rgb(color: str) -> tuple[int, int, int]:
    # based on: https://stackoverflow.com/questions/29643352/converting-hex-to-rgb-value-in-python
    h = color.strip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore


@functools.cache
def get_background_color(color: str) -> str:
    # based on https://stackoverflow.com/questions/9780632/how-do-i-determine-if-a-color-is-closer-to-white-or-black
    if color.startswith("#"):
        with contextlib.suppress(Exception):
            r, g, b = html_to_rgb(color)
            y = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if y < 128:
                return "white"
    return "black"


class LabelView(ui.html):
    _tooltip: ui.tooltip

    def __init__(self, label: models.Label) -> None:
        super().__init__(label.name)
        self.label = label
        self.classes.append("rounded-full")
        self.style["display"] = "inline-flex"
        self.style["overflow"] = "hidden"
        self.style["border-color"] = self.label.color
        self.style["border-width"] = ".25rem"
        self.tailwind.font_size("sm")
        with self:
            self._tooltip = ui.tooltip(label.description or "")
        self.update_properties()

    def update_properties(self) -> None:
        self.style["background-color"] = self.label.color
        self.style["color"] = self.label.text_color
        if "::" in self.label.name:
            l1, _, l2 = self.label.name.partition("::")
            background = get_background_color(self.label.text_color)
            self.style["background-color"] = background
            self.content = (
                f"<span style='background-color:{self.label.color};"
                f"  padding: .125rem .25rem .125rem .25rem'>{l1}</span>"
                f"<span style='padding: .125rem .5rem .125rem .25rem; "
                f"  overflow: hidden;display: inline-block;'>{l2}</span>"
            )
        else:
            self.tailwind.padding("px-2")
            self.tailwind.padding("py-1")
            self.content = self.label.name
        self._tooltip.text = self.label.description or ""


class LabelIssueCard(sortable.MoveableCard):
    def __init__(self, issue: models.Issue, parent_board: "LabelBoard") -> None:
        super().__init__()
        self.issue = deepcopy(issue)
        self.parent_board = parent_board
        self._label_views: dict[models.Label, LabelView] = {}
        self.label_row_elements: tuple[LabelView, ...] = ()

        with self:
            # init issue card
            self.tailwind.width("full")
            self.tailwind.padding("p-0.5")
            self.header = ui.link(issue.title, issue.web_url, new_tab=True)
            self.label_row = ui.row()
            self.update_label_row()
            with ui.row(wrap=False) as row:
                row.tailwind.align_items("center")
                self.reference = ui.label(issue.references.full)
                btn = ui.button(
                    "", color="green", icon="info", on_click=self.show_details
                )
                btn.tailwind.size("1")

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

    @staticmethod
    def items_section(name: str, value: str) -> None:
        ui.label(f"{name}:")
        ui.label(value).tailwind.font_family("serif")

    def show_details(self) -> None:
        """Show details for issue"""
        dialog = self.parent_board.dialog
        dialog.clear()

        with dialog, ui.card():
            with ui.row():
                ui.link(
                    self.issue.title, target=self.issue.web_url, new_tab=True
                ).tailwind.font_size("xl").drop_shadow("lg")
                ui.label(f"[{self.issue.state}]").tailwind.font_size("lg")

            ui.label(
                f"{self.issue.references.full} (ID: {self.issue.id})"
            ).tailwind.font_size("sm")
            with ui.grid(columns=2) as lst:
                lst.tailwind.space_between("y-0")
                lst.tailwind.padding("p-0")
                self.items_section(
                    "Created at",
                    f"{self.issue.created_at.astimezone():%Y-%m-%d %H:%M:%S}",
                )
                self.items_section(
                    "Last updated",
                    f"{self.issue.updated_at.astimezone():%Y-%m-%d %H:%M:%S}",
                )
                if self.issue.due_at:
                    self.items_section(
                        "Due at", f"{self.issue.due_at.astimezone():%Y-%m-%d %H:%M:%S}"
                    )
                self.items_section(
                    "Assignees",
                    ", ".join(assignee.username for assignee in self.issue.assignees),
                )
            with ui.card() as desc_card:
                desc_card.tailwind.width("full")
                desc_card.tailwind.background_color("gray-50")
                ui.markdown(self.issue.description or "**EMPTY DESCRIPTION**")
            ui.button("Close", on_click=dialog.close).tailwind.align_self("center")

        dialog.open()


class MoveableLabel(ui.row):
    @property
    def label(self) -> models.Label:
        return self.label_view.label

    def __init__(self, label: models.Label) -> None:
        super().__init__(wrap=False)
        with self:
            self.tailwind.width("full")
            self.tailwind.cursor("grab")
            self.classes(sortable.DROP_HANDLE)
            self.label_view = LabelView(label)


class ActiveBoardLabels(ui.column):
    """
    Configure the active board
    """

    def __init__(self, board: models.LabelBoard) -> None:
        self.board = board

        super().__init__(wrap=False)
        with self.classes("bg-blue-grey-2 rounded shadow-2"):
            self.tailwind.height("full")
            self.tailwind.padding("p-0")
            self.tailwind.width("96")
            self.name = ui.input(
                "Name", placeholder="Name of the Label bord", value=board.name
            )
            with ui.scroll_area() as area:
                area.tailwind.height("full")
                area.tailwind.width("96")
                self.opened = ui.switch("Opened", value=board.has_opened)
                with sortable.SortableColumn(
                    name=f"{self.board.id}_active"
                ) as card_column:
                    self.card_column = card_column
                    card_column.style("width: 22rem")
                    card_column.tailwind.padding("p-0")

                    for label in board.card_labels:
                        MoveableLabel(label)

                self.closed = ui.switch("Closed", value=board.has_opened)

    def save(self) -> None:
        cards: dict[str | str, models.LabelCard] = {
            card.label.name: card
            for card in self.board.cards
            if isinstance(card.label, models.Label)
        }
        new_cards: list[models.LabelCard] = []

        if self.opened.value:
            if self.board.has_opened:
                new_cards.append(self.board.cards[0])
            else:
                new_cards.append(models.LabelCard(label="opened", issues=()))

        for label_view in self.card_column.cards(MoveableLabel):
            if label_view.label.name in cards:
                new_cards.append(cards[label_view.label.name])
            else:
                new_cards.append(models.LabelCard(label=label_view.label, issues=()))

        if self.closed.value:
            if self.board.has_closed:
                new_cards.append(self.board.cards[-1])
            else:
                new_cards.append(models.LabelCard(label="closed", issues=()))

        try:
            new_board = models.LabelBoard(
                id=self.board.id,
                name=self.name.value,
                cards=tuple(new_cards),
            )
            data.save_label_board(new_board)
        except Exception as e:
            ui.notify(f"Could not save board:\n{type(e).__name__}: {e}", type="warning")
        else:
            self.board = new_board
            ui.notify("Saved successfully", type="positive")


class InactiveBoardLabels(ui.column):
    def __init__(
        self, board: models.LabelBoard, labels: Mapping[str, models.Label]
    ) -> None:
        self.labels = labels
        self.active_labels = {label.name for label in board.card_labels}

        super().__init__(wrap=False)
        with self.classes("bg-blue-grey-2 rounded shadow-2"):
            self.tailwind.height("full")
            self.tailwind.padding("p-0")
            self.tailwind.width("96")
            with ui.scroll_area() as area:
                area.tailwind.height("full")
                area.tailwind.width("96")

                with sortable.SortableColumn(name=f"{self.id}_inactive") as card_column:
                    card_column.style("width: 22rem")
                    card_column.tailwind.padding("p-0")

                    for label in sorted(
                        self.labels.values(), key=lambda label: label.name
                    ):
                        if label.name not in self.active_labels:
                            MoveableLabel(label)


class BoardConfiguration(ui.element):
    def __init__(self, board: models.LabelBoard, issues: gitlab.Issues) -> None:
        super().__init__()
        self.board = board
        issues.refresh()
        labels = controller.get_labels_from_issues(issues.values())
        with self:
            self.tailwind.height("screen")
            self.top_row = ui.row(wrap=False)
            with self.top_row:
                self.top_row.tailwind.width("full")
                self.top_row.tailwind.padding("p-4")
                ui.button("Menu", on_click=navigate_to("/"))
                ui.button("Save", on_click=self.save)
                ui.button("Save and view", on_click=self.save_and_view)
                ui.button("Cancel and view", on_click=navigate_to(self.board.view_link))

            self.card_row = ui.row(wrap=False)
            with self.card_row:
                self.card_row.tailwind.height("full")
                self.card_row.tailwind.width("screen")
                self.active = ActiveBoardLabels(board=board)
                self.inactive = InactiveBoardLabels(board=board, labels=labels)
                # empty column at the end in order to prevent some view bug
                ui.column().tailwind.width("1")

    def save(self) -> None:
        self.active.save()

    def save_and_view(self) -> None:
        self.save()
        ui.navigate.to(self.board.view_link)


class LabelColumn(ui.column):
    """Render a column with sortable cards by labels inside"""

    def __init__(self, card: models.LabelCard, parent_board: "LabelBoard") -> None:
        self.card = card
        self.parent_board = parent_board
        self._issue_cards: dict[models.IssueID, LabelIssueCard] = {}
        self._card_ids: dict[ElementID, LabelIssueCard] = {}
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
        for card in self.card_column.cards(LabelIssueCard):
            self._issue_cards[card.issue.id] = card
            self._card_ids[card.id] = card
        self.set_count_label()

    def _update_or_create_issue_card(self, issue: models.Issue) -> LabelIssueCard:
        """
        Return an updated existing LabelIssueCard or create a new one
        """
        try:
            issue_card = self._issue_cards[issue.id]
        except KeyError:
            # Issue card not found create a new on
            issue_card = LabelIssueCard(issue, self.parent_board)
            self._issue_cards[issue.id] = issue_card
            self._card_ids[issue_card.id] = issue_card
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
                    del self._card_ids[element.id]
                    self.card_column.client.remove_elements(
                        element.descendants(include_self=True)
                    )
                    del self._issue_cards[issue_id]
                self.card_column.default_slot.children = issue_cards
                for issue_card in issue_cards:
                    issue_card.parent_slot = self.card_column.default_slot
                self.card_column.update()

    async def update_gl_issue_state(self, element_id: ElementID) -> None:
        card = self._card_ids[element_id]
        await run.io_bound(
            self.parent_board.issues.assign_new_labels,
            card.issue,
            self.card.label,
            self.parent_board.board.card_labels,
        )
        self.parent_board.update_cards()

    async def _update_position(
        self, element_id: ElementID, new_place: int, new_list: ElementID
    ) -> None:
        self.refresh_card_by_ui()
        target = self.parent_board.id2column[new_list]
        if self != target:
            target.refresh_card_by_ui()
            await target.update_gl_issue_state(element_id)
        self.parent_board.update_and_save()

    def __str__(self) -> str:
        return f"<Label Column {self.id} {self.card}>"


class LabelBoard(ui.element):
    columns: tuple[LabelColumn, ...]
    id2column: Mapping[ElementID, LabelColumn]
    issues: gitlab.Issues

    def __init__(self, board: models.LabelBoard, issues: gitlab.Issues) -> None:
        super().__init__()
        self.board = board
        self.issues = issues
        self.dialog = ui.dialog()
        self.id2column = {}

        with self:
            self.tailwind.height("screen")
            self.top_row = ui.row(wrap=False)
            with self.top_row:
                self.top_row.tailwind.width("full")
                self.top_row.tailwind.padding("p-4")
                ui.icon("label")
                ui.label(self.board.name)
                ui.button("Menu", on_click=navigate_to("/"))
                ui.button("Refresh", on_click=self.refresh)
                ui.button("Edit Board", on_click=navigate_to(board.edit_link))

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
        self.update_cards()

    @property
    def card_labels(self) -> tuple[models.Label, ...]:
        labels: Iterable[models.Label | str] = (card.label for card in self.board.cards)
        return tuple(label for label in labels if isinstance(label, models.Label))

    @property
    def column_cards(self) -> tuple[models.LabelCard, ...]:
        """Cards as display by the ui"""
        return tuple(column.card for column in self.columns)

    def update_cards(self) -> None:
        sorted_cards = controller.sort_issues_in_cards_by_label(
            tuple(self.issues.values()), self.column_cards
        )
        self.board = self.board.evolve(*sorted_cards)
        for column, card in zip(self.columns, self.board.cards, strict=True):
            column.card = card
        for column in self.columns:
            column.update_issue_cards()

    async def refresh(self, notify: bool = True) -> None:
        """
        Refresh the UI state from gitlab data
        """
        if notify:
            ui.notify(
                "Starting to load new issues from gitlab",
                position="center",
                type="info",
            )
        res = await run.io_bound(self.issues.refresh)
        if isinstance(res, str):
            self.update_cards()  # Still update the cards
            ui.notify(res, type="warning")
        else:
            self.update_cards()
            if notify:
                ui.notify("Refreshed Cards", position="center", type="positive")

    def update_and_save(self) -> None:
        """
        Save current state of the board as shown the UI
        """
        self.board = self.board.evolve(*self.column_cards)
        data.save_label_board(self.board)


if __name__ in ("__main__", "__mp_main__"):  # pragma: no cover
    # just test how labels look like
    with ui.card():
        LabelView(
            models.Label(name="status::waiting", text_color="#000000", color="red")
        )
        LabelView(models.Label(name="foobar", text_color="#000000", color="red"))

    ui.run()
