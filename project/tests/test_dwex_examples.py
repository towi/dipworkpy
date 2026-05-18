"""Every .dwex example is automatically a regression test for conflict_game."""
from pathlib import Path

import pytest

from dipworkpy.conflict_game import conflict_game
from dipworkpy.tools.dwex.lang import parse_file
from dipworkpy.tools.dwex.to_situation import to_expected, to_situation


LEGACY_FIELD_ALIASES = {"CHN"}

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


def test_dwex_examples_do_not_use_legacy_field_aliases() -> None:
    used_fields: set[str] = set()
    for path in DWEX_ROOT.rglob("*.dwex"):
        doc = parse_file(path)
        used_fields.update(field.name for field in doc.fields)
        used_fields.update(edge.a for edge in doc.edges)
        used_fields.update(edge.b for edge in doc.edges)
        used_fields.update(unit.current for unit in doc.units)
        used_fields.update(order.current for order in doc.orders)
        used_fields.update(order.dest for order in doc.orders if order.dest)
        used_fields.update(doc.expected_pattfields)

    assert used_fields.isdisjoint(LEGACY_FIELD_ALIASES)
