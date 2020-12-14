# under test
from dipworkpy.dip_eval.eval_k1 import parse_edges


def test_parse_edges_spaces():
    assert parse_edges("Vie--Mun") == [("Vie", "Mun")]
    assert parse_edges("Vie -- Mun") == [("Vie", "Mun")]
    assert parse_edges("Vie  --Mun") == [("Vie", "Mun")]
    assert parse_edges(" Vie  --Mun") == [("Vie", "Mun")]
    assert parse_edges(" Vie  --Mun ") == [("Vie", "Mun")]
    assert parse_edges("Vie-- Mun ") == [("Vie", "Mun")]


def test_parse_edges_empty():
    assert parse_edges("") == []
    assert parse_edges(";") == []
    assert parse_edges(";;") == []
    assert parse_edges("; ;") == []
    assert parse_edges("  ; ;") == []
    assert parse_edges(";   ") == []


def test_parse_edges_trail():
    assert parse_edges("Vie--Mun;") == [("Vie", "Mun")]
    assert parse_edges(";Vie--Mun") == [("Vie", "Mun")]
    assert parse_edges(";Vie--Mun;") == [("Vie", "Mun")]
    assert parse_edges(" ;Vie--Mun;") == [("Vie", "Mun")]
    assert parse_edges(" ;Vie--Mun; ; ") == [("Vie", "Mun")]


def test_parse_edges_list():
    assert parse_edges("Vie--Mun;Kie--NTH") == [("Vie", "Mun"), ("Kie","NTH")]
    assert parse_edges("Vie--Mun;;Kie--NTH") == [("Vie", "Mun"), ("Kie","NTH")]
    assert parse_edges("Vie-- Mun; ;Kie--NTH") == [("Vie", "Mun"), ("Kie","NTH")]
    assert parse_edges("Vie--Mun;Kie-- NTH ;") == [("Vie", "Mun"), ("Kie","NTH")]


def test_parse_edges_inner_spaces():
    # inner spaces are kept exactly. this may change.
    assert parse_edges("Vie Center -- Mun;Kie  Harbour--NTH") == [("Vie Center", "Mun"), ("Kie  Harbour","NTH")]


def test_parse_edges_newlines():
    assert parse_edges("""Vie -- Mun;
       Kie -- NTH ;
    Bel--Par""") == [("Vie", "Mun"), ("Kie","NTH"), ("Bel","Par")]


if __name__ == "__main__":
    import sys
    import pytest
    pytest.main(sys.argv)
