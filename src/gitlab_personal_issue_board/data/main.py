import logging
from collections import Counter
from collections.abc import Iterable

from nicegui import ui

from gitlab_personal_issue_board import gitlab, models, view_model
from gitlab_personal_issue_board.data import boards

"""
      "name": "status::blocked",
      "name": "status::doing",
      "name": "status::done",
      "name": "status::evaluate",
      "name": "status::invalid",
      "name": "status::ready",
      "name": "status::review",
      "name": "status::stale",
      "name": "status::testing",
      "name": "status::unknown",
      "name": "status::waitfrom collections import Countering",
      "name": "status::wontfix",

"""

logger = logging.getLogger(__name__)


def gen_board(issues: gitlab.Issues, label_names: Iterable[str]) -> models.LabelBoard:
    issue_variants: dict[str, Counter[models.Label]] = {}
    for issue in issues.values():
        for label in issue.labels:
            issue_variants.setdefault(label.name, Counter()).update((label,))

    labels: dict[str, models.Label] = {
        label_name: max(counts.keys(), key=counts.get)  # type: ignore[arg-type]
        for label_name, counts in issue_variants.items()
    }

    return models.LabelBoard(
        name="Test status",
        cards=(
            models.LabelCard(label="opened", issues=()),
            *(
                models.LabelCard(label=labels[label], issues=())
                for label in label_names
            ),
            models.LabelCard(
                label="closed",
                issues=(),
            ),
        ),
    )


BOARD_ID = models.LabelBoardID("dc1b6246-4422-4f9a-89dc-6377e4ce3e00")


def main() -> None:
    issues = gitlab.Issues()
    logger.info(f"Loaded {len(issues)} issues")
    print("Load board")
    board = boards.load_label_board(BOARD_ID)
    print("Load LabelBoard")
    view_model.LabelBoard(board, issues=issues)
    print("Finished load label board")
    # ver 71
    ui.run(title="GL Personal Board", show=False)


if __name__ == "__mp_main__":
    main()

if __name__ == "__main__":
    main()
