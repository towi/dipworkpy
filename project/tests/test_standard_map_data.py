"""Smoke-test the bundled standard.json - structural sanity only."""

import hashlib
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "dipworkpy/geography/map/data/standard.json"
STANDARD_JSON_SHA256 = "ef58466d2eaa6dc31733cb42ec60bfc40557f0d3a57d224e7377c7b2aa96b8c7"


def test_standard_json_exists():
    assert DATA.exists(), f"missing {DATA}"


def test_standard_json_parses():
    with open(DATA) as f:
        m = json.load(f)
    assert "fields" in m
    assert "units" in m


def test_standard_json_snapshot_hash():
    with open(DATA) as f:
        m = json.load(f)
    canonical = json.dumps(m, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == STANDARD_JSON_SHA256


def test_standard_has_all_34_supply_centers():
    with open(DATA) as f:
        m = json.load(f)
    sc_count = sum(1 for f in m["fields"].values() if f.get("is_supply_center"))
    assert sc_count == 34, f"expected 34 supply centers, got {sc_count}"


def test_standard_has_subfields_for_split_coasts():
    with open(DATA) as f:
        m = json.load(f)
    fields = m["fields"]
    for sup, subs in [("Spa", ["SpN", "SpS"]), ("Pet", ["PeN", "PeS"]), ("Bul", ["BuE", "BuS"])]:
        assert sup in fields, f"missing superfield {sup}"
        for sub in subs:
            assert sub in fields, f"missing subfield {sub}"
            assert fields[sub]["sub_of"] == sup


def test_standard_fields_have_local_borders_and_neighbor_order():
    with open(DATA) as f:
        m = json.load(f)
    for field_name, field in m["fields"].items():
        assert "borders" in field, f"missing borders on {field_name}"
        assert "neighbor_order" in field, f"missing neighbor_order on {field_name}"
        assert isinstance(field["borders"], dict)
        assert isinstance(field["neighbor_order"], list)


def test_standard_borders_use_unit_grammar():
    with open(DATA) as f:
        m = json.load(f)
    for field_name, field in m["fields"].items():
        for neighbor, units in field["borders"].items():
            assert neighbor in m["fields"], f"bad border {field_name}:{neighbor}"
            assert set(units) <= {"A", "F", "$convoy"}, f"bad units on {field_name}:{neighbor}: {units!r}"
