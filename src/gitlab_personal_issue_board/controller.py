"""
Buisness Logic (Controller) handling sorting Issues into Cards/Boards
"""

import types
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from .models import Issue, IssueID, Label, LabelCard


def get_labels_from_issues(issues: Iterable[Issue]) -> Mapping[str, Label]:
    """
    Extract Labels from issues

    Returns a Mapping of label name to most occurred label definition.
    """

    issue_variants: dict[str, Counter[Label]] = {}
    for issue in issues:
        for label in issue.labels:
            issue_variants.setdefault(label.name, Counter()).update((label,))

    return types.MappingProxyType(
        {
            label_name: max(counts.keys(), key=counts.get)  # type: ignore[arg-type]
            for label_name, counts in issue_variants.items()
        }
    )


def sort_issues_in_cards_by_label(
    issues: Sequence[Issue], cards: Sequence[LabelCard]
) -> Iterable[LabelCard]:
    """
    Sort *issues* into *cards* as gitlab would do.

    This means:
    - closed issues are sorted into closed card
    - a card with a label contains all issues that have this label, even
      if this mean an issues appears in multiple cards
    - all issues that are not part of

    The sorting of the issues in cards are kept.
    Issues that are newly added to a card a prepended in the order of *issues*.
    """
    if not cards:
        # if no cards are given, then just return an empty tuple
        # as otherwise indexing last and first elements would fail
        return

    id2issue = {issue.id: issue for issue in issues}

    issues_distributed: set[IssueID] = set()

    # create card_issues_old that contain the issue id filtered for the given cards
    # we use iterate in reversed order in order to fill issues_distributed
    # for a potential "opened" card at the beginning.
    card_issues_old: list[list[IssueID]] = []
    for card in reversed(cards):
        issue_ids = list(card.filtered_issues(id2issue, issues_distributed))
        card_issues_old.append(issue_ids)
        issues_distributed = issues_distributed | set(issue_ids)

    # after we have the old issues we need to determine new issue to add
    card_issues_new: list[list[IssueID]] = []
    for card, already_added in zip(reversed(cards), card_issues_old, strict=True):
        to_add: list[IssueID] = [
            issue.id
            for issue in issues
            if issue.id not in already_added and card.valid(issue, issues_distributed)
        ]
        issues_distributed = issues_distributed | set(to_add)
        card_issues_new.append(to_add)

    # the card_issues_* have to be reverted to get the correct order of cards
    for card, issue_old, issue_new in zip(
        cards, reversed(card_issues_old), reversed(card_issues_new), strict=True
    ):
        yield card.evolve(issue_new, issue_old)
