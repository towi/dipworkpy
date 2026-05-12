"""Smoke-test the bundled standard.json - structural sanity only."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "dipworkpy/geography/map/data/standard.json"


def test_standard_json_exists():
    assert DATA.exists(), f"missing {DATA}"


def test_standard_json_parses():
    with open(DATA) as f:
        m = json.load(f)
    assert "fields" in m
    assert "edges" in m


def test_standard_has_all_34_supply_centers():
    with open(DATA) as f:
        m = json.load(f)
    sc_count = sum(1 for f in m["fields"].values() if f.get("is_supply_center"))
    assert sc_count == 34, f"expected 34 supply centers, got {sc_count}"


def test_standard_has_subfields_for_split_coasts():
    with open(DATA) as f:
        m = json.load(f)
    fields = m["fields"]
    for sup, subs in [("Spa", ["SpN", "SpS"]), ("Pet", ["PeN", "PeS"]),
                      ("Bul", ["BuE", "BuS"])]:
        assert sup in fields, f"missing superfield {sup}"
        for sub in subs:
            assert sub in fields, f"missing subfield {sub}"
            assert fields[sub]["sub_of"] == sup


def test_standard_edges_use_passable_grammar():
    with open(DATA) as f:
        m = json.load(f)
    valid_passable = {"ja", "nein", "-", "imp"}
    for edge_key, e in m["edges"].items():
        for k in ["army", "fleet", "convoy_move"]:
            v = e[k]
            # Either a Passable string, or a subfield name (coast-required)
            assert v in valid_passable or (isinstance(v, str) and len(v) <= 4), \
                f"bad {k} on {edge_key}: {v!r}"
