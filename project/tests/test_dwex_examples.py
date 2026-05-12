"""Every .dwex example is automatically a regression test for conflict_game."""
from pathlib import Path

import pytest

from dipworkpy.conflict_game import conflict_game
from dipworkpy.tools.dwex.lang import parse_file
from dipworkpy.tools.dwex.to_situation import to_expected, to_situation

DWEX_ROOT = Path(__file__).resolve().parent.parent / "doc/examples/dwex"


def _ids(p: Path) -> str:
    return p.stem


@pytest.mark.parametrize(
    "path",
    sorted(DWEX_ROOT.rglob("*.dwex")),
    ids=_ids,
)
def test_dwex_example_runs_clean(path: Path) -> None:
    doc = parse_file(path)
    sit = to_situation(doc)
    expected = to_expected(doc)
    result = conflict_game(sit)
    assert result <= expected, (
        f"{path.stem}: result mismatch\n"
        f"expected: {expected.__log__()}\n"
        f"actual:   {result.__log__()}"
    )
