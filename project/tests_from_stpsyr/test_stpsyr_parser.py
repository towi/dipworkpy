import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dipworkpy.model import OrderType
from stpsyr_test_runner import StpsyrTestRunner

BASE = os.path.dirname(os.path.abspath(__file__))


def _parse(name):
    return StpsyrTestRunner().parse_file(os.path.join(BASE, name))


def test_case_counts_match_parseable_cases():
    # 93 headers on disk; 6.b case 14 is a header-only TODO stub.
    expected = {
        "datc-6.a.txt": 12,
        "datc-6.b.txt": 12,
        "datc-6.c.txt": 7,
        "datc-6.d.txt": 33,
        "datc-6.e.txt": 15,
        "datc-6.f.txt": 13,
    }
    for fname, count in expected.items():
        cases = _parse(fname)
        assert len(cases) == count, f"{fname}: {len(cases)} != {count}"


def test_multiphase_case_is_split():
    # 6.a case 5 "Move to own sector with convoy": 2 movement phases
    cases = _parse("datc-6.a.txt")
    case5 = next(c for c in cases if c.number == 5)
    assert len(case5.phases) == 2
    assert len(case5.phases[0].orders) == 4
    assert len(case5.phases[1].orders) == 5


def test_msup_dest_is_supported_units_start():
    # "tyr S ven-tri" -> msup with dest=Ven (unit start), NOT Tri
    cases = _parse("datc-6.a.txt")
    case5 = next(c for c in cases if c.number == 5)
    msups = [o for p in case5.phases for o in p.orders if o.order == OrderType.msup]
    assert any(o.current == "Tyr" and o.dest == "Ven" for o in msups), msups


def test_explicit_hold_H_notation():
    # datc-6.d.txt contains '    A tri H' style holds (e.g. line 161)
    cases = _parse("datc-6.d.txt")
    holds = [o for c in cases for p in c.phases for o in p.orders if o.order == OrderType.hld]
    assert holds, "explicit 'X H' holds must parse as hld, not vanish"


def test_coast_suffix_collapses_to_superfield():
    r = StpsyrTestRunner()
    assert r.parse_territory_name("spa/nc") == "Spa"
    assert r.parse_territory_name("spa/sc") == "Spa"
    assert r.parse_territory_name("bul/ec") == "Bul"
    assert r.parse_territory_name("stp/sc") == "Pet"


def test_canonical_renames():
    r = StpsyrTestRunner()
    assert r.parse_territory_name("lvp") == "Lpl"
    assert r.parse_territory_name("sev") == "Seb"
    assert r.parse_territory_name("stp") == "Pet"
    assert r.parse_territory_name("mao") == "MID"
    assert r.parse_territory_name("nao") == "NAT"
    assert r.parse_territory_name("nwg") == "NWS"
    assert r.parse_territory_name("nwy") == "Nor"
    assert r.parse_territory_name("bal") == "BAS"
    assert r.parse_territory_name("lyo") == "LYO"
    assert r.parse_territory_name("aeg") == "AEG"


def test_builds_and_disbands_parsed():
    cases = _parse("datc-6.e.txt")
    with_disband = [c for c in cases if any(p.disbands for p in c.phases)]
    assert with_disband, "expected at least one case with 'D hel'"
    d = next(p for c in with_disband for p in c.phases if p.disbands)
    assert d.disbands == ["HEL"]
