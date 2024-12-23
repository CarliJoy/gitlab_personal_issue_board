from typing import Callable, Optional, Final
from pprint import pprint
from nicegui import ui
from nicegui.events import GenericEventArguments

DROP_HANDLE: Final[str] = "drop_handle"

class SortableColumn(ui.element, component='sortable_column.js', default_classes='nicegui-column'):

    def __init__(self, name: str, *, on_change: Optional[Callable] = None, group:str = None) -> None:
        super().__init__()
        self.name = name
        with self.classes('bg-blue-grey-2 w-60 p-4 rounded shadow-2'):
            ui.label(name).classes('text-bold ml-1')
        self.on('item-drop', self.drop)
        self.on_change = on_change
        self._items: list[int] = []
        self._props['group'] = group

    def update_position(self, element_id: int, new_place: int, new_list: int):
        """
        Correct the position of element_id within new_list in new_place
        """

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

    async def drop(self, e) -> None:
        element_id = e.args["id"]
        new_index = e.args["new_index"]
        new_list = e.args["new_list"]
        self.update_position(element_id, new_index, new_list)
        if self.on_change:
            self.on_change(self, self.client.elements[new_list], self.client.elements[element_id], new_index)
        else:
            print(e)

class MoveableCard(ui.card):
    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name: str = name
        self._classes.append(DROP_HANDLE)
        with self:
            ui.label(name)


def on_change(source: SortableColumn, target: SortableColumn, card: MoveableCard, index: int) -> None:
    print(f"Moved {card.name} in {source.name} to {target.name} ({index})")

def refresh():
    draw.refresh()

@ui.refreshable
def draw():
    ui.button('reset').on_click(refresh)
    with ui.row():
        with SortableColumn("1er", on_change=on_change,group='test') as c1:
            for i in range(10):
                MoveableCard(f"Card {i}")

            with ui.card():
                ui.label(f"Fixed Card")
            ui.label(c1.id)

        with SortableColumn("10er", on_change=on_change,group='test') as c2:
            for i in range(10):
                MoveableCard(f"Card {i}0")
            with ui.card():
                ui.label(f"Fixed Card")
            ui.label(c2.id)

draw()

ui.run()