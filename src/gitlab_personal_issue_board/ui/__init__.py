from collections.abc import Callable

from nicegui import ui


def navigate_to(url: str, new_tab: bool = False) -> Callable[[], None]:
    def _do_navigate() -> None:
        ui.navigate.to(url, new_tab=new_tab)

    return _do_navigate
