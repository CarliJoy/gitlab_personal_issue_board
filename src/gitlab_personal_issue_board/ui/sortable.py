"""
Sortable column using sortable.js.

based on https://github.com/itworkedlastime/nicegui-sortable-column
and https://github.com/zauberzeug/nicegui/discussions/3830#discussioncomment-10963832
"""

import contextlib
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Final, Literal, Protocol, TypeVar

from nicegui import app, events, ui

type ElementID = int

DROP_HANDLE: Final[str] = "drop_handle"
DEFAULT_GROUP: Final[str] = "default_sortable_group"
T = TypeVar("T", bound=ui.element)

app.add_static_file(
    local_file=Path(__file__).parent / "Sortable.min.js", url_path="/js/Sortable.min.js"
)


class OnChange(Protocol):
    def __call__(
        self,
        source: "SortableColumn",
        target: ui.element,
        card: ui.element,
        index: int,
    ) -> None: ...


class OnChangeId(Protocol):
    async def __call__(
        self, element_id: ElementID, new_place: ElementID, new_list: ElementID
    ) -> None: ...


class SortableColumn(ui.element, component="sortable_column.js"):
    def __init__(
        self,
        name: str,
        *,
        on_change: OnChange | None = None,
        on_change_id: OnChangeId | None = None,
        group: str = DEFAULT_GROUP,
    ) -> None:
        super().__init__()
        self.classes.append("row")
        self.classes.append("nicegui-row")
        self.classes.append("no-wrapped")
        self.name = name
        self.on("item-drop", self.drop)
        self.on_change = on_change
        self.on_change_id = on_change_id
        self._props["group"] = group

    def update_position(
        self, element_id: ElementID, new_place: int, new_list: ElementID
    ) -> None:
        """Correct the position of element_id within new_list in new_place."""
        element = self.client.elements[element_id]
        target = self.client.elements[new_list]
        element.move(target, new_place)

    async def drop(self, e: events.GenericEventArguments) -> None:
        element_id = int(e.args["id"])
        new_index = int(e.args["new_index"])
        new_list = int(e.args["new_list"])
        self.update_position(element_id, new_index, new_list)
        if self.on_change_id:
            await self.on_change_id(element_id, new_index, new_list)
        if self.on_change:
            self.on_change(
                self,
                self.client.elements[new_list],
                self.client.elements[element_id],
                new_index,
            )

    def cards(self, typ: type[T]) -> Iterable[T]:
        for element in self.default_slot.children:
            if isinstance(element, typ):
                yield element

    def __str__(self) -> str:
        return self.name


class MoveableCard(ui.card):
    def __init__(
        self,
        name: str | None = None,
        align_items: Literal["start", "end", "center", "baseline", "stretch"]
        | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, align_items=align_items, **kwargs)
        self.name: str = name or ""
        self._classes.append(DROP_HANDLE)
        if name is not None:
            with self:
                ui.label(name)

    def __str__(self) -> str:
        return self.name


class SortableExample:
    @contextlib.contextmanager
    @staticmethod
    def sortable_column(
        name: str, on_change: OnChange | None = None, group: str = DEFAULT_GROUP
    ) -> Generator[tuple[ui.column, SortableColumn], None, None]:
        with ui.column(wrap=True).classes(
            "bg-blue-grey-2 w-60 p-4 rounded shadow-2"
        ) as outer_column:
            ui.label(name).classes("text-bold ml-1")

            with SortableColumn(name, on_change=on_change, group=group) as column:
                column.classes("p-4 w-60")
                yield outer_column, column

            ui.label(str(column.id))

    @classmethod
    def refresh(cls) -> None:
        cls.draw.refresh()

    @classmethod
    @ui.refreshable
    def draw(cls) -> None:
        ui.button("reset").on_click(cls.refresh)

        def on_change(
            source: SortableColumn, target: ui.element, card: ui.element, index: int
        ) -> None:
            print(f"Moved {card} in {source} to {target} ({index})")
            update_label()

        c1: SortableColumn
        c2: SortableColumn

        with ui.row():
            with cls.sortable_column("1er", on_change=on_change) as (_, c1):
                for i in range(10):
                    MoveableCard(f"Card {i}")

            with cls.sortable_column("10er", on_change=on_change) as (_, c2):
                for i in range(10):
                    MoveableCard(f"Card {i}0")

        c1_label = ui.label("1er:")
        c2_label = ui.label("10er:")

        def update_label() -> None:
            c1_label.text = (
                f"1er: {', '.join(f"'{card}'" for card in c1.cards(MoveableCard))}"
            )
            c2_label.text = (
                f"10er: {', '.join(f"'{card}'" for card in c2.cards(MoveableCard))}"
            )

        update_label()

    @classmethod
    def run(cls) -> None:
        cls.draw()  # type: ignore[call-arg]
        ui.run()


if __name__ == "__mp_main__":
    SortableExample.run()

if __name__ == "__main__":
    SortableExample.run()
