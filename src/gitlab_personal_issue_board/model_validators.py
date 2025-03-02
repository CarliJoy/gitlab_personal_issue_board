from collections import Counter
from collections.abc import Collection, Iterable
from typing import Any, Literal, Protocol


class CardLike(Protocol):
    """Anything like *models.LabelCard*"""

    @property
    def is_opened(self) -> bool: ...

    @property
    def is_closed(self) -> bool: ...

    label: Any


def validate_label_cards(
    label_cards: Collection[CardLike],
) -> Collection[CardLike]:
    """
    Ensure each label is only applied once. Open is always first,
    """
    length = len(label_cards)

    def check_valid_open_closed(i: int, card: CardLike) -> Literal[True]:
        if card.is_opened and i != 0:
            raise ValueError("The 'opened' card can only be the first card.")
        if card.is_closed and i != length - 1:
            raise ValueError("The 'closed' card can only be the last card.")
        return True

    label_counter = Counter(
        str(card.label)
        for i, card in enumerate(label_cards)
        if check_valid_open_closed(i, card)
    )
    duplicates = tuple(
        f"{card} ({count}x)" for card, count in label_counter.items() if count > 1
    )
    if duplicates:
        raise ValueError(f"There are duplicate cards for {', '.join(duplicates)}")
    return label_cards


def uniq[T](elements: Iterable[T]) -> tuple[T, ...]:
    """
    Deduplicate iterable, keeping only the first occurrence of each element.

    Returns:
        tuple: with deduplicated *elements*

    Example:
        >>> uniq([1, 2, 3, 4, 1, 2, 5])
        (1, 2, 3, 4, 5)
    """
    seen: set[T] = set()

    def was_seen(elem: T) -> bool:
        if elem in seen:
            return True
        seen.add(elem)
        return False

    return tuple(elem for elem in elements if not was_seen(elem))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
