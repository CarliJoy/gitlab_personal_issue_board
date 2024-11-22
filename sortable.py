from typing import Callable, Optional, Final
from pprint import pprint
from nicegui import ui
from nicegui.events import GenericEventArguments

DROP_HANDLE: Final[str] = "drop_handle"

class SortableColumn(ui.element, component='sortable_column.js', default_classes='nicegui-column'):

    def __init__(self, name: str, *, on_change: Optional[Callable] = None, group:str = None) -> None:
        super().__init__()
        with self.classes('bg-blue-grey-2 w-60 p-4 rounded shadow-2'):
            ui.label(name).classes('text-bold ml-1')
        self.on('item-drop', self.drop)
        # self.on('drop', self.ddrop)
        self.on_change = on_change
        self._items: list[int] = []
        self._props['group'] = group

    async def drop(self, e) -> None:
        if self.on_change:
            await self.on_change(self, e, self.client.elements[e.args["id"]])
        else:
            print(e)

    async def ddrop(self, e) -> None:
        print(e)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._items = [item.id  for item in self.default_slot.children  if isinstance(item, MoveableCard)]
        super().__exit__(exc_type, exc_val, exc_tb)

class MoveableCard(ui.card):
    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name: str = name
        self._classes.append(DROP_HANDLE)
        with self:
            ui.label(name)


async def on_change(col: SortableColumn, e: GenericEventArguments, card: MoveableCard):
    print(f"Moved {card.name}")
    print(e)
    pprint(e.args)

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