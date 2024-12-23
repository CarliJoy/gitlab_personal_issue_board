from typing import Callable, Optional, Protocol
from dataclasses import dataclass

from nicegui import ui


class Item(Protocol):
    title: str


dragged: Optional["Card"] = None


class Column(ui.column):

    def __init__(self, name: str, on_drop: Optional[Callable[[Item, str], None]] = None) -> None:
        super().__init__()
        with self.classes('bg-blue-grey-2 w-60 p-4 rounded shadow-2'):
            ui.label(name).classes('text-bold ml-1')
        self.name = name
        self.on('dragover.prevent', self.highlight)
        self.on('dragleave', self.unhighlight)
        self.on('drop', self.move_card)
        self.on_drop = on_drop

    def highlight(self) -> None:
        self.classes(remove='bg-blue-grey-2', add='bg-blue-grey-3')

    def unhighlight(self) -> None:
        self.classes(remove='bg-blue-grey-3', add='bg-blue-grey-2')

    def move_card(self) -> None:
        global dragged  # pylint: disable=global-statement # noqa: PLW0603
        self.unhighlight()
        dragged.parent_slot.parent.remove(dragged)
        with self:
            Card(dragged.item)
        self.on_drop(dragged.item, self.name)
        dragged = None


class Card(ui.card):

    def __init__(self, item: Item) -> None:
        super().__init__()
        self.item = item
        with self.props('draggable').classes('w-full cursor-pointer bg-grey-1'):
            ui.label(item.title)
        self.on('dragstart', self.handle_dragstart)

    def handle_dragstart(self) -> None:
        global dragged  # pylint: disable=global-statement # noqa: PLW0603
        dragged = self


@dataclass
class ToDo:
    title: str


def handle_drop(todo: ToDo, location: str):
    ui.notify(f'"{todo.title}" is now in {location}')


with ui.row():
    with Column('Next', on_drop=handle_drop):
        Card(ToDo('1 Simplify Layouting'))
        Card(ToDo('2 Provide Deployment'))
    with Column('Doing', on_drop=handle_drop):
        Card(ToDo('3 Improve Documentation'))
    with Column('Done', on_drop=handle_drop):
        Card(ToDo('4 Invent NiceGUI'))
        Card(ToDo('5 Test in own Projects'))
        Card(ToDo('6 Publish as Open Source'))
        Card(ToDo('7 Release Native-Mode'))

if __name__ in {"__main__", "__mp_main__"}:
    ui.run()