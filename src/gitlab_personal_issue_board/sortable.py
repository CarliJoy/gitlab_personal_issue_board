from typing import Final, Literal, Protocol

from nicegui import events, ui

DROP_HANDLE: Final[str] = "drop_handle"
DEFAULT_GROUP: Final[str] = "default_sortable_group"


class OnChange(Protocol):
    def __call__(
        self,
        source: "SortableColumn",
        target: ui.element,
        card: ui.element,
        index: int,
    ) -> None: ...


class SortableColumn(
    ui.element, component="sortable_column.js", default_classes="nicegui-column"
):
    def __init__(
        self,
        name: str,
        *,
        on_change: OnChange | None = None,
        group: str = DEFAULT_GROUP,
    ) -> None:
        super().__init__()
        self.name = name
        with self.classes("bg-blue-grey-2 w-60 p-4 rounded shadow-2"):
            ui.label(name).classes("text-bold ml-1")
        self.on("item-drop", self.drop)
        self.on_change = on_change
        self._items: list[int] = []
        self._props["group"] = group

    def update_position(self, element_id: int, new_place: int, new_list: int) -> None:
        """Correct the position of element_id within new_list in new_place."""
        element = self.client.elements[element_id]

        # Remove the element from the current position
        self.default_slot.children.remove(element)

        if new_list == self.id:
            # Insert the element into the new position
            self.default_slot.children.insert(new_place, element)
        else:
            # Move the dragged element to new outer element
            target = self.client.elements[new_list]
            element.parent_slot = target.default_slot
            target.default_slot.children.insert(new_place, element)
            target.update()

        # Trigger re-rendering of the UI
        self.update()

    async def drop(self, e: events.GenericEventArguments) -> None:
        element_id = int(e.args["id"])
        new_index = int(e.args["new_index"])
        new_list = int(e.args["new_list"])
        self.update_position(element_id, new_index, new_list)
        if self.on_change:
            self.on_change(
                self,
                self.client.elements[new_list],
                self.client.elements[element_id],
                new_index,
            )
        else:
            print(e)

    def __str__(self) -> str:
        return self.name


class MoveableCard(ui.card):
    def __init__(
        self,
        name: str,
        align_items: Literal["start", "end", "center", "baseline", "stretch"]
        | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, align_items=align_items, **kwargs)
        self.name: str = name
        self._classes.append(DROP_HANDLE)
        with self:
            ui.label(name)


def on_change(
    source: SortableColumn, target: ui.element, card: ui.element, index: int
) -> None:
    print(f"Moved {card} in {source} to {target} ({index})")


def refresh() -> None:
    draw.refresh()


@ui.refreshable
def draw() -> None:
    ui.button("reset").on_click(refresh)
    with ui.row():
        with SortableColumn("1er", on_change=on_change, group="test") as c1:
            for i in range(10):
                MoveableCard(f"Card {i}")

            with ui.card():
                ui.label("Fixed Card")
            ui.label(str(c1.id))

        with SortableColumn("10er", on_change=on_change, group="test") as c2:
            for i in range(10):
                MoveableCard(f"Card {i}0")
            with ui.card():
                ui.label("Fixed Card")
            ui.label(str(c2.id))


def run() -> None:
    draw()
    ui.run()


if __name__ == "__mp_main__":
    run()

if __name__ == "__main__":
    run()
